"""
Experiment Registry — Structured catalog of quantum experiments.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time, json, os, hashlib


class ExperimentType(Enum):
    BELL_STATE = "bell_state"
    GHZ_STATE = "ghz_state"
    W_STATE = "w_state"
    THETA_SWEEP = "theta_sweep"
    THETA_LOCK = "theta_lock"
    CHI_PC = "chi_pc"
    AETERNA_PORTA = "aeterna_porta"
    DNA_ENCODED = "dna_encoded"
    LAMBDA_PHI = "lambda_phi"
    CONSCIOUSNESS = "consciousness"
    VACUUM_ENERGY = "vacuum_energy"
    TELEPORTATION = "teleportation"
    ERROR_MITIGATION = "error_mitigation"
    ENTANGLEMENT = "entanglement"
    RAMSEY = "ramsey"
    CUSTOM = "custom"


class ExperimentStatus(Enum):
    DISCOVERED = "discovered"     # Found on filesystem
    CATALOGED = "cataloged"       # Metadata extracted
    DESIGNED = "designed"         # Created by designer, not yet run
    QUEUED = "queued"             # Ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ANALYZED = "analyzed"         # Results analyzed


@dataclass
class ResultRecord:
    """A single experiment result."""
    result_path: str
    result_type: str  # "json", "log", "csv"
    size_bytes: int = 0
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def summary_line(self) -> str:
        metrics = ", ".join(f"{k}={v}" for k, v in list(self.key_metrics.items())[:4])
        return f"{os.path.basename(self.result_path)} ({self.size_bytes:,}B) {metrics}"


@dataclass
class ExperimentRecord:
    """A cataloged quantum experiment."""
    id: str
    name: str
    exp_type: ExperimentType
    status: ExperimentStatus
    script_path: Optional[str] = None
    result_paths: List[str] = field(default_factory=list)
    results: List[ResultRecord] = field(default_factory=list)
    description: str = ""
    backends: List[str] = field(default_factory=list)
    qubits: int = 0
    shots: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    key_findings: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.exp_type.value,
            "status": self.status.value,
            "script": self.script_path,
            "results": [r.result_path for r in self.results],
            "description": self.description,
            "backends": self.backends,
            "qubits": self.qubits,
            "shots": self.shots,
            "parameters": self.parameters,
            "key_findings": self.key_findings,
            "tags": self.tags,
        }


class ExperimentRegistry:
    """Central registry of all quantum experiments."""

    def __init__(self, persist_path: Optional[str] = None):
        self.experiments: Dict[str, ExperimentRecord] = {}
        self.persist_path = persist_path or os.path.expanduser(
            "~/.config/osiris/lab_registry.json"
        )

    def register(self, record: ExperimentRecord) -> str:
        """Register an experiment, return its ID."""
        self.experiments[record.id] = record
        return record.id

    def get(self, exp_id: str) -> Optional[ExperimentRecord]:
        return self.experiments.get(exp_id)

    def list_all(
        self,
        exp_type: Optional[ExperimentType] = None,
        status: Optional[ExperimentStatus] = None,
        tag: Optional[str] = None,
    ) -> List[ExperimentRecord]:
        """List experiments with optional filters."""
        results = list(self.experiments.values())
        if exp_type:
            results = [r for r in results if r.exp_type == exp_type]
        if status:
            results = [r for r in results if r.status == status]
        if tag:
            results = [r for r in results if tag in r.tags]
        return sorted(results, key=lambda r: r.updated_at, reverse=True)

    def search(self, query: str) -> List[ExperimentRecord]:
        """Search experiments by name, description, or tags."""
        q = query.lower()
        return [
            r for r in self.experiments.values()
            if q in r.name.lower()
            or q in r.description.lower()
            or any(q in t.lower() for t in r.tags)
        ]

    def stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        total_results = 0
        for r in self.experiments.values():
            by_type[r.exp_type.value] = by_type.get(r.exp_type.value, 0) + 1
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
            total_results += len(r.results)
        return {
            "total_experiments": len(self.experiments),
            "total_results": total_results,
            "by_type": by_type,
            "by_status": by_status,
        }

    def save(self):
        """Persist registry to disk."""
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        data = {
            "version": "1.0",
            "saved_at": time.time(),
            "experiments": {
                k: v.to_dict() for k, v in self.experiments.items()
            },
        }
        with open(self.persist_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load(self) -> int:
        """Load registry from disk. Returns count loaded."""
        if not os.path.exists(self.persist_path):
            return 0
        try:
            with open(self.persist_path) as f:
                data = json.load(f)
            for eid, edata in data.get("experiments", {}).items():
                if eid not in self.experiments:
                    record = ExperimentRecord(
                        id=eid,
                        name=edata.get("name", eid),
                        exp_type=ExperimentType(edata.get("type", "custom")),
                        status=ExperimentStatus(edata.get("status", "discovered")),
                        script_path=edata.get("script"),
                        description=edata.get("description", ""),
                        backends=edata.get("backends", []),
                        qubits=edata.get("qubits", 0),
                        shots=edata.get("shots", 0),
                        parameters=edata.get("parameters", {}),
                        key_findings=edata.get("key_findings", {}),
                        tags=edata.get("tags", []),
                    )
                    self.experiments[eid] = record
            return len(data.get("experiments", {}))
        except Exception:
            return 0
