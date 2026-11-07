#!/usr/bin/env python3
"""
harvest_hp003.py — Telemetry Harvester & Evaluator for OSIRIS-HP-003 Multi-Qubit Hayden-Preskill
Extracts physical counts from 45 circuits across 3 randomized blocks and evaluates H1-H5.
"""

import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
from qiskit_ibm_runtime import QiskitRuntimeService

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EXPERIMENT_DIR))


def main():
    print("=" * 80)
    print("OSIRIS-HP-003: PHYSICAL HARDWARE TELEMETRY HARVESTER")
    print("=" * 80)

    receipt_file = EXPERIMENT_DIR / "job_receipt_hp003.json"
    if not receipt_file.exists():
        raise FileNotFoundError(f"Receipt file not found: {receipt_file}")

    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    job_id = receipt["job_id"]
    backend_name = receipt["backend"]
    print(f"Target Job ID  : {job_id}")
    print(f"Target Backend : {backend_name}")

    service = QiskitRuntimeService()
    job = service.job(job_id)
    status_str = str(job.status())
    print(f"Current Job Status : {status_str}")

    backend = service.backend(backend_name)
    b_status = backend.status()
    print(f"Backend Status     : operational={b_status.operational}, pending_jobs={b_status.pending_jobs}")

    if "DONE" not in status_str.upper():
        print(f"\n[INFO] Job {job_id} is currently {status_str}. Pending jobs on {backend_name}: {b_status.pending_jobs}.")
        print("Hardware acquisition is still queued/running. Exiting without harvesting.")
        return

    print(f"\n[SUCCESS] Hardware job {job_id} is DONE! Extracting tomographic telemetry across 45 circuits...")
    result = job.result()
    metrics = job.metrics() if hasattr(job, "metrics") else {}
    usage = metrics.get("usage", {})
    print(f"  Real QPU Compute Consumed: {usage}")

    manifest_file = EXPERIMENT_DIR / "hp003_staging_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    meta_list = manifest["circuit_metadata"]

    circuit_records = []
    structured_data = {}

    for cct_idx, pub_res in enumerate(result):
        meta = meta_list[cct_idx]
        b_idx = meta["block_index"]
        arm = meta["arm"]
        basis = meta["basis"]

        data_bin = pub_res.data
        clbit_name = list(data_bin.keys())[0]
        bitarray = getattr(data_bin, clbit_name)
        counts = bitarray.get_counts()
        shots = sum(counts.values())

        # Classical bits: c[0] is R1, c[1] is M1', c[2] is R2, c[3] is M2'
        exp_pair1 = 0.0
        exp_pair2 = 0.0

        for bitstr, count in counts.items():
            bs = bitstr.replace(" ", "")
            p1 = 1.0 if bs[-1] == bs[-2] else -1.0
            p2 = 1.0 if bs[-3] == bs[-4] else -1.0
            exp_pair1 += p1 * count
            exp_pair2 += p2 * count

        exp_pair1 /= shots
        exp_pair2 /= shots

        circuit_records.append({
            "circuit_idx": cct_idx,
            "block": b_idx,
            "arm": arm,
            "basis": basis,
            "exp_pair1": round(exp_pair1, 6),
            "exp_pair2": round(exp_pair2, 6),
            "shots": shots,
            "counts_unique": len(counts)
        })

        key = (b_idx, arm)
        if key not in structured_data:
            structured_data[key] = {}
        structured_data[key][basis] = {
            "pair1": exp_pair1,
            "pair2": exp_pair2,
            "shots": shots
        }

    # Compute block-level fidelities
    arms = manifest["arms"]
    n_blocks = manifest["n_blocks"]
    block_evaluations = []
    arm_block_fidelities = {arm: {"f1": [], "f2": [], "f_mean": [], "f_prod": []} for arm in arms}

    for b_idx in range(n_blocks):
        b_summary = {"block_id": b_idx, "arms": {}}
        for arm in arms:
            b_arm = structured_data[(b_idx, arm)]
            # F = (1 + <XX> - <YY> + <ZZ>) / 4
            f1 = (1.0 + b_arm["XX"]["pair1"] - b_arm["YY"]["pair1"] + b_arm["ZZ"]["pair1"]) / 4.0
            f2 = (1.0 + b_arm["XX"]["pair2"] - b_arm["YY"]["pair2"] + b_arm["ZZ"]["pair2"]) / 4.0
            f_mean = 0.5 * (f1 + f2)
            f_prod = f1 * f2

            b_summary["arms"][arm] = {
                "f1": round(f1, 6),
                "f2": round(f2, 6),
                "f_mean": round(f_mean, 6),
                "f_prod": round(f_prod, 6)
            }
            arm_block_fidelities[arm]["f1"].append(f1)
            arm_block_fidelities[arm]["f2"].append(f2)
            arm_block_fidelities[arm]["f_mean"].append(f_mean)
            arm_block_fidelities[arm]["f_prod"].append(f_prod)

        block_evaluations.append(b_summary)

    # Synthesize across all 3 blocks
    arm_synthesis = {}
    for arm in arms:
        data = arm_block_fidelities[arm]
        m_f1 = float(np.mean(data["f1"]))
        m_f2 = float(np.mean(data["f2"]))
        m_fmean = float(np.mean(data["f_mean"]))
        m_fprod = float(np.mean(data["f_prod"]))

        sem_fmean = float(np.std(data["f_mean"], ddof=1) / math.sqrt(n_blocks)) if n_blocks > 1 else 0.0
        witness_w = 0.50 - m_fmean
        witness_w1 = 0.50 - m_f1
        witness_w2 = 0.50 - m_f2
        z_score = (m_fmean - 0.50) / sem_fmean if sem_fmean > 0 else 0.0

        arm_synthesis[arm] = {
            "mean_f1": round(m_f1, 6),
            "mean_f2": round(m_f2, 6),
            "mean_f_average": round(m_fmean, 6),
            "mean_f_prod": round(m_fprod, 6),
            "sem_f_average": round(sem_fmean, 6),
            "entanglement_witness": round(witness_w, 6),
            "witness_w1": round(witness_w1, 6),
            "witness_w2": round(witness_w2, 6),
            "z_score": round(z_score, 2),
            "is_entangled": bool(witness_w < 0),
            "block_fidelities_mean": [round(x, 6) for x in data["f_mean"]]
        }

    # Evaluate pre-registered hypotheses H1 - H5
    f1_arm_a = arm_synthesis["Arm A"]["mean_f1"]
    f2_arm_a = arm_synthesis["Arm A"]["mean_f2"]
    f_arm_b = arm_synthesis["Arm B"]["mean_f_average"]
    z_arm_b = arm_synthesis["Arm B"]["z_score"]

    f1_arm_b_def = arm_synthesis["Arm B-Def"]["mean_f1"]
    f2_arm_b_def = arm_synthesis["Arm B-Def"]["mean_f2"]
    w1_arm_b_def = arm_synthesis["Arm B-Def"]["witness_w1"]

    f_arm_b_ctrl = arm_synthesis["Arm B-Ctrl"]["mean_f_average"]
    f_arm_b_held = arm_synthesis["Arm B-Held"]["mean_f_average"]

    endpoints = {
        "H1_reversibility_positive_control": {
            "claim": "F1(Arm A) >= 0.85 and F2(Arm A) >= 0.85 independently",
            "observed_f1": f1_arm_a,
            "observed_f2": f2_arm_a,
            "passed": bool(f1_arm_a >= 0.85 and f2_arm_a >= 0.85)
        },
        "H2_primary_multiqubit_restricted_recovery": {
            "claim": "F_mean(Arm B) > 0.50 with Z > 3.72 (p < 1e-4)",
            "observed": f_arm_b,
            "z_score": z_arm_b,
            "witness": arm_synthesis["Arm B"]["entanglement_witness"],
            "passed": bool(f_arm_b > 0.50 and z_arm_b > 3.72)
        },
        "H3_quantum_capacity_single_photon_threshold": {
            "claim": "F1(Arm B-Def) <= 0.55 (W1 >= 0) and F2(Arm B-Def) <= 0.35 (Capacity bound)",
            "observed_f1": f1_arm_b_def,
            "observed_f2": f2_arm_b_def,
            "witness_w1": w1_arm_b_def,
            "passed": bool(f1_arm_b_def <= 0.55 and f2_arm_b_def <= 0.35)
        },
        "H4_unentangled_early_radiation_baseline": {
            "claim": "F_mean(Arm B-Ctrl) <= 0.35 (Unentangled baseline)",
            "observed": f_arm_b_ctrl,
            "passed": bool(f_arm_b_ctrl <= 0.35)
        },
        "H5_heldout_scrambler_specificity": {
            "claim": "F_mean(Arm B-Held) <= 0.35 (Specificity gate)",
            "observed": f_arm_b_held,
            "passed": bool(f_arm_b_held <= 0.35)
        }
    }

    results = {
        "benchmark_id": manifest["benchmark_id"],
        "backend": backend_name,
        "job_id": job_id,
        "timestamp_harvested": time.time(),
        "total_shots_acquired": sum(r["shots"] for r in circuit_records),
        "circuit_records": circuit_records,
        "block_evaluations": block_evaluations,
        "arm_synthesis": arm_synthesis,
        "hypothesis_verifications": endpoints
    }

    out_file = EXPERIMENT_DIR / "physical_hp003_results.json"
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nPhysical results saved to: {out_file.name}")

    print("\n" + "=" * 80)
    print("PRE-REGISTERED HYPOTHESIS VERIFICATIONS")
    print("=" * 80)
    for h_name, h_data in endpoints.items():
        status = "[PASS]" if h_data["passed"] else "[FAIL]"
        print(f"{status:7s} {h_name}: {h_data['claim']}")
        if "observed" in h_data:
            print(f"        Observed: {h_data['observed']}")
        else:
            print(f"        Observed: F1={h_data.get('observed_f1')}, F2={h_data.get('observed_f2')}")

    print("\n[SUCCESS] Telemetry harvest and synthesis complete.")


if __name__ == "__main__":
    main()
