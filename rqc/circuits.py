"""Circuit families with a fixed layer structure.

A circuit on n qubits with depth d has d layers. Each layer applies U(θ, φ, λ) = Rz(φ)·Ry(θ)·Rz(λ) to every qubit,
then CZ on a brickwork of nearest-neighbour pairs on a line: pairs (i, i+1) with i ≡ layer (mod 2). The structure,
and so the two-qubit gate count, depends only on (n, d); circuits differ only in their single-qubit angles. This is
what makes the adaptive and random arms comparable.
"""
from dataclasses import dataclass
import hashlib
import json

import numpy as np


@dataclass(frozen=True)
class Circuit:
    n: int
    depth: int
    angles: tuple          # depth x n x 3, as nested tuples of floats

    def cz_pairs(self, layer):
        return [(i, i + 1) for i in range(layer % 2, self.n - 1, 2)]

    @property
    def two_qubit_gates(self):
        return sum(len(self.cz_pairs(layer)) for layer in range(self.depth))

    def structure(self):
        return (self.n, self.depth, tuple(tuple(self.cz_pairs(layer)) for layer in range(self.depth)))

    def digest(self):
        """SHA-256 of the canonical circuit (angles rounded to 1e-12), for ledger rows."""
        body = json.dumps({"n": self.n, "depth": self.depth,
                           "angles": [[[round(a, 12) for a in g] for g in layer] for layer in self.angles]},
                          separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()


def _freeze(arr):
    return tuple(tuple(tuple(float(x) for x in g) for g in layer) for layer in arr)


def random_circuit(n, depth, seed):
    """Fresh random angles: θ ~ arccos(1 - 2u) (Haar-like on the sphere), φ, λ ~ U[0, 2π)."""
    rng = np.random.default_rng(seed)
    theta = np.arccos(1 - 2 * rng.random((depth, n)))
    phi, lam = rng.random((2, depth, n)) * 2 * np.pi
    return Circuit(n, depth, _freeze(np.stack([theta, phi, lam], axis=-1)))


def perturbed(circuit, sigma, seed):
    """Same structure, every angle moved by N(0, sigma). Used by the adaptive arm."""
    rng = np.random.default_rng(seed)
    a = np.array(circuit.angles) + rng.normal(0.0, sigma, size=np.array(circuit.angles).shape)
    return Circuit(circuit.n, circuit.depth, _freeze(a))


def to_qiskit(circuit):
    """Qiskit QuantumCircuit for hardware runs (qiskit is optional). Qubit q here is qubit q in Qiskit."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(circuit.n)
    for layer, gates in enumerate(circuit.angles):
        for q, (theta, phi, lam) in enumerate(gates):
            qc.rz(lam, q)
            qc.ry(theta, q)
            qc.rz(phi, q)
        for a, b in circuit.cz_pairs(layer):
            qc.cz(a, b)
    qc.measure_all()
    return qc


def to_cirq(circuit, qubits):
    """Cirq circuit on the given device qubits (qubit q here -> qubits[q]); measurement key 'm' in that order."""
    import cirq
    ops = []
    for layer, gates in enumerate(circuit.angles):
        for q, (theta, phi, lam) in enumerate(gates):
            ops += [cirq.rz(lam).on(qubits[q]), cirq.ry(theta).on(qubits[q]), cirq.rz(phi).on(qubits[q])]
        ops += [cirq.CZ(qubits[a], qubits[b]) for a, b in circuit.cz_pairs(layer)]
    return cirq.Circuit(ops + [cirq.measure(*qubits, key="m")])
