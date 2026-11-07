#!/usr/bin/env python3
"""
harvest_hp002.py — Telemetry Harvester for OSIRIS-HP-002 Certified Recovery
Monitors Job dbn9e10qtr0c73acjf50 on ibm_fez, extracts counts from 36 circuits,
and computes reconstructed Bell state fidelities across all 4 experimental arms.
"""

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from qiskit_ibm_runtime import QiskitRuntimeService

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EXPERIMENT_DIR))


def main():
    print("=" * 80)
    print("OSIRIS-HP-002: PHYSICAL HARDWARE TELEMETRY HARVESTER")
    print("=" * 80)

    receipt_file = EXPERIMENT_DIR / "job_receipt_hp002.json"
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
        print("Waiting for physical hardware execution to complete...")
        job.wait_for_final_state()
        status_str = str(job.status())
        print(f"Final Job Status   : {status_str}")

    if "DONE" not in status_str.upper():
        print(f"[ERROR] Job terminated with non-DONE status: {status_str}")
        return

    print(f"\n[SUCCESS] Hardware job {job_id} is DONE! Extracting tomographic telemetry across 36 circuits...")
    result = job.result()
    metrics = job.metrics() if hasattr(job, "metrics") else {}
    usage = metrics.get("usage", {})
    print(f"  Real QPU Compute Consumed: {usage}")

    arms = [
        "Arm A (Full-Access Inverse)",
        "Arm B (Restricted Recovery - Matched)",
        "Arm B Control (Separable Trapped)",
        "Arm B Held-Out (Scrambler Specificity Gate)"
    ]
    bases = ["XX", "YY", "ZZ"]
    n_blocks = 3

    block_data = {arm: [] for arm in arms}
    circuit_records = []

    # Iterate through the 36 circuits: 3 blocks x 4 arms x 3 bases
    cct_idx = 0
    for b_idx in range(n_blocks):
        for arm in arms:
            arm_exp = {}
            arm_var = {}
            for basis in bases:
                pub_res = result[cct_idx]
                data_bin = pub_res.data
                clbit_name = list(data_bin.keys())[0]
                bitarray = getattr(data_bin, clbit_name)
                counts = bitarray.get_counts()
                shots = sum(counts.values())

                # Measurement ordering: classical bit 0 is R, bit 1 is Decoded
                # Qiskit bitstring convention: 'b1 b0'
                exp_val = 0.0
                for bitstring, count in counts.items():
                    cb = bitstring.replace(" ", "")
                    parity = 1.0 if cb[0] == cb[1] else -1.0
                    exp_val += parity * count
                exp_val /= shots

                arm_exp[basis] = exp_val
                arm_var[basis] = (1.0 - exp_val**2) / shots

                circuit_records.append({
                    "circuit_idx": cct_idx,
                    "block": b_idx,
                    "arm": arm,
                    "basis": basis,
                    "exp_val": round(exp_val, 6),
                    "shots": shots,
                    "counts": counts
                })
                cct_idx += 1

            # Bell state fidelity: F = (1 + <XX> - <YY> + <ZZ>) / 4
            f_block = (1.0 + arm_exp["XX"] - arm_exp["YY"] + arm_exp["ZZ"]) / 4.0
            sigma_block = math.sqrt(sum(arm_var.values())) / 4.0
            block_data[arm].append({
                "block": b_idx,
                "fidelity": f_block,
                "sigma": sigma_block,
                "exp_xx": arm_exp["XX"],
                "exp_yy": arm_exp["YY"],
                "exp_zz": arm_exp["ZZ"]
            })

    # Synthesize across the 3 randomized blocks
    arm_synthesis = {}
    print("\n" + "=" * 95)
    print(f"OSIRIS-HP-002: EMPIRICAL HARDWARE TOMOGRAPHIC RESULTS ({backend_name})")
    print("=" * 95)
    print(f"{'Experimental Arm':<42} | {'<XX>':<7} | {'<YY>':<7} | {'<ZZ>':<7} | {'Reconstructed F_ent':<16} | {'Determination'}")
    print("-" * 95)

    for arm in arms:
        fids = [b["fidelity"] for b in block_data[arm]]
        xxs = [b["exp_xx"] for b in block_data[arm]]
        yys = [b["exp_yy"] for b in block_data[arm]]
        zzs = [b["exp_zz"] for b in block_data[arm]]

        mean_f = float(np.mean(fids))
        sem_f = float(np.std(fids) / math.sqrt(n_blocks))
        mean_xx = float(np.mean(xxs))
        mean_yy = float(np.mean(yys))
        mean_zz = float(np.mean(zzs))

        is_entangled = mean_f > 0.50
        status_flag = "ENTANGLED" if is_entangled else "SEPARABLE"

        arm_synthesis[arm] = {
            "mean_fidelity": round(mean_f, 6),
            "sem_fidelity": round(sem_f, 6),
            "mean_xx": round(mean_xx, 6),
            "mean_yy": round(mean_yy, 6),
            "mean_zz": round(mean_zz, 6),
            "is_entangled": is_entangled,
            "entanglement_witness": round(0.5 - mean_f, 6),
            "block_fidelities": [round(f, 6) for f in fids]
        }
        print(f"{arm:<42} | {mean_xx:+6.4f} | {mean_yy:+6.4f} | {mean_zz:+6.4f} | {mean_f*100:6.2f} +/- {sem_f*100:4.2f}% | {status_flag}")

    # Key Comparative Endpoints
    f_b = arm_synthesis["Arm B (Restricted Recovery - Matched)"]["mean_fidelity"]
    f_ctrl = arm_synthesis["Arm B Control (Separable Trapped)"]["mean_fidelity"]
    f_heldout = arm_synthesis["Arm B Held-Out (Scrambler Specificity Gate)"]["mean_fidelity"]
    f_a = arm_synthesis["Arm A (Full-Access Inverse)"]["mean_fidelity"]

    delta_ctrl = (f_b - f_ctrl) * 100
    delta_heldout = (f_b - f_heldout) * 100

    print("-" * 95)
    print(f"Primary Endpoint (Arm B Fidelity): {f_b*100:.2f}% (Threshold > 50.0% -> {'PASSED' if f_b > 0.50 else 'FAILED'})")
    print(f"Secondary Endpoint (Gain over Trapped Control): Delta F = {delta_ctrl:+.2f} pp (Threshold >= +50.0 pp -> {'PASSED' if delta_ctrl >= 50.0 else 'FAILED'})")
    print(f"Specificity Gate (Held-Out Scrambler Collapse): F = {f_heldout*100:.2f}% (Threshold <= 50.0% -> {'PASSED' if f_heldout <= 0.50 else 'FAILED'})")
    print(f"Reversibility Ceiling (Arm A Control): F = {f_a*100:.2f}%")

    analysis = {
        "benchmark_id": "OSIRIS-HP-002",
        "backend": backend_name,
        "job_id": job_id,
        "execution_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_circuits": len(result),
        "total_physical_shots": len(result) * receipt["shots_per_circuit"],
        "qpu_usage": usage,
        "arm_synthesis": arm_synthesis,
        "endpoints_evaluation": {
            "primary_restricted_recovery": {
                "claim": "F_ent(Arm B) > 0.50",
                "observed": round(f_b, 6),
                "passed": bool(f_b > 0.50)
            },
            "secondary_gain_over_control": {
                "claim": "Delta F(Arm B - Control) >= +50.0 pp",
                "observed_delta_pp": round(delta_ctrl, 2),
                "passed": bool(delta_ctrl >= 50.0)
            },
            "specificity_gate_heldout": {
                "claim": "F_ent(Arm B Held-Out) <= 0.50",
                "observed": round(f_heldout, 6),
                "passed": bool(f_heldout <= 0.50)
            },
            "reversibility_positive_control": {
                "claim": "F_ent(Arm A) >= 0.85",
                "observed": round(f_a, 6),
                "passed": bool(f_a >= 0.85)
            }
        },
        "block_level_data": block_data,
        "circuit_records": circuit_records
    }

    out_file = EXPERIMENT_DIR / "physical_hp002_results.json"
    out_file.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"\nFinal OSIRIS-HP-002 Synthesis written to: {out_file.name}")

    receipt["status"] = "COMPLETED"
    receipt["qpu_usage"] = usage
    receipt["results_file"] = out_file.name
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Receipt updated to COMPLETED.")


if __name__ == "__main__":
    main()
