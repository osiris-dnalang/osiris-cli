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


def _line_on_device(graph, n):
    """A simple path of n connected qubits, found deterministically: depth-first from each qubit in sorted order."""
    nodes = sorted(graph.nodes)

    def extend(path):
        if len(path) == n:
            return path
        for nb in sorted(graph.neighbors(path[-1])):
            if nb not in path:
                found = extend(path + [nb])
                if found:
                    return found
        return None
    for start in nodes:
        found = extend([start])
        if found:
            return found
    raise ValueError(f"no path of {n} connected qubits")


def cirq_qvm_sampler(processor_id, n, seed=0):
    """Google Quantum Virtual Machine: a device noise model shipped with cirq-google (e.g. 'willow_pink'),
    simulated with qsim. Circuits are compiled to the CZ gateset and validated against the device."""
    import cirq
    import cirq_google
    import qsimcirq
    props = cirq_google.engine.load_device_noise_properties(processor_id)
    noise = cirq_google.NoiseModelFromGoogleNoiseProperties(props)
    device = cirq_google.engine.create_device_from_processor_id(processor_id)
    qubits = _line_on_device(device.metadata.nx_graph, n)
    sim = qsimcirq.QSimSimulator(noise=noise, seed=seed)
    from .circuits import to_cirq

    def sample(circuit, shots):
        c = cirq.optimize_for_target_gateset(to_cirq(circuit, qubits), gateset=cirq.CZTargetGateset())
        device.validate_circuit(c)
        bits = sim.run(c, repetitions=shots).measurements["m"]          # shots x n, column q = qubit q
        weights = 1 << np.arange(circuit.n - 1, -1, -1)
        return (bits.astype(np.int64) * weights).sum(axis=1)

    record = {"backend": f"cirq-qvm:{processor_id}", "qubits": [str(q) for q in qubits],
              "noise_source": "cirq_google.engine.load_device_noise_properties (shipped median calibration)"}
    return sample, record
