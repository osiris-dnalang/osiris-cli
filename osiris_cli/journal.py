"""The operational journal: OSIRIS's append-only, hash-chained evidence ledger (L8).

One JSON object per line, each chained to the one before it:

    hash = SHA-256(prev || canonical(entry without prev and hash))

where canonical is sorted-key, compact JSON. The field names are the journal's own (prev, hash,
ts, kind), so every entry already in provenance/osiris_operational_journal.jsonl still verifies.
The Phase 2 L8 schema maps onto them: prev_hash -> prev, entry_hash -> hash, timestamp_utc -> ts,
event_type -> kind. Entries appended from here on also carry seq_id, their 0-based position.

Appends go through chain_lock: the tip is read from disk under an exclusive lock, so two writers
cannot both link to it and fork the chain, and a torn last line refuses the append
(chain_lock.ChainTailError) instead of being skipped over.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from osiris_cli import chain_lock

_HEX64 = re.compile(r"[0-9a-f]{64}")


def _canon(d: Any) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_sha256(payload: Any) -> str:
    """SHA-256 of a payload's canonical JSON: what append_event records next to the payload."""
    return hashlib.sha256(_canon(payload).encode("utf-8")).hexdigest()


class OperationalMerkleLedger:
    """
    Append-only Merkle hash-chained ledger for operational quantum and agent executions.
    Preserves cryptographic provenance: hash_i = SHA256(prev_hash || canonical(entry)).
    """
    GENESIS = "0" * 64
    RESERVED = ("prev", "hash", "ts", "kind", "seq_id")

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    @staticmethod
    def _canon(d: Dict[str, Any]) -> str:
        return _canon(d)

    @staticmethod
    def _next_seq(f, last: Optional[Dict[str, Any]]) -> int:
        """The position the next entry takes. Entries written before seq_id existed are counted."""
        if last is None:
            return 0
        if type(last.get("seq_id")) is int:
            return last["seq_id"] + 1
        f.seek(0)
        return sum(1 for line in f if line.strip())

    def append(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        clash = sorted(set(payload) & set(self.RESERVED))
        if clash:
            raise ValueError(f"payload keys {clash} are reserved by the journal")
        with chain_lock.locked_tail(str(self.path)) as (f, last):
            prev = last["hash"] if last else self.GENESIS
            entry = {
                "prev": prev,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "kind": kind,
                "seq_id": self._next_seq(f, last),
                **payload,
            }
            body_to_hash = {k: v for k, v in entry.items() if k != "prev"}
            entry["hash"] = hashlib.sha256((prev + _canon(body_to_hash)).encode("utf-8")).hexdigest()
            chain_lock.write_line(f, entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return entry

    def append_event(
        self,
        event_type: str,
        substrate_node: str,
        payload: Dict[str, Any],
        action_fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append one L8 event: the payload, its SHA-256, the node it happened on and, when the event
        acts on a proposed step, that step's gap_analyzer.compute_action_fingerprint."""
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be a non-empty string")
        if not isinstance(substrate_node, str) or not substrate_node.strip():
            raise ValueError("substrate_node must be a non-empty string")
        if action_fingerprint is not None and not (
            isinstance(action_fingerprint, str) and _HEX64.fullmatch(action_fingerprint)
        ):
            raise ValueError("action_fingerprint must be 64 lowercase hex characters or None")
        return self.append(event_type, {
            "substrate_node": substrate_node,
            "action_fingerprint": action_fingerprint,
            "payload": payload,
            "payload_sha256": payload_sha256(payload),
        })

    def verify(self) -> Optional[str]:
        """Verify entire cryptographic chain from genesis. None when intact, else the first fault."""
        prev = self.GENESIS
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        position = 0
        with self.path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    return f"Entry {i}: not JSON"
                if not isinstance(e, dict):
                    return f"Entry {i}: not a JSON object"
                if e.get("prev") != prev:
                    return f"Entry {i}: prev-hash mismatch (expected {prev}, got {e.get('prev')})"
                body = {k: v for k, v in e.items() if k not in ("prev", "hash")}
                want = hashlib.sha256((prev + _canon(body)).encode("utf-8")).hexdigest()
                if e.get("hash") != want:
                    return f"Entry {i}: hash mismatch (expected {want}, got {e.get('hash')})"
                if "seq_id" in e and e["seq_id"] != position:
                    return f"Entry {i}: seq_id {e['seq_id']!r} at position {position}"
                if "payload" in e and "payload_sha256" in e and e["payload_sha256"] != payload_sha256(e["payload"]):
                    return f"Entry {i}: payload_sha256 does not match its payload"
                prev = e["hash"]
                position += 1
        return None
