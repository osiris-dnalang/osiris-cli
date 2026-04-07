import numpy as np
from qiskit import QuantumCircuit

def random_circuit(n_qubits=8, depth=3):
    qc = QuantumCircuit(n_qubits, n_qubits)

    qc.h(0)

    for d in range(depth):
        for i in range(n_qubits - 1):
            qc.cx(i, i+1)
            qc.rz(np.random.uniform(0, 2*np.pi), i+1)
            qc.sx(i+1)

    qc.measure(range(n_qubits), range(n_qubits))
    return qc


def generate_batch():
    circuits = []
    meta = []

    for depth in range(1, 7):
        for _ in range(100):
            circuits.append(random_circuit(depth=depth))
            meta.append({"depth": depth})

    return circuits, meta