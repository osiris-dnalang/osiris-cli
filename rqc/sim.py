"""Exact statevector simulation (numpy), for ideal output probabilities. Practical to about 24 qubits.

Index convention: basis index i has qubit 0 as its most significant bit (bitstring "q0 q1 ... q(n-1)").
Qiskit counts keys are the reverse ("q(n-1) ... q0"); use bitstring_to_index(key[::-1]) for them.
"""
import numpy as np


def _u(theta, phi, lam):
    rz = lambda a: np.array([[np.exp(-0.5j * a), 0], [0, np.exp(0.5j * a)]])
    ry = np.array([[np.cos(theta / 2), -np.sin(theta / 2)], [np.sin(theta / 2), np.cos(theta / 2)]])
    return rz(phi) @ ry @ rz(lam)


def statevector(circuit):
    n = circuit.n
    psi = np.zeros((2,) * n, dtype=complex)
    psi[(0,) * n] = 1.0
    for layer, gates in enumerate(circuit.angles):
        for q, (theta, phi, lam) in enumerate(gates):
            psi = np.moveaxis(np.tensordot(_u(theta, phi, lam), psi, axes=([1], [q])), 0, q)
        for a, b in circuit.cz_pairs(layer):
            idx = [slice(None)] * n
            idx[a], idx[b] = 1, 1
            psi[tuple(idx)] *= -1
    return psi.reshape(-1)


def probabilities(circuit):
    p = np.abs(statevector(circuit)) ** 2
    return p / p.sum()


def bitstring_to_index(bits):
    return int(bits, 2)
