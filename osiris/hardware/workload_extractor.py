"""
IBM Quantum Workload Substrate Extractor — processes job results through
phase-conjugate substrate pipeline.
"""

import hashlib
import json
import math
import os
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    from osiris.defense.phase_conjugate import (
        PhaseConjugateSubstratePreprocessor,
        PlanckConstants,
        UniversalConstants,
        SphericalTrig,
        SphericalTetrahedron,
    )
    _HAS_PHASE_CONJUGATE = True
except ImportError:
    _HAS_PHASE_CONJUGATE = False


# ─────────────────────────────────────────────────────────────
# IBM Quantum Backend Specifications
# ─────────────────────────────────────────────────────────────

@dataclass
class IBMBackendSpec:
    name: str
    processor: str
    num_qubits: int
    t1_us: float
    t2_us: float
    readout_error: float
    cx_error: float
    documented_fidelity: float

    @property
    def decoherence_rate(self) -> float:
        return 1.0 / (self.t2_us * 1e-6) if self.t2_us > 0 else 0.1

    @property
    def lambda_coherence(self) -> float:
        return self.documented_fidelity * (1 - self.readout_error)


IBM_BACKENDS = {
    "ibm_brisbane": IBMBackendSpec("ibm_brisbane", "Eagle r3", 127, 250.0, 150.0, 0.015, 0.008, 0.869),
    "ibm_torino": IBMBackendSpec("ibm_torino", "Heron", 133, 300.0, 200.0, 0.012, 0.006, 0.88),
    "ibm_kyoto": IBMBackendSpec("ibm_kyoto", "Eagle r1", 127, 200.0, 100.0, 0.018, 0.010, 0.85),
    "ibm_osaka": IBMBackendSpec("ibm_osaka", "Eagle r1", 127, 220.0, 120.0, 0.016, 0.009, 0.86),
    "ibm_fez": IBMBackendSpec("ibm_fez", "Heron", 156, 350.0, 250.0, 0.010, 0.005, 0.90),
}


# ─────────────────────────────────────────────────────────────
# Job Result Structure
# ─────────────────────────────────────────────────────────────

@dataclass
class QuantumJobResult:
    job_id: str
    backend: str
    shots: int
    counts: Dict[str, int]
    timestamp: str
    circuit_depth: int = 0
    num_qubits: int = 2
    execution_time_s: float = 0.0

    @property
    def probabilities(self) -> Dict[str, float]:
        total = sum(self.counts.values())
        return {k: v / total for k, v in self.counts.items()} if total > 0 else {}

    @property
    def bell_fidelity(self) -> float:
        if self.num_qubits != 2:
            return 0.0
        n00 = self.counts.get("00", 0)
        n11 = self.counts.get("11", 0)
        total = sum(self.counts.values())
        return (n00 + n11) / total if total > 0 else 0.0

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "backend": self.backend,
            "shots": self.shots,
            "counts": self.counts,
            "probabilities": self.probabilities,
            "bell_fidelity": self.bell_fidelity,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────
# Workload Extractor
# ─────────────────────────────────────────────────────────────

@dataclass
class WorkloadExtractor:
    """Extracts quantum job results from workloads.zip files."""

    def __post_init__(self):
        self.extracted_jobs: List[QuantumJobResult] = []
        self.extraction_log: List[Dict] = []

    def extract_from_zip(self, zip_path: str) -> List[QuantumJobResult]:
        jobs: List[QuantumJobResult] = []
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for filename in zf.namelist():
                    if filename.endswith(".json"):
                        with zf.open(filename) as f:
                            try:
                                data = json.load(f)
                                job = self._parse_job_json(data, filename)
                                if job:
                                    jobs.append(job)
                            except json.JSONDecodeError:
                                self.extraction_log.append(
                                    {"file": filename, "status": "JSON_PARSE_ERROR"}
                                )
        except zipfile.BadZipFile:
            self.extraction_log.append({"path": zip_path, "status": "BAD_ZIP_FILE"})
        self.extracted_jobs.extend(jobs)
        return jobs

    def _parse_job_json(self, data: Dict, filename: str) -> Optional[QuantumJobResult]:
        try:
            if "results" in data:
                result = data["results"][0] if data["results"] else {}
                counts = result.get("data", {}).get("counts", {})
                counts = self._hex_to_binary_counts(counts)
            elif "counts" in data:
                counts = data["counts"]
            else:
                return None
            return QuantumJobResult(
                job_id=data.get("job_id", data.get("id", hashlib.md5(filename.encode()).hexdigest()[:12])),
                backend=data.get("backend", data.get("backend_name", "unknown")),
                shots=data.get("shots", sum(counts.values())),
                counts=counts,
                timestamp=data.get("date", data.get("timestamp", datetime.utcnow().isoformat())),
                circuit_depth=data.get("depth", 0),
                num_qubits=self._infer_num_qubits(counts),
            )
        except Exception:
            return None

    @staticmethod
    def _hex_to_binary_counts(counts: Dict[str, int]) -> Dict[str, int]:
        result = {}
        for key, value in counts.items():
            if key.startswith("0x"):
                binary = bin(int(key, 16))[2:]
                result[binary.zfill(2)] = value
            else:
                result[key] = value
        return result

    @staticmethod
    def _infer_num_qubits(counts: Dict[str, int]) -> int:
        if not counts:
            return 0
        max_key = max(counts.keys(), key=len)
        return len(max_key.replace(" ", ""))

    def create_synthetic_job(self, backend_name: str = "ibm_brisbane",
                             shots: int = 8192, fidelity: float = 0.869) -> QuantumJobResult:
        import random
        p_correlated = fidelity
        p_00 = p_correlated * 0.5
        p_11 = p_correlated - p_00
        p_01 = (1 - p_correlated) * 0.5
        p_10 = 1 - p_00 - p_11 - p_01
        counts = {
            "00": int(shots * p_00),
            "01": int(shots * p_01),
            "10": int(shots * p_10),
            "11": int(shots * p_11),
        }
        counts["00"] += shots - sum(counts.values())
        return QuantumJobResult(
            job_id=f"synth_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}",
            backend=backend_name,
            shots=shots,
            counts=counts,
            timestamp=datetime.utcnow().isoformat() + "Z",
            circuit_depth=5,
            num_qubits=2,
        )


# ─────────────────────────────────────────────────────────────
# Substrate Pipeline
# ─────────────────────────────────────────────────────────────

@dataclass
class SubstratePipeline:
    """Transforms IBM Quantum workloads into phase-conjugate substrate representations."""

    def __post_init__(self):
        self.extractor = WorkloadExtractor()
        self.pipeline_log: List[Dict] = []

    def process_job(self, job: QuantumJobResult) -> Dict[str, Any]:
        backend_spec = IBM_BACKENDS.get(job.backend)
        coherence = backend_spec.lambda_coherence if backend_spec else job.bell_fidelity
        gamma = backend_spec.decoherence_rate if backend_spec else 0.1
        return {
            "job_metadata": job.to_dict(),
            "coherence_estimate": coherence,
            "gamma_estimate": gamma,
            "backend_spec": {
                "processor": backend_spec.processor,
                "num_qubits": backend_spec.num_qubits,
                "documented_fidelity": backend_spec.documented_fidelity,
            } if backend_spec else None,
        }
