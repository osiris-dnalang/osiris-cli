from qiskit import QuantumCircuit
from qiskit.quantum_info import Clifford, Pauli

# Scrambler on (1, 2, 3) = (M, B1, B2)
scrambler = QuantumCircuit(3)
scrambler.cx(0, 1) # cx(M, B1)
scrambler.h(0)     # h(M)
scrambler.cx(1, 2) # cx(B1, B2)
scrambler.h(1)     # h(B1)
scrambler.cx(0, 2) # cx(M, B2)
scrambler.h(2)     # h(B2)

cliff = Clifford(scrambler)
print("Clifford tableau for scrambler on (M, B1, B2):")
for p_in in ["XII", "ZII"]:
    p_evolved = Pauli(p_in).evolve(cliff)
    print(f"  {p_in} -> {p_evolved}")
