"""Samplers: `sampler(circuit, shots) -> numpy array of basis indices` (qubit 0 most significant).

aer_sampler_from_backend builds a noisy simulator from an IBM backend's current calibration (read-only: it fetches
the backend target; nothing is submitted) and returns the sampler plus a calibration record for the ledger.
Requires qiskit, qiskit-aer and qiskit-ibm-runtime (optional extras).
"""
import hashlib
import json

import numpy as np

from .circuits import to_qiskit


def counts_to_indices(counts):
    """Qiskit counts (keys 'q(n-1)...q0') -> array of indices with qubit 0 most significant."""
    out = []
    for key, c in counts.items():
        out.extend([int(key.replace(" ", "")[::-1], 2)] * c)
    return np.array(out, dtype=np.int64)


def calibration_record(backend):
    props = backend.properties()
    d = props.to_dict() if props is not None else {}
    blob = json.dumps(d, sort_keys=True, default=str).encode()
    return {"backend": backend.name, "last_update_date": str(d.get("last_update_date")),
            "calibration_sha256": hashlib.sha256(blob).hexdigest()}


def aer_sampler_from_backend(backend, layout, seed=0, optimization_level=1):
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    sim = AerSimulator.from_backend(backend)
    rng = np.random.default_rng(seed)

    def sample(circuit, shots):
        if len(layout) != circuit.n:
            raise ValueError("layout must name one physical qubit per circuit qubit")
        tqc = transpile(to_qiskit(circuit), backend=backend, initial_layout=list(layout),
                        optimization_level=optimization_level, seed_transpiler=0)
        res = sim.run(tqc, shots=shots, seed_simulator=int(rng.integers(2**31))).result()
        return counts_to_indices(res.get_counts())

    return sample, calibration_record(backend)
