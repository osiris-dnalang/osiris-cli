#!/usr/bin/env python3
"""
test_hp003_staged.py — Comprehensive Unit & Hypothesis Verification Suite for OSIRIS-HP-003
Tests all 5 pre-registered arms and hardware invariants against exact simulation.
"""

import json
from pathlib import Path
import numpy as np
import pytest

EXPERIMENT_DIR = Path(__file__).resolve().parent

from qiskit import QuantumCircuit, qpy
from qiskit.quantum_info import Statevector, DensityMatrix, partial_trace, state_fidelity
from stage_hp003_harness import build_hp003_circuit, BENCHMARK_ID, N_BLOCKS

BELL_IDEAL_1Q = DensityMatrix(Statevector([1/np.sqrt(2), 0, 0, 1/np.sqrt(2)]))

def get_reconstructed_fidelities(arm_name: str):
    """Computes exact simulation fidelities for R1-M1' and R2-M2'."""
    qc = build_hp003_circuit(arm_name, "ZZ")
    qc_no_meas = QuantumCircuit(8)
    for instr in qc.data:
        if instr.operation.name != "measure":
            qc_no_meas.append(instr.operation, instr.qubits, instr.clbits)
            
    sv = Statevector.from_instruction(qc_no_meas)
    
    # R1 is q0, M1' is q2 -> trace out [1, 3, 4, 5, 6, 7]
    rho_rm1 = partial_trace(sv, [1, 3, 4, 5, 6, 7])
    # R2 is q1, M2' is q3 -> trace out [0, 2, 4, 5, 6, 7]
    rho_rm2 = partial_trace(sv, [0, 2, 4, 5, 6, 7])
    
    f1 = float(state_fidelity(rho_rm1, BELL_IDEAL_1Q))
    f2 = float(state_fidelity(rho_rm2, BELL_IDEAL_1Q))
    f_prod = f1 * f2
    
    return f1, f2, f_prod


def test_h1_arm_a_full_inverse_control():
    """H1: Reversibility positive control ceiling must achieve >= 0.85 independently for both pairs."""
    f1, f2, f_prod = get_reconstructed_fidelities("Arm A")
    assert f1 >= 0.85, f"Arm A R1-M1 failed: {f1}"
    assert f2 >= 0.85, f"Arm A R2-M2 failed: {f2}"
    assert np.isclose(f1, 1.0, atol=1e-4)
    assert np.isclose(f2, 1.0, atol=1e-4)


def test_h2_arm_b_restricted_recovery():
    """H2: Restricted recovery with 2 emitted photons must exceed 0.50 (ideal = 1.0) and be entangled."""
    f1, f2, f_prod = get_reconstructed_fidelities("Arm B")
    mean_f = 0.5 * (f1 + f2)
    assert mean_f > 0.50, f"Arm B mean recovery failed separability: {mean_f}"
    assert (0.50 - mean_f) < 0, f"Arm B witness failed entanglement: {0.50 - mean_f}"
    assert np.isclose(f1, 1.0, atol=1e-4)
    assert np.isclose(f2, 1.0, atol=1e-4)


def test_h3_arm_b_deficient_single_photon_capacity_bound():
    """H3: Sub-capacity control (single photon) is capped at F1 <= 0.5001 (W1 >= 0) and F2 <= 0.35."""
    f1, f2, f_prod = get_reconstructed_fidelities("Arm B-Def")
    mean_f = 0.5 * (f1 + f2)
    
    # Capacity Bound Verification:
    # Photon D1 allows optimal decoder to reach classical separability bound F1 = 0.5000 (W1 = 0.0)
    assert f1 <= 0.5001, f"Arm B-Def f1 exceeded single-photon capacity bound: {f1}"
    assert np.isclose(f1, 0.50, atol=1e-4)
    
    # Second photon is missing, so R2 cannot be decoded (remains at noise floor 0.25)
    assert f2 <= 0.35, f"Arm B-Def f2 exceeded noise floor: {f2}"
    assert np.isclose(f2, 0.25, atol=1e-4)
    
    # Entanglement Witness check: W1 >= 0, W_mean > 0 (NO ENTANGLEMENT FORMED)
    w1 = 0.50 - f1
    w_mean = 0.50 - mean_f
    assert w1 >= -1e-6, f"Single photon formed illegal entanglement: W1={w1}"
    assert w_mean > 0, f"Single photon formed mean entanglement: W_mean={w_mean}"


def test_h4_arm_b_control_separable_trapped():
    """H4: Unentangled baseline with separable |0000> on B and E must collapse to <= 0.35."""
    f1, f2, f_prod = get_reconstructed_fidelities("Arm B-Ctrl")
    mean_f = 0.5 * (f1 + f2)
    assert mean_f <= 0.35, f"Arm B-Ctrl exceeded separable limit: {mean_f}"
    assert np.isclose(f1, 0.25, atol=1e-4)
    assert np.isclose(f2, 0.25, atol=1e-4)


def test_h5_arm_b_heldout_scrambler_specificity():
    """H5: Held-out audited scrambler U2 (seed 158) against fixed decoder must collapse to <= 0.35."""
    f1, f2, f_prod = get_reconstructed_fidelities("Arm B-Held")
    mean_f = 0.5 * (f1 + f2)
    assert mean_f <= 0.35, f"Arm B-Held exceeded specificity limit: {mean_f}"
    assert np.isclose(f1, 0.25, atol=1e-4)
    assert np.isclose(f2, 0.25, atol=1e-4)


def test_quarantine_firewall_invariants():
    """Verifies zero decoder gates on remnants C1, C2 (qubits 4, 5) and quarantine of D2 in Arm B-Def."""
    qc_b = build_hp003_circuit("Arm B", "ZZ")
    qc_def = build_hp003_circuit("Arm B-Def", "ZZ")
    
    for i in range(34, len(qc_b.data)):
        instr = qc_b.data[i]
        q_indices = [q._index for q in instr.qubits]
        assert 4 not in q_indices and 5 not in q_indices, f"Firewall breach in Arm B at {i}: {instr}"

    for i in range(34, len(qc_def.data)):
        instr = qc_def.data[i]
        q_indices = [q._index for q in instr.qubits]
        assert 4 not in q_indices and 5 not in q_indices, f"Firewall breach in Arm B-Def at {i}: {instr}"
        if not instr.clbits:
            assert 3 not in q_indices, f"D2 quarantine breach in Arm B-Def at {i}: {instr}"


def test_frozen_circuit_count_and_manifest():
    """Validates manifest integrity if manifest exists."""
    manifest_path = EXPERIMENT_DIR / "hp003_staging_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["benchmark_id"] == BENCHMARK_ID
        assert manifest["total_circuits"] == 45
        assert manifest["shots_per_circuit"] == 1024
        assert manifest["total_shots"] == 46080
        assert manifest["max_cz"] <= 55
        assert manifest["max_depth"] <= 110
