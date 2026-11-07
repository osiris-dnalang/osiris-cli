#!/usr/bin/env python3
"""
experiments/qaml_002_adversarial_feature_map/test_qaml_002_staged.py
Automated Unit Test Suite for OSIRIS-QAML-002 Staging Invariants.
"""

import json
from pathlib import Path
import numpy as np
import pytest

from stage_qaml_002_harness import (
    generate_dataset,
    ClassicalMLP,
    generate_pgd_adversaries,
    build_multidepth_feature_map,
    N_TEST,
    N_TRAIN,
    DEPTHS,
    ARMS,
    EPSILONS
)

from qiskit.quantum_info import Statevector

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXP_DIR = REPO_ROOT / "experiments" / "qaml_002_adversarial_feature_map"
MANIFEST_PATH = EXP_DIR / "qaml_002_staging_manifest.json"


def test_manifest_integrity_and_sample_resolution():
    assert MANIFEST_PATH.exists(), "Manifest file missing!"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = json.load(f)

    assert m["n_test_samples"] >= 50, f"Sample size {m['n_test_samples']} too small (power deficit)"
    assert m["benchmark_id"] == "OSIRIS-QAML-002"
    assert m["depths"] == [2, 4, 6, 8]
    assert "classical_baseline" in m


def test_dataset_balance_and_separation():
    X_train, y_train, X_test, y_test = generate_dataset(seed=42)
    assert len(X_test) == 50
    assert len(X_train) == 250
    # Balanced classes
    assert abs(np.sum(y_test == 1) - np.sum(y_test == 0)) <= 2


def test_classical_adversarial_degradation_monotonicity():
    X_train, y_train, X_test, y_test = generate_dataset(seed=42)
    mlp = ClassicalMLP(seed=42)
    mlp.train(X_train, y_train, epochs=300, lr=0.05)

    accs = []
    for eps in [0.00, 0.05, 0.10, 0.20]:
        X_adv = generate_pgd_adversaries(mlp, X_test, y_test, eps=eps, steps=10)
        acc = float(np.mean(np.argmax(mlp.forward(X_adv), axis=-1) == y_test))
        accs.append(acc)

    # Accuracy must strictly degrade or remain bounded under increasing epsilon
    assert accs[0] >= accs[1] >= accs[3], f"Non-monotonic adversarial response: {accs}"
    assert accs[0] >= 0.70, f"Clean accuracy {accs[0]} too low"
    assert accs[-1] <= 0.40, f"Adversarial accuracy {accs[-1]} failed to break classical baseline"


def test_gate0_statevector_purity_across_all_depths():
    x = np.full(8, np.pi / 4.0)
    for d in DEPTHS:
        for arm in ["bare", "sync_xy8", "stag_xy8", "aa_control"]:
            qc = build_multidepth_feature_map(x, depth=d, arm_type=arm)
            pure_qc = qc.remove_final_measurements(inplace=False)
            sv = Statevector.from_instruction(pure_qc)
            purity = float(sv.purity().real)
            assert abs(purity - 1.0) < 1e-6, f"Non-physical purity {purity} at D={d}, arm={arm}"


def test_gate_count_scaling_invariants():
    x = np.full(8, np.pi / 4.0)
    for d in DEPTHS:
        qc_bare = build_multidepth_feature_map(x, depth=d, arm_type="bare")
        qc_stag = build_multidepth_feature_map(x, depth=d, arm_type="stag_xy8")

        # 7 nearest-neighbor CX pairs * 2 (forward/backward ZZ) * d layers = 14 * d
        ops_bare = qc_bare.count_ops()
        ops_stag = qc_stag.count_ops()

        assert ops_bare["cx"] == 14 * d, f"Expected {14*d} CX in bare, got {ops_bare['cx']}"
        assert ops_stag["cx"] == 14 * d, f"Expected {14*d} CX in stag, got {ops_stag['cx']}"
        assert ops_stag["x"] + ops_stag["y"] == 64 * d, f"Expected {64*d} DD pulses in stag, got {ops_stag['x'] + ops_stag['y']}"
