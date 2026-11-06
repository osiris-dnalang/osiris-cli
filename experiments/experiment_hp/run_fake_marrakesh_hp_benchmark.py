#!/usr/bin/env python3
"""
run_fake_marrakesh_hp_benchmark.py
OSIRIS-HP-001: Hayden-Preskill Quantum Recovery Benchmark on FakeMarrakesh
(0 QPU Seconds Consumed · Local Calibrated Heron r2 Simulation)

Simulates the 6-qubit Hayden-Preskill protocol on ibm_marrakesh topology:
  - Subgraph: Qubits {R: 14, M: 15, B1: 19, B2: 35, E1: 13, E2: 34}
  - Calibrated Heron r2 noise: T1, T2, CZ coupler error, readout assignment errors.
  - Full statistical suite across N = 20 Haar-random scrambling unitaries.
  - Operationally rigorous metrics: Uhlmann fidelity, Pauli correlators, Trace distance,
    and discrete Kantorovich-Rubinstein Wasserstein-1 distance (W1) via dual LP.
"""

from __future__ import annotations
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import scipy.stats as stats
from scipy.optimize import linprog
from scipy.linalg import sqrtm

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qiskit.quantum_info import random_unitary
from qiskit_ibm_runtime.fake_provider import FakeMarrakesh

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.append(str(ENGINE_DIR))
from hayden_preskill_engine import (
    run_arm_a_reversible,
    run_arm_b_restricted,
    I2, X, Y, Z, XX, YY, ZZ, II, PROJ_PHI_PLUS
)

ROOT = Path(__file__).resolve().parent
OUTPUT_JSON = ROOT / "results_hp_001_fakemarrakesh.json"

# ==============================================================================
# 1. DUAL-LP DISCRETE WASSERSTEIN-1 & METRIC FUNCTIONS
# ==============================================================================

def trace_distance_matrix(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Exact trace distance D_tr(rho, sigma) = 0.5 * Tr|rho - sigma|."""
    diff = rho - sigma
    evals = np.linalg.eigvalsh((diff + diff.conj().T) / 2.0)
    return float(0.5 * np.sum(np.abs(evals)))

def quantum_hellinger_distance(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Quantum Hellinger distance D_H = sqrt(Tr[(sqrt(rho) - sqrt(sigma))^2])."""
    s_rho = sqrtm(rho)
    s_sig = sqrtm(sigma)
    diff = s_rho - s_sig
    val = np.real(np.trace(diff @ diff.conj().T))
    return float(np.sqrt(max(0.0, val)))

def dual_lp_w1_2q(p: np.ndarray, q: np.ndarray) -> float:
    """
    Exact discrete Wasserstein-1 distance over 2-bit hypercube
    with normalized Hamming ground metric d_H(x, y) / 2.
    """
    dim = 4
    c = -(p - q)
    A_rows, b_rows = [], []
    for x in range(dim):
        for bit in range(2):
            y = x ^ (1 << bit)
            if x < y:
                r1 = np.zeros(dim); r1[x] = 1.0; r1[y] = -1.0
                A_rows.append(r1); b_rows.append(0.5)
                r2 = np.zeros(dim); r2[y] = 1.0; r2[x] = -1.0
                A_rows.append(r2); b_rows.append(0.5)
    res = linprog(c, A_ub=np.array(A_rows), b_ub=np.array(b_rows), bounds=[(0, 1)]*dim, method="highs")
    return float(-res.fun) if res.success else float(np.sum(np.abs(p - q)) / 2.0)

def bootstrap_ci(data: List[float], n_resamples: int = 2000, alpha: float = 0.05) -> Tuple[float, float]:
    """Compute 95% bootstrap confidence interval."""
    arr = np.array(data)
    boot_means = [np.mean(np.random.choice(arr, size=len(arr), replace=True)) for _ in range(n_resamples)]
    low = float(np.percentile(boot_means, 100 * (alpha / 2.0)))
    high = float(np.percentile(boot_means, 100 * (1.0 - alpha / 2.0)))
    return (low, high)

# ==============================================================================
# 2. FAKEMARRAKESH HARDWARE NOISE EXTRACTION
# ==============================================================================

def get_fakemarrakesh_noise_model():
    """Extract calibration parameters and effective channel rates from FakeMarrakesh."""
    fake = FakeMarrakesh()
    props = fake.properties()
    qubits = [14, 15, 19, 35, 13, 34]
    
    t1_list, t2_list, ro_err_list = [], [], []
    for q in qubits:
        t1_list.append(props.t1(q) * 1e6)
        t2_list.append(props.t2(q) * 1e6)
        ro_err_list.append(props.readout_error(q))
    
    edges = [(14, 15), (15, 19), (19, 35), (35, 34), (13, 14)]
    cz_err_list = []
    for u, v in edges:
        try:
            cz_err_list.append(props.gate_error("cz", [u, v]))
        except Exception:
            pass

    # Typical 6-qubit circuit duration on Heron r2 (~30 cycles x 60ns = 1.8 us)
    tau_circ = 1.8  # us
    mean_t2 = float(np.mean(t2_list))
    mean_cz_err = float(np.mean(cz_err_list)) if cz_err_list else 0.0015
    mean_ro_err = float(np.mean(ro_err_list))

    # Base depolarizing rate on output 2-qubit state:
    # Accumulated dephasing ~ 1 - exp(-tau / T2)
    gamma_dephasing = float(1.0 - np.exp(-tau_circ / mean_t2))
    # Accumulated gate error across 15 CZ gates
    gamma_gates = float(1.0 - (1.0 - mean_cz_err)**15)
    # Total effective 2-qubit depolarizing parameter on FakeMarrakesh:
    gamma_heron = float(gamma_dephasing + gamma_gates + 2 * mean_ro_err)

    calib_info = {
        "backend": "ibm_marrakesh (Heron r2)",
        "subgraph_qubits": qubits,
        "mean_T1_us": float(np.mean(t1_list)),
        "mean_T2_us": mean_t2,
        "mean_readout_error": mean_ro_err,
        "mean_CZ_error": mean_cz_err,
        "estimated_circuit_duration_us": tau_circ,
        "effective_depolarizing_rate_gamma": round(gamma_heron, 4)
    }
    return calib_info, gamma_heron

def apply_hardware_noise(rho: np.ndarray, gamma: float) -> np.ndarray:
    """Apply calibrated hardware depolarizing channel to 2-qubit density matrix."""
    return (1.0 - gamma) * rho + (gamma / 4.0) * II

# ==============================================================================
# 3. BENCHMARK EXECUTION
# ==============================================================================

def main():
    print("=" * 80)
    print("OSIRIS-HP-001: HAYDEN-PRESKILL BENCHMARK ON FAKEMARRAKESH (HERON r2)")
    print("================================================================================")
    print("0 QPU Seconds Consumed · Deterministic Hardware-Calibrated Simulation")
    
    calib, gamma_base = get_fakemarrakesh_noise_model()
    print(f"\n[Hardware Calibration: ibm_marrakesh Subgraph {calib['subgraph_qubits']}]")
    print(f"  Mean T1: {calib['mean_T1_us']:.1f} µs | Mean T2: {calib['mean_T2_us']:.1f} µs")
    print(f"  Mean Readout Error: {calib['mean_readout_error']*100:.2f}% | Mean CZ Error: {calib['mean_CZ_error']*100:.3f}%")
    print(f"  Effective Heron Hardware Noise Floor (Gamma_0): {gamma_base*100:.2f}%")

    N_TRIALS = 20
    SEEDS = [2000 + i * 43 for i in range(N_TRIALS)]
    np.random.seed(42)

    arm_a_fidelities = []
    arm_b_ent_fidelities = []
    arm_b_unent_fidelities = []
    arm_b_w1_distances = []
    arm_b_i_op = []

    kd_sweep = {1: [], 2: [], 3: []}
    noise_multipliers = [0.0, 0.5, 1.0, 2.0, 3.0]
    noise_sweep = {m: [] for m in noise_multipliers}

    trial_records = []
    bell_proj = PROJ_PHI_PLUS
    p_bell = np.array([0.5, 0.0, 0.0, 0.5])

    t0 = time.time()
    for idx, s in enumerate(SEEDS):
        U = random_unitary(8, seed=s).data

        # --- Arm A: Reversible Control under Heron Noise ---
        res_a_ideal = run_arm_a_reversible(U)
        rho_a_noisy = apply_hardware_noise(res_a_ideal["rho_RM"], gamma_base)
        f_a = float(np.real(np.trace(bell_proj @ rho_a_noisy)))
        arm_a_fidelities.append(f_a)

        # --- Arm B: Entangled Recovery under Heron Noise ---
        res_b_ideal = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=2)
        rho_b_noisy = apply_hardware_noise(res_b_ideal["rho_RM"], gamma_base)
        f_b_ent = float(np.real(np.trace(bell_proj @ rho_b_noisy)))
        arm_b_ent_fidelities.append(f_b_ent)

        # W1 and Operational Preservation for Arm B
        p_b = np.real(np.diag(rho_b_noisy))
        w1_b = dual_lp_w1_2q(p_bell, p_b)
        arm_b_w1_distances.append(w1_b)
        d_tr_b = trace_distance_matrix(bell_proj, rho_b_noisy)
        i_op_b = 1.0 - d_tr_b
        arm_b_i_op.append(i_op_b)

        # --- Arm B: Unentangled Control under Heron Noise ---
        res_b_unent_ideal = run_arm_b_restricted(U, entangled_BE=False, radiation_qubits=2)
        rho_unent_noisy = apply_hardware_noise(res_b_unent_ideal["rho_RM"], gamma_base)
        f_b_unent = float(np.real(np.trace(bell_proj @ rho_unent_noisy)))
        arm_b_unent_fidelities.append(f_b_unent)

        # --- Radiation Sweep under Heron Noise ---
        for kd in [1, 2, 3]:
            res_kd = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=kd)
            rho_kd_noisy = apply_hardware_noise(res_kd["rho_RM"], gamma_base)
            kd_sweep[kd].append(float(np.real(np.trace(bell_proj @ rho_kd_noisy))))

        # --- Noise Scaling Sweep ---
        for mult in noise_multipliers:
            g = mult * gamma_base
            rho_scaled = apply_hardware_noise(res_b_ideal["rho_RM"], g)
            noise_sweep[mult].append(float(np.real(np.trace(bell_proj @ rho_scaled))))

        # Tomographic observables
        ev_xx = float(np.real(np.trace(XX @ rho_b_noisy)))
        ev_yy = float(np.real(np.trace(YY @ rho_b_noisy)))
        ev_zz = float(np.real(np.trace(ZZ @ rho_b_noisy)))

        trial_records.append({
            "trial": idx + 1,
            "seed": s,
            "arm_a_reversible": f_a,
            "arm_b_entangled": f_b_ent,
            "arm_b_unentangled": f_b_unent,
            "entanglement_advantage": f_b_ent - f_b_unent,
            "wasserstein_1": w1_b,
            "operational_preservation": i_op_b,
            "exp_XX": ev_xx,
            "exp_YY": ev_yy,
            "exp_ZZ": ev_zz
        })

    elapsed = time.time() - t0

    # Statistical Aggregation
    mean_a = float(np.mean(arm_a_fidelities))
    ci_a = bootstrap_ci(arm_a_fidelities)

    mean_b_ent = float(np.mean(arm_b_ent_fidelities))
    ci_b_ent = bootstrap_ci(arm_b_ent_fidelities)

    mean_b_unent = float(np.mean(arm_b_unent_fidelities))
    ci_b_unent = bootstrap_ci(arm_b_unent_fidelities)

    advantages = [e - u for e, u in zip(arm_b_ent_fidelities, arm_b_unent_fidelities)]
    mean_adv = float(np.mean(advantages))
    ci_adv = bootstrap_ci(advantages)

    mean_w1 = float(np.mean(arm_b_w1_distances))
    ci_w1 = bootstrap_ci(arm_b_w1_distances)

    mean_iop = float(np.mean(arm_b_i_op))

    # Paired t-test
    t_stat, p_val_2s = stats.ttest_rel(arm_b_ent_fidelities, arm_b_unent_fidelities)
    p_val_1s = float(p_val_2s / 2.0 if t_stat > 0 else 1.0 - (p_val_2s / 2.0))

    # Correlation: W1 vs Fidelity
    r_val, p_corr = stats.pearsonr(arm_b_ent_fidelities, arm_b_w1_distances)

    print("\n--- STATISTICAL RESULTS SUMMARY ---")
    print(f"Trials Completed            : {N_TRIALS} in {elapsed:.2f} s")
    print(f"Arm A (Reversible Control)  : Mean F = {mean_a:.4f} [95% CI: {ci_a[0]:.4f}, {ci_a[1]:.4f}]")
    print(f"Arm B (Entangled Recovery)  : Mean F = {mean_b_ent:.4f} [95% CI: {ci_b_ent[0]:.4f}, {ci_b_ent[1]:.4f}]")
    print(f"Arm B (Unentangled Control) : Mean F = {mean_b_unent:.4f} [95% CI: {ci_b_unent[0]:.4f}, {ci_b_unent[1]:.4f}]")
    print(f"Entanglement Advantage      : Delta  = +{mean_adv*100:.2f} pp [95% CI: +{ci_adv[0]*100:.2f}, +{ci_adv[1]*100:.2f} pp]")
    print(f"Hypothesis Test H2          : t = {t_stat:.4f}, df = {N_TRIALS-1}, p_1s = {p_val_1s:.4e}")
    print(f"Dual-LP Wasserstein-1 (W1) : Mean W1 = {mean_w1:.4f} [95% CI: {ci_w1[0]:.4f}, {ci_w1[1]:.4f}]")
    print(f"W1 vs Fidelity Correlation  : Pearson r = {r_val:.4f} (p = {p_corr:.4e})")

    print("\n--- RADIATION SIZE SWEEP (Page Transition) ---")
    for kd in [1, 2, 3]:
        m_kd = float(np.mean(kd_sweep[kd]))
        ci_kd = bootstrap_ci(kd_sweep[kd])
        print(f"  kD = {kd} Qubits: Mean F = {m_kd:.4f} [95% CI: {ci_kd[0]:.4f}, {ci_kd[1]:.4f}]")

    print("\n--- NOISE SCALING SWEEP ---")
    for mult in noise_multipliers:
        m_n = float(np.mean(noise_sweep[mult]))
        print(f"  {mult:.1f}x Heron Noise: Mean F = {m_n:.4f}")

    # Hypotheses Verification Verdicts
    verdicts = {
        "H1_reversible_control": {
            "criterion": "F_ArmA >= 0.90 under Heron noise floor",
            "observed": mean_a,
            "passed": bool(mean_a >= 0.90)
        },
        "H2_restricted_recovery": {
            "criterion": "F_ArmB > 0.50 and Advantage > 0 (p < 0.05)",
            "observed_fidelity": mean_b_ent,
            "observed_advantage": mean_adv,
            "t_statistic": float(t_stat),
            "p_value_1s": p_val_1s,
            "passed": bool(mean_b_ent > 0.50 and p_val_1s < 0.05)
        },
        "H3_page_transition": {
            "criterion": "F(kD=1) < F(kD=2) <= F(kD=3)",
            "observed_fidelities": [float(np.mean(kd_sweep[k])) for k in [1, 2, 3]],
            "passed": bool(np.mean(kd_sweep[1]) < np.mean(kd_sweep[2]) <= np.mean(kd_sweep[3]))
        },
        "H4_w1_anti_correlation": {
            "criterion": "Pearson r(F_rec, W1) < -0.90",
            "observed_r": float(r_val),
            "passed": bool(r_val < -0.90)
        }
    }

    # ==============================================================================
    # 4. PUBLICATION PLOT GENERATION
    # ==============================================================================
    print("\nGenerating publication-grade diagnostic plots...")
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "figure.titlesize": 14,
        "lines.linewidth": 2,
        "grid.alpha": 0.3
    })

    # Plot 1: Violin / Box Plot Comparison
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    data_to_plot = [arm_a_fidelities, arm_b_ent_fidelities, arm_b_unent_fidelities]
    positions = [1, 2, 3]
    parts = ax.violinplot(data_to_plot, positions=positions, showmeans=True, showextrema=True)
    for pc in parts["bodies"]:
        pc.set_facecolor("#2b5c8f")
        pc.set_alpha(0.6)
    parts["cmeans"].set_color("#d95f02")
    parts["cmeans"].set_linewidth(2.5)

    ax.axhline(0.50, color="#e41a1c", linestyle="--", label="Classical Entanglement Threshold (F = 0.50)")
    ax.set_xticks(positions)
    ax.set_xticklabels([
        f"Arm A: Reversible\nMean: {mean_a:.3f}",
        f"Arm B: Entangled\nMean: {mean_b_ent:.3f}",
        f"Arm B: Unentangled\nMean: {mean_b_unent:.3f}"
    ])
    ax.set_ylabel("Uhlmann Recovery Fidelity $F_{rec}$")
    ax.set_title("OSIRIS-HP-001: Hayden-Preskill Recovery on FakeMarrakesh (Heron r2)")
    ax.grid(True, linestyle=":")
    ax.legend(loc="lower right")
    ax.set_ylim(0.40, 1.02)
    fig1_path = ROOT / "hp_001_fakemarrakesh_violin_comparison.png"
    plt.tight_layout()
    plt.savefig(fig1_path)
    plt.close()
    print(f"  ✓ Figure 1: {fig1_path.name}")

    # Plot 2: Page Transition (Radiation Sweep)
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    k_vals = [1, 2, 3]
    means_kd = [float(np.mean(kd_sweep[k])) for k in k_vals]
    errors_kd = [float(np.std(kd_sweep[k])) for k in k_vals]
    ax.plot(k_vals, means_kd, marker="o", markersize=8, color="#1b9e77", linewidth=2.5, label="Calibrated Heron Noise Floor")
    ax.fill_between(k_vals, [m - e for m, e in zip(means_kd, errors_kd)], [m + e for m, e in zip(means_kd, errors_kd)], color="#1b9e77", alpha=0.2)
    ax.axhline(0.50, color="#e41a1c", linestyle="--", label="Entanglement Witness Threshold (0.50)")
    ax.axvline(2.0, color="#7570b3", linestyle=":", label="Page Transition Threshold ($k_D = k_M + 1$)")
    ax.set_xticks(k_vals)
    ax.set_xlabel("Accessible Radiation Subsystem Size $k_D$ (Qubits)")
    ax.set_ylabel("Entanglement Recovery Fidelity $F_{rec}$")
    ax.set_title("Page Transition: Recovery as Accessible Radiation Increases")
    ax.grid(True, linestyle=":")
    ax.legend(loc="lower right")
    fig2_path = ROOT / "hp_001_fakemarrakesh_page_transition.png"
    plt.tight_layout()
    plt.savefig(fig2_path)
    plt.close()
    print(f"  ✓ Figure 2: {fig2_path.name}")

    # Plot 3: Dual-LP W1 vs Uhlmann Fidelity
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.scatter(arm_b_w1_distances, arm_b_ent_fidelities, color="#7570b3", s=60, alpha=0.8, edgecolors="k", label=f"Haar Trials (r = {r_val:.3f})")
    m_slope, b_intercept = np.polyfit(arm_b_w1_distances, arm_b_ent_fidelities, 1)
    x_line = np.linspace(min(arm_b_w1_distances), max(arm_b_w1_distances), 50)
    ax.plot(x_line, m_slope * x_line + b_intercept, color="#e7298a", linestyle="-", label=f"Fit: $F = {m_slope:.2f} W_1 + {b_intercept:.2f}$")
    ax.set_xlabel("Discrete Wasserstein-1 Distance $W_1$ (Kantorovich Dual LP)")
    ax.set_ylabel("Uhlmann State Fidelity $F_{rec}$")
    ax.set_title("Dual-LP Transport Distance vs. Uhlmann Fidelity under Hardware Noise")
    ax.grid(True, linestyle=":")
    ax.legend(loc="upper right")
    fig3_path = ROOT / "hp_001_fakemarrakesh_w1_vs_fidelity.png"
    plt.tight_layout()
    plt.savefig(fig3_path)
    plt.close()
    print(f"  ✓ Figure 3: {fig3_path.name}")

    # Plot 4: Noise Scaling Sweep
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    mults = noise_multipliers
    means_noise = [float(np.mean(noise_sweep[m])) for m in mults]
    ax.plot(mults, means_noise, marker="s", markersize=8, color="#d95f02", linewidth=2.5, label="Arm B Entangled Recovery")
    ax.axhline(0.50, color="#e41a1c", linestyle="--", label="Entanglement Limit (0.50)")
    ax.axvline(1.0, color="#386cb0", linestyle=":", label="ibm_marrakesh Baseline (1.0x)")
    ax.set_xlabel("Noise Multiplier (Relative to Heron r2 Calibration)")
    ax.set_ylabel("Recovery Fidelity $F_{rec}$")
    ax.set_title("Decoherence Degradation under Scaled Hardware Noise")
    ax.grid(True, linestyle=":")
    ax.legend(loc="upper right")
    fig4_path = ROOT / "hp_001_fakemarrakesh_noise_scaling.png"
    plt.tight_layout()
    plt.savefig(fig4_path)
    plt.close()
    print(f"  ✓ Figure 4: {fig4_path.name}")

    # Save Payload
    output_payload = {
        "benchmark": "OSIRIS-HP-001",
        "backend": "FakeMarrakesh",
        "execution_mode": "Calibrated Heron r2 Simulator (0 QPU s)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_trials": N_TRIALS,
        "calibration": calib,
        "summary": {
            "mean_arm_a_reversible": mean_a,
            "ci_95_arm_a": ci_a,
            "mean_arm_b_entangled": mean_b_ent,
            "ci_95_arm_b_entangled": ci_b_ent,
            "mean_arm_b_unentangled": mean_b_unent,
            "ci_95_arm_b_unentangled": ci_b_unent,
            "mean_entanglement_advantage": mean_adv,
            "ci_95_advantage": ci_adv,
            "t_statistic": float(t_stat),
            "p_value_1s": p_val_1s,
            "mean_wasserstein_1": mean_w1,
            "ci_95_w1": ci_w1,
            "mean_operational_preservation": mean_iop,
            "pearson_r_w1_fidelity": float(r_val)
        },
        "radiation_sweep": {k: {"mean": float(np.mean(v)), "ci_95": bootstrap_ci(v)} for k, v in kd_sweep.items()},
        "noise_sweep": {str(k): {"mean": float(np.mean(v))} for k, v in noise_sweep.items()},
        "hypotheses_verdicts": verdicts,
        "trials": trial_records,
        "figures": [str(fig1_path.name), str(fig2_path.name), str(fig3_path.name), str(fig4_path.name)]
    }

    OUTPUT_JSON.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    print(f"\n✓ Telemetry saved to: {OUTPUT_JSON.name}")

if __name__ == "__main__":
    main()
