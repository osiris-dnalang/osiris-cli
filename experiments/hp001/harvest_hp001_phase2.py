#!/usr/bin/env python3
"""
harvest_hp001_phase2.py — Telemetry Harvester for OSIRIS-HP-001 Phase 2 Reconstructed Recovery
Monitors Job dbn8m444148s7390gnmg on ibm_fez, extracts counts, and computes reconstructed Bell state fidelities.
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
    print("OSIRIS-HP-001 PHASE 2: PHYSICAL HARDWARE TELEMETRY HARVESTER")
    print("=" * 80)

    receipt_file = EXPERIMENT_DIR / "job_receipt_hp001_phase2_fez.json"
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

    print(f"\n[SUCCESS] Hardware job {job_id} is DONE! Extracting tomographic telemetry...")
    result = job.result()
    metrics = job.metrics() if hasattr(job, "metrics") else {}
    usage = metrics.get("usage", {})
    print(f"  Real QPU Compute Consumed: {usage}")

    # Circuit definitions in order:
    # 0, 1, 2: Arm A (XX, YY, ZZ)
    # 3, 4, 5: Arm B (XX, YY, ZZ)
    # 6, 7, 8: Arm B Control (XX, YY, ZZ)
    arm_specs = [
        ("Arm A (Full-Access Inverse)", ["XX", "YY", "ZZ"], 0),
        ("Arm B (Restricted Recovery - Early Ent)", ["XX", "YY", "ZZ"], 3),
        ("Arm B Control (Separable Trapped)", ["XX", "YY", "ZZ"], 6)
    ]

    analysis = {
        "job_id": job_id,
        "backend": backend_name,
        "execution_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_circuits": len(result),
        "total_physical_shots": len(result) * receipt["shots_per_circuit"],
        "qpu_usage": usage,
        "arms": {}
    }

    print("\n" + "=" * 80)
    print("EMPIRICAL TOMOGRAPHIC RECONSTRUCTION RESULTS")
    print("=" * 80)
    print(f"{'Experimental Arm':<38} | {'<XX>':<8} | {'<YY>':<8} | {'<ZZ>':<8} | {'F_ent':<16} | {'Status'}")
    print("-" * 95)

    for arm_name, bases, offset in arm_specs:
        exp_vals = {}
        var_vals = {}
        for b_idx, basis in enumerate(bases):
            cct_idx = offset + b_idx
            pub_res = result[cct_idx]
            data_bin = pub_res.data
            clbit_name = list(data_bin.keys())[0]
            bitarray = getattr(data_bin, clbit_name)
            counts = bitarray.get_counts()
            shots = sum(counts.values())

            # Measurement ordering: classical bit 0 is R, classical bit 1 is Decoded
            # Qiskit bitstring convention: 'b1 b0' (index 0 is b1, index 1 is b0)
            exp_val = 0.0
            for bitstring, count in counts.items():
                cb = bitstring.replace(" ", "")
                # Parity: bit0 == bit1 -> +1, else -1
                parity = 1.0 if cb[0] == cb[1] else -1.0
                exp_val += parity * count
            exp_val /= shots
            exp_vals[basis] = exp_val
            var_vals[basis] = (1.0 - exp_val**2) / shots

        # Bell fidelity: F = (1 + <XX> - <YY> + <ZZ>) / 4
        # Standard error: sigma_F = sqrt(var(XX) + var(YY) + var(ZZ)) / 4
        f_ent = (1.0 + exp_vals["XX"] - exp_vals["YY"] + exp_vals["ZZ"]) / 4.0
        sigma_f = math.sqrt(sum(var_vals.values())) / 4.0
        is_entangled = f_ent > 0.50

        status_flag = "ENTANGLED" if is_entangled else "SEPARABLE"

        print(f"{arm_name:<38} | {exp_vals['XX']:+7.4f}  | {exp_vals['YY']:+7.4f}  | {exp_vals['ZZ']:+7.4f}  | {f_ent*100:6.2f} +/- {sigma_f*100:4.2f}% | {status_flag}")

        analysis["arms"][arm_name] = {
            "exp_xx": round(exp_vals["XX"], 6),
            "exp_yy": round(exp_vals["YY"], 6),
            "exp_zz": round(exp_vals["ZZ"], 6),
            "fidelity": round(f_ent, 6),
            "sigma_fidelity": round(sigma_f, 6),
            "is_entangled": is_entangled,
            "entanglement_witness": round(0.5 - f_ent, 6)
        }

    f_b = analysis["arms"]["Arm B (Restricted Recovery - Early Ent)"]["fidelity"]
    f_ctrl = analysis["arms"]["Arm B Control (Separable Trapped)"]["fidelity"]
    delta_f = f_b - f_ctrl
    analysis["delta_recovery_gain"] = round(delta_f, 6)

    print("-" * 95)
    print(f"Restricted Hayden-Preskill Entanglement Gain (Arm B - Control): Delta F = {delta_f*100:+.2f} pp")
    print(f"Entanglement Witness Check (Arm B): {analysis['arms']['Arm B (Restricted Recovery - Early Ent)']['entanglement_witness']:+.4f} (< 0 implies genuine entanglement)")

    # Save final results
    out_file = EXPERIMENT_DIR / "physical_hp001_phase2_results.json"
    out_file.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"\nFinal Tomographic Results saved to: {out_file.name}")

    receipt["status"] = "COMPLETED"
    receipt["qpu_usage"] = usage
    receipt["results_file"] = out_file.name
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Receipt updated to COMPLETED.")


if __name__ == "__main__":
    main()
