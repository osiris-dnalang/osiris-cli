from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace, entropy

qc = QuantumCircuit(6)
qc.h(0); qc.cx(0, 1) # (R, M)
qc.h(2); qc.cx(2, 4) # (B1, E1)
qc.h(3); qc.cx(3, 5) # (B2, E2)

# Scrambler on (1, 2, 3)
qc.cx(1, 2)
qc.h(1)
qc.cx(2, 3)
qc.h(2)
qc.cx(1, 3)
qc.h(3)

sv = Statevector.from_instruction(qc)
# Trace out radiation (1, 4, 5) -> leaves (R, C1, C2) = (0, 2, 3)
rho_remnant = partial_trace(sv, [1, 4, 5])
rho_r = partial_trace(rho_remnant, [1, 2])
rho_c = partial_trace(rho_remnant, [0])

s_r = entropy(rho_r)
s_c = entropy(rho_c)
s_tot = entropy(rho_remnant)
mi_remnant = s_r + s_c - s_tot
print(f"Mutual Information with Remnant I(R : C) = {mi_remnant:.4f} (Should be 0.0000)")
