"""
CHRONOS: Temporal / Lineage Tracking Scribe
============================================

Tracks the temporal evolution of organisms and maintains the
immutable ledger of state transitions across the 11D-CRSM manifold.

Pole: Center (Spine)
Function: Temporal tracking, lineage recording, telemetry
"""

from typing import Dict, Any, List, Optional
import time, hashlib, json


class CHRONOS:
    """Temporal lineage tracker and telemetry scribe.

    Records every state transition with cryptographic chaining
    to produce a non-repudiable history of organism evolution.
    """

    def __init__(self):
        self.role = "scribe"
        self.pole = "center"
        self.ledger: List[Dict[str, Any]] = []
        self._prev_hash = "0" * 64  # genesis

    def record(
        self,
        event_type: str,
        organism_name: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a state transition in the immutable ledger.

        Each entry is hash-chained to the previous for integrity.
        """
        entry = {
            "seq": len(self.ledger),
            "timestamp": time.time(),
            "event_type": event_type,
            "organism": organism_name,
            "data": data or {},
            "prev_hash": self._prev_hash,
        }
        payload = json.dumps(entry, sort_keys=True, default=str)
        entry["hash"] = hashlib.sha256(payload.encode()).hexdigest()
        self._prev_hash = entry["hash"]
        self.ledger.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire ledger chain."""
        prev = "0" * 64
        for entry in self.ledger:
            if entry["prev_hash"] != prev:
                return False
            check = dict(entry)
            check.pop("hash")
            payload = json.dumps(check, sort_keys=True, default=str)
            expected = hashlib.sha256(payload.encode()).hexdigest()
            if entry["hash"] != expected:
                return False
            prev = entry["hash"]
        return True

    def get_lineage(self, organism_name: str) -> List[Dict[str, Any]]:
        """Get all ledger entries for a specific organism."""
        return [e for e in self.ledger if e["organism"] == organism_name]

    def get_telemetry_summary(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "pole": self.pole,
            "total_entries": len(self.ledger),
            "chain_valid": self.verify_chain(),
            "organisms_tracked": len(set(e["organism"] for e in self.ledger)),
        }

    def __repr__(self) -> str:
        return f"CHRONOS(role='{self.role}', entries={len(self.ledger)})"
