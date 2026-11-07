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
    # We build the ZZ circuit without measurement to extract full statevector
    qc = build_hp003_circuit(arm_name, "ZZ")
    # Remove measurements
    qc_no_meas = QuantumCircuit(8)
    for instr in qc.data:
        if instr.operation.name != "measure":
            qc_no_meas.append(instr.operation, instr.qubits, instr.clbits)
            
    sv = Statevector.from_instruction(qc_no_meas)
    
    # R1 is q0, M1' is q2 -> trace out [1, 3, 4, 5, 6, 7]
    rho_rm1 = partial_trace(sv, [1, 3, 4, 5, 6, 7])
    # R2 is q1, M2' is q3 -> trace out [0, 2, 4, 5, 6, 7]
    rho_rm2 = partial_trace(sv, [0, 2, 4, 5, 6, 7])
    # Joint R1, R2, M1', M2' -> trace out [4, 5, 6, 7]
    rho_joint = partial_trace(sv, [4, 5, 6, 7])
    
    f1 = float(state_fidelity(rho_rm1, BELL_IDEAL_1Q))
    f2 = float(state_fidelity(rho_rm2, BELL_IDEAL_1Q))
    
    # Target joint 4-qubit state: |Phi+>_02 \otimes |Phi+>_13
    target_qc = QuantumCircuit(4)
    target_qc.h(0); target_qc.cx(0, 2)
    target_qc.h(1); target_qc.cx(1, 3)
    target_dm = DensityMatrix(Statevector.from_instruction(target_qc))
    f_joint = float(state_fidelity(rho_joint, target_dm))
    
    return f1, f2, f_joint


def test_h1_arm_a_full_inverse_control():
    """H1: Reversibility positive control ceiling must achieve >= 0.85."""
    f1, f2, f_joint = get_reconstructed_fidelities("Arm A")
    assert f1 >= 0.85, f"Arm A R1-M1 failed: {f1}"
    assert f2 >= 0.85, f"Arm A R2-M2 failed: {f2}"
    assert f_joint >= 0.85, f"Arm A Joint failed: {f_joint}"
    assert np.isclose(f1, 1.0, atol=1e-4)
    assert np.isclose(f2, 1.0, atol=1e-4)
    assert np.isclose(f_joint, 1.0, atol=1e-4)


def test_h2_arm_b_restricted_recovery():
    """H2: Restricted recovery with 2 emitted photons must exceed 0.50 (ideal = 1.0)."""
    f1, f2, f_joint = get_reconstructed_fidelities("Arm B")
    mean_f = 0.5 * (f1 + f2)
    assert mean_f > 0.50, f"Arm B mean recovery failed separability: {mean_f}"
    assert f_joint > 0.50, f"Arm B joint recovery failed: {f_joint}"
    assert np.isclose(f1, 1.0, atol=1e-4)
    assert np.isclose(f2, 1.0, atol=1e-4)
    assert np.isclose(f_joint, 1.0, atol=1e-4)


def test_h3_arm_b_deficient_single_photon_capacity_bound():
    """H3: Sub-capacity control (single photon) must fail 2-qubit recovery (f_joint <= 0.35, f_joint = 1/16 = 0.0625)."""
    f1, f2, f_joint = get_reconstructed_fidelities("Arm B-Def")
    assert f1 <= 0.35, f"Arm B-Def f1 exceeded capacity limit: {f1}"
    assert f2 <= 0.35, f"Arm B-Def f2 exceeded capacity limit: {f2}"
    assert f_joint <= 0.35, f"Arm B-Def joint exceeded capacity limit: {f_joint}"
    assert np.isclose(f1, 0.25, atol=1e-4)
    assert np.isclose(f2, 0.25, atol=1e-4)
    assert np.isclose(f_joint, 0.0625, atol=1e-4)


def test_h4_arm_b_control_separable_trapped():
    """H4: Trapped control with separable |0000> on B and E must collapse to <= 0.35."""
    f1, f2, f_joint = get_reconstructed_fidelities("Arm B-Ctrl")
    mean_f = 0.5 * (f1 + f2)
    assert mean_f <= 0.35, f"Arm B-Ctrl exceeded separable limit: {mean_f}"
    assert f_joint <= 0.35, f"Arm B-Ctrl joint exceeded limit: {f_joint}"
    assert np.isclose(f1, 0.25, atol=1e-4)
    assert np.isclose(f2, 0.25, atol=1e-4)


def test_h5_arm_b_heldout_scrambler_specificity():
    """H5: Held-out scrambler against fixed decoder must collapse to <= 0.35 (f_joint = 1/16 = 0.0625)."""
    f1, f2, f_joint = get_reconstructed_fidelities("Arm B-Held")
    mean_f = 0.5 * (f1 + f2)
    assert mean_f <= 0.35, f"Arm B-Held exceeded specificity limit: {mean_f}"
    assert f_joint <= 0.35, f"Arm B-Held joint exceeded limit: {f_joint}"
    assert np.isclose(f1, 0.25, atol=1e-4)
    assert np.isclose(f2, 0.25, atol=1e-4)
    assert np.isclose(f_joint, 0.0625, atol=1e-4)


def test_frozen_circuit_count_and_manifest():
    """Validates manifest integrity, QPY serialization, and frozen circuit count."""
    manifest_path = EXPERIMENT_DIR / "hp003_staging_manifest.json"
    assert manifest_path.exists(), "Manifest missing"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    assert manifest["benchmark_id"] == BENCHMARK_ID
    assert manifest["total_circuits"] == 45
    assert manifest["shots_per_circuit"] == 1024
    assert manifest["total_shots"] == 46080
    assert manifest["max_cz"] <= 55
    assert manifest["max_depth"] <= 95
    
    qpy_path = EXPERIMENT_DIR / "hp003_staged_circuits.qpy"
    assert qpy_path.exists(), "QPY file missing"
    with open(qpy_path, "rb") as f:
        circs = qpy.load(f)
    assert len(circs) == 45, f"Expected 45 circuits, got {len(circs)}"
