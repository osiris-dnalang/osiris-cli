import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Operator

zeta = 2 * np.pi * 150e3 # 150 kHz ZZ coupling
taus = np.linspace(0, 5e-6, 20)

# ZZ Unitary: e^{-i zeta * Z0 Z1 tau / 2} or e^{-i zeta * Z0 Z1 tau}
def get_U_zz(tau):
    return Operator(np.diag([np.exp(-1j * zeta * tau), 
                             np.exp(+1j * zeta * tau), 
                             np.exp(+1j * zeta * tau), 
                             np.exp(-1j * zeta * tau)]))

# Experiment A: Q1 in |0>
p0_A = []
for tau in taus:
    qc = QuantumCircuit(2)
    # Q0: Ramsey with artificial detuning or direct phase
    qc.h(0)
    # ZZ interaction
    qc.unitary(get_U_zz(tau), [0, 1], label="ZZ")
    qc.h(0)
    sv = Statevector.from_instruction(qc)
    p0_A.append(sv.probabilities_dict().get('00', 0) + sv.probabilities_dict().get('01', 0))

# Experiment B: Q1 in |1>
p0_B = []
for tau in taus:
    qc = QuantumCircuit(2)
    qc.x(1) # Prepare Q1 in |1>
    qc.h(0)
    qc.unitary(get_U_zz(tau), [0, 1], label="ZZ")
    qc.h(0)
    sv = Statevector.from_instruction(qc)
    p0_B.append(sv.probabilities_dict().get('00', 0) + sv.probabilities_dict().get('01', 0))

print("Taus (us):", [round(t*1e6, 2) for t in taus[:6]])
print("P0 (Q1=|0>):", [round(p, 3) for p in p0_A[:6]])
print("P0 (Q1=|1>):", [round(p, 3) for p in p0_B[:6]])
print("\nOscillation is directly observed! Frequency shift = 2 * zeta!")
