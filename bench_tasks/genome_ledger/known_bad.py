
import hashlib
import json
import time


class GenomeLedger:
    def __init__(self, filepath=None):
        self.filepath = filepath
        self.chain = []

    def _calculate_hash(self, index, timestamp, entry_type, payload, prev_hash):
        payload_str = json.dumps(payload, sort_keys=True)
        raw = f"{index}{timestamp}{entry_type}{payload_str}{prev_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def append(self, entry_type, payload):
        index = len(self.chain)
        timestamp = time.time()
        prev_hash = self.chain[-1]["hash"] if self.chain else "0" * 64
        entry_hash = self._calculate_hash(index, timestamp, entry_type, payload, prev_hash)

        block = {
            "index": index,
            "timestamp": timestamp,
            "entry_type": entry_type,
            "payload": payload,
            "prev_hash": prev_hash,
            "hash": entry_hash,
        }
        self.chain.append(block)
        if self.filepath:
            self.save()
        return block

    def verify(self):
        for i, block in enumerate(self.chain):
            if block["index"] != i:
                return False
            expected_prev = self.chain[i - 1]["hash"] if i > 0 else "0" * 64
            if block["prev_hash"] != expected_prev:
                return False
            calc_hash = self._calculate_hash(
                block["index"],
                block["timestamp"],
                block["entry_type"],
                block["payload"],
                block["prev_hash"],
            )
            if block["hash"] != calc_hash:
                return False
        return True

    def save(self):
        if self.filepath:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.chain, f, indent=2)

    def load(self):
        if self.filepath:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.chain = json.load(f)
        return self.verify()
