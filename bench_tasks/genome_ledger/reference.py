import hashlib
import json
import os

GENESIS = "0" * 64


def _canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def _digest(entry_without_hash):
    return hashlib.sha256((entry_without_hash["prev"] + _canon(entry_without_hash)).encode()).hexdigest()


class GenomeLedger:
    def __init__(self, path):
        self.path = path

    def _entries(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def append(self, kind, payload):
        entries = self._entries()
        entry = {"kind": kind, "payload": payload, "prev": entries[-1]["hash"] if entries else GENESIS}
        entry["hash"] = _digest(entry)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(_canon(entry) + "\n")
        return entry

    def verify(self):
        try:
            entries = self._entries()
        except json.JSONDecodeError:
            return False
        prev = GENESIS
        for e in entries:
            body = {k: v for k, v in e.items() if k != "hash"}
            if e.get("prev") != prev or e.get("hash") != _digest(body):
                return False
            prev = e["hash"]
        return True
