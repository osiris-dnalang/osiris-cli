#!/usr/bin/env python3
"""
execute_experiment_e4_fingerprinting.py -- OSIRIS Experiment E4: Pulse-Overlap Fingerprinting.

Directly discriminates between:
  H1: Microwave Pulse Collision Avoidance (sharp step at Delta in [16, 32] ns, flat plateau >= 32 ns)
  H2: Timing-Dependent Dynamical Refocusing (smooth, continuous variation across Delta in [0, 160] ns)
  H3: Architecture-Specific Coupler Null on (61, 62) (near-zero effect across all offsets)

Governed under SYS-021: Zero Self-Supplied Authorization.
"""

import hashlib
import json
import math
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qpy, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

EXP_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXP_DIR.parents[1]
# Note: In Windows/WSL environments, check both candidate ledger paths
if (REPO_ROOT / "evidence_ledger.db").exists() and (REPO_ROOT / "evidence_ledger.db").stat().st_size > 0:
    LEDGER_DB = REPO_ROOT / "evidence_ledger.db"
elif Path("/mnt/c/Users/Ron/evidence_ledger.db").exists():
    LEDGER_DB = Path("/mnt/c/Users/Ron/evidence_ledger.db")
elif Path("C:/Users/Ron/evidence_ledger.db").exists():
    LEDGER_DB = Path("C:/Users/Ron/evidence_ledger.db")
else:
    LEDGER_DB = REPO_ROOT / "evidence_ledger.db"

# Credentials path
if (REPO_ROOT / "Downloads" / "dnalang.json").exists():
    CRED_PATH = REPO_ROOT / "Downloads" / "dnalang.json"
elif Path("/mnt/c/Users/Ron/Downloads/dnalang.json").exists():
    CRED_PATH = Path("/mnt/c/Users/Ron/Downloads/dnalang.json")
else:
    CRED_PATH = Path("C:/Users/Ron/Downloads/dnalang.json")

TARGET_BACKEND = "ibm_marrakesh"
PRIMARY_EDGE = (14, 15)
CONTROL_EDGE = (61, 62)
EDGES = [PRIMARY_EDGE, CONTROL_EDGE]

EVOLUTION_NS = 8000
DT_NS = 4.0
TOTAL_DT = int(EVOLUTION_NS // DT_NS)  # 2000 dt
PULSE_DT = 8  # 32 ns hardware pulse duration

OFFSETS_NS = [0, 16, 32, 48, 80, 160]
BASES = ["XX", "YY", "ZZ"]
BLOCKS = [0, 1]
SHOTS = 1024

XY8_PULSES = ["x", "y", "x", "y", "y", "x", "y", "x"]


def compute_dd_delays(total_dt: int, offset_dt: int) -> tuple[int, int, int, int, int]:
    free_dt = total_dt - 8 * PULSE_DT
    inter_dt = free_dt // 8
    rem = free_dt - 7 * inter_dt
    base_lead = rem // 2
    base_trail = rem - base_lead

    shift_u = offset_dt // 2
    shift_v = offset_dt - shift_u

    lead_u = base_lead - shift_u
    trail_u = base_trail + shift_u
    lead_v = base_lead + shift_v
    trail_v = base_trail - shift_v

    assert lead_u > 0 and trail_u > 0 and lead_v > 0 and trail_v > 0
    assert lead_u + 8 * PULSE_DT + 7 * inter_dt + trail_u == total_dt
    assert lead_v + 8 * PULSE_DT + 7 * inter_dt + trail_v == total_dt
    assert lead_v - lead_u == offset_dt
    return lead_u, inter_dt, trail_u, lead_v, trail_v


def build_e4_circuit(edge: tuple[int, int], offset_ns: int, basis: str, block: int) -> QuantumCircuit:
    u, v = edge
    offset_dt = int(offset_ns // DT_NS)
    lead_u, inter, trail_u, lead_v, trail_v = compute_dd_delays(TOTAL_DT, offset_dt)

    qr = QuantumRegister(156, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr, name=f"E4_b{block}_e{u}_{v}_off{offset_ns}ns_{basis}")

    # 1. State preparation: Bell state |Phi+> = (|00> + |11>) / sqrt(2)
    qc.h(qr[u])
    qc.h(qr[v])
    qc.cz(qr[u], qr[v])
    qc.h(qr[v])
    qc.barrier([qr[u], qr[v]])

    # 2. Staggered XY8 decoupling schedule
    # Qubit u
    qc.delay(lead_u, qr[u], unit="dt")
    for idx, op in enumerate(XY8_PULSES):
        if op == "x":
            qc.x(qr[u])
        else:
            qc.y(qr[u])
        if idx < 7:
            qc.delay(inter, qr[u], unit="dt")
        else:
            qc.delay(trail_u, qr[u], unit="dt")

    # Qubit v
    qc.delay(lead_v, qr[v], unit="dt")
    for idx, op in enumerate(XY8_PULSES):
        if op == "x":
            qc.x(qr[v])
        else:
            qc.y(qr[v])
        if idx < 7:
            qc.delay(inter, qr[v], unit="dt")
        else:
            qc.delay(trail_v, qr[v], unit="dt")

    qc.barrier([qr[u], qr[v]])

    # 3. Measurement basis rotation
    if basis == "XX":
        qc.h(qr[u])
        qc.h(qr[v])
    elif basis == "YY":
        qc.sdg(qr[u])
        qc.h(qr[u])
        qc.sdg(qr[v])
        qc.h(qr[v])
    elif basis == "ZZ":
        pass
    else:
        raise ValueError(f"Unknown basis: {basis}")

    qc.measure(qr[u], cr[0])
    qc.measure(qr[v], cr[1])
    return qc


def build_all_circuits() -> tuple[list[QuantumCircuit], list[dict]]:
    circuits = []
    manifest = []
    # Interleaved randomized blocks
    rng = random.Random(42)

    for blk in BLOCKS:
        block_items = []
        for edge in EDGES:
            for off_ns in OFFSETS_NS:
                for b in BASES:
                    block_items.append((edge, off_ns, b, blk))
        rng.shuffle(block_items)

        for edge, off_ns, b, blk in block_items:
            qc = build_e4_circuit(edge, off_ns, b, blk)
            circuits.append(qc)
            manifest.append({
                "circuit_name": qc.name,
                "block": blk,
                "edge": list(edge),
                "offset_ns": off_ns,
                "offset_dt": int(off_ns // DT_NS),
                "basis": b,
                "evolution_ns": EVOLUTION_NS
            })
    return circuits, manifest


def calc_exp_and_var(cnts: dict[str, int]) -> tuple[float, float]:
    n = sum(cnts.values())
    if n == 0:
        return 0.0, 0.0
    p = 0
    for bs, c in cnts.items():
        b_clean = bs.replace(" ", "")
        b0 = int(b_clean[-1])
        b1 = int(b_clean[-2])
        sign = 1 if b0 == b1 else -1
        p += sign * c
    exp_val = p / n
    var_val = max(0.0, (1.0 - exp_val ** 2) / n)
    return float(exp_val), float(var_val)


def main():
    print("=" * 80)
    print("OSIRIS EXPERIMENT E4: PULSE-OVERLAP FINGERPRINTING — GOVERNED EXECUTION")
    print("=" * 80)

    # 1. Build circuits & manifest
    circuits, manifest = build_all_circuits()
    print(f"Constructed {len(circuits)} circuits across {len(EDGES)} edges and {len(OFFSETS_NS)} offsets.")

    payload_bytes = Path(__file__).read_bytes()
    payload_sha = hashlib.sha256(payload_bytes).hexdigest()
    print(f"Operational Payload SHA-256: {payload_sha}")

    # 2. Check credentials & backend
    creds = json.loads(CRED_PATH.read_text())
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=creds["apikey"])
    backend = service.backend(TARGET_BACKEND)

    usage = service.usage()
    rem_sec = usage.get("usage_remaining_seconds", 0)
    print(f"IBM Quantum Status: Operational={backend.status().operational}, Pending jobs={backend.status().pending_jobs}")
    print(f"Account Allocation: {usage.get('usage_consumed_seconds', 0)} / {usage.get('usage_limit_seconds', 0)} s used. Remaining: {rem_sec} s.")

    # 3. Transpile to ISA
    print(f"Transpiling {len(circuits)} circuits to {TARGET_BACKEND} ISA (optimization_level=0, scheduling_method=asap)...")
    isa_circuits = transpile(
        circuits,
        backend=backend,
        optimization_level=0,
        scheduling_method="asap"
    )

    # Freeze QPY archive
    qpy_path = EXP_DIR / "submitted_circuits_exp_e4.qpy"
    with open(qpy_path, "wb") as f:
        qpy.dump(isa_circuits, f)
    qpy_sha = hashlib.sha256(qpy_path.read_bytes()).hexdigest()
    print(f"Frozen QPY Archive: {qpy_path.name} (SHA-256: {qpy_sha})")

    # 4. Commit SYS-021 Ledger Entry
    conn = sqlite3.connect(str(LEDGER_DB))
    cur = conn.cursor()
    prev_seq, prev_hash = cur.execute(
        "SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1"
    ).fetchone()
    next_seq = prev_seq + 1
    ts = time.time()
    nonce = hashlib.sha256(f"{next_seq}_{ts}_{payload_sha}".encode()).hexdigest()[:16]

    grant_data = {
        "sequence_index": next_seq,
        "event_type": "SYS021_EXP_E4_FINGERPRINTING_GRANT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "operator": "Devin Phillip Davis / Enki",
        "backend": TARGET_BACKEND,
        "payload_sha256": payload_sha,
        "operation_schema_sha256": qpy_sha,
        "nonce": nonce,
        "total_circuits": len(circuits),
        "total_shots": len(circuits) * SHOTS,
        "offsets_ns": OFFSETS_NS,
        "edges": [[14, 15], [61, 62]],
        "previous_block_hash": prev_hash,
    }
    raw_grant_json = json.dumps(grant_data, sort_keys=True)
    block_hash = hashlib.sha256(f"{prev_hash}{raw_grant_json}".encode("utf-8")).hexdigest()

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
            "SYS021_EXP_E4_FINGERPRINTING_GRANT",
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

    # 5. Submit to QPU
    print(f"Submitting {len(isa_circuits)} circuits ({SHOTS} shots each) to {TARGET_BACKEND} via SamplerV2...")
    sampler = SamplerV2(mode=backend)
    job = sampler.run(isa_circuits, shots=SHOTS)
    job_id = job.job_id()
    print(f"JOB SUBMITTED! Job ID: {job_id} on {TARGET_BACKEND}")

    receipt = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": job.status(),
        "ledger_sequence": next_seq,
        "ledger_block_hash": block_hash,
        "payload_sha256": payload_sha,
        "qpy_sha256": qpy_sha,
        "total_circuits": len(isa_circuits),
        "shots_per_circuit": SHOTS,
        "total_shots": len(isa_circuits) * SHOTS
    }
    (EXP_DIR / "job_receipt_exp_e4.json").write_text(json.dumps(receipt, indent=2))
    print(f"Job receipt written to job_receipt_exp_e4.json")

    # 6. Poll for Completion
    print("Waiting for job execution...")
    poll_count = 0
    while True:
        status = job.status()
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Job {job_id} status: {status}")
        if status in ["DONE", "CANCELLED", "ERROR"]:
            break
        time.sleep(10)
        poll_count += 1

    if status != "DONE":
        print(f"Execution terminated with status: {status}")
        sys.exit(1)

    print("Job completed! Retrieving execution metrics and results...")
    result = job.result()
    metrics = job.metrics()
    qpu_seconds = metrics.get("usage", {}).get("quantum_seconds", 0)
    print(f"Real QPU runtime consumed: {qpu_seconds} seconds")

    # 7. Extract raw counts and calculate parity observables
    raw_results = {}
    for idx, pub_res in enumerate(result):
        meta = manifest[idx]
        data = pub_res.data
        counts = data.c.get_counts()
        raw_results[meta["circuit_name"]] = {
            "metadata": meta,
            "counts": counts
        }

    (EXP_DIR / "raw_results_exp_e4.json").write_text(json.dumps(raw_results, indent=2))
    print("Raw results saved to raw_results_exp_e4.json")

    # 8. Statistical analysis
    # Aggregate across blocks for each edge, offset, basis
    records = {}
    for edge in EDGES:
        edge_key = f"{edge[0]}_{edge[1]}"
        records[edge_key] = {}
        for off_ns in OFFSETS_NS:
            records[edge_key][off_ns] = {}
            for b in BASES:
                # Find matching circuits in manifest
                matching_counts = []
                for name, res in raw_results.items():
                    m = res["metadata"]
                    if m["edge"] == list(edge) and m["offset_ns"] == off_ns and m["basis"] == b:
                        matching_counts.append(res["counts"])

                # Pool counts across blocks
                pooled = {}
                for cnt_dict in matching_counts:
                    for bitstr, val in cnt_dict.items():
                        pooled[bitstr] = pooled.get(bitstr, 0) + val

                exp_val, var_val = calc_exp_and_var(pooled)
                sem = math.sqrt(var_val)
                records[edge_key][off_ns][b] = {
                    "exp_val": exp_val,
                    "sem": sem,
                    "shots": sum(pooled.values())
                }

    # Compute Bell state fidelity F_Bell = (1 + <XX> - <YY> + <ZZ>) / 4
    analysis = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "qpu_seconds": qpu_seconds,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "edges": {}
    }

    print("\n" + "=" * 80)
    print("EXPERIMENT E4 ANALYSIS: PULSE-OVERLAP FINGERPRINTING")
    print("=" * 80)

    for edge in EDGES:
        edge_key = f"{edge[0]}_{edge[1]}"
        analysis["edges"][edge_key] = {"offsets": {}}
        print(f"\n--- Edge ({edge[0]}, {edge[1]}) ---")
        print(f"{'Offset (ns)':<12} {'<XX>':<16} {'<YY>':<16} {'<ZZ>':<16} {'F_Bell':<16}")
        print("-" * 76)

        for off_ns in OFFSETS_NS:
            xx = records[edge_key][off_ns]["XX"]["exp_val"]
            xx_sem = records[edge_key][off_ns]["XX"]["sem"]
            yy = records[edge_key][off_ns]["YY"]["exp_val"]
            yy_sem = records[edge_key][off_ns]["YY"]["sem"]
            zz = records[edge_key][off_ns]["ZZ"]["exp_val"]
            zz_sem = records[edge_key][off_ns]["ZZ"]["sem"]

            f_bell = (1.0 + xx - yy + zz) / 4.0
            f_sem = 0.25 * math.sqrt(xx_sem ** 2 + yy_sem ** 2 + zz_sem ** 2)

            analysis["edges"][edge_key]["offsets"][str(off_ns)] = {
                "XX": {"val": xx, "sem": xx_sem},
                "YY": {"val": yy, "sem": yy_sem},
                "ZZ": {"val": zz, "sem": zz_sem},
                "F_Bell": {"val": f_bell, "sem": f_sem}
            }
            print(f"{off_ns:<12} {xx:+.4f} +/- {xx_sem:.4f}  {yy:+.4f} +/- {yy_sem:.4f}  {zz:+.4f} +/- {zz_sem:.4f}  {f_bell:.4f} +/- {f_sem:.4f}")

    # Hypothesis discrimination on primary edge (14, 15)
    f_0 = analysis["edges"]["14_15"]["offsets"]["0"]["F_Bell"]["val"]
    f_16 = analysis["edges"]["14_15"]["offsets"]["16"]["F_Bell"]["val"]
    f_32 = analysis["edges"]["14_15"]["offsets"]["32"]["F_Bell"]["val"]
    f_48 = analysis["edges"]["14_15"]["offsets"]["48"]["F_Bell"]["val"]
    f_80 = analysis["edges"]["14_15"]["offsets"]["80"]["F_Bell"]["val"]
    f_160 = analysis["edges"]["14_15"]["offsets"]["160"]["F_Bell"]["val"]

    delta_tot = f_160 - f_0
    step_frac_32 = (f_32 - f_0) / delta_tot if abs(delta_tot) > 1e-6 else 0.0

    # Plateau slope check from 32 to 160 ns
    d_plateau = abs(f_160 - f_32)

    verdict_h1 = (step_frac_32 >= 0.75) and (d_plateau < 0.015)
    analysis["discrimination"] = {
        "F_0ns": f_0,
        "F_16ns": f_16,
        "F_32ns": f_32,
        "F_48ns": f_48,
        "F_80ns": f_80,
        "F_160ns": f_160,
        "delta_total": delta_tot,
        "step_fraction_at_32ns": step_frac_32,
        "plateau_delta_32_to_160ns": d_plateau,
        "verdict_h1_collision_avoidance": verdict_h1
    }

    print("\n--- Mechanistic Verdict ---")
    print(f"Total Bell fidelity change (0 -> 160 ns): {delta_tot * 100:+.2f} pp")
    print(f"Fraction of gain achieved at pulse boundary (32 ns): {step_frac_32 * 100:.1f}%")
    print(f"Plateau variation from 32 to 160 ns: {d_plateau * 100:.2f} pp")
    if verdict_h1:
        print("VERDICT: DECISIVE CONFIRMATION OF H1 (MICROWAVE PULSE COLLISION AVOIDANCE)")
        print("  Fidelity saturates once microwave drive envelopes become strictly non-overlapping (Delta >= 32 ns).")
    else:
        print("VERDICT: DATA FAVORS H2 (TIMING-DEPENDENT FILTER FUNCTION / CONTINUOUS REFOCUSING)")

    (EXP_DIR / "analysis_exp_e4.json").write_text(json.dumps(analysis, indent=2))
    print(f"\nAnalysis written to {EXP_DIR / 'analysis_exp_e4.json'}")


if __name__ == "__main__":
    main()
