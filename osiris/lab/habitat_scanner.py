"""
Habitat Scanner — Zero-dependency filesystem task ingestion
===========================================================

Scans workspace directories for organisms (.dna, .json), experiment
scripts (.py), result files, and genome snapshots.  Produces a
unified inventory without network calls or external packages.
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import json
import hashlib
import re
import time


class HabitatEntry:
    """Single item discovered in the habitat."""

    __slots__ = ("path", "kind", "name", "sha256", "size_bytes", "metadata", "discovered_at")

    def __init__(self, path: str, kind: str, name: str, sha256: str,
                 size_bytes: int, metadata: Optional[Dict[str, Any]] = None):
        self.path = path
        self.kind = kind
        self.name = name
        self.sha256 = sha256
        self.size_bytes = size_bytes
        self.metadata = metadata or {}
        self.discovered_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "name": self.name,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "discovered_at": self.discovered_at,
        }


# Classify by extension + content heuristics
_EXT_MAP = {
    ".dna": "organism",
    ".json": "data",
    ".py": "script",
    ".qasm": "circuit",
    ".toml": "config",
    ".md": "doc",
    ".csv": "data",
    ".txt": "data",
}

_ORGANISM_KEYS = {"genes", "genome", "name", "domain", "purpose"}
_RESULT_KEYS = {"fidelity", "phi", "gamma", "counts", "backend"}


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _classify_json(path: str) -> Tuple[str, Dict[str, Any]]:
    """Distinguish organism descriptors from result dumps."""
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return "data", {}
    if not isinstance(data, dict):
        return "data", {}
    keys = set(data.keys())
    if keys & _ORGANISM_KEYS:
        return "organism", {"organism_name": data.get("name", "")}
    if keys & _RESULT_KEYS:
        return "result", {k: data[k] for k in _RESULT_KEYS & keys}
    return "data", {}


def _classify_py(path: str) -> Tuple[str, Dict[str, Any]]:
    """Detect quantum experiment scripts."""
    try:
        with open(path) as f:
            head = f.read(4096)
    except OSError:
        return "script", {}
    meta: Dict[str, Any] = {}
    if re.search(r"QuantumCircuit|qiskit|cirq|dna_ir", head, re.I):
        kind = "quantum_script"
    elif re.search(r"evolve|genome|organism|population", head, re.I):
        kind = "evolution_script"
    elif re.search(r"import osiris|from osiris", head, re.I):
        kind = "osiris_script"
    else:
        kind = "script"
    meta["has_main"] = "__name__" in head and "__main__" in head
    return kind, meta


class HabitatScanner:
    """Scan filesystem directories and produce an inventory."""

    IGNORE_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache", ".pytest_cache"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB cap

    def __init__(self, roots: Optional[List[str]] = None):
        self.roots = roots or ["."]
        self.inventory: List[HabitatEntry] = []

    def scan(self, roots: Optional[List[str]] = None) -> List[HabitatEntry]:
        """Walk *roots* (defaults to init roots) and classify every file."""
        self.inventory.clear()
        for root in (roots or self.roots):
            self._walk(root)
        return list(self.inventory)

    def _walk(self, root: str):
        if not os.path.isdir(root):
            return
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in self.IGNORE_DIRS]
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size > self.MAX_FILE_SIZE:
                    continue
                ext = os.path.splitext(fname)[1].lower()
                kind = _EXT_MAP.get(ext, "unknown")
                meta: Dict[str, Any] = {}

                # Deeper classification
                if ext == ".json":
                    kind, meta = _classify_json(path)
                elif ext == ".py":
                    kind, meta = _classify_py(path)

                entry = HabitatEntry(
                    path=path,
                    kind=kind,
                    name=os.path.splitext(fname)[0],
                    sha256=_file_sha256(path),
                    size_bytes=size,
                    metadata=meta,
                )
                self.inventory.append(entry)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def organisms(self) -> List[HabitatEntry]:
        return [e for e in self.inventory if e.kind == "organism"]

    def scripts(self) -> List[HabitatEntry]:
        return [e for e in self.inventory if e.kind.endswith("script")]

    def results(self) -> List[HabitatEntry]:
        return [e for e in self.inventory if e.kind == "result"]

    def by_kind(self, kind: str) -> List[HabitatEntry]:
        return [e for e in self.inventory if e.kind == kind]

    def summary(self) -> Dict[str, Any]:
        kinds: Dict[str, int] = {}
        total_bytes = 0
        for e in self.inventory:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
            total_bytes += e.size_bytes
        return {
            "total_files": len(self.inventory),
            "total_bytes": total_bytes,
            "kinds": kinds,
            "roots": self.roots,
        }

    def to_dict(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.inventory]
