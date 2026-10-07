# Test fixture: dnalang-core v0.2.0 (commit 227261e), dnalang/ledger.py, copied unmodified below
# this header from https://github.com/osiris-dnalang/dnalang-core so the genome-ledger
# supersession tests run without dnalang-core installed. Runtime code uses the real package.
# Licensed under the Apache License, Version 2.0. Copyright 2026 Devin Phillip Davis.

"""Append-only, hash-chained run ledger (JSONL).

Each entry: {"prev": <hash>, "ts": ..., ...payload..., "hash": SHA256(prev || canonical(payload))}.
Tamper-evidence rests on SHA-256 collision resistance and nothing else. `verify()`
re-derives every hash. Entries are written *before* a job is submitted (write-ahead)
and completed by a second entry when results arrive, so an abandoned job still
leaves a trace.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

GENESIS = "0" * 64


def _canon(d: Dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def _last_hash(self) -> str:
        last = GENESIS
        for e in self:
            last = e["hash"]
        return last

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        with self.path.open() as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    def append(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        entry = {"prev": self._last_hash(), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "kind": kind, **payload}
        entry["hash"] = hashlib.sha256((entry["prev"] + _canon({k: v for k, v in entry.items() if k != "prev"})).encode()).hexdigest()
        with self.path.open("a") as f:
            f.write(_canon(entry) + "\n")
        return entry

    def verify(self) -> Optional[str]:
        """Return None if the chain is intact, else a message naming the first bad entry."""
        prev = GENESIS
        for i, e in enumerate(self):
            body = {k: v for k, v in e.items() if k not in ("prev", "hash")}
            want = hashlib.sha256((prev + _canon(body)).encode()).hexdigest()
            if e.get("prev") != prev:
                return f"entry {i}: prev-hash mismatch"
            if e.get("hash") != want:
                return f"entry {i}: hash mismatch"
            prev = e["hash"]
        return None
