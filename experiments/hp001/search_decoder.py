from qiskit import QuantumCircuit
from qiskit.quantum_info import Clifford, Statevector, state_fidelity, DensityMatrix, partial_trace

# Let's find the decoder unitary on (1, 4, 5)
# In the 6-qubit circuit:
# State before decoding:
qc_prep = QuantumCircuit(6)
qc_prep.h(0); qc_prep.cx(0, 1) # (R, M)
qc_prep.h(2); qc_prep.cx(2, 4) # (B1, E1)
qc_prep.h(3); qc_prep.cx(3, 5) # (B2, E2)
# Scrambler on (1, 2, 3)
qc_prep.cx(1, 2)
qc_prep.h(1)
qc_prep.cx(2, 3)
qc_prep.h(2)
qc_prep.cx(1, 3)
qc_prep.h(3)

# Target: after decoder V acting ONLY on (1, 4, 5), qubit 4 (or 1) is decoded message M'
# such that state on (0, decoded) is |Phi+> = (|00> + |11>)/sqrt(2).
# Let's synthesize the Clifford decoder:
# Let's see what stabilizer generators are on (0, 1, 4, 5):
from qiskit.quantum_info import StabilizerTableau, Pauli

# Let's test a brute force search over 2-3 Clifford gate sequences on (1, 4, 5):
# Qubits: 1 is D, 4 is E1, 5 is E2.
# Possible 2-qubit gates among (1, 4, 5): cx, cz, swap, and 1Q gates: h, s, sdg, x, z
from qiskit.quantum_info import DensityMatrix

target_bell = DensityMatrix.from_label('00') + DensityMatrix.from_label('11')
target_bell = DensityMatrix(Statevector.from_label('00') + Statevector.from_label('11')) / np.sqrt(2)
bell_ideal = DensityMatrix(Statevector([1/np.sqrt(2), 0, 0, 1/np.sqrt(2)]))

import itertools

single_qubit_gates = [('id',), ('h',), ('s',), ('sdg',), ('h', 's'), ('s', 'h')]
pairs = [(1, 4), (4, 1), (1, 5), (5, 1), (4, 5), (5, 4)]

print("Searching for exact Clifford decoder on radiation qubits (1, 4, 5)...")

def test_decoder(dec_gates, dec_target_qubit=4):
    qc = qc_prep.copy()
    for g, q in dec_gates:
        if g == 'cx':
            qc.cx(q[0], q[1])
        elif g == 'cz':
            qc.cz(q[0], q[1])
        elif g == 'h':
            qc.h(q)
        elif g == 's':
            qc.s(q)
        elif g == 'sdg':
            qc.sdg(q)
        elif g == 'x':
            qc.x(q)
        elif g == 'z':
            qc.z(q)
    sv = Statevector.from_instruction(qc)
    # Trace out (2, 3) and the other two radiation qubits
    other_rad = [q for q in [1, 4, 5] if q != dec_target_qubit]
    trace_out = [2, 3] + other_rad
    rho_rm = partial_trace(sv, trace_out)
    fid = state_fidelity(rho_rm, bell_ideal)
    return fid

# Let's test single/two gate combinations
found = False
for depth in range(1, 6):
    # Try combinations
    if found: break
    print(f"Trying depth {depth}...")
    # Let's search using random sampling of Clifford circuits or symplectic inversion
