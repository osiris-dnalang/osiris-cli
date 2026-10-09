"""Local control plane for the S2 amendment-5 workflow (draft): evidence database, content-addressed artifacts,
typed intents, approvals bound to an exact payload, and a job outbox with leases, budget reservations and
reconciliation. Mock adapters only are exercised in this repository's tests; no live provider is called here.

Authority and limits (see docs/rqc/S2/CONTROL_NOTES.md):
- The evidence database and artifact store on local disk are authoritative. They protect against accidental
  corruption and against a process that goes through this API; they do not protect against a privileged local
  operator who edits the files (the hash chain makes such edits detectable, not impossible).
- `synchronous=FULL` + WAL is a required configuration. Durability then rests on the OS and storage honouring fsync;
  tests here kill no power and prove nothing about power loss.
- An idempotency key is a local name for one job. It gives exactly-once *recording*; it does not make a provider
  execute exactly once. A provider without native idempotency whose submit times out is in OUTCOME_UNKNOWN until a
  reconciliation says executed / not executed; it is never resubmitted automatically.
- CRSM constants, CCCE metrics and PCRB play no part in any decision here.
- `verify_bundle` checks that the files on disk are the implementation snapshot and documents a bundle manifest
  names, without any artifact embedding its own hash.
"""
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid

import numpy as np

from .hardware import BudgetExhausted

EVENT_VERSION = "rqc-evidence-event/1"
INTENT_SCHEMA = "rqc-s2-intent/1"
GENESIS = "0" * 64
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# name, value set, value PRAGMA reports back
EVIDENCE_PRAGMAS = (("journal_mode", "WAL", "wal"), ("synchronous", "FULL", 2), ("foreign_keys", "ON", 1),
                    ("busy_timeout", "5000", 5000), ("temp_store", "MEMORY", 2), ("trusted_schema", "OFF", 0))
TELEMETRY_PRAGMAS = (("journal_mode", "WAL", "wal"), ("synchronous", "NORMAL", 1), ("busy_timeout", "1000", 1000))

# Scopes an approval can carry. Only "execute" authorizes a dispatch; "read_only" covers inspection (usage queries,
# backend listings) and never a submission.
SCOPES = ("read_only", "execute")
# Targets. "local-fake" never leaves the machine; anything else is an external effect.
LOCAL_TARGETS = ("local-fake",)


class DurabilityError(RuntimeError):
    """The evidence database could not be opened with the required settings."""


class IntegrityError(RuntimeError):
    """Evidence or an artifact failed verification."""


class NotAuthorized(RuntimeError):
    """No valid approval covers this dispatch."""


class LeaseHeld(RuntimeError):
    """Another live worker holds the lease for this job."""


class ReconciliationRequired(RuntimeError):
    """The job's outcome is unknown; it must be reconciled before anything else happens to it."""


class AmbiguousOutcome(RuntimeError):
    """Raised by an adapter when a submission may or may not have reached the provider."""

    def __init__(self, msg, provider_ref=None):
        super().__init__(msg)
        self.provider_ref = provider_ref


class DefiniteFailure(RuntimeError):
    """Raised by an adapter when the provider certainly did not execute the job."""


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


# ---- connections ------------------------------------------------------------------------------------------------

def _apply(con, pragmas):
    for name, value, expect in pragmas:
        con.execute(f"PRAGMA {name} = {value}")
        got = con.execute(f"PRAGMA {name}").fetchone()[0]
        if got != expect:
            raise DurabilityError(f"PRAGMA {name}: wanted {expect!r}, connection reports {got!r}")


MIGRATIONS = [
    ("0001_initial", """
    CREATE TABLE artifacts (sha256 TEXT PRIMARY KEY CHECK (length(sha256) = 64), size INTEGER NOT NULL,
                            kind TEXT NOT NULL);
    CREATE TABLE intents (intent_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                          payload_sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
                          target TEXT NOT NULL, created_at REAL NOT NULL);
    CREATE TABLE approvals (approval_id TEXT PRIMARY KEY, intent_id TEXT NOT NULL REFERENCES intents(intent_id),
                            scope TEXT NOT NULL CHECK (scope IN ('read_only', 'execute')),
                            payload_sha256 TEXT NOT NULL, target TEXT NOT NULL, budget_seconds REAL NOT NULL,
                            expires_at REAL NOT NULL, approver TEXT NOT NULL, created_at REAL NOT NULL);
    CREATE TABLE revocations (approval_id TEXT PRIMARY KEY REFERENCES approvals(approval_id),
                              reason TEXT NOT NULL, at REAL NOT NULL);
    CREATE TABLE outbox (idem_key TEXT PRIMARY KEY, intent_id TEXT NOT NULL REFERENCES intents(intent_id),
                         request_sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
                         state TEXT NOT NULL CHECK (state IN ('leased', 'dispatching', 'done', 'failed',
                                                              'outcome_unknown', 'not_executed')),
                         lease_owner TEXT, lease_expires REAL, reserved_s REAL NOT NULL,
                         actual_s REAL, provider_ref TEXT, result_sha256 TEXT REFERENCES artifacts(sha256),
                         updated_at REAL NOT NULL);
    CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL, prev_hash TEXT NOT NULL,
                         hash TEXT NOT NULL UNIQUE);
    CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
    CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
    CREATE TRIGGER intents_no_update BEFORE UPDATE ON intents BEGIN SELECT RAISE(ABORT, 'intents are immutable'); END;
    CREATE TRIGGER intents_no_delete BEFORE DELETE ON intents BEGIN SELECT RAISE(ABORT, 'intents are immutable'); END;
    CREATE TRIGGER approvals_no_update BEFORE UPDATE ON approvals BEGIN SELECT RAISE(ABORT, 'approvals are immutable'); END;
    CREATE TRIGGER approvals_no_delete BEFORE DELETE ON approvals BEGIN SELECT RAISE(ABORT, 'approvals are immutable'); END;
    CREATE TRIGGER artifacts_no_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT, 'artifacts are immutable'); END;
    CREATE TRIGGER outbox_no_delete BEFORE DELETE ON outbox BEGIN SELECT RAISE(ABORT, 'outbox rows are kept'); END;
    """),
]


def connect_evidence(path):
    """Every evidence connection goes through here: required PRAGMAs set and read back, migrations applied.
    Fails closed (DurabilityError) rather than running with weaker settings; ':memory:' cannot use WAL and is
    refused."""
    if path == ":memory:" or not path:
        raise DurabilityError("evidence needs a file-backed database (WAL)")
    con = sqlite3.connect(path, timeout=5.0, isolation_level=None, check_same_thread=False)
    try:
        _apply(con, EVIDENCE_PRAGMAS)
        con.execute("BEGIN IMMEDIATE")
        con.execute("CREATE TABLE IF NOT EXISTS schema_migrations (id TEXT PRIMARY KEY, sha256 TEXT NOT NULL)")
        done = dict(con.execute("SELECT id, sha256 FROM schema_migrations").fetchall())
        for mid, sql in MIGRATIONS:
            h = sha256(sql.encode())
            if mid in done:
                if done[mid] != h:
                    raise DurabilityError(f"migration {mid} differs from the one applied")
                continue
            for stmt in _statements(sql):
                con.execute(stmt)
            con.execute("INSERT INTO schema_migrations VALUES (?, ?)", (mid, h))
        con.execute("COMMIT")
    except BaseException:
        if con.in_transaction:
            con.execute("ROLLBACK")
        con.close()
        raise
    return con


def _statements(sql):
    # split on ';' at end of statement, keeping trigger bodies (which contain '; END') whole
    out, cur = [], []
    for part in sql.split(";"):
        cur.append(part)
        joined = ";".join(cur).strip()
        if not joined:
            cur = []
            continue
        if joined.upper().startswith("CREATE TRIGGER") and not joined.upper().endswith("END"):
            continue
        out.append(joined)
        cur = []
    return out


def connect_telemetry(path):
    """Non-authoritative: progress, heartbeats. NORMAL sync is allowed here and only here."""
    con = sqlite3.connect(path, timeout=1.0, isolation_level=None, check_same_thread=False)
    _apply(con, TELEMETRY_PRAGMAS)
    con.execute("CREATE TABLE IF NOT EXISTS telemetry (ts REAL, kind TEXT, body TEXT)")
    return con


class Telemetry:
    """Best effort. A failure here is counted and swallowed: it can never block, roll back or authorize anything."""

    def __init__(self, path):
        self.dropped = 0
        try:
            self._con = connect_telemetry(path)
        except Exception:                                   # noqa: BLE001
            self._con = None

    def emit(self, kind, body):
        try:
            if self._con is None:
                raise RuntimeError("telemetry unavailable")
            self._con.execute("INSERT INTO telemetry VALUES (?, ?, ?)", (time.time(), kind, json.dumps(body)))
        except Exception:                                   # noqa: BLE001
            self.dropped += 1


# ---- artifacts ------------------------------------------------------------------------------------------------

class ArtifactStore:
    """objects/<aa>/<sha256>, identity = SHA-256 of the stored bytes. Publication: write to staging, fsync, verify,
    hard-link into place (fails if the name exists, so an existing hash is never replaced), fsync the directory,
    remove the staging name. A database row may reference an artifact only after put() returned, so a crash
    leaves at worst an unreferenced object or a staging file (both harmless; see sweep_staging)."""

    def __init__(self, root):
        self.root = os.path.realpath(root)
        self.objects = os.path.join(self.root, "objects")
        self.staging = os.path.join(self.root, "staging")
        for d in (self.root, self.objects, self.staging):
            os.makedirs(d, exist_ok=True)
            if os.path.islink(d) or not os.path.realpath(d).startswith(self.root):
                raise IntegrityError(f"{d} escapes the artifact root")

    def path_of(self, digest):
        if not isinstance(digest, str) or not _HEX64.match(digest):
            raise ValueError("artifact id must be 64 lowercase hex characters")
        p = os.path.join(self.objects, digest[:2], digest)
        real = os.path.realpath(p)
        if not real.startswith(self.objects + os.sep):
            raise IntegrityError(f"{digest} resolves outside the store")
        return p

    def put(self, data):
        digest = sha256(data)
        final = self.path_of(digest)
        os.makedirs(os.path.dirname(final), exist_ok=True)
        if os.path.exists(final):
            if self.get(digest) != data:                    # get() verifies; a mismatch raises there
                raise IntegrityError(f"{digest}: existing object differs")
            return digest
        tmp = os.path.join(self.staging, f"{uuid.uuid4().hex}.part")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        with open(tmp, "rb") as f:
            if sha256(f.read()) != digest:
                os.unlink(tmp)
                raise IntegrityError("staged bytes do not match their hash")
        try:
            os.link(tmp, final)
        except FileExistsError:
            pass                                            # a concurrent writer published it; verified below
        finally:
            os.unlink(tmp)
        _fsync_dir(os.path.dirname(final))
        if self.get(digest) != data:
            raise IntegrityError(f"{digest}: published object differs")
        return digest

    def get(self, digest):
        p = self.path_of(digest)
        if not os.path.exists(p):
            raise IntegrityError(f"{digest}: missing")
        with open(p, "rb") as f:
            data = f.read()
        if sha256(data) != digest:
            raise IntegrityError(f"{digest}: content does not match its hash")
        return data

    def sweep_staging(self, older_than_s=3600, now=None):
        now = time.time() if now is None else now
        removed = []
        for name in os.listdir(self.staging):
            p = os.path.join(self.staging, name)
            if now - os.path.getmtime(p) >= older_than_s:
                os.unlink(p)
                removed.append(name)
        return removed


def _fsync_dir(d):
    try:
        fd = os.open(d, os.O_RDONLY)
    except OSError:
        return                                              # platforms without directory fds
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


# ---- evidence ------------------------------------------------------------------------------------------------

class Evidence:
    """Authoritative store: one connection (from connect_evidence) plus the artifact store."""

    def __init__(self, root, clock=time.time):
        os.makedirs(root, exist_ok=True)
        self.con = connect_evidence(os.path.join(root, "evidence.sqlite"))
        self.artifacts = ArtifactStore(os.path.join(root, "artifacts"))
        self.clock = clock

    # events: call inside a transaction
    def _event(self, kind, intent_id, body):
        row = self.con.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row[0] if row else GENESIS
        b = canonical({"v": EVENT_VERSION, "kind": kind, "intent_id": intent_id, "at": self.clock(), "body": body})
        h = sha256(prev.encode() + b)
        self.con.execute("INSERT INTO events (body, prev_hash, hash) VALUES (?, ?, ?)", (b.decode(), prev, h))
        return h

    def tx(self):
        return _Tx(self.con)

    def record(self, kind, intent_id, body):
        with self.tx():
            return self._event(kind, intent_id, body)

    def verify_chain(self):
        prev = GENESIS
        for seq, body, p, h in self.con.execute("SELECT seq, body, prev_hash, hash FROM events ORDER BY seq"):
            if p != prev or sha256(prev.encode() + body.encode()) != h:
                return False, f"event {seq}: chain broken"
            prev = h
        return True, "ok"

    def events(self, intent_id=None):
        rows = self.con.execute("SELECT body FROM events ORDER BY seq").fetchall()
        out = [json.loads(r[0]) for r in rows]
        return [e for e in out if intent_id is None or e["intent_id"] == intent_id]

    def put_artifact(self, data, kind):
        digest = self.artifacts.put(data)                   # published and fsynced before any row refers to it
        with self.tx():
            self.con.execute("INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?)", (digest, len(data), kind))
        return digest

    def verify_artifacts(self):
        bad = []
        for (digest,) in self.con.execute("SELECT sha256 FROM artifacts").fetchall():
            try:
                self.artifacts.get(digest)
            except IntegrityError as e:
                bad.append(str(e))
        return bad

    # intents and approvals
    def create_intent(self, kind, payload, target):
        data = canonical(payload)
        digest = self.put_artifact(data, "intent-payload")
        intent_id = f"{kind}:{sha256(canonical({'payload': digest, 'target': target}))[:16]}"
        with self.tx():
            if self.con.execute("SELECT 1 FROM intents WHERE intent_id = ?", (intent_id,)).fetchone():
                return intent_id
            self.con.execute("INSERT INTO intents VALUES (?, ?, ?, ?, ?)",
                             (intent_id, kind, digest, target, self.clock()))
            self._event("intent.created", intent_id, {"payload_sha256": digest, "target": target})
        return intent_id

    def approve(self, intent_id, scope, budget_seconds, expires_at, approver):
        if scope not in SCOPES:
            raise ValueError(f"unknown scope {scope!r}")
        row = self.con.execute("SELECT payload_sha256, target FROM intents WHERE intent_id = ?",
                               (intent_id,)).fetchone()
        if row is None:
            raise KeyError(intent_id)
        if approver.startswith("policy:") and (scope != "execute" or row[1] not in LOCAL_TARGETS):
            raise NotAuthorized("automatic (policy) approval is only for local targets with no external effect")
        # `approver` is a label, not an authenticated identity: anyone who can call this API on the operator's
        # account can approve. The boundary is who can write this database, not this argument.
        approval_id = "appr_" + uuid.uuid4().hex
        with self.tx():
            self.con.execute("INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (approval_id, intent_id, scope, row[0], row[1], float(budget_seconds),
                              float(expires_at), approver, self.clock()))
            self._event("approval.granted", intent_id, {"approval_id": approval_id, "scope": scope,
                                                        "payload_sha256": row[0], "target": row[1],
                                                        "budget_seconds": budget_seconds, "expires_at": expires_at,
                                                        "approver": approver})
        return approval_id

    def revoke(self, approval_id, reason):
        with self.tx():
            iid = self.con.execute("SELECT intent_id FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
            self.con.execute("INSERT INTO revocations VALUES (?, ?, ?)", (approval_id, reason, self.clock()))
            self._event("approval.revoked", iid[0] if iid else None, {"approval_id": approval_id, "reason": reason})

    def authorize(self, intent_id, payload, target):
        """Return the approval that covers dispatching `payload` to `target` now, or raise NotAuthorized (and record
        the denial; if the denial cannot be recorded, the error propagates - fail closed)."""
        reason, approval = self._check(intent_id, payload, target)
        if reason:
            self.record("authorization.denied", intent_id, {"reason": reason, "target": target})
            raise NotAuthorized(reason)
        return approval

    def _check(self, intent_id, payload, target):
        ok, why = self.verify_chain()
        if not ok:
            return f"evidence chain fails verification ({why})", None
        row = self.con.execute("SELECT payload_sha256, target FROM intents WHERE intent_id = ?",
                               (intent_id,)).fetchone()
        if row is None:
            return "no such intent", None
        digest = sha256(canonical(payload))
        if digest != row[0]:
            return "payload differs from the intent", None
        try:
            if self.artifacts.get(row[0]) != canonical(payload):
                return "stored intent payload differs", None
        except IntegrityError as e:
            return f"intent payload artifact: {e}", None
        if target != row[1]:
            return f"intent is for {row[1]!r}, not {target!r}", None
        now = self.clock()
        for aid, scope, pdig, tgt, budget, exp in self.con.execute(
                "SELECT approval_id, scope, payload_sha256, target, budget_seconds, expires_at FROM approvals "
                "WHERE intent_id = ? ORDER BY created_at DESC", (intent_id,)).fetchall():
            if scope != "execute" or pdig != digest or tgt != target or exp <= now:
                continue
            if self.con.execute("SELECT 1 FROM revocations WHERE approval_id = ?", (aid,)).fetchone():
                continue
            if float(payload.get("budget_seconds", -1)) != budget:
                continue
            return None, {"approval_id": aid, "budget_seconds": budget, "expires_at": exp}
        return "no unexpired, unrevoked execute approval bound to this payload, target and budget", None


class _Tx:
    def __init__(self, con):
        self.con = con

    def __enter__(self):
        self.con.execute("BEGIN IMMEDIATE")
        return self.con

    def __exit__(self, et, e, tb):
        self.con.execute("COMMIT" if et is None else "ROLLBACK")
        return False


# ---- outbox dispatcher ------------------------------------------------------------------------------------------

def request_doc(requests):
    return {"pubs": [{"circuit_sha256": c.digest(), "shots": int(s)} for c, s in requests]}


class Dispatcher:
    """run_batch / preflight for GatheringSampler, backed by the outbox.

    One job = one outbox row, keyed by idem_key = SHA-256(intent_id, pub digests and shots). Sequence per job:
      lease (reserve projected seconds against the approved budget) -> re-authorize -> 'dispatching' committed ->
      adapter.submit -> receipt ('done', results stored as an artifact first) | 'failed' | 'outcome_unknown'.
    A job already 'done' is replayed from its stored result without contacting the provider (restart after a crash
    re-runs the deterministic search and replays completed jobs). 'outcome_unknown' blocks until reconcile().
    """

    def __init__(self, evidence, intent_id, payload, target, adapter, worker_id, project, lease_s=900.0):
        self.ev, self.intent_id, self.payload, self.target = evidence, intent_id, payload, target
        self.adapter, self.worker, self.project, self.lease_s = adapter, worker_id, project, lease_s
        self.replayed = 0

    def idem_key(self, requests):
        return sha256(canonical({"intent": self.intent_id, "req": request_doc(requests)}))

    def committed_seconds(self):
        # a finished job counts max(reported, reserved): qiskit-ibm-runtime's job.usage() returns 0 until the
        # provider has computed usage, so a low or missing report never frees budget
        done = self.ev.con.execute("SELECT COALESCE(SUM(MAX(COALESCE(actual_s, 0), reserved_s)), 0) FROM outbox "
                                   "WHERE intent_id = ? AND state = 'done'", (self.intent_id,)).fetchone()[0]
        held = self.ev.con.execute("SELECT COALESCE(SUM(reserved_s), 0) FROM outbox WHERE intent_id = ? AND "
                                   "state IN ('leased', 'dispatching', 'outcome_unknown', 'failed')",
                                   (self.intent_id,)).fetchone()[0]
        return float(done) + float(held)

    def preflight(self, requests):
        approval = self.ev.authorize(self.intent_id, self.payload, self.target)
        row = self._row(self.idem_key(requests))
        if row is not None and row["state"] == "done":
            return                                          # replay: costs nothing
        need = self.project(requests)
        if self.committed_seconds() + need > approval["budget_seconds"]:
            self.ev.record("budget.refused", self.intent_id, {"committed": self.committed_seconds(), "need": need,
                                                              "budget": approval["budget_seconds"]})
            raise BudgetExhausted(f"committed {self.committed_seconds():.0f}s + projected {need}s > "
                                  f"{approval['budget_seconds']:.0f}s")

    def _row(self, key):
        r = self.ev.con.execute("SELECT state, lease_owner, lease_expires, result_sha256, reserved_s, provider_ref "
                                "FROM outbox WHERE idem_key = ?", (key,)).fetchone()
        if r is None:
            return None
        return dict(zip(("state", "lease_owner", "lease_expires", "result_sha256", "reserved_s", "provider_ref"), r))

    def _set(self, key, state, event, body, **cols):
        sets = ", ".join(f"{c} = ?" for c in ("state", "updated_at") + tuple(cols))
        with self.ev.tx():
            self.ev.con.execute(f"UPDATE outbox SET {sets} WHERE idem_key = ?",
                                (state, self.ev.clock()) + tuple(cols.values()) + (key,))
            self.ev._event(event, self.intent_id, dict({"idem_key": key, "state": state}, **body))

    def _replay(self, key, row):
        doc = json.loads(self.ev.artifacts.get(row["result_sha256"]))
        self.replayed += 1
        self.ev.record("job.replayed", self.intent_id, {"idem_key": key, "result_sha256": row["result_sha256"]})
        return ([np.array(x, dtype=np.int64) for x in doc["samples"]],
                {"job_id": doc["provider_ref"], "replayed": True, "circuit_sha256": doc["circuit_sha256"]})

    def lease(self, requests):
        """Atomically take (or retake an expired) lease. Returns the key."""
        key = self.idem_key(requests)
        req_sha = self.ev.put_artifact(canonical(request_doc(requests)), "job-request")
        now = self.ev.clock()
        with self.ev.tx() as con:
            r = con.execute("SELECT state, lease_owner, lease_expires FROM outbox WHERE idem_key = ?",
                            (key,)).fetchone()
            if r is None:
                con.execute("INSERT INTO outbox (idem_key, intent_id, request_sha256, state, lease_owner, "
                            "lease_expires, reserved_s, updated_at) VALUES (?, ?, ?, 'leased', ?, ?, ?, ?)",
                            (key, self.intent_id, req_sha, self.worker, now + self.lease_s,
                             float(self.project(requests)), now))
            elif r[0] == "leased" and (r[1] == self.worker or r[2] <= now):
                con.execute("UPDATE outbox SET lease_owner = ?, lease_expires = ?, updated_at = ? "
                            "WHERE idem_key = ?", (self.worker, now + self.lease_s, now, key))
            elif r[0] == "leased":
                raise LeaseHeld(f"{key[:12]} leased by {r[1]} until {r[2]:.0f}")
            else:
                raise ReconciliationRequired(f"{key[:12]} is {r[0]}") if r[0] in ("dispatching",
                                                                                   "outcome_unknown") \
                    else RuntimeError(f"{key[:12]} is {r[0]}; not leasable")
            self.ev._event("job.leased", self.intent_id, {"idem_key": key, "worker": self.worker,
                                                          "lease_expires": now + self.lease_s})
        return key

    def __call__(self, requests):
        key = self.idem_key(requests)
        row = self._row(key)
        if row is not None and row["state"] == "done":
            return self._replay(key, row)
        if row is not None and row["state"] in ("dispatching", "outcome_unknown"):
            if self.adapter.supports_idempotency:
                self.reconcile_with_adapter(key)
                row = self._row(key)
                if row["state"] == "done":
                    return self._replay(key, row)
            raise ReconciliationRequired(f"job {key[:12]} has an unknown outcome; reconcile before continuing")
        if row is not None and row["state"] == "failed":
            raise RuntimeError(f"job {key[:12]} failed terminally; not resubmitted")
        self.lease(requests)
        self.ev.authorize(self.intent_id, self.payload, self.target)          # re-validate at dispatch
        self._set(key, "dispatching", "job.dispatching", {"worker": self.worker})
        try:
            results, meta = self.adapter.submit(requests, key)
        except AmbiguousOutcome as e:
            self._set(key, "outcome_unknown", "job.outcome_unknown", {"error": str(e)},
                      provider_ref=e.provider_ref)
            raise
        except DefiniteFailure as e:
            self._set(key, "failed", "job.failed", {"error": str(e)})
            raise
        except BaseException as e:                          # noqa: BLE001 - unknown error class: assume ambiguous
            self._set(key, "outcome_unknown", "job.outcome_unknown", {"error": repr(e)})
            raise AmbiguousOutcome(repr(e)) from e
        self._receipt(key, requests, results, meta)
        return results, meta

    def _receipt(self, key, requests, results, meta):
        doc = {"protocol_sha256": sha256(canonical(self.payload)), "provider_ref": meta.get("job_id"),
               "circuit_sha256": [c.digest() for c, _ in requests], "shots": [int(s) for _, s in requests],
               "samples": [np.asarray(x).tolist() for x in results], "meta": {k: v for k, v in meta.items()
                                                                              if k != "circuit_sha256"}}
        res_sha = self.ev.put_artifact(canonical(doc), "job-result")         # artifact before the row refers to it
        self._set(key, "done", "job.receipt", {"provider_ref": meta.get("job_id"), "result_sha256": res_sha,
                                               "billed_s": meta.get("quantum_seconds")},
                  actual_s=float(meta.get("quantum_seconds") or 0.0), provider_ref=meta.get("job_id"),
                  result_sha256=res_sha)

    def recover(self):
        """After a restart: expired leases with no dispatch attempt simply lapse (nothing left this machine);
        rows stuck in 'dispatching' become 'outcome_unknown'."""
        now = self.ev.clock()
        stuck = self.ev.con.execute("SELECT idem_key FROM outbox WHERE intent_id = ? AND state = 'dispatching'",
                                    (self.intent_id,)).fetchall()
        for (key,) in stuck:
            self._set(key, "outcome_unknown", "job.outcome_unknown", {"error": "found mid-dispatch at restart"})
        lapsed = self.ev.con.execute("SELECT idem_key FROM outbox WHERE intent_id = ? AND state = 'leased' AND "
                                     "lease_expires <= ?", (self.intent_id, now)).fetchall()
        for (key,) in lapsed:
            self.ev.record("job.lease_expired", self.intent_id, {"idem_key": key})
        return {"outcome_unknown": [k for (k,) in stuck], "lease_expired": [k for (k,) in lapsed]}

    def reconcile_with_adapter(self, key):
        found = self.adapter.lookup(key)
        if found is None:
            self.ev.record("job.reconcile_inconclusive", self.intent_id, {"idem_key": key})
            return
        requests, results, meta = found
        self._receipt(key, requests, results, meta)

    def reconcile(self, key, executed, evidence_note, results=None, requests=None, meta=None):
        """Operator or provider-lookup decision for an outcome_unknown job. executed=False releases it for a new
        dispatch only through a fresh lease; executed=True requires the results."""
        row = self._row(key)
        if row is None or row["state"] not in ("outcome_unknown", "dispatching"):
            raise RuntimeError(f"{key[:12]} is not awaiting reconciliation")
        if executed:
            if results is None:
                raise ValueError("an executed job is reconciled with its results")
            self._receipt(key, requests, results, dict(meta or {}, reconciled=evidence_note))
        else:
            self._set(key, "not_executed", "job.reconciled_not_executed", {"note": evidence_note})
            with self.ev.tx() as con:                       # the slot can be leased again, as a new attempt
                con.execute("UPDATE outbox SET state = 'leased', lease_owner = NULL, lease_expires = 0 "
                            "WHERE idem_key = ?", (key,))
                self.ev._event("job.released", self.intent_id, {"idem_key": key})


# ---- adapters ------------------------------------------------------------------------------------------------

class MockAdapter:
    """In-memory provider. supports_idempotency=True: a repeated key returns the first execution and lookup() finds
    it. supports_idempotency=False: every submit executes, and lookup() is unavailable. `fail_after_execute` makes
    the next submit execute and then raise AmbiguousOutcome (an accepted job whose response was lost)."""

    def __init__(self, sample, supports_idempotency):
        self.sample, self.supports_idempotency = sample, supports_idempotency
        self.executions, self._done, self.fail_after_execute, self.fail_before = 0, {}, 0, 0

    def submit(self, requests, key):
        if self.supports_idempotency and key in self._done:
            return self._done[key][1], self._done[key][2]
        if self.fail_before:
            self.fail_before -= 1
            raise DefiniteFailure("rejected by provider before execution")
        self.executions += 1
        results = [self.sample(c, s) for c, s in requests]
        meta = {"job_id": f"mock-{self.executions}", "quantum_seconds": 1.0,
                "circuit_sha256": [c.digest() for c, _ in requests]}
        if self.supports_idempotency:
            self._done[key] = (requests, results, meta)
        if self.fail_after_execute:
            self.fail_after_execute -= 1
            raise AmbiguousOutcome("timeout after submission", provider_ref=meta["job_id"])
        return results, meta

    def lookup(self, key):
        if not self.supports_idempotency:
            raise NotImplementedError("this provider has no lookup by idempotency key")
        return self._done.get(key)


class QiskitBatchAdapter:
    """One multi-pub SamplerV2 job per submit. Used here only with qiskit_ibm_runtime fake backends (local Aer).
    qiskit-ibm-runtime offers no client idempotency key, so supports_idempotency is False: a submit that raises
    after the provider may have accepted the job is AmbiguousOutcome."""

    supports_idempotency = False

    def __init__(self, backend, layout, sampler_factory=None, usage_of=None):
        from .hardware import _quantum_seconds
        from .samplers import calibration_record
        self.backend, self.layout = backend, list(layout)
        if sampler_factory is None:
            from qiskit_ibm_runtime import SamplerV2
            sampler_factory = lambda: SamplerV2(mode=backend)  # noqa: E731
        self._sampler = sampler_factory()
        self._usage_of = usage_of or _quantum_seconds
        self.calibration = calibration_record(backend)

    def submit(self, requests, key):
        from qiskit import transpile

        from .circuits import to_qiskit
        from .samplers import counts_to_indices
        try:
            pubs = [(transpile(to_qiskit(c), backend=self.backend, initial_layout=self.layout,
                               optimization_level=1, seed_transpiler=0), None, s) for c, s in requests]
        except Exception as e:                              # noqa: BLE001 - nothing was sent
            raise DefiniteFailure(f"transpile: {e!r}") from e
        job = None
        try:
            job = self._sampler.run(pubs)
            result = job.result()
            counts = [result[i].data.meas.get_counts() for i in range(len(pubs))]
        except Exception as e:                              # noqa: BLE001
            raise AmbiguousOutcome(repr(e), provider_ref=job.job_id() if job is not None else None) from e
        try:
            usage_status = (job.metrics().get("usage") or {}).get("status")
        except Exception:                                   # noqa: BLE001 - local/fake modes have no metrics
            usage_status = None
        meta = {"job_id": job.job_id(), "quantum_seconds": self._usage_of(job), "usage_status": usage_status,
                "backend": self.backend.name,
                "layout": self.layout, "calibration": self.calibration,
                "circuit_sha256": [c.digest() for c, _ in requests]}
        return [counts_to_indices(k) for k in counts], meta

    def lookup(self, key):
        raise NotImplementedError("reconcile by provider job id / tags, recorded by an operator")


def code_manifest(root, paths):
    """{relative path: sha256 of bytes}; the hash of its canonical form identifies the code being run."""
    out = {}
    for p in paths:
        with open(os.path.join(root, p), "rb") as f:
            out[p] = sha256(f.read())
    return out


BUNDLE_SCHEMA = "rqc-s2-amendment5-bundle/1"
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def verify_bundle(root, manifest_path, code_files, document_files, amendment_doi=None):
    """Check the bundle manifest against the files on disk. Returns a list of problems (empty = verified).

    Manifest layout (no circular hashes): implementation = {commit, files: {path: sha256}} for code_files at that
    commit; documents = {path: sha256} for document_files; amendment_path names the document that must cite
    implementation.commit. The amendment never contains its own commit or the manifest's hash. With amendment_doi
    (hardware use), the manifest must also record status 'deposited' and that DOI."""
    try:
        with open(manifest_path, "rb") as f:
            m = json.loads(f.read())
    except FileNotFoundError:
        return [f"manifest {manifest_path} missing"]
    except ValueError as e:
        return [f"manifest unreadable: {e}"]
    problems = []
    if m.get("schema") != BUNDLE_SCHEMA:
        problems.append(f"manifest schema {m.get('schema')!r} is not {BUNDLE_SCHEMA!r}")
    impl = m.get("implementation") or {}
    commit = impl.get("commit") or ""
    if not _COMMIT.match(commit):
        problems.append("implementation.commit is not a full 40-hex commit hash")
    for label, want, got in (("implementation.files", code_files, impl.get("files") or {}),
                             ("documents", document_files, m.get("documents") or {})):
        if set(got) != set(want):
            problems.append(f"{label} lists {sorted(got)}, expected {sorted(want)}")
        for p in want:
            try:
                with open(os.path.join(root, p), "rb") as f:
                    actual = sha256(f.read())
            except FileNotFoundError:
                problems.append(f"{p} missing")
                continue
            if got.get(p) != actual:
                problems.append(f"{p} sha256 {actual[:12]} differs from manifest {str(got.get(p))[:12]}")
    ap = m.get("amendment_path")
    if ap not in document_files:
        problems.append("amendment_path is not one of the documents")
    elif commit and os.path.exists(os.path.join(root, ap)):
        with open(os.path.join(root, ap), encoding="utf-8") as f:
            if commit not in f.read():
                problems.append(f"{ap} does not cite implementation commit {commit[:12]}")
    if amendment_doi is not None:
        if m.get("status") != "deposited":
            problems.append(f"manifest status is {m.get('status')!r}, not 'deposited'")
        if m.get("amendment_doi") != amendment_doi:
            problems.append(f"manifest amendment_doi {m.get('amendment_doi')!r} is not {amendment_doi!r}")
    return problems
