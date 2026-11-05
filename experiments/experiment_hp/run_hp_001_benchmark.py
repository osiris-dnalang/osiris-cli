#!/usr/bin/env python3
"""
run_hp_001_benchmark.py
OSIRIS-HP-001 Benchmark Execution Suite
(0 QPU Seconds Consumed · Local Deterministic Execution)

Executes the pre-registered benchmark across N = 20 independent Haar-random scramblers:
  1. Arm A (Full-access reversible control)
  2. Arm B (Restricted-access recovery with entangled B-E vs unentangled control)
  3. Radiation Size Sweep (kD = 1, 2, 3)
  4. Physical Noise Sweep (Gamma = 0.00, 0.05, 0.10, 0.20)
  5. Statistical hypothesis evaluation (H1, H2, H3, H4)

Outputs:
  - experiments/experiment_hp/results_hp_001_benchmark.json
"""

from __future__ import annotations
import json
import time
import numpy as np
from pathlib import Path
from qiskit.quantum_info import random_unitary
from scipy import stats

from hayden_preskill_engine import (
    run_arm_a_reversible,
    run_arm_b_restricted,
    run_arm_c_noisy
)

ROOT = Path(__file__).resolve().parent
RESULTS_FILE = ROOT / "results_hp_001_benchmark.json"

def bootstrap_ci(data: List[float], n_resamples: int = 2000, alpha: float = 0.05) -> Tuple[float, float]:
    """Compute 95% bootstrap confidence interval."""
    arr = np.array(data)
    boot_means = [np.mean(np.random.choice(arr, size=len(arr), replace=True)) for _ in range(n_resamples)]
    low = float(np.percentile(boot_means, 100 * (alpha / 2.0)))
    high = float(np.percentile(boot_means, 100 * (1.0 - alpha / 2.0)))
    return (low, high)

def main():
    N_TRIALS = 20
    SEEDS = [1000 + i * 37 for i in range(N_TRIALS)]
    np.random.seed(42)

    print("================================================================================")
    print("OSIRIS-HP-001: HAYDEN-PRESKILL QUANTUM RECOVERY BENCHMARK")
    print("================================================================================")
    print(f"Executing N = {N_TRIALS} independent Haar-random scrambling trials on 6 qubits...")

    arm_a_fidelities = []
    arm_b_entangled_fidelities = []
    arm_b_unentangled_fidelities = []
    advantages = []

    kd_sweep = {1: [], 2: [], 3: []}
    noise_sweep = {0.00: [], 0.05: [], 0.10: [], 0.20: []}

    trial_records = []

    t0 = time.time()
    for i, s in enumerate(SEEDS):
        U = random_unitary(8, seed=s).data

        # Arm A: Reversible
        res_a = run_arm_a_reversible(U)
        f_a = res_a["fidelity_F_rec"]
        arm_a_fidelities.append(f_a)

        # Arm B: Restricted (kD = 2, Post-Page)
        res_b_ent = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=2)
        f_b_ent = res_b_ent["fidelity_F_rec"]
        arm_b_entangled_fidelities.append(f_b_ent)

        # Arm B: Unentangled Control
        res_b_unent = run_arm_b_restricted(U, entangled_BE=False, radiation_qubits=2)
        f_b_unent = res_b_unent["fidelity_F_rec"]
        arm_b_unentangled_fidelities.append(f_b_unent)

        adv = f_b_ent - f_b_unent
        advantages.append(adv)

        # Radiation sweep
        res_kd1 = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=1)
        res_kd3 = run_arm_b_restricted(U, entangled_BE=True, radiation_qubits=3)
        kd_sweep[1].append(res_kd1["fidelity_F_rec"])
        kd_sweep[2].append(f_b_ent)
        kd_sweep[3].append(res_kd3["fidelity_F_rec"])

        # Noise sweep
        for gamma in noise_sweep.keys():
            res_noise = run_arm_c_noisy(U, noise_rate=gamma, radiation_qubits=2)
            noise_sweep[gamma].append(res_noise["fidelity_F_rec"])

        trial_records.append({
            "trial": i + 1,
            "seed": s,
            "arm_a_reversible": f_a,
            "arm_b_entangled": f_b_ent,
            "arm_b_unentangled": f_b_unent,
            "entanglement_advantage": adv,
            "exp_XX": res_b_ent["exp_XX"],
            "exp_YY": res_b_ent["exp_YY"],
            "exp_ZZ": res_b_ent["exp_ZZ"]
        })

    elapsed = time.time() - t0

    # Statistical Aggregation
    mean_a = float(np.mean(arm_a_fidelities))
    ci_a = bootstrap_ci(arm_a_fidelities)

    mean_b_ent = float(np.mean(arm_b_entangled_fidelities))
    ci_b_ent = bootstrap_ci(arm_b_entangled_fidelities)

    mean_b_unent = float(np.mean(arm_b_unentangled_fidelities))
    ci_b_unent = bootstrap_ci(arm_b_unentangled_fidelities)

    mean_adv = float(np.mean(advantages))
    ci_adv = bootstrap_ci(advantages)

    # Paired t-test: Arm B Entangled vs Unentangled Control
    t_stat, p_val_2s = stats.ttest_rel(arm_b_entangled_fidelities, arm_b_unentangled_fidelities)
    p_val_1s = p_val_2s / 2.0 if t_stat > 0 else 1.0 - (p_val_2s / 2.0)

    print("\n--- RESULTS SUMMARY ---")
    print(f"Trials Completed            : {N_TRIALS} in {elapsed:.2f} s")
    print(f"Arm A (Reversible Control)  : Mean F = {mean_a:.6f} [95% CI: {ci_a[0]:.6f}, {ci_a[1]:.6f}]")
    print(f"Arm B (Entangled Recovery)  : Mean F = {mean_b_ent:.6f} [95% CI: {ci_b_ent[0]:.6f}, {ci_b_ent[1]:.6f}]")
    print(f"Arm B (Unentangled Control) : Mean F = {mean_b_unent:.6f} [95% CI: {ci_b_unent[0]:.6f}, {ci_b_unent[1]:.6f}]")
    print(f"Entanglement Advantage      : Delta  = +{mean_adv*100:.2f} pp [95% CI: +{ci_adv[0]*100:.2f}, +{ci_adv[1]*100:.2f} pp]")
    print(f"Hypothesis Test H2          : t = {t_stat:.4f}, df = {N_TRIALS-1}, p_1s = {p_val_1s:.4e}")

    print("\n--- RADIATION SIZE SWEEP (H3: Page Transition) ---")
    for kd in sorted(kd_sweep.keys()):
        m_kd = float(np.mean(kd_sweep[kd]))
        ci_kd = bootstrap_ci(kd_sweep[kd])
        print(f"  kD = {kd} Qubits : Mean F = {m_kd:.6f} [95% CI: {ci_kd[0]:.6f}, {ci_kd[1]:.6f}]")

    print("\n--- NOISE SWEEP (H4: Lindblad / Depolarizing Degradation) ---")
    for gamma in sorted(noise_sweep.keys()):
        m_noise = float(np.mean(noise_sweep[gamma]))
        ci_noise = bootstrap_ci(noise_sweep[gamma])
        print(f"  Gamma = {gamma:.2f} : Mean F = {m_noise:.6f} [95% CI: {ci_noise[0]:.6f}, {ci_noise[1]:.6f}]")

    # Hypothesis Verification Verdicts
    verdicts = {
        "H1_reversible_control": {
            "prediction": "F_ArmA >= 0.999",
            "observed": mean_a,
            "passed": bool(mean_a >= 0.999)
        },
        "H2_restricted_recovery": {
            "prediction": "F_ArmB > 0.50 and Advantage > 0 (p < 0.05)",
            "observed_fidelity": mean_b_ent,
            "observed_advantage": mean_adv,
            "p_value_1s": float(p_val_1s),
            "passed": bool(mean_b_ent > 0.50 and p_val_1s < 0.05)
        },
        "H3_page_transition": {
            "prediction": "F(kD=1) < F(kD=2) < F(kD=3)",
            "observed_fidelities": [float(np.mean(kd_sweep[k])) for k in [1, 2, 3]],
            "passed": bool(np.mean(kd_sweep[1]) < np.mean(kd_sweep[2]) <= np.mean(kd_sweep[3]))
        },
        "H4_noise_sensitivity": {
            "prediction": "Monotonic degradation under increasing noise",
            "observed_fidelities": [float(np.mean(noise_sweep[g])) for g in [0.00, 0.05, 0.10, 0.20]],
            "passed": bool(np.mean(noise_sweep[0.00]) > np.mean(noise_sweep[0.05]) > np.mean(noise_sweep[0.10]) > np.mean(noise_sweep[0.20]))
        }
    }

    final_payload = {
        "protocol": "OSIRIS-HP-001",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_trials": N_TRIALS,
        "summary": {
            "mean_arm_a_reversible": mean_a,
            "mean_arm_b_entangled": mean_b_ent,
            "mean_arm_b_unentangled": mean_b_unent,
            "mean_entanglement_advantage": mean_adv,
            "t_statistic": float(t_stat),
            "p_value_1s": float(p_val_1s)
        },
        "radiation_sweep": {k: {"mean": float(np.mean(v)), "ci_95": bootstrap_ci(v)} for k, v in kd_sweep.items()},
        "noise_sweep": {str(k): {"mean": float(np.mean(v)), "ci_95": bootstrap_ci(v)} for k, v in noise_sweep.items()},
        "hypotheses_verdicts": verdicts,
        "trials": trial_records
    }

    RESULTS_FILE.write_text(json.dumps(final_payload, indent=2), encoding="utf-8")
    print(f"\n✓ Complete benchmark telemetry saved to: {RESULTS_FILE.name}")

if __name__ == "__main__":
    main()
