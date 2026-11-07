#!/usr/bin/env python3
"""
find_hp003_scrambler_decoder.py — Synthesizes 4-qubit Clifford Scrambler & Restricted Decoder for OSIRIS-HP-003
Scales Hayden-Preskill benchmark to a 2-qubit message k = 2 across an 8-qubit register.
"""

import sys
import numpy as np
from pathlib import Path
from itertools import product

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace, entropy, DensityMatrix, Clifford

def compute_mi(rho_AB, qA_indices, qB_indices):
    """Computes mutual information I(A : B) = S(A) + S(B) - S(AB) in bits."""
    n_total = int(np.log2(rho_AB.data.shape[0]))
    all_qubits = list(range(n_total))
    keep = sorted(list(set(qA_indices + qB_indices)))
    trace_out = [q for q in all_qubits if q not in keep]
    
    if trace_out:
        rho_sub = partial_trace(rho_AB, trace_out)
    else:
        rho_sub = rho_AB
        
    sub_qubits = sorted(keep)
    rel_A = [sub_qubits.index(q) for q in qA_indices]
    rel_B = [sub_qubits.index(q) for q in qB_indices]
    
    rho_A = partial_trace(rho_sub, rel_B)
    rho_B = partial_trace(rho_sub, rel_A)
    
    s_A = entropy(rho_A, base=2)
    s_B = entropy(rho_B, base=2)
    s_AB = entropy(rho_sub, base=2)
    return float(s_A + s_B - s_AB)

def test_candidate_scrambler(U_circ):
    """
    Register layout:
    0: R1 (Reference 1)
    1: R2 (Reference 2)
    2: M1 (Message 1)
    3: M2 (Message 2)
    4: B1 (Black Hole Remnant 1)
    5: B2 (Black Hole Remnant 2)
    6: E1 (Early Radiation 1)
    7: E2 (Early Radiation 2)
    """
    qc = QuantumCircuit(8)
    # Bell pair R1 - M1
    qc.h(0)
    qc.cx(0, 2)
    # Bell pair R2 - M2
    qc.h(1)
    qc.cx(1, 3)
    # Bell pair B1 - E1
    qc.h(4)
    qc.cx(4, 6)
    # Bell pair B2 - E2
    qc.h(5)
    qc.cx(5, 7)
    
    # Apply Scrambler U on (M1, M2, B1, B2) -> qubits (2, 3, 4, 5)
    qc.compose(U_circ, qubits=[2, 3, 4, 5], inplace=True)
    
    psi = Statevector.from_instruction(qc)
    rho = DensityMatrix(psi)
    
    # Decoupling conditions:
    # Reference R = (0, 1)
    # Late Radiation D = (2, 3)
    # Remnant C = (4, 5)
    # Early Radiation E = (6, 7)
    
    mi_R_D = compute_mi(rho, [0, 1], [2, 3])
    mi_R_E = compute_mi(rho, [0, 1], [6, 7])
    mi_R_C = compute_mi(rho, [0, 1], [4, 5])
    mi_R_DE = compute_mi(rho, [0, 1], [2, 3, 6, 7])
    
    return mi_R_D, mi_R_E, mi_R_C, mi_R_DE, psi

import random

def build_candidate_scrambler(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    qc = QuantumCircuit(4, name="Scrambler_4Q")
    # 4-qubit scrambling network on (M1, M2, B1, B2)
    # Layer 1: Hadamards
    for q in range(4):
        if random.random() > 0.3:
            qc.h(q)
    # Layer 2: Entangling CZ/CX
    pairs = [(0, 2), (1, 3), (0, 3), (1, 2), (0, 1), (2, 3)]
    for u, v in pairs:
        gate_type = random.choice(["cx", "cz", "swap", "none"])
        if gate_type == "cx":
            qc.cx(u, v)
        elif gate_type == "cz":
            qc.cz(u, v)
        elif gate_type == "swap":
            qc.swap(u, v)
    # Layer 3: Phases & Hadamards
    for q in range(4):
        if random.random() > 0.4:
            qc.s(q)
        if random.random() > 0.4:
            qc.h(q)
    # Layer 4: Entangling cross-couplings
    for u, v in [(2, 0), (3, 1), (1, 0), (3, 2)]:
        if random.random() > 0.3:
            qc.cx(u, v)
    return qc

def search_scramblers(max_trials=200):
    print("Searching for 4-qubit scrambler satisfying complete decoupling...")
    for seed in range(max_trials):
        qc = build_candidate_scrambler(seed)
        mi_R_D, mi_R_E, mi_R_C, mi_R_DE, _ = test_candidate_scrambler(qc)
        if abs(mi_R_D) < 1e-4 and abs(mi_R_E) < 1e-4 and abs(mi_R_C) < 1e-4 and abs(mi_R_DE - 4.0) < 1e-4:
            print(f"[FOUND] Seed {seed} satisfies all 4 decoupling conditions!")
            print(f"  I(R : D)  = {mi_R_D:.6f} bits")
            print(f"  I(R : E)  = {mi_R_E:.6f} bits")
            print(f"  I(R : C)  = {mi_R_C:.6f} bits")
            print(f"  I(R : DE) = {mi_R_DE:.6f} bits")
            return seed, qc
    print("No perfect candidate found in initial search.")
    return None, None

from qiskit.quantum_info import random_clifford, state_fidelity

def synthesize_decoder(scrambler_circ, max_clifford_trials=5000):
    print("\nSynthesizing 4-qubit Clifford decoder on joint radiation (D1, D2, E1, E2)...")
    qc = QuantumCircuit(8)
    qc.h(0); qc.cx(0, 2) # |Phi+>_{R1 M1}
    qc.h(1); qc.cx(1, 3) # |Phi+>_{R2 M2}
    qc.h(4); qc.cx(4, 6) # |Phi+>_{B1 E1}
    qc.h(5); qc.cx(5, 7) # |Phi+>_{B2 E2}
    qc.compose(scrambler_circ, qubits=[2, 3, 4, 5], inplace=True)
    
    # Target state: Bell pair R1-M1' and R2-M2'
    # R1 is qubit 0, R2 is qubit 1, M1' will be qubit 2, M2' will be qubit 3
    bell_1q = Statevector([1/np.sqrt(2), 0, 0, 1/np.sqrt(2)])
    bell_2q_target = bell_1q.expand(bell_1q) # |Phi+>_12 \otimes |Phi+>_03 depending on order
    # Let's create exact 4-qubit target state on (R1, R2, M1', M2')
    target_qc = QuantumCircuit(4)
    target_qc.h(0); target_qc.cx(0, 2)
    target_qc.h(1); target_qc.cx(1, 3)
    target_dm = DensityMatrix(Statevector.from_instruction(target_qc))
    
    for seed in range(max_clifford_trials):
        c = random_clifford(4, seed=seed)
        test_qc = qc.copy()
        test_qc.append(c.to_circuit(), [2, 3, 6, 7])
        sv = Statevector.from_instruction(test_qc)
        # Trace out remnants (4, 5) and extra radiation (6, 7)
        rho_out = partial_trace(sv, [4, 5, 6, 7])
        f = state_fidelity(rho_out, target_dm)
        if np.isclose(f, 1.0, atol=1e-4):
            print(f"[FOUND] Exact Clifford Decoder! Seed {seed}, Joint Fidelity: {f:.6f}")
            return seed, c
    print("Decoder not found in initial random Clifford trials.")
    return None, None

if __name__ == "__main__":
    seed, scrambler_qc = search_scramblers()
    if scrambler_qc:
        dec_seed, dec_cliff = synthesize_decoder(scrambler_qc)


