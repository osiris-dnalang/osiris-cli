# FULL EXPERIMENT SCRIPT
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.random import random_circuit
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from scipy.stats import ttest_ind

service = QiskitRuntimeService()
sampler = Sampler()

def compute_xeb(samples, probs, n):
    vals = [probs.get(s, 0) for s in samples]
    return (2**n) * np.mean(vals) - 1

def ideal_probs(qc):
    return Statevector.from_instruction(qc).probabilities_dict()

def run_circuit(qc, shots=4000):
    job = sampler.run([qc], shots=shots)
    result = job.result()
    counts = result[0].data.meas.get_counts()
    samples = []
    for b, c in counts.items():
        samples += [b]*c
    return samples

def adaptive_layer(qc, feedback):
    for i in range(qc.num_qubits):
        theta = np.pi/(i+2)
        if feedback is not None:
            theta *= (1 + feedback)
        qc.rx(theta, i)
    return qc

rcs_results = []
rqc_results = []

for seed in range(10):
    base = random_circuit(12, 8, seed=seed, measure=True)

    probs = ideal_probs(base.remove_final_measurements(inplace=False))
    samples = run_circuit(base)
    rcs_results.append(compute_xeb(samples, probs, 12))

    feedback = None
    qc = base.remove_final_measurements(inplace=False)

    for _ in range(5):
        qc_iter = qc.copy()
        qc_iter = adaptive_layer(qc_iter, feedback)
        qc_iter.measure_all()

        probs_iter = ideal_probs(qc_iter.remove_final_measurements(inplace=False))
        samples_iter = run_circuit(qc_iter)
        feedback = compute_xeb(samples_iter, probs_iter, 12)

    rqc_results.append(feedback)

print("RCS:", np.mean(rcs_results))
print("RQC:", np.mean(rqc_results))

stat, p = ttest_ind(rcs_results, rqc_results)
print("p-value:", p)
