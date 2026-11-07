import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, DensityMatrix, partial_trace, state_fidelity

# Let's construct a parameterized / Clifford scrambling circuit on 6 qubits:
# Qubits:
# 0: R (Reference)
# 1: M (Message)
# 2: B1 (Black hole)
# 3: B2 (Black hole)
# 4: E1 (Early radiation)
# 5: E2 (Early radiation)

# Canonical Bell state on 2 qubits
bell_circ = QuantumCircuit(2)
bell_circ.h(0)
bell_circ.cx(0, 1)
bell_sv = Statevector.from_instruction(bell_circ)
bell_dm = DensityMatrix(bell_sv)

def test_clifford_scrambler():
    # Let's test a canonical scrambler U on (M, B1, B2) = (1, 2, 3)
    # A standard scrambling circuit consists of 2-qubit Clifford gates that delocalize information:
    qc = QuantumCircuit(6)
    
    # 1. State preparation
    # |Phi+> on (R, M) -> (0, 1)
    qc.h(0)
    qc.cx(0, 1)
    
    # |Phi+> on (B1, E1) -> (2, 4)
    qc.h(2)
    qc.cx(2, 4)
    
    # |Phi+> on (B2, E2) -> (3, 5)
    qc.h(3)
    qc.cx(3, 5)
    
    # 2. Scrambler U on (M, B1, B2) = (1, 2, 3)
    # For example, standard 3-qubit scrambling network:
    qc.cx(1, 2)
    qc.h(1)
    qc.cx(2, 3)
    qc.h(2)
    qc.cx(1, 3)
    qc.h(3)
    
    # In this state, after U:
    # Qubit 1 is D (late radiation)
    # Qubits 2, 3 are C1, C2 (black hole remnant, inaccessible)
    # Qubits 4, 5 are E1, E2 (early radiation)
    
    # Inaccessible remnant: qubits 2, 3
    # Accessible radiation: qubits 1, 4, 5
    
    # Let's compute statevector
    sv = Statevector.from_instruction(qc)
    
    # Reduced density matrix on (R, D, E1, E2) = (0, 1, 4, 5)
    # Qiskit partial trace traces OUT specified qubits: trace out (2, 3)
    rho_accessible = partial_trace(sv, [2, 3])
    
    print("Accessible density matrix shape:", rho_accessible.data.shape)
    # rho_accessible lives on (0, 1, 4, 5) -> 4 qubits (dim 16)
    # Register 0 is R. Registers 1, 4, 5 are radiation (D, E1, E2).
    
    # Let's check the mutual information I(R: D, E1, E2)
    # If information is recovered, I(R: rad) = 2 (for 1 qubit maximally entangled).
    from qiskit.quantum_info import entropy, mutual_information
    rho_r = partial_trace(rho_accessible, [1, 2, 3]) # relative indices in 4-qubit system
    rho_rad = partial_trace(rho_accessible, [0])
    
    s_r = entropy(rho_r)
    s_rad = entropy(rho_rad)
    s_tot = entropy(rho_accessible)
    mi = s_r + s_rad - s_tot
    print(f"S(R) = {s_r:.4f}, S(rad) = {s_rad:.4f}, S(total) = {s_tot:.4f}")
    print(f"Mutual Information I(R : rad) = {mi:.4f} (Ideal = 2.0000)")
    
test_clifford_scrambler()
