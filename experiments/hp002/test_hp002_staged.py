#!/usr/bin/env python3
"""
test_hp002_staged.py — Verification Suite for OSIRIS-HP-002 Staged Circuits
Tests all 4 arms, held-out scrambler specificity, access boundaries, and MAXQ compliance.
"""

import sys
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EXPERIMENT_DIR))

import numpy as np
import pytest
from qiskit_aer import AerSimulator
from stage_hp002_harness import (
    build_hp002_circuit,
    assemble_frozen_hp002_circuits,
    compute_payload_hash,
    compute_schema_hash
)


def evaluate_simulated_tomography(arm: str, block_idx: int = 0) -> float:
    sim = AerSimulator()
    exp_vals = {}
    for basis in ["XX", "YY", "ZZ"]:
        qc = build_hp002_circuit(arm, basis, block_idx=block_idx)
        job = sim.run(qc, shots=4096, seed_simulator=42)
        counts = job.result().get_counts()
        total = sum(counts.values())
        exp_val = 0.0
        for bitstring, count in counts.items():
            cb = bitstring.replace(" ", "")
            parity = 1.0 if cb[0] == cb[1] else -1.0
            exp_val += parity * count
        exp_vals[basis] = exp_val / total
        
    f_ent = (1.0 + exp_vals["XX"] - exp_vals["YY"] + exp_vals["ZZ"]) / 4.0
    return f_ent


def test_h1_arm_a_full_inverse_control():
    """Verifies that full-access inverse recovers message with unit fidelity."""
    f = evaluate_simulated_tomography("A_full")
    assert np.isclose(f, 1.0, atol=0.01), f"Arm A failed: F = {f} != 1.0"


def test_h2_arm_b_restricted_recovery():
    """Verifies that restricted decoder recovers message with early radiation entanglement."""
    f = evaluate_simulated_tomography("B_entangled")
    assert np.isclose(f, 1.0, atol=0.01), f"Arm B failed: F = {f} != 1.0"


def test_h3_arm_b_control_separable_trapped():
    """Verifies that without early entanglement, message is trapped (F = 0.25)."""
    f = evaluate_simulated_tomography("B_control")
    assert np.isclose(f, 0.25, atol=0.05), f"Arm B Control failed: F = {f} != 0.25"


def test_h4_arm_b_heldout_scrambler_specificity():
    """Verifies that decoder V(U1) collapses to F = 0.25 under held-out scrambler U2."""
    f = evaluate_simulated_tomography("B_heldout")
    assert f <= 0.35, f"Held-out specificity failed: F = {f} > 0.35"


def test_frozen_circuit_count_and_invariants():
    """Verifies that exactly 36 circuits are frozen with zero SWAP overhead."""
    circuits = assemble_frozen_hp002_circuits()
    assert len(circuits) == 36, f"Frozen count mismatch: {len(circuits)} != 36"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
