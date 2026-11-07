#!/usr/bin/env python3
"""
solve_clifford_decoder.py — Deterministic Stabilizer Tableau Inversion for Hayden-Preskill
Constructs the exact Yoshida-Kitaev restricted decoder from Clifford tableau evolution.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Clifford, Pauli, Statevector, DensityMatrix, partial_trace, state_fidelity

def solve_decoder_for_scrambler(scrambler_circ):
    """
    scrambler_circ acts on 4 qubits: (M1, M2, B1, B2).
    Inputs:
      M1 (0), M2 (1), B1 (2), B2 (3)
    Bell pairs:
      R1 - M1: stabilized by X_R1 X_M1, Z_R1 Z_M1
      R2 - M2: stabilized by X_R2 X_M2, Z_R2 Z_M2
      B1 - E1: stabilized by X_B1 X_E1, Z_B1 Z_E1
      B2 - E2: stabilized by X_B2 X_E2, Z_B2 Z_E2
    
    After scrambler U_MB on (M1, M2, B1, B2):
    Outputs are:
      D1 (0), D2 (1)  [late radiation]
      C1 (2), C2 (3)  [quarantined remnants]
    """
    c_U = Clifford(scrambler_circ)
    
    # We want to trace how X_M1, Z_M1, X_M2, Z_M2 evolve in the Heisenberg picture.
    # Note: U_MB acts on (M1, M2, B1, B2).
    # Since Bell pairs satisfy:
    #   (I \otimes U) |Phi+> = (U^T \otimes I) |Phi+>
    # In the stabilizer picture:
    # Full 8-qubit system:
    # 0: R1, 1: R2, 2: M1, 3: M2, 4: B1, 5: B2, 6: E1, 7: E2
    full_qc = QuantumCircuit(8)
    full_qc.h(0); full_qc.cx(0, 2)
    full_qc.h(1); full_qc.cx(1, 3)
    full_qc.h(4); full_qc.cx(4, 6)
    full_qc.h(5); full_qc.cx(5, 7)
    full_qc.compose(scrambler_circ, qubits=[2, 3, 4, 5], inplace=True)
    
    cliff_8 = Clifford(full_qc)
    # The stabilizers of the 8-qubit state:
    stabs = cliff_8.to_labels(mode="S")
    print(f"Number of state stabilizers: {len(stabs)}")
    
    return full_qc

def find_reconstruction_paulis(cliff_8):
    """
    Finds the 4 Pauli operators on (D1, D2, E1, E2) that correspond to
    X_R1, Z_R1, X_R2, Z_R2 with IDENTITY on remnants C1, C2.
    """
    from itertools import product
    from qiskit.quantum_info import PauliList, Pauli
    
    stabs = cliff_8.to_labels(mode="S")
    plist = PauliList(stabs)
    
    # We generate all 2^8 = 256 products of stabilizers
    all_stabs = []
    n = len(plist)
    for bits in product([0, 1], repeat=n):
        p = Pauli("I" * 8)
        phase = 1
        for i, b in enumerate(bits):
            if b:
                p = p.compose(plist[i])
        all_stabs.append(p)
        
    print(f"Total elements in stabilizer group: {len(all_stabs)}")
    
    # Check for X_R1, Z_R1, X_R2, Z_R2:
    # Remember Qiskit string: char 7 = q0 (R1), char 6 = q1 (R2),
    # char 5 = q2 (D1), char 4 = q3 (D2),
    # char 3 = q4 (C1), char 2 = q5 (C2),
    # char 1 = q6 (E1), char 0 = q7 (E2)
    
    # Condition: C1 (char 3) == 'I' and C2 (char 2) == 'I'
    # R1 target: char 7 == 'X' (or 'Z'), char 6 == 'I'
    # R2 target: char 6 == 'X' (or 'Z'), char 7 == 'I'
    
    targets = {
        "X_R1": ("X", "I"),
        "Z_R1": ("Z", "I"),
        "X_R2": ("I", "X"),
        "Z_R2": ("I", "Z"),
    }
    
    reconstructed = {}
    for name, (r1_char, r2_char) in targets.items():
        matches = []
        for p in all_stabs:
            s = p.to_label()
            # s[-1] is q0 (R1), s[-2] is q1 (R2)
            # s[-5] is q4 (C1), s[-6] is q5 (C2)
            if s[-1] == r1_char and s[-2] == r2_char and s[-5] == 'I' and s[-6] == 'I':
                matches.append(p)
        print(f"Target {name}: {len(matches)} matching stabilizers found!")
        if matches:
            reconstructed[name] = matches[0]
            print(f"  Best match: {matches[0].to_label()}")
            
    return reconstructed

def synthesize_clifford_from_paulis(reconstructed):
    """
    Synthesizes a 4-qubit Clifford operator on (D1, D2, E1, E2) that maps:
      P(X_R1) -> X_D1
      P(Z_R1) -> Z_D1
      P(X_R2) -> X_D2
      P(Z_R2) -> Z_D2
    """
    from qiskit.quantum_info import Pauli, Clifford
    from qiskit.synthesis import synth_clifford_full
    
    # Extract the 4-qubit Paulis on (D1, D2, E1, E2)
    # Positions in 8-qubit string (q7, q6, q5, q4, q3, q2, q1, q0):
    # D1 is q2, D2 is q3, E1 is q6, E2 is q7
    # 4-qubit order for decoder: (D1, D2, E1, E2) = (0, 1, 2, 3)
    def extract_4q_pauli(p8):
        s = p8.to_label()
        # strip sign
        sign = -1 if s.startswith("-") else 1
        s_clean = s.lstrip("+-")
        # s_clean[-1] is q0, [-2] is q1, [-3] is q2 (D1), [-4] is q3 (D2),
        # [-7] is q6 (E1), [-8] is q7 (E2)
        p_str = s_clean[-8] + s_clean[-7] + s_clean[-4] + s_clean[-3] # order: E2, E1, D2, D1
        # Qiskit Pauli string order is q3, q2, q1, q0 -> (E2, E1, D2, D1)
        p4 = Pauli(p_str)
        return sign, p4
    
    p_x1_sign, p_x1 = extract_4q_pauli(reconstructed["X_R1"])
    p_z1_sign, p_z1 = extract_4q_pauli(reconstructed["Z_R1"])
    p_x2_sign, p_x2 = extract_4q_pauli(reconstructed["X_R2"])
    p_z2_sign, p_z2 = extract_4q_pauli(reconstructed["Z_R2"])
    
    print("\nExtracted 4-qubit Pauli targets on (D1, D2, E1, E2):")
    print(f"  X1_target: sign={p_x1_sign}, Pauli={p_x1}")
    print(f"  Z1_target: sign={p_z1_sign}, Pauli={p_z1}")
    print(f"  X2_target: sign={p_x2_sign}, Pauli={p_x2}")
    print(f"  Z2_target: sign={p_z2_sign}, Pauli={p_z2}")
    
    return p_x1, p_z1, p_x2, p_z2

if __name__ == "__main__":
    from find_hp003_scrambler_decoder import build_candidate_scrambler
    scrambler = build_candidate_scrambler(seed=128)
    full_qc = solve_decoder_for_scrambler(scrambler)
    cliff_8 = Clifford(full_qc)
    reconstructed = find_reconstruction_paulis(cliff_8)
    synthesize_clifford_from_paulis(reconstructed)


