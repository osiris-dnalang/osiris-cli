"""SYS-021 production grants: the owner's signed approval for one production operation.

The policy is docs/governance/ACTION_18_APPROVAL_AUTHORITY.md. The owner drafts grant.json,
signs it at the node's own terminal, and the operation passes both files to ``authorize``:

    python -m osiris_cli.grants draft --payload-digest <sha256> --scope <scope> > grant.json
    ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n osiris-grant grant.json

``authorize`` lets the operation through only if every check passes. A check that cannot be
made (no ssh-keygen, an unreadable clock, a broken ledger) counts as failed.

1. ``ssh-keygen -Y verify`` accepts grant.json.sig against governance/allowed_signers for the
   principal ``owner`` in the namespace ``osiris-grant``. OpenSSH itself refuses a key that is
   not enrolled, another principal, another namespace and any changed byte.
2. The signed grant names this operation's payload digest and scope.
3. The verifying node's clock reports NTP synchronization, and
   signed_at <= now <= signed_at + expires_s.
4. The ledger holds no AUTHORIZATION_REVOKED or AUTHORIZATION_CONSUMED event for the grant.
   This is checked under the ledger's lock, and AUTHORIZATION_GRANTED and
   AUTHORIZATION_CONSUMED are written before the lock is released, so a grant authorizes one
   operation once.

A refusal writes nothing. grant.json is read once: the bytes ssh-keygen checks are the bytes
parsed. A grant's id is the SHA-256 of those bytes.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from osiris_cli import chain_lock

NAMESPACE = "osiris-grant"
PRINCIPAL = "owner"
DEFAULT_EXPIRES_S = 900  # action 18, section 5: 15 minutes from signed_at
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_SIGNERS = os.path.join(REPO, "governance", "allowed_signers")
LEDGER_PATH = os.path.join(os.path.expanduser("~"), ".osiris", "authorization_ledger.jsonl")
GENESIS = "0" * 64
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
REQUIRED = ("payload_digest", "scope", "signed_at", "expires_s")
GRANTED, CONSUMED, REVOKED = "AUTHORIZATION_GRANTED", "AUTHORIZATION_CONSUMED", "AUTHORIZATION_REVOKED"
_DIGEST = re.compile(r"[0-9a-f]{64}")
_GOOD = re.compile(r'^Good "%s" signature for %s with \S+ key (SHA256:[A-Za-z0-9+/]+)$'
                   % (re.escape(NAMESPACE), re.escape(PRINCIPAL)), re.M)


@dataclass(frozen=True)
class Decision:
    authorized: bool
    reason: str
    record: Optional[Dict[str, Any]] = None

    def __bool__(self) -> bool:
        return self.authorized


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(d: Dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _iso(t: float) -> str:
    return time.strftime(TIME_FORMAT, time.gmtime(t))


def _epoch(value: Any) -> Optional[int]:
    """Seconds since the epoch for a UTC time written exactly as TIME_FORMAT, else None."""
    if not isinstance(value, str):
        return None
    try:
        t = calendar.timegm(time.strptime(value, TIME_FORMAT))
    except ValueError:
        return None
    return t if _iso(t) == value else None


def _unique_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError("a key appears twice")
    return dict(pairs)


def parse_grant(data: bytes) -> Tuple[Optional[Dict[str, Any]], str]:
    """The grant's fields, or None and why the bytes are not a grant."""
    try:
        grant = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_keys)
    except (UnicodeDecodeError, ValueError) as e:
        return None, f"grant is not JSON ({e})"
    if not isinstance(grant, dict):
        return None, "grant is not a JSON object"
    missing = [k for k in REQUIRED if k not in grant]
    if missing:
        return None, "grant lacks " + ", ".join(missing)
    if not (isinstance(grant["payload_digest"], str) and _DIGEST.fullmatch(grant["payload_digest"])):
        return None, "payload_digest is not a lowercase SHA-256 hex digest"
    if not (isinstance(grant["scope"], str) and grant["scope"].strip()):
        return None, "scope is not a non-empty string"
    if _epoch(grant["signed_at"]) is None:
        return None, f"signed_at is not a UTC time written as {TIME_FORMAT}"
    expires_s = grant["expires_s"]
    if isinstance(expires_s, bool) or not isinstance(expires_s, int) or expires_s <= 0:
        return None, "expires_s is not a positive whole number of seconds"
    return grant, "well formed"


def verify_signature(data: bytes, signature_path: str,
                     allowed_signers: str = ALLOWED_SIGNERS) -> Tuple[bool, str]:
    """(True, key fingerprint) if ssh-keygen accepts the signature, else (False, why)."""
    exe = shutil.which("ssh-keygen")
    if exe is None:
        return False, "ssh-keygen not found, so the signature cannot be checked"
    if not os.path.isfile(allowed_signers):
        return False, f"no trust root at {allowed_signers}"
    cmd = [exe, "-Y", "verify", "-f", allowed_signers, "-I", PRINCIPAL, "-n", NAMESPACE,
           "-s", signature_path]
    try:
        r = subprocess.run(cmd, input=data, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"ssh-keygen did not run ({e})"
    out = r.stdout.decode("utf-8", "replace")
    good = _GOOD.search(out)
    if r.returncode != 0 or good is None:
        detail = (r.stderr.decode("utf-8", "replace").strip() or out.strip()).splitlines()
        return False, "signature refused: " + (detail[-1] if detail else f"ssh-keygen exit {r.returncode}")
    return True, good.group(1)


def clock_synchronized() -> Tuple[bool, str]:
    """Whether the system clock reports NTP synchronization. A status that cannot be read is a
    no: under PRoot timedatectl has no systemd to ask, so Node Alpha fails closed."""
    exe = shutil.which("timedatectl")
    if exe is None:
        return False, "timedatectl not found, so NTP synchronization cannot be read"
    try:
        r = subprocess.run([exe, "show", "--property=NTPSynchronized", "--value"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"timedatectl did not run ({e})"
    if r.returncode != 0:
        first = (r.stderr.strip().splitlines() or [f"exit {r.returncode}"])[0]
        return False, f"NTP synchronization cannot be read: {first}"
    value = r.stdout.strip()
    if value != "yes":
        return False, f"the system clock is not NTP-synchronized (NTPSynchronized={value or 'empty'})"
    return True, "NTP-synchronized"


def _entry(kind: str, payload: Dict[str, Any], prev: str, ts: str) -> Dict[str, Any]:
    entry = {"kind": kind, "payload": payload, "prev": prev, "ts": ts}
    entry["hash"] = _sha256(_canon(entry).encode("utf-8"))
    return entry


def _read_chain(f) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """Every entry of an open ledger, or None if any entry breaks the chain."""
    f.seek(0)
    rows: List[Dict[str, Any]] = []
    prev = GENESIS
    for n, line in enumerate(f.read().splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except ValueError:
            return None, f"ledger line {n} is not JSON"
        if not (isinstance(e, dict) and isinstance(e.get("payload"), dict)):
            return None, f"ledger line {n} is not an event"
        body = {k: e.get(k) for k in ("kind", "payload", "prev", "ts")}
        if e.get("prev") != prev or e.get("hash") != _sha256(_canon(body).encode("utf-8")):
            return None, f"ledger chain broken at line {n}"
        rows.append(e)
        prev = e["hash"]
    return rows, "ok"


def _write(f, entries: List[Dict[str, Any]]) -> None:
    """All entries in one write, durable before the lock is released."""
    f.seek(0, os.SEEK_END)
    f.write("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries).encode("utf-8"))
    f.flush()
    os.fsync(f.fileno())


def _events(rows: List[Dict[str, Any]], grant_id: str) -> set:
    return {e["kind"] for e in rows if e["payload"].get("grant_id") == grant_id}


def _check_grant(grant_path: str, payload_digest: str, scope: str, signature_path: Optional[str],
                 allowed_signers: str, clock: Callable[[], Tuple[bool, str]]
                 ) -> Tuple[Optional[Dict[str, Any]], Optional[bytes], str]:
    """Checks 1-3 but the time window: (grant, its bytes, key fingerprint) or (None, None, why)."""
    signature_path = signature_path or grant_path + ".sig"
    try:
        with open(grant_path, "rb") as fh:
            data = fh.read()
    except OSError as e:
        return None, None, f"no grant at {grant_path} ({e.strerror})"
    if not os.path.isfile(signature_path):
        return None, None, f"no signature at {signature_path}"
    signed, detail = verify_signature(data, signature_path, allowed_signers)
    if not signed:
        return None, None, detail
    grant, why = parse_grant(data)
    if grant is None:
        return None, None, why
    if grant["payload_digest"] != payload_digest:
        return None, None, (f"grant is bound to payload {grant['payload_digest'][:16]}…, "
                            f"not {payload_digest[:16]}…")
    if grant["scope"] != scope:
        return None, None, f"grant is for scope {grant['scope']!r}, not {scope!r}"
    synced, why = clock()
    if not synced:
        return None, None, why
    return grant, data, detail


def _outside_window(grant: Dict[str, Any], now: float) -> Optional[str]:
    signed_at = _epoch(grant["signed_at"])
    if now < signed_at:
        return f"grant not valid before {grant['signed_at']} (now {_iso(now)})"
    if now > signed_at + grant["expires_s"]:
        return f"grant expired at {_iso(signed_at + grant['expires_s'])} (now {_iso(now)})"
    return None


def authorize(grant_path: str, payload_digest: str, scope: str, *,
              signature_path: Optional[str] = None, allowed_signers: str = ALLOWED_SIGNERS,
              ledger_path: str = LEDGER_PATH, node: Optional[str] = None,
              now: Optional[float] = None,
              clock: Callable[[], Tuple[bool, str]] = clock_synchronized) -> Decision:
    """Authorize one production operation once, or say why not. ``now`` is for tests."""
    grant, data, detail = _check_grant(grant_path, payload_digest, scope, signature_path,
                                       allowed_signers, clock)
    if grant is None:
        return Decision(False, detail)
    grant_id = _sha256(data)
    try:
        with open(allowed_signers, "rb") as fh:
            trust_root = _sha256(fh.read())
        with chain_lock.locked_tail(ledger_path) as (f, _last):
            t = time.time() if now is None else now
            late = _outside_window(grant, t)
            if late:
                return Decision(False, late)
            rows, why = _read_chain(f)
            if rows is None:
                return Decision(False, why)
            seen = _events(rows, grant_id)
            if REVOKED in seen:
                return Decision(False, f"grant {grant_id[:16]}… was revoked")
            if CONSUMED in seen:
                return Decision(False, f"grant {grant_id[:16]}… was already used")
            record = {"grant_id": grant_id, "principal": PRINCIPAL, "key_fingerprint": detail,
                      "method": "ssh-sig", "namespace": NAMESPACE, "scope": scope,
                      "payload_digest": payload_digest, "signed_at": grant["signed_at"],
                      "expires_at": _iso(_epoch(grant["signed_at"]) + grant["expires_s"]),
                      "node": node or platform.node(), "trust_root_sha256": trust_root}
            granted = _entry(GRANTED, record, rows[-1]["hash"] if rows else GENESIS, _iso(t))
            consumed = _entry(CONSUMED, {"grant_id": grant_id, "payload_digest": payload_digest,
                                         "scope": scope}, granted["hash"], _iso(t))
            _write(f, [granted, consumed])
    except (OSError, chain_lock.ChainTailError, chain_lock.ChainLockTimeout) as e:
        return Decision(False, f"ledger unavailable ({e})")
    return Decision(True, f"authorized once: {scope} for payload {payload_digest[:16]}…",
                    {**record, "consumption": "CONSUMED"})


def revoke(grant_id: str, reason: str, ledger_path: str = LEDGER_PATH) -> Dict[str, Any]:
    """Append AUTHORIZATION_REVOKED for a grant. Its earlier events stay as they are."""
    if not _DIGEST.fullmatch(grant_id):
        raise ValueError("grant_id is the SHA-256 of grant.json, in lowercase hex")
    if not reason.strip():
        raise ValueError("a revocation needs a reason")
    with chain_lock.locked_tail(ledger_path) as (f, _last):
        rows, why = _read_chain(f)
        if rows is None:
            raise chain_lock.ChainTailError(why)
        entry = _entry(REVOKED, {"grant_id": grant_id, "reason": reason},
                       rows[-1]["hash"] if rows else GENESIS, _iso(time.time()))
        _write(f, [entry])
    return entry


def draft(payload_digest: str, scope: str, expires_s: int = DEFAULT_EXPIRES_S,
          now: Optional[float] = None) -> bytes:
    """grant.json for the owner to sign now: canonical JSON with a fresh nonce."""
    grant = {"payload_digest": payload_digest, "scope": scope,
             "signed_at": _iso(time.time() if now is None else now),
             "expires_s": expires_s, "nonce": secrets.token_hex(16)}
    data = (_canon(grant) + "\n").encode("utf-8")
    if parse_grant(data)[0] is None:
        raise ValueError(parse_grant(data)[1])
    return data


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m osiris_cli.grants",
                                     description="SYS-021 production grants (action 18)")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draft", help="print a grant.json for the owner to sign")
    c = sub.add_parser("check", help="check a signed grant without using it")
    for p in (d, c):
        p.add_argument("--payload-digest", required=True)
        p.add_argument("--scope", required=True)
    d.add_argument("--expires-s", type=int, default=DEFAULT_EXPIRES_S)
    c.add_argument("grant")
    c.add_argument("--allowed-signers", default=ALLOWED_SIGNERS)
    r = sub.add_parser("revoke", help="revoke a grant by its id")
    r.add_argument("grant_id")
    r.add_argument("--reason", required=True)
    for p in (c, r):
        p.add_argument("--ledger", default=LEDGER_PATH)
    args = parser.parse_args(argv)

    if args.command == "draft":
        try:
            sys.stdout.write(draft(args.payload_digest, args.scope, args.expires_s).decode("utf-8"))
        except ValueError as e:
            print(f"not drafted: {e}", file=sys.stderr)
            return 1
        return 0
    if args.command == "revoke":
        try:
            revoke(args.grant_id, args.reason, args.ledger)
        except (ValueError, OSError, chain_lock.ChainTailError) as e:
            print(f"not revoked: {e}", file=sys.stderr)
            return 1
        print(f"revoked {args.grant_id}")
        return 0
    grant, data, detail = _check_grant(args.grant, args.payload_digest, args.scope, None,
                                       args.allowed_signers, clock_synchronized)
    problem = detail if grant is None else _outside_window(grant, time.time())
    if problem is None and os.path.exists(args.ledger):
        with open(args.ledger, "rb") as f:
            rows, why = _read_chain(f)
        seen = _events(rows, _sha256(data)) if rows is not None else set()
        problem = why if rows is None else ("revoked" if REVOKED in seen else
                                            "already used" if CONSUMED in seen else None)
    if problem:
        print(f"refused: {problem}")
        return 1
    print(f"valid and unused: grant {_sha256(data)} signed by {detail} (checked only; nothing authorized)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
