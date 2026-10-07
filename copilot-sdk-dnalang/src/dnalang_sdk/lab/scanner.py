"""
Lab Scanner — Discovers quantum experiments and results on the filesystem.
"""

from typing import Dict, Any, List, Optional, Tuple
import os, json, re, hashlib, glob as globmod
from .registry import (
    ExperimentRegistry, ExperimentRecord, ResultRecord,
    ExperimentType, ExperimentStatus,
)


# Pattern → ExperimentType mapping for scripts
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

# Pattern → ExperimentType mapping for result files
RESULT_PATTERNS: List[Tuple[str, ExperimentType]] = [
    (r"bell", ExperimentType.BELL_STATE),
    (r"ghz", ExperimentType.GHZ_STATE),
    (r"w.state|w4_fidelity|phi_total_w", ExperimentType.W_STATE),
    (r"theta.sweep|theta_sweep", ExperimentType.THETA_SWEEP),
    (r"theta.lock|fine.scan", ExperimentType.THETA_LOCK),
    (r"chi.pc|chi_pc|phase.sweep", ExperimentType.CHI_PC),
    (r"aeterna.porta|aeterna_porta|ignition", ExperimentType.AETERNA_PORTA),
    (r"dna.circuit|dna_circuit", ExperimentType.DNA_ENCODED),
    (r"lambda.phi|lambda_phi", ExperimentType.LAMBDA_PHI),
    (r"conscious|ccce|scaling", ExperimentType.CONSCIOUSNESS),
    (r"vacuum", ExperimentType.VACUUM_ENERGY),
    (r"teleport", ExperimentType.TELEPORTATION),
    (r"fidelity", ExperimentType.ENTANGLEMENT),
    (r"ramsey", ExperimentType.RAMSEY),
]


def _classify_script(path: str, content: str) -> Tuple[ExperimentType, str]:
    """Classify a Python script by its content."""
    combined = os.path.basename(path).lower() + " " + content[:2000].lower()
    for pattern, exp_type, desc in SCRIPT_PATTERNS:
        if re.search(pattern, combined):
            return exp_type, desc
    return ExperimentType.CUSTOM, "Quantum experiment"


def _classify_result(path: str) -> ExperimentType:
    """Classify a result file by its name."""
    name = os.path.basename(path).lower()
    for pattern, exp_type in RESULT_PATTERNS:
        if re.search(pattern, name):
            return exp_type
    return ExperimentType.CUSTOM


def _extract_script_metadata(path: str, content: str) -> Dict[str, Any]:
    """Extract metadata from a Python experiment script."""
    meta: Dict[str, Any] = {"backends": [], "qubits": 0, "shots": 0, "has_main": False}

    # Backends
    for backend in ["ibm_fez", "ibm_nighthawk", "ibm_torino", "ibm_brisbane",
                     "ibm_kyoto", "ibm_osaka", "ibm_sherbrooke",
                     "aer_simulator", "AerSimulator", "StatevectorSampler"]:
        if backend in content:
            meta["backends"].append(backend)

    # Qubits
    qm = re.findall(r"QuantumCircuit\((\d+)", content)
    if qm:
        meta["qubits"] = max(int(q) for q in qm)

    # Shots
    sm = re.findall(r"shots\s*[=:]\s*(\d+)", content)
    if sm:
        meta["shots"] = max(int(s) for s in sm)

    # Has main block
    meta["has_main"] = '__name__' in content and '__main__' in content

    # Has qiskit
    meta["uses_qiskit"] = "qiskit" in content

    return meta


def _extract_result_metrics(path: str) -> Dict[str, Any]:
    """Extract key metrics from a JSON result file."""
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return {}

    metrics = {}

    if isinstance(data, dict):
        # Direct metric extraction
        for key in ["fidelity", "phi", "gamma", "ccce", "concurrence",
                     "negativity", "entropy", "chi_pc", "theta_lock",
                     "w2_distance", "success_rate", "phi_total"]:
            if key in data:
                metrics[key] = data[key]

        # Nested in results
        if "results" in data and isinstance(data["results"], list):
            metrics["result_count"] = len(data["results"])
            # Try to get top-level metrics from first result
            if data["results"]:
                first = data["results"][0]
                if isinstance(first, dict):
                    for k in ["fidelity", "phi", "concurrence"]:
                        if k in first:
                            metrics[f"first_{k}"] = first[k]

        # Counts
        if "counts" in data:
            metrics["unique_states"] = len(data["counts"]) if isinstance(data["counts"], dict) else 0

        # Shots
        if "shots" in data:
            metrics["shots"] = data["shots"]

        # Backend
        if "backend" in data:
            metrics["backend"] = data["backend"]

    return metrics


class LabScanner:
    """Filesystem scanner for quantum experiments and results."""

    SCAN_DIRS = [
        "",  # home root
        "quantum_workspace",
        "all experiments",
        "complete_research_archive",
        "repro_job_archives",
        "repro_job_exports",
        "dna_benchmarks",
        "ENKI-420-repos",
        "osiris_cockpit",
        "Desktop",
        "EVIDENCE_VAULT",
        "workloads (5)",
        "Documents",
    ]

    def __init__(self, home: Optional[str] = None):
        self.home = home or os.path.expanduser("~")

    def scan_all(self, registry: ExperimentRegistry) -> Dict[str, int]:
        """Full scan: discover scripts, results, organisms. Returns counts."""
        counts = {
            "scripts": 0,
            "results": 0,
            "organisms": 0,
            "linked": 0,
        }

        scripts = self._scan_scripts()
        results = self._scan_results()
        organisms = self._scan_organisms()

        # Register scripts
        for path, exp_type, desc, meta in scripts:
            eid = self._make_id(path)
            if eid not in registry.experiments:
                record = ExperimentRecord(
                    id=eid,
                    name=os.path.basename(path).replace(".py", ""),
                    exp_type=exp_type,
                    status=ExperimentStatus.CATALOGED,
                    script_path=path,
                    description=desc,
                    backends=meta.get("backends", []),
                    qubits=meta.get("qubits", 0),
                    shots=meta.get("shots", 0),
                    parameters={"has_main": meta.get("has_main", False),
                                "uses_qiskit": meta.get("uses_qiskit", False)},
                    tags=["script", exp_type.value],
                )
                registry.register(record)
                counts["scripts"] += 1

        # Register results and try to link to scripts
        for path, exp_type, metrics, size in results:
            # Try to find matching experiment
            linked = False
            for eid, record in registry.experiments.items():
                if record.exp_type == exp_type and record.script_path:
                    rr = ResultRecord(
                        result_path=path,
                        result_type="json",
                        size_bytes=size,
                        key_metrics=metrics,
                    )
                    record.results.append(rr)
                    record.result_paths.append(path)
                    if record.status == ExperimentStatus.CATALOGED:
                        record.status = ExperimentStatus.COMPLETED
                    linked = True
                    counts["linked"] += 1
                    break

            if not linked:
                # Register as standalone result
                eid = self._make_id(path)
                if eid not in registry.experiments:
                    record = ExperimentRecord(
                        id=eid,
                        name=os.path.basename(path).replace(".json", ""),
                        exp_type=exp_type,
                        status=ExperimentStatus.COMPLETED,
                        results=[ResultRecord(
                            result_path=path,
                            result_type="json",
                            size_bytes=size,
                            key_metrics=metrics,
                        )],
                        result_paths=[path],
                        key_findings=metrics,
                        tags=["result", exp_type.value],
                    )
                    registry.register(record)
                    counts["results"] += 1

        # Register organisms
        for path in organisms:
            eid = self._make_id(path)
            if eid not in registry.experiments:
                record = ExperimentRecord(
                    id=eid,
                    name=os.path.basename(path),
                    exp_type=ExperimentType.DNA_ENCODED,
                    status=ExperimentStatus.DISCOVERED,
                    script_path=path,
                    tags=["organism", "dna"],
                )
                registry.register(record)
                counts["organisms"] += 1

        return counts

    def _scan_scripts(self) -> List[Tuple[str, ExperimentType, str, Dict]]:
        """Find Python scripts with quantum experiment logic."""
        found = []
        seen = set()

        for subdir in self.SCAN_DIRS:
            base = os.path.join(self.home, subdir) if subdir else self.home
            if not os.path.isdir(base):
                continue

            # Scan Python files (1 level for root, recursive for subdirs)
            patterns = [os.path.join(base, "*.py")]
            if subdir:
                patterns.append(os.path.join(base, "**", "*.py"))

            for pattern in patterns:
                for path in globmod.glob(pattern, recursive=True):
                    if path in seen or "__pycache__" in path or "venv" in path or "node_modules" in path or ".git" in path:
                        continue
                    if len(found) >= 500:  # cap at 500 scripts
                        break
                    seen.add(path)
                    try:
                        with open(path, encoding="utf-8", errors="ignore") as f:
                            content = f.read(5000)  # first 5KB
                    except Exception:
                        continue

                    # Must have quantum-related imports
                    if not any(kw in content for kw in [
                        "qiskit", "QuantumCircuit", "quantum", "entangle",
                        "bell_state", "theta_lock", "chi_pc", "aeterna",
                        "lambda_phi", "consciousness", "fidelity",
                    ]):
                        continue

                    exp_type, desc = _classify_script(path, content)
                    meta = _extract_script_metadata(path, content)
                    found.append((path, exp_type, desc, meta))

        return found

    def _scan_results(self) -> List[Tuple[str, ExperimentType, Dict, int]]:
        """Find JSON result files."""
        found = []
        seen = set()

        for subdir in self.SCAN_DIRS:
            base = os.path.join(self.home, subdir) if subdir else self.home
            if not os.path.isdir(base):
                continue

            patterns = [os.path.join(base, "*.json")]
            if subdir:
                patterns.append(os.path.join(base, "**", "*.json"))

            for pattern in patterns:
                for path in globmod.glob(pattern, recursive=True):
                    if path in seen or "__pycache__" in path or "node_modules" in path or ".git" in path:
                        continue
                    if len(found) >= 500:
                        break
                    seen.add(path)

                    name = os.path.basename(path).lower()
                    # Filter for quantum-relevant JSON
                    quantum_keywords = [
                        "result", "experiment", "fidelity", "quantum", "sweep",
                        "theta", "phi", "bell", "chi", "ghz", "aeterna", "job-",
                        "lambda", "consciousness", "entangle", "w4_", "w_state",
                        "dna_circuit", "ramsey", "ignition", "physics",
                    ]
                    if not any(kw in name for kw in quantum_keywords):
                        continue

                    try:
                        size = os.path.getsize(path)
                    except Exception:
                        size = 0

                    # Skip very large files (>50MB) and tiny files (<10B)
                    if size > 50_000_000 or size < 10:
                        continue

                    exp_type = _classify_result(path)
                    metrics = _extract_result_metrics(path) if size < 5_000_000 else {}
                    found.append((path, exp_type, metrics, size))

        return found

    def _scan_organisms(self) -> List[str]:
        """Find .dna organism files."""
        found = []
        for subdir in self.SCAN_DIRS:
            base = os.path.join(self.home, subdir) if subdir else self.home
            if not os.path.isdir(base):
                continue
            for pattern in [os.path.join(base, "*.dna"),
                            os.path.join(base, "**", "*.dna")]:
                for path in globmod.glob(pattern, recursive=True):
                    if path not in found:
                        found.append(path)

        # Also find organism_state.json and genesis_manifest.json
        for fname in ["organism_state.json", "genesis_manifest.json"]:
            fp = os.path.join(self.home, fname)
            if os.path.exists(fp):
                found.append(fp)

        return found

    def _make_id(self, path: str) -> str:
        """Generate a stable ID from a file path."""
        rel = os.path.relpath(path, self.home)
        return hashlib.md5(rel.encode()).hexdigest()[:12]
