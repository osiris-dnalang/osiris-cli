"""osiris.quantum — Quantum simulation, benchmarking, RQC."""

import importlib as _il


def __getattr__(name):
    _map = {
        "local_qvm": "osiris.quantum.local_qvm",
        "benchmarker": "osiris.quantum.benchmarker",
        "benchmark_suite": "osiris.quantum.benchmark_suite",
        "rqc_framework": "osiris.quantum.rqc_framework",
        "rqc_orchestrator": "osiris.quantum.rqc_orchestrator",
    }
    if name in _map:
        return _il.import_module(_map[name])
    raise AttributeError(f"module 'osiris.quantum' has no attribute {name!r}")
