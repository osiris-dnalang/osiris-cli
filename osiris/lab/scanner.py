"""
Lab Scanner — Discovers quantum experiments and results on the filesystem.
"""

from typing import Dict, Any, List, Optional, Tuple
import os
import json
import re
import hashlib
from .registry import (
    ExperimentRegistry,
    ExperimentRecord,
    ResultRecord,
    ExperimentType,
    ExperimentStatus,
)

SCRIPT_PATTERNS: List[Tuple[str, ExperimentType, str]] = [
    (r"bell.state|bell_state|create_bell", ExperimentType.BELL_STATE, "Bell state preparation"),
    (r"ghz.state|ghz_state|create_ghz", ExperimentType.GHZ_STATE, "GHZ state preparation"),
    (r"w.state|w_state|phi_total_w", ExperimentType.W_STATE, "W-state entanglement"),
    (r"theta.sweep|theta_sweep|angle.sweep", ExperimentType.THETA_SWEEP, "Theta parameter sweep"),
    (r"theta.lock|theta_lock|fine.scan", ExperimentType.THETA_LOCK, "Theta lock verification"),
    (r"chi.pc|chi_pc|phase.conjugat", ExperimentType.CHI_PC, "Chi-PC phase conjugation"),
    (r"aeterna.porta|aeterna_porta|ignition", ExperimentType.AETERNA_PORTA, "Aeterna Porta deployment"),
    (r"dna.circuit|dna_circuit|dna.encod", ExperimentType.DNA_ENCODED, "DNA-encoded circuit"),
    (r"lambda.phi|lambda_phi|conservation", ExperimentType.LAMBDA_PHI, "Lambda-Phi conservation"),
    (r"conscious|ccce|scaling", ExperimentType.CONSCIOUSNESS, "Consciousness scaling"),
    (r"vacuum.energy|vacuum_energy|casimir", ExperimentType.VACUUM_ENERGY, "Vacuum energy"),
    (r"teleport|omega_teleport", ExperimentType.TELEPORTATION, "Quantum teleportation"),
    (r"error.mitigat|zne|mitiq", ExperimentType.ERROR_MITIGATION, "Error mitigation"),
    (r"entangle|concurrence|negativity", ExperimentType.ENTANGLEMENT, "Entanglement witness"),
    (r"ramsey|spectroscop", ExperimentType.RAMSEY, "Ramsey spectroscopy"),
]


def _classify_script(path: str, content: str) -> Tuple[ExperimentType, str]:
    combined = os.path.basename(path).lower() + " " + content[:2000].lower()
    for pattern, exp_type, desc in SCRIPT_PATTERNS:
        if re.search(pattern, combined):
            return exp_type, desc
    return ExperimentType.CUSTOM, "Quantum experiment"


def _extract_script_metadata(path: str, content: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"backends": [], "qubits": 0, "shots": 0, "has_main": False}
    for backend in ["ibm_fez", "ibm_nighthawk", "ibm_torino", "ibm_brisbane",
                     "ibm_kyoto", "ibm_osaka", "ibm_sherbrooke",
                     "aer_simulator", "AerSimulator", "StatevectorSampler"]:
        if backend in content:
            meta["backends"].append(backend)
    qm = re.findall(r"QuantumCircuit\((\d+)", content)
    if qm:
        meta["qubits"] = max(int(q) for q in qm)
    sm = re.findall(r"shots\s*[=:]\s*(\d+)", content)
    if sm:
        meta["shots"] = max(int(s) for s in sm)
    meta["has_main"] = "__name__" in content and "__main__" in content
    meta["uses_qiskit"] = "qiskit" in content
    return meta


def _extract_result_metrics(path: str) -> Dict[str, Any]:
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return {}
    metrics = {}
    if isinstance(data, dict):
        for key in ["fidelity", "phi", "gamma", "ccce", "concurrence",
                     "negativity", "entropy", "chi_pc", "theta_lock",
                     "w2_distance", "success_rate", "phi_total"]:
            if key in data:
                metrics[key] = data[key]
        if "counts" in data:
            metrics["unique_states"] = len(data["counts"]) if isinstance(data["counts"], dict) else 0
        if "shots" in data:
            metrics["shots"] = data["shots"]
        if "backend" in data:
            metrics["backend"] = data["backend"]
    return metrics


class LabScanner:
    """Filesystem scanner for quantum experiments and results."""

    def __init__(self, home: Optional[str] = None):
        self.home = home or os.path.expanduser("~")

    def scan_scripts(self, directory: str) -> List[Tuple[str, ExperimentType, str, Dict]]:
        results = []
        if not os.path.isdir(directory):
            return results
        for root, dirs, files in os.walk(directory):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, errors="replace") as f:
                        content = f.read(4096)
                except Exception:
                    continue
                exp_type, desc = _classify_script(path, content)
                meta = _extract_script_metadata(path, content)
                results.append((path, exp_type, desc, meta))
        return results

    def scan_results(self, directory: str) -> List[Tuple[str, Dict]]:
        results = []
        if not os.path.isdir(directory):
            return results
        for root, dirs, files in os.walk(directory):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(root, fname)
                metrics = _extract_result_metrics(path)
                if metrics:
                    results.append((path, metrics))
        return results
