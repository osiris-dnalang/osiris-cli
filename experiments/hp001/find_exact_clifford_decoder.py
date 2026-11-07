from qiskit import QuantumCircuit
from qiskit.quantum_info import Clifford, Statevector, state_fidelity, DensityMatrix, partial_trace
import numpy as np

# Total 6-qubit system:
# 0: R
# 1: M (becomes late radiation D)
# 2: B1 (remnant, traced out)
# 3: B2 (remnant, traced out)
# 4: E1 (early radiation)
# 5: E2 (early radiation)

# Initial preparation and scrambling
qc = QuantumCircuit(6)
qc.h(0); qc.cx(0, 1) # |Phi+>_RM
qc.h(2); qc.cx(2, 4) # |Phi+>_{B1 E1}
qc.h(3); qc.cx(3, 5) # |Phi+>_{B2 E2}

# Scrambler on (1, 2, 3)
qc.cx(1, 2)
qc.h(1)
qc.cx(2, 3)
qc.h(2)
qc.cx(1, 3)
qc.h(3)

# Now decoder acts on (1, 4, 5) = (D, E1, E2)
# We want to map:
# X_rec = Y_D * Y_E1 * Z_E2 -> X_D
# Z_rec = X_D               -> Z_D
# Let's find Clifford on (1, 4, 5):
# Notice:
# To map Z_rec = X_D to Z_D: a Hadamard on D maps X_D to Z_D!
# But we also need Y_D * Y_E1 * Z_E2 to map to X_D!
# Let's test Clifford synthesis or greedy search on (1, 4, 5):

bell_ideal = DensityMatrix(Statevector([1/np.sqrt(2), 0, 0, 1/np.sqrt(2)]))

from qiskit.synthesis import synth_clifford_full

# Let's test random Clifford on 3 qubits to find the exact match:
from qiskit.quantum_info import random_clifford

found_cliff = None
for seed in range(5000):
    c = random_clifford(3, seed=seed)
    # Apply to (1, 4, 5)
    test_qc = qc.copy()
    test_qc.append(c.to_circuit(), [1, 4, 5])
    sv = Statevector.from_instruction(test_qc)
    # Trace out 2, 3 (remnants) and 4, 5 (other radiation)
    rho_rm = partial_trace(sv, [2, 3, 4, 5])
    f = state_fidelity(rho_rm, bell_ideal)
    if np.isclose(f, 1.0, atol=1e-5):
        print(f"FOUND EXACT CLIFFORD DECODER! Seed: {seed}, Fidelity: {f:.6f}")
        found_cliff = c
        break

if found_cliff:
    dec_circ = found_cliff.to_circuit().decompose()
    print("Decomposed Decoder Circuit:")
    print(dec_circ)
