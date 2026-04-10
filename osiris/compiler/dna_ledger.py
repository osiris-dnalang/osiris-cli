"""
DNA-Lang Immutable Ledger — Cryptographic lineage tracking for quantum organisms.
"""

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class LineageEntry:
    lineage_hash: str
    organism_name: str
    generation: int
    parent_hash: Optional[str] = None
    ancestor_hashes: List[str] = field(default_factory=list)
    gate_count: int = 0
    circuit_depth: int = 0
    qubit_count: int = 0
    qasm_hash: str = ""
    lambda_coherence: float = 0.0
    gamma_decoherence: float = 0.0
    phi_integrated_info: float = 0.0
    fitness_score: float = 0.0
    execution_backend: Optional[str] = None
    execution_timestamp: Optional[str] = None
    execution_fidelity: float = 0.0
    measurement_counts: Dict[str, int] = field(default_factory=dict)
    created_at: str = ""
    verified: bool = False
    verification_hash: str = ""

    def compute_verification_hash(self) -> str:
        data = (
            f"{self.lineage_hash}:{self.organism_name}:{self.generation}:"
            f"{self.parent_hash}:{self.gate_count}:{self.circuit_depth}:"
            f"{self.fitness_score}:{self.created_at}"
        )
        self.verification_hash = hashlib.sha256(data.encode()).hexdigest()
        return self.verification_hash

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvolutionLineage:
    root_hash: str
    root_organism: str
    current_generation: int
    entries: List[LineageEntry] = field(default_factory=list)
    total_organisms: int = 0
    avg_fitness: float = 0.0
    best_fitness: float = 0.0
    best_organism_hash: str = ""
    fitness_breakthroughs: List[Dict[str, Any]] = field(default_factory=list)

    def add_entry(self, entry: LineageEntry):
        self.entries.append(entry)
        self.total_organisms += 1
        self.current_generation = max(self.current_generation, entry.generation)
        fitnesses = [e.fitness_score for e in self.entries]
        self.avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
        if entry.fitness_score > self.best_fitness:
            self.best_fitness = entry.fitness_score
            self.best_organism_hash = entry.lineage_hash
            self.fitness_breakthroughs.append({
                "generation": entry.generation,
                "fitness": entry.fitness_score,
                "lineage_hash": entry.lineage_hash,
            })


class QuantumLedger:
    """JSON-based immutable ledger for quantum organism lineages."""

    def __init__(self, ledger_path: str = "quantum_ledger.json"):
        self.ledger_path = Path(ledger_path)
        self.entries: Dict[str, LineageEntry] = {}
        self.lineages: Dict[str, EvolutionLineage] = {}

    def record_entry(self, entry: LineageEntry) -> str:
        if not entry.created_at:
            entry.created_at = str(time.time())
        entry.compute_verification_hash()
        self.entries[entry.lineage_hash] = entry
        return entry.lineage_hash

    def get_entry(self, lineage_hash: str) -> Optional[LineageEntry]:
        return self.entries.get(lineage_hash)

    def get_lineage(self, organism_name: str) -> List[LineageEntry]:
        return sorted(
            [e for e in self.entries.values() if e.organism_name == organism_name],
            key=lambda e: e.generation,
        )

    def save(self):
        data = {
            "version": "1.0",
            "saved_at": time.time(),
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
        }
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load(self) -> int:
        if not self.ledger_path.exists():
            return 0
        try:
            with open(self.ledger_path) as f:
                data = json.load(f)
            for lh, edata in data.get("entries", {}).items():
                if lh not in self.entries:
                    self.entries[lh] = LineageEntry(**{
                        k: v for k, v in edata.items()
                        if k in LineageEntry.__dataclass_fields__
                    })
            return len(data.get("entries", {}))
        except Exception:
            return 0

    def stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self.entries),
            "organisms": len(set(e.organism_name for e in self.entries.values())),
            "max_generation": max(
                (e.generation for e in self.entries.values()), default=0
            ),
            "best_fitness": max(
                (e.fitness_score for e in self.entries.values()), default=0.0
            ),
        }
