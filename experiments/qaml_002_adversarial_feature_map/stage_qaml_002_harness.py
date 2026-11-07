#!/usr/bin/env python3
"""
experiments/qaml_002_adversarial_feature_map/stage_qaml_002_harness.py
OSIRIS-QAML-002: Staging Harness for High-Sample Multi-Depth Adversarial Feature Maps.
Governed under SYS-021 Zero Self-Supplied Authorization.
"""

import json
import math
import random
import sys
import time
from pathlib import Path
import numpy as np

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXP_DIR = REPO_ROOT / "experiments" / "qaml_002_adversarial_feature_map"
EXP_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK_ID = "OSIRIS-QAML-002"
N_QUBITS = 8
N_TEST = 50
N_TRAIN = 250
DEPTHS = [2, 4, 6, 8]
EPSILONS = [0.00, 0.05, 0.10, 0.20]
ARMS = ["classical", "bare", "sync_xy8", "stag_xy8", "aa_control"]


# ---------------------------------------------------------------------------
# 1. Balanced Dataset Generation: 8D Concentric Non-Linear Hyperspheres
# ---------------------------------------------------------------------------
def generate_dataset(seed: int = 42):
    rng = np.random.default_rng(seed)
    total_samples = N_TRAIN + N_TEST
    X = []
    y = []

    for i in range(total_samples):
        u = rng.standard_normal(N_QUBITS)
        u /= np.linalg.norm(u)
        label = i % 2
        r = rng.uniform(0.40, 0.70) if label == 1 else rng.uniform(0.80, 1.10)
        pt = u * r
        scaled = (pt + 1.0) * (np.pi / 2.0)
        X.append(scaled)
        y.append(label)

    X = np.array(X, dtype=np.float64)
    y = np.array(y, dtype=np.int64)

    X_train, X_test = X[:N_TRAIN], X[N_TRAIN:total_samples]
    y_train, y_test = y[:N_TRAIN], y[N_TRAIN:total_samples]
    return X_train, y_train, X_test, y_test


# ---------------------------------------------------------------------------
# 2. Classical Reference Baseline: 2-Layer Non-Linear MLP
# ---------------------------------------------------------------------------
class ClassicalMLP:
    def __init__(self, seed: int = 42):
        rng = np.random.default_rng(seed)
        self.W1 = rng.standard_normal((N_QUBITS, 32)) * 0.3
        self.b1 = np.zeros(32)
        self.W2 = rng.standard_normal((32, 2)) * 0.3
        self.b2 = np.zeros(2)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.h = np.maximum(0, x @ self.W1 + self.b1)
        self.logits = self.h @ self.W2 + self.b2
        exp_l = np.exp(self.logits - np.max(self.logits, axis=-1, keepdims=True))
        return exp_l / np.sum(exp_l, axis=-1, keepdims=True)

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 500, lr: float = 0.05):
        N = len(y)
        for _ in range(epochs):
            probs = self.forward(X)
            dlogits = (probs - np.eye(2)[y]) / N

            dW2 = self.h.T @ dlogits
            db2 = np.sum(dlogits, axis=0)
            dh = dlogits @ self.W2.T
            dz1 = dh * (self.h > 0)
            dW1 = X.T @ dz1
            db1 = np.sum(dz1, axis=0)

            self.W2 -= lr * dW2
            self.b2 -= lr * db2
            self.W1 -= lr * dW1
            self.b1 -= lr * db1

    def input_grad(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        probs = self.forward(x)
        dlogits = probs - np.eye(2)[y]
        dh = dlogits @ self.W2.T
        dz1 = dh * (self.h > 0)
        return dz1 @ self.W1.T


def generate_pgd_adversaries(model: ClassicalMLP, X: np.ndarray, y: np.ndarray, eps: float, steps: int = 15):
    if eps <= 0.0:
        return X.copy()
    alpha = eps / 4.0
    X_adv = X.copy()
    for _ in range(steps):
        grad = model.input_grad(X_adv, y)
        X_adv = np.clip(X_adv + alpha * np.sign(grad), 0.0, np.pi)
        X_adv = np.clip(X_adv, X - eps, X + eps)
    return X_adv


# ---------------------------------------------------------------------------
# 3. Multi-Depth Quantum Feature Map Assembly
# ---------------------------------------------------------------------------
def build_multidepth_feature_map(x: np.ndarray, depth: int, arm_type: str) -> QuantumCircuit:
    qc = QuantumCircuit(N_QUBITS, N_QUBITS)
    xy8_gates = ['x', 'y', 'x', 'y', 'y', 'x', 'y', 'x']

    for d in range(depth):
        # 1. Hadamard Layer
        for q in range(N_QUBITS):
            qc.h(q)

        # 2. Single-qubit Z phase rotation
        for q in range(N_QUBITS):
            qc.rz(float(2.0 * x[q]), q)

        # 3. Two-qubit ZZ interaction across nearest-neighbor chain
        for q in range(N_QUBITS - 1):
            theta = float(2.0 * (np.pi - x[q]) * (np.pi - x[q + 1]))
            qc.cx(q, q + 1)
            qc.rz(theta, q + 1)
            qc.cx(q, q + 1)

        qc.barrier()

        # 4. Insert Dynamical Decoupling Sequence per Arm Policy
        if arm_type == "sync_xy8":
            for g in xy8_gates:
                for q in range(N_QUBITS):
                    if g == 'x': qc.x(q)
                    else: qc.y(q)
                qc.barrier()
        elif arm_type in ("stag_xy8", "aa_control"):
            # Bipartite Staggering: Sublattice A (even) vs Sublattice B (odd)
            for g in xy8_gates:
                # Sublattice A (qubits 0, 2, 4, 6)
                for q in range(0, N_QUBITS, 2):
                    if g == 'x': qc.x(q)
                    else: qc.y(q)
                qc.barrier()
                # Sublattice B (qubits 1, 3, 5, 7)
                for q in range(1, N_QUBITS, 2):
                    if g == 'x': qc.x(q)
                    else: qc.y(q)
                qc.barrier()
        elif arm_type == "bare":
            # No DD pulses (bare idle decay)
            qc.barrier()

    # Final measurement layer
    for q in range(N_QUBITS):
        qc.measure(q, q)
    return qc


def main():
    print("=" * 80)
    print("OSIRIS-QAML-002: MULTI-DEPTH HIGH-SAMPLE STAGING HARNESS")
    print("=" * 80)

    # 1. Dataset & Baseline Training
    print(f"Generating 8D hypersphere dataset: N_train={N_TRAIN}, N_test={N_TEST} (seed 42)...")
    X_train, y_train, X_test, y_test = generate_dataset(seed=42)

    mlp = ClassicalMLP(seed=42)
    mlp.train(X_train, y_train, epochs=500, lr=0.05)

    clean_acc = float(np.mean(np.argmax(mlp.forward(X_test), axis=-1) == y_test))
    train_acc = float(np.mean(np.argmax(mlp.forward(X_train), axis=-1) == y_train))
    print(f"Classical MLP Baseline Trained:")
    print(f"  Train Accuracy: {train_acc*100:.2f}%")
    print(f"  Clean Test Acc: {clean_acc*100:.2f}% (N={N_TEST}, step size = 2.0 pp)")

    # Generate adversarial test sets
    adv_datasets = {}
    for eps in EPSILONS:
        X_adv = generate_pgd_adversaries(mlp, X_test, y_test, eps=eps, steps=15)
        acc_eps = float(np.mean(np.argmax(mlp.forward(X_adv), axis=-1) == y_test))
        adv_datasets[str(eps)] = {
            "accuracy": acc_eps,
            "mean_perturbation": float(np.mean(np.abs(X_adv - X_test)))
        }
        print(f"  PGD eps={eps:.2f}: Acc = {acc_eps*100:.2f}% (Retention = {acc_eps/clean_acc*100:.1f}%)")

    # 2. Gate 0 Statevector Pre-Flight Validation across Depths & Arms
    print("\nGate 0 Pre-Flight Statevector Checks:")
    x_sample = X_test[0]
    purity_records = {}
    for d in DEPTHS:
        for arm in ["bare", "sync_xy8", "stag_xy8", "aa_control"]:
            qc = build_multidepth_feature_map(x_sample, depth=d, arm_type=arm)
            pure_qc = qc.remove_final_measurements(inplace=False)
            sv = Statevector.from_instruction(pure_qc)
            purity = float(sv.purity().real)
            assert 0.99999 <= purity <= 1.00001, f"Purity violation at D={d}, arm={arm}: {purity}"
            purity_records[f"D{d}_{arm}"] = purity
    print(f"  Checked {len(purity_records)} circuits: All purities identically 1.000000 (Pure unitary evolution).")

    # 3. Gate Complexity Audit
    complexity_records = {}
    print("\nGate Complexity Audit across Depths:")
    for d in DEPTHS:
        complexity_records[f"depth_{d}"] = {}
        for arm in ["bare", "sync_xy8", "stag_xy8"]:
            qc = build_multidepth_feature_map(x_sample, depth=d, arm_type=arm)
            ops = qc.count_ops()
            cx_count = ops.get("cx", 0)
            pulse_count = ops.get("x", 0) + ops.get("y", 0)
            depth_val = qc.depth()
            complexity_records[f"depth_{d}"][arm] = {
                "cx_count": cx_count,
                "dd_pulses": pulse_count,
                "logical_depth": depth_val
            }
            print(f"  D={d} {arm:<10}: CX={cx_count:2d}, DD Pulses={pulse_count:2d}, Depth={depth_val:3d}")

    # 4. Save Staging Manifest
    manifest = {
        "benchmark_id": BENCHMARK_ID,
        "n_qubits": N_QUBITS,
        "n_test_samples": N_TEST,
        "n_train_samples": N_TRAIN,
        "depths": DEPTHS,
        "epsilons": EPSILONS,
        "arms": ARMS,
        "classical_baseline": {
            "clean_accuracy": clean_acc,
            "adversarial_accuracies": adv_datasets
        },
        "gate_complexity": complexity_records,
        "statevector_purities": purity_records,
        "timestamp": time.time()
    }

    manifest_file = EXP_DIR / "qaml_002_staging_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Staging complete: Manifest saved to {manifest_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
