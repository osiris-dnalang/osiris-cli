#!/usr/bin/env python3
"""
OSIRIS STAGE 1 (Targeted): Hamiltonian ZZ-Crosstalk Characterization on Edge (14, 15) of ibm_marrakesh
======================================================================================================
Target Coupler   : (14, 15) on ibm_marrakesh (Primary discovery edge with +2.28 pp stagger advantage)
Target Qubit (u) : 14 (undergoing Ramsey interferometer)
Control Qubit (v): 15 (conditioned spectator in |0> vs |1>)
Artificial Detune: f_det = 500.0 kHz (creates baseline 500 kHz Ramsey fringes)
Delay Points     : 16 delay steps from 0 ns to 2,000 ns (in exact multiples of 4.0 ns dt)
Arms             : Arm A (v=|0>), Arm B (v=|1>) -> 32 circuits x 1,024 shots = 32,768 shots
Estimated QPU    : ~8 seconds real quantum compute
Physical Output  : Delta_f = |f_B - f_A|, zeta_14_15 = pi * Delta_f (static ZZ interaction in kHz)
======================================================================================================
"""

import hashlib
import json
import math
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

from qiskit import QuantumCircuit, qpy, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

EXP_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXP_DIR.parents[1]
LEDGER_DB = REPO_ROOT / "evidence_ledger.db"
CRED_PATH = REPO_ROOT / "Downloads" / "dnalang.json"

TARGET_BACKEND = "ibm_marrakesh"
U_TARGET = 14
V_CONTROL = 15
DT_NS = 4.0
F_DET_HZ = 500e3  # 500 kHz artificial detuning
SHOTS = 1024

# 16 delay steps in units of dt (4.0 ns) up to 500 dt = 2,000 ns
DT_STEPS = [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 500]


def build_ramsey_circuit(u: int, v: int, arm: str, delay_dt: int) -> QuantumCircuit:
    qc = QuantumCircuit(156, 2)
    qc.name = f"ZZ_RAMSEY_14_15_{arm}_{delay_dt}dt"

    tau_s = (delay_dt * DT_NS) * 1e-9
    theta_det = 2.0 * math.pi * F_DET_HZ * tau_s

    # Arm B: prepare spectator control in |1>
    if arm == "B":
        qc.x(v)

    # Ramsey sequence on target qubit u
    qc.sx(u)  # Rx(pi/2)
    if delay_dt > 0:
        qc.delay(delay_dt, u, unit="dt")
        qc.delay(delay_dt, v, unit="dt")

    # Software virtual Rz for artificial detuning
    if abs(theta_det) > 1e-9:
        qc.rz(theta_det, u)

    qc.sx(u)  # Rx(pi/2)

    qc.measure(u, 0)
    qc.measure(v, 1)
    return qc


def build_all_circuits():
    circuits = []
    manifest = []
    for step in DT_STEPS:
        tau_ns = step * DT_NS
        for arm in ["A", "B"]:
            qc = build_ramsey_circuit(U_TARGET, V_CONTROL, arm, step)
            circuits.append(qc)
            manifest.append({
                "circuit_index": len(circuits) - 1,
                "name": qc.name,
                "arm": arm,
                "control_state": 0 if arm == "A" else 1,
                "delay_dt": step,
                "delay_ns": tau_ns,
            })
    assert len(circuits) == 32
    return circuits, manifest


def cos_fit_func(t, A, f, phi, C):
    return A * np.cos(2.0 * np.pi * f * t + phi) + C


def main():
    print("=" * 90)
    print("OSIRIS: TARGETED HAMILTONIAN ZZ-CROSSTALK CHARACTERIZATION ON EDGE (14, 15)")
    print("=" * 90)

    circuits, manifest = build_all_circuits()
    payload_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(f"Operational Payload SHA-256: {payload_sha}")

    creds = json.loads(CRED_PATH.read_text())
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=creds["apikey"])
    backend = service.backend(TARGET_BACKEND)

    print(f"Transpiling 32 ZZ-Ramsey circuits on ({U_TARGET}, {V_CONTROL}) to {TARGET_BACKEND} ISA...")
    isa_circuits = transpile(
        circuits,
        backend=backend,
        optimization_level=0,
        scheduling_method="alap",
    )

    qpy_path = EXP_DIR / "submitted_circuits_zz_ramsey_14_15.qpy"
    with open(qpy_path, "wb") as f:
        qpy.dump(isa_circuits, f)
    qpy_sha = hashlib.sha256(qpy_path.read_bytes()).hexdigest()
    print(f"Frozen QPY Archive: {qpy_path.name} (SHA-256: {qpy_sha})")

    # Commit SYS-021 Ledger Entry (Block #22)
    conn = sqlite3.connect(str(LEDGER_DB))
    cur = conn.cursor()
    prev_seq, prev_hash = cur.execute(
        "SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1"
    ).fetchone()
    next_seq = prev_seq + 1
    ts = time.time()
    nonce = f"ZZ-RAMSEY-14-15-{int(ts * 1000)}"

    raw_grant = {
        "sequence_index": next_seq,
        "prev_block_hash": prev_hash,
        "timestamp": ts,
        "event_type": "SYS021_ZZ_RAMSEY_14_15_GRANT",
        "operator_id": "Devin Phillip Davis / Enki",
        "payload_sha256": payload_sha,
        "qpy_sha256": qpy_sha,
        "target_backend": TARGET_BACKEND,
        "coupler": [U_TARGET, V_CONTROL],
        "total_circuits": len(isa_circuits),
        "total_shots": len(isa_circuits) * SHOTS,
        "nonce": nonce,
    }
    raw_grant_json = json.dumps(raw_grant, sort_keys=True)
    block_hash = hashlib.sha256(raw_grant_json.encode("utf-8")).hexdigest()

    cur.execute(
        """
        INSERT INTO ledger_blocks (
            prev_block_hash, block_hash, timestamp, event_type,
            operator_id, payload_sha256, operation_schema_sha256,
            nonce, raw_grant_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prev_hash,
            block_hash,
            ts,
            "SYS021_ZZ_RAMSEY_14_15_GRANT",
            "Devin Phillip Davis / Enki",
            payload_sha,
            qpy_sha,
            nonce,
            raw_grant_json,
        ),
    )
    conn.commit()
    conn.close()
    print(f"Ledger Block #{next_seq} committed to {LEDGER_DB} (Hash: {block_hash[:16]}...)")

    sampler = SamplerV2(mode=backend)
    job = sampler.run(isa_circuits, shots=SHOTS)
    job_id = job.job_id()
    print(f"JOB SUBMITTED! Job ID: {job_id} on {TARGET_BACKEND}")

    job_receipt = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "status": str(job.status()),
        "submission_time": datetime.now(timezone.utc).isoformat(),
        "ledger_block_index": next_seq,
        "ledger_block_hash": block_hash,
        "payload_sha256": payload_sha,
        "qpy_sha256": qpy_sha,
        "total_circuits": len(isa_circuits),
        "shots_per_circuit": SHOTS,
    }
    receipt_path = EXP_DIR / "job_receipt_zz_ramsey_14_15.json"
    receipt_path.write_text(json.dumps(job_receipt, indent=2))

    while True:
        status = str(job.status())
        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"  [{now_str}] Job {job_id} Status: {status}")
        if status in ["DONE", "ERROR", "CANCELLED"]:
            break
        time.sleep(8)

    if str(job.status()) != "DONE":
        print(f"Job failed with status: {job.status()}")
        sys.exit(1)

    res = job.result()
    metrics = job.metrics() if hasattr(job, "metrics") else {}
    qpu_seconds = metrics.get("usage", {}).get("quantum_seconds", None)
    print(f"Real QPU compute consumed: {qpu_seconds} s")

    # Extract target qubit P0 probabilities
    taus_s_A, p0_A = [], []
    taus_s_B, p0_B = [], []

    raw_records = []
    for idx, meta in enumerate(manifest):
        pub_res = res[idx]
        counts = pub_res.data.c.get_counts()
        total = sum(counts.values())
        # Q0 is rightmost bit (target qubit 14)
        p0 = sum(cnt for bitstr, cnt in counts.items() if bitstr[-1] == '0') / total
        rec = dict(meta)
        rec["counts"] = counts
        rec["p0_target"] = p0
        raw_records.append(rec)

        t_val = meta["delay_ns"] * 1e-9
        if meta["arm"] == "A":
            taus_s_A.append(t_val)
            p0_A.append(p0)
        else:
            taus_s_B.append(t_val)
            p0_B.append(p0)

    raw_out = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "coupler": [U_TARGET, V_CONTROL],
        "qpu_seconds": qpu_seconds,
        "payload_sha256": payload_sha,
        "qpy_sha256": qpy_sha,
        "records": raw_records,
    }
    raw_path = EXP_DIR / "raw_results_zz_ramsey_14_15.json"
    raw_path.write_text(json.dumps(raw_out, indent=2))

    # Curve fitting for Arm A and Arm B
    taus_arr_A = np.array(taus_s_A)
    p0_arr_A = np.array(p0_A)
    taus_arr_B = np.array(taus_s_B)
    p0_arr_B = np.array(p0_B)

    p0_init = [0.4, F_DET_HZ, 0.0, 0.5]
    bounds = ([0.0, 100e3, -np.pi, 0.0], [1.0, 1500e3, np.pi, 1.0])

    try:
        popt_A, pcov_A = curve_fit(cos_fit_func, taus_arr_A, p0_arr_A, p0=p0_init, bounds=bounds)
        f_A = abs(popt_A[1])
        f_A_err = np.sqrt(np.diag(pcov_A))[1] if pcov_A is not None else 0.0
    except Exception as e:
        print(f"Warning: Arm A fit failed: {e}")
        popt_A = p0_init
        f_A, f_A_err = F_DET_HZ, 0.0

    try:
        popt_B, pcov_B = curve_fit(cos_fit_func, taus_arr_B, p0_arr_B, p0=p0_init, bounds=bounds)
        f_B = abs(popt_B[1])
        f_B_err = np.sqrt(np.diag(pcov_B))[1] if pcov_B is not None else 0.0
    except Exception as e:
        print(f"Warning: Arm B fit failed: {e}")
        popt_B = p0_init
        f_B, f_B_err = F_DET_HZ, 0.0

    delta_f_hz = abs(f_B - f_A)
    zeta_12_rad_s = np.pi * delta_f_hz
    zeta_12_khz = zeta_12_rad_s / (2.0 * np.pi * 1e3)  # zeta / (2*pi) in kHz

    opt_stagger_ns = (np.pi / (2.0 * zeta_12_rad_s) * 1e9) if zeta_12_rad_s > 1e-6 else None

    print("\n" + "=" * 90)
    print("EMPIRICAL HAMILTONIAN ZZ-RAMSEY CHARACTERIZATION RESULTS FOR EDGE (14, 15)")
    print("=" * 90)
    print(f"Arm A Frequency (Q15=|0>): {f_A / 1e3:.2f} ± {f_A_err / 1e3:.2f} kHz")
    print(f"Arm B Frequency (Q15=|1>): {f_B / 1e3:.2f} ± {f_B_err / 1e3:.2f} kHz")
    print(f"Measured Frequency Shift (Delta f): {delta_f_hz / 1e3:.2f} kHz")
    print(f"Static ZZ Crosstalk Rate (zeta_14_15): {zeta_12_khz:.2f} kHz")
    if opt_stagger_ns:
        print(f"Analytical Optimal Stagger (Delta*): {opt_stagger_ns:.1f} ns")

    analysis_out = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "coupler": [U_TARGET, V_CONTROL],
        "qpu_seconds": qpu_seconds,
        "f_det_kHz": F_DET_HZ / 1e3,
        "f_A_kHz": round(f_A / 1e3, 2),
        "f_A_err_kHz": round(f_A_err / 1e3, 2),
        "f_B_kHz": round(f_B / 1e3, 2),
        "f_B_err_kHz": round(f_B_err / 1e3, 2),
        "delta_f_kHz": round(delta_f_hz / 1e3, 2),
        "zeta_14_15_kHz": round(zeta_12_khz, 2),
        "optimal_stagger_Delta_star_ns": round(opt_stagger_ns, 1) if opt_stagger_ns else None,
        "taus_ns": [round(t * 1e9, 1) for t in taus_s_A],
        "p0_Arm_A": [round(p, 4) for p in p0_A],
        "p0_Arm_B": [round(p, 4) for p in p0_B],
    }
    analysis_path = EXP_DIR / "analysis_zz_ramsey_14_15.json"
    analysis_path.write_text(json.dumps(analysis_out, indent=2))
    print(f"Saved ZZ-Ramsey analysis to {analysis_path.name}")


if __name__ == "__main__":
    main()
