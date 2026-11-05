#!/usr/bin/env python3
"""
execute_experiment_e3_pilot_216circ.py
OSIRIS Frontier Quantum-Control Program — Experiment E3 Pilot: Prospective 4-Arm Control Compiler v2 Validation
Target: IBM Marrakesh (Heron r2, 156 qubits)

Prospective Pre-Registered Specification:
  - Frozen Pre-Registration Hash (216-circuit planner): 047f277b5bcf1859277eb32f7887fec086aaab192a4c454addb0ee13ba675b8d
  - Frozen Pre-Registration Hash (E3 7-coupler model) : 1890ed5d8185195ff554962a94d6b7f1e70571f784bc7f10fcc0c0c04e301c6f
  - Unseen Held-Out Edges (3): (12,13) [slow 84ns], (24,25) [fast 68ns, high bilateral dephasing], (44,45) [clean fast 68ns]
  - Evolution Durations (2): 4,000 ns (1000 dt) and 8,000 ns (2000 dt) [6 unseen (edge, duration) test cells]
  - Independent Protocol Arms (4):
      1. C_QISKIT_SYNC_XY8           (0 ns offset)
      2. D_QISKIT_OPTIMIZED_STAG_XY8 (tau/2 quantized to 8ns grid: 248 ns at 4us, 496 ns at 8us)
      3. E_FIXED_STAG_XY8_80         (80 ns bilateral stagger — strongest E2 baseline)
      4. F_OSIRIS_CONTROL_COMPILER_V2 (Pre-registered risk-aware offset: 0ns on 12-13@4/8us & 24-25@8us,
                                       40ns on 24-25@4us, 120ns on 44-45@4us, 80ns on 44-45@8us)
  - Measurement Bases (3): XX, YY, ZZ (evaluating certified Bell-state fidelity F_Bell)
  - Randomized Acquisition Blocks: 3 blocks (72 circuits/block = 216 total ISA circuits)
  - Shots: 1,024 per circuit (221,184 total physical shots)

Operator: Devin Phillip Davis / Enki
Invariants: SYS-021 (Zero Self-Supplied Authorization, Payload-Bound Grants)
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import numpy as np
from scipy import stats
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.qpy import dump as qpy_dump
from qiskit.quantum_info import Statevector, Pauli
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

EXP_DIR = Path("/mnt/c/Users/Ron/experiments/experiment_e")
EXP_DIR.mkdir(parents=True, exist_ok=True)

LEDGER_JSONL = EXP_DIR / "ledger.jsonl"
EVIDENCE_DB = Path("/mnt/c/Users/Ron/evidence_ledger.db")
PREREG_216_FILE = EXP_DIR / "preregistered_hardware_benchmark_v2_216circ.json"
EXPECTED_PREREG_216_SHA256 = "047f277b5bcf1859277eb32f7887fec086aaab192a4c454addb0ee13ba675b8d"
PREREG_E3_FILE = EXP_DIR / "preregistered_predictions_exp_e3.json"
EXPECTED_PREREG_E3_SHA256 = "d5868e4b8c8927a9a0f44661722438f3a95b3d26d605099a761d96b624aff103"
EXPECTED_PREREG_E3_CANONICAL_SHA256 = "1890ed5d8185195ff554962a94d6b7f1e70571f784bc7f10fcc0c0c04e301c6f"

KEY_FILE = Path("/mnt/c/Users/Ron/Downloads/dnalang.json")
with open(KEY_FILE) as f:
    key_info = json.load(f)
TOKEN = key_info["apikey"]

OPERATOR_ID = "Devin Phillip Davis / Enki"
OP_SCHEMA = "OSIRIS_QPU_EXP_E3_PILOT_216CIRC_V2"
TARGET_BACKEND = "ibm_marrakesh"

PILOT_EDGES = [(12, 13), (24, 25), (44, 45)]
DURATIONS_NS = [4000, 8000]
BASES = ["XX", "YY", "ZZ"]
DT_NS = 4.0
PULSE_DT = 9
SHOTS = 1024
BLOCKS = 3
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

    assert lead_u > 0 and trail_u > 0 and lead_v > 0 and trail_v > 0, (
        f"Invalid delays for total_dt={total_dt}, offset_dt={offset_dt}: "
        f"lu={lead_u}, tu={trail_u}, lv={lead_v}, tv={trail_v}"
    )
    assert lead_u + 8 * PULSE_DT + 7 * inter_dt + trail_u == total_dt
    assert lead_v + 8 * PULSE_DT + 7 * inter_dt + trail_v == total_dt
    assert lead_v - lead_u == offset_dt
    return lead_u, inter_dt, trail_u, lead_v, trail_v


def verify_preregistration_and_unitary_gate() -> dict:
    print("Verifying Frozen Pre-Registration Locks & Statevector Gate...")
    for pfile, expected in [
        (PREREG_216_FILE, EXPECTED_PREREG_216_SHA256),
        (PREREG_E3_FILE, EXPECTED_PREREG_E3_SHA256),
    ]:
        if not pfile.exists():
            raise RuntimeError(f"Missing pre-registration file: {pfile}")
        actual = hashlib.sha256(pfile.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Pre-registration hash mismatch on {pfile.name}! Expected {expected}, got {actual}")
        print(f"  [PASS] {pfile.name} locked: {actual}")

    # Verify Statevector unitary preservation and delay math across all offsets used in E3 Pilot
    for total_dt, off_ns in [(1000, 0), (1000, 40), (1000, 80), (1000, 120), (1000, 248), (2000, 0), (2000, 80), (2000, 496)]:
        lu, inter, tu, lv, tv = compute_dd_delays(total_dt, int(off_ns // DT_NS))
        assert lu > 0 and lv > 0

    res = {}
    for basis in BASES:
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.h(1)
        qc.cz(0, 1)
        qc.h(1)
        for op in XY8_PULSES:
            getattr(qc, op)(0)
            getattr(qc, op)(1)
        if basis == "XX":
            qc.h(0)
            qc.h(1)
        elif basis == "YY":
            qc.sdg(0)
            qc.h(0)
            qc.sdg(1)
            qc.h(1)
        sv = Statevector.from_instruction(qc)
        res[basis] = float(sv.expectation_value(Pauli("ZZ")).real)
    fid = (1.0 + res["XX"] - res["YY"] + res["ZZ"]) / 4.0
    assert abs(fid - 1.0) < 1e-9
    print("  [PASS] Certified |Phi+> preparation, XY8 unitary preservation, and all offset delay bounds verified.")
    return json.loads(PREREG_216_FILE.read_text())


def build_e3_pilot_circuit(
    edge: tuple[int, int], dur_ns: int, arm_name: str, off_ns: int, basis: str, blk: int
) -> QuantumCircuit:
    u, v = edge
    total_dt = int(dur_ns // DT_NS)
    off_dt = int(off_ns // DT_NS)

    qr = QuantumRegister(156, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr, name=f"expE3_b{blk}_{arm_name}_{dur_ns}ns_{basis}_q{u}_q{v}")

    qc.h(qr[u])
    qc.h(qr[v])
    qc.cz(qr[u], qr[v])
    qc.h(qr[v])
    qc.barrier([qr[u], qr[v]])

    lu, inter, tu, lv, tv = compute_dd_delays(total_dt, off_dt)
    qc.delay(lu, qr[u], unit="dt")
    for idx, op in enumerate(XY8_PULSES):
        getattr(qc, op)(qr[u])
        qc.delay(inter if idx < 7 else tu, qr[u], unit="dt")
    qc.delay(lv, qr[v], unit="dt")
    for idx, op in enumerate(XY8_PULSES):
        getattr(qc, op)(qr[v])
        qc.delay(inter if idx < 7 else tv, qr[v], unit="dt")

    qc.barrier([qr[u], qr[v]])
    if basis == "XX":
        qc.h(qr[u])
        qc.h(qr[v])
    elif basis == "YY":
        qc.sdg(qr[u])
        qc.h(qr[u])
        qc.sdg(qr[v])
        qc.h(qr[v])
    qc.measure(qr[u], cr[0])
    qc.measure(qr[v], cr[1])
    return qc


def calc_exp_and_var(cnts: dict[str, int]) -> tuple[float, float]:
    n = sum(cnts.values())
    if n == 0:
        return 0.0, 0.0
    p = sum((1 if bs.replace(" ", "")[-1] == bs.replace(" ", "")[-2] else -1) * c for bs, c in cnts.items())
    exp_val = p / n
    return float(exp_val), float(max(0.0, (1.0 - exp_val ** 2) / n))


def cluster_stats(diffs_by_cluster: list[float]) -> dict:
    arr = np.array(diffs_by_cluster, dtype=float) * 100.0
    G = len(arr)
    df = G - 1
    mean_pp = float(np.mean(arr))
    se_pp = float(np.std(arr, ddof=1) / math.sqrt(G)) if G > 1 else 0.0
    t_val = mean_pp / se_pp if se_pp > 0 else 0.0
    p_2s = float(2.0 * (1.0 - stats.t.cdf(abs(t_val), df=df))) if df > 0 else 1.0
    p_1s = float(1.0 - stats.t.cdf(t_val, df=df)) if df > 0 else 0.5
    t_crit = float(stats.t.ppf(0.975, df=df)) if df > 0 else 0.0
    return {
        "clusters": G,
        "df": df,
        "mean_diff_pp": round(mean_pp, 4),
        "se_pp": round(se_pp, 4),
        "ci95_pp": [round(mean_pp - t_crit * se_pp, 4), round(mean_pp + t_crit * se_pp, 4)],
        "t_stat": round(t_val, 4),
        "p_2sided": round(p_2s, 6),
        "p_1sided": round(p_1s, 6),
        "cluster_values_pp": [round(float(x), 4) for x in arr],
    }


def main():
    print("=" * 96)
    print("OSIRIS EXPERIMENT E3 PILOT (216 CIRCUITS, 221,184 SHOTS) — GOVERNED EXECUTION ON IBM_MARRAKESH")
    print("=" * 96)

    prereg = verify_preregistration_and_unitary_gate()
    osiris_delta_map = {
        (r["edge"], r["duration_ns"]): int(r["osiris_v2_selected_delta_ns"])
        for r in prereg["preregistered_cell_predictions"]
    }

    self_path = Path(__file__).resolve()
    payload_sha256 = hashlib.sha256(self_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(OP_SCHEMA.encode("utf-8")).hexdigest()
    print(f"Operational Payload SHA-256: {payload_sha256}")

    priv_key_path = Path("/home/enki/.osiris/keystore/node_beta_operator.key")
    if not priv_key_path.exists():
        sys.exit(1)
    priv = Ed25519PrivateKey.from_private_bytes(priv_key_path.read_bytes())
    pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    now = time.time()
    nonce = f"ads-sys021-expE3pilot-{uuid.uuid4().hex}"
    grant_data = {
        "expires_at": now + 86400,
        "nonce": nonce,
        "operation_schema_sha256": schema_sha256,
        "operator_id": OPERATOR_ID,
        "payload_sha256": payload_sha256,
        "prereg_216_sha256": EXPECTED_PREREG_216_SHA256,
        "prereg_e3_sha256": EXPECTED_PREREG_E3_SHA256,
        "public_key": pub_hex,
        "timestamp": now,
    }
    grant_data["signature"] = priv.sign(json.dumps(grant_data, sort_keys=True, separators=(",", ":")).encode()).hex()
    (EXP_DIR / "sys021_grant_e3_pilot.json").write_text(json.dumps(grant_data, indent=2))

    conn = sqlite3.connect(EVIDENCE_DB)
    with conn:
        latest = conn.execute("SELECT block_hash, sequence_index FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1").fetchone()
        prev_hash = latest[0] if latest else "0" * 64
        seq = (latest[1] + 1) if latest else 1
        block_content = {
            "sequence_index": seq,
            "prev_block_hash": prev_hash,
            "timestamp": now,
            "event_type": "SYS021_EXP_E3_PILOT_216CIRC_GRANT",
            "operator_id": OPERATOR_ID,
            "payload_sha256": payload_sha256,
            "operation_schema_sha256": schema_sha256,
            "nonce": nonce,
        }
        b_hash = hashlib.sha256(json.dumps(block_content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        conn.execute("""
            INSERT INTO ledger_blocks (
                prev_block_hash, block_hash, timestamp, event_type,
                operator_id, payload_sha256, operation_schema_sha256,
                nonce, raw_grant_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (prev_hash, b_hash, now, "SYS021_EXP_E3_PILOT_216CIRC_GRANT", OPERATOR_ID, payload_sha256, schema_sha256, nonce, json.dumps(grant_data)))
    print(f"Ledger Block #{seq} committed to {EVIDENCE_DB} (Hash: {b_hash[:16]}...)")

    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=TOKEN)
    backend = service.backend(TARGET_BACKEND)

    rng = np.random.default_rng(2026110503)
    circuits_to_run, metadata_list = [], []
    for blk in range(BLOCKS):
        block_items = []
        for e in PILOT_EDGES:
            ek = f"({e[0]},{e[1]})"
            for dur_ns in DURATIONS_NS:
                qopt_off = 248 if dur_ns == 4000 else 496
                osiris_off = osiris_delta_map[(ek, dur_ns)]
                arms = [
                    ("C_QISKIT_SYNC_XY8", 0),
                    ("D_QISKIT_OPTIMIZED_STAG_XY8", qopt_off),
                    ("E_FIXED_STAG_XY8_80", 80),
                    ("F_OSIRIS_CONTROL_COMPILER_V2", osiris_off),
                ]
                for arm_name, off_ns in arms:
                    for ba in BASES:
                        qc = build_e3_pilot_circuit(e, dur_ns, arm_name, off_ns, ba, blk)
                        block_items.append((qc, {
                            "block": blk,
                            "edge": [e[0], e[1]],
                            "duration_ns": dur_ns,
                            "protocol": arm_name,
                            "offset_ns": off_ns,
                            "basis": ba,
                            "name": qc.name,
                        }))
        rng.shuffle(block_items)
        for qc, meta in block_items:
            circuits_to_run.append(qc)
            metadata_list.append(meta)

    print(f"Transpiling {len(circuits_to_run)} circuits to {TARGET_BACKEND} ISA...")
    isa_circuits = transpile(circuits_to_run, backend=backend, optimization_level=0, scheduling_method="asap")
    qpy_path = EXP_DIR / "submitted_circuits_exp_e3_pilot.qpy"
    with open(qpy_path, "wb") as f:
        qpy_dump(isa_circuits, f)
    qpy_sha256 = hashlib.sha256(qpy_path.read_bytes()).hexdigest()

    sampler = SamplerV2(mode=backend)
    job = sampler.run(isa_circuits, shots=SHOTS)
    job_id = job.job_id()
    print(f"JOB SUBMITTED! Job ID: {job_id}")

    (EXP_DIR / "job_receipts_exp_e3_pilot.json").write_text(json.dumps({
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "circuit_count": len(isa_circuits),
        "shots_per_circuit": SHOTS,
        "blocks": BLOCKS,
        "qpy_sha256": qpy_sha256,
        "prereg_216_sha256": EXPECTED_PREREG_216_SHA256,
        "prereg_e3_sha256": EXPECTED_PREREG_E3_SHA256,
        "payload_sha256": payload_sha256,
        "ledger_sequence": seq,
        "metadata": metadata_list,
    }, indent=2))

    last_status = None
    while True:
        status = str(job.status())
        if status != last_status:
            print(f"  [{time.strftime('%H:%M:%S')}] Job {job_id} Status: {status}")
            last_status = status
        if "DONE" in status.upper() or "CANCEL" in status.upper() or "ERROR" in status.upper():
            break
        time.sleep(10)

    if "DONE" not in last_status.upper():
        print(f"Job {job_id} did not complete with DONE: {last_status}")
        sys.exit(1)

    res = job.result()
    raw_counts = [pub_res.data.c.get_counts() for pub_res in res]
    (EXP_DIR / "raw_results_exp_e3_pilot.json").write_text(json.dumps(raw_counts))
    qpu_seconds = getattr(job, "usage", lambda: None)()
    print(f"Real QPU compute consumed: {qpu_seconds} s")

    # Group by edge -> dur -> protocol -> block -> basis
    grouped = {}
    for meta, cnts in zip(metadata_list, raw_counts):
        ek = f"({meta['edge'][0]},{meta['edge'][1]})"
        dur = f"{meta['duration_ns']}ns"
        pr = meta["protocol"]
        blk = meta["block"]
        ba = meta["basis"]
        grouped.setdefault(ek, {}).setdefault(dur, {}).setdefault(pr, {}).setdefault(blk, {})[ba] = calc_exp_and_var(cnts)

    out_cells = {}
    arm_names = [
        "C_QISKIT_SYNC_XY8",
        "D_QISKIT_OPTIMIZED_STAG_XY8",
        "E_FIXED_STAG_XY8_80",
        "F_OSIRIS_CONTROL_COMPILER_V2",
    ]
    edge_cluster_diffs = {
        "OSIRIS_V2_vs_FIXED_80": {},
        "OSIRIS_V2_vs_SYNC_XY8": {},
        "OSIRIS_V2_vs_QISKIT_OPT_STAG": {},
        "FIXED_80_vs_SYNC_XY8": {},
    }
    block_cluster_diffs = {k: {b: [] for b in range(BLOCKS)} for k in edge_cluster_diffs}

    for ek, dur_dict in grouped.items():
        out_cells[ek] = {}
        for dur, pr_dict in dur_dict.items():
            f_by_proto = {}
            for pr, blk_dict in pr_dict.items():
                f_blks = [
                    (1.0 + blk_dict[b]["XX"][0] - blk_dict[b]["YY"][0] + blk_dict[b]["ZZ"][0]) / 4.0
                    for b in sorted(blk_dict)
                ]
                f_by_proto[pr] = f_blks

            d_os_f80 = np.array(f_by_proto["F_OSIRIS_CONTROL_COMPILER_V2"]) - np.array(f_by_proto["E_FIXED_STAG_XY8_80"])
            d_os_syn = np.array(f_by_proto["F_OSIRIS_CONTROL_COMPILER_V2"]) - np.array(f_by_proto["C_QISKIT_SYNC_XY8"])
            d_os_qop = np.array(f_by_proto["F_OSIRIS_CONTROL_COMPILER_V2"]) - np.array(f_by_proto["D_QISKIT_OPTIMIZED_STAG_XY8"])
            d_f80_syn = np.array(f_by_proto["E_FIXED_STAG_XY8_80"]) - np.array(f_by_proto["C_QISKIT_SYNC_XY8"])

            edge_cluster_diffs["OSIRIS_V2_vs_FIXED_80"].setdefault(ek, []).extend(d_os_f80.tolist())
            edge_cluster_diffs["OSIRIS_V2_vs_SYNC_XY8"].setdefault(ek, []).extend(d_os_syn.tolist())
            edge_cluster_diffs["OSIRIS_V2_vs_QISKIT_OPT_STAG"].setdefault(ek, []).extend(d_os_qop.tolist())
            edge_cluster_diffs["FIXED_80_vs_SYNC_XY8"].setdefault(ek, []).extend(d_f80_syn.tolist())

            for b in range(BLOCKS):
                block_cluster_diffs["OSIRIS_V2_vs_FIXED_80"][b].append(float(d_os_f80[b]))
                block_cluster_diffs["OSIRIS_V2_vs_SYNC_XY8"][b].append(float(d_os_syn[b]))
                block_cluster_diffs["OSIRIS_V2_vs_QISKIT_OPT_STAG"][b].append(float(d_os_qop[b]))
                block_cluster_diffs["FIXED_80_vs_SYNC_XY8"][b].append(float(d_f80_syn[b]))

            dur_int = int(dur.replace("ns", ""))
            out_cells[ek][dur] = {
                "osiris_v2_offset_ns": osiris_delta_map[(ek, dur_int)],
                "F_Bell_C_QISKIT_SYNC_XY8": float(np.mean(f_by_proto["C_QISKIT_SYNC_XY8"])),
                "F_Bell_D_QISKIT_OPTIMIZED_STAG_XY8": float(np.mean(f_by_proto["D_QISKIT_OPTIMIZED_STAG_XY8"])),
                "F_Bell_E_FIXED_STAG_XY8_80": float(np.mean(f_by_proto["E_FIXED_STAG_XY8_80"])),
                "F_Bell_F_OSIRIS_CONTROL_COMPILER_V2": float(np.mean(f_by_proto["F_OSIRIS_CONTROL_COMPILER_V2"])),
                "Delta_OSIRIS_V2_minus_FIXED_80_mean_pp": round(float(np.mean(d_os_f80)) * 100.0, 4),
                "Delta_OSIRIS_V2_minus_FIXED_80_se_pp": round(float(np.std(d_os_f80, ddof=1) / math.sqrt(BLOCKS)) * 100.0, 4),
                "Delta_OSIRIS_V2_minus_SYNC_XY8_mean_pp": round(float(np.mean(d_os_syn)) * 100.0, 4),
                "Delta_OSIRIS_V2_minus_QISKIT_OPT_mean_pp": round(float(np.mean(d_os_qop)) * 100.0, 4),
                "blocks_by_arm": {k: [round(float(x), 6) for x in f_by_proto[k]] for k in arm_names},
            }

    coupler_clustered = {
        k: cluster_stats([float(np.mean(vals)) for vals in ek_map.values()])
        for k, ek_map in edge_cluster_diffs.items()
    }
    block_clustered = {
        k: cluster_stats([float(np.mean(vals)) for vals in b_map.values()])
        for k, b_map in block_cluster_diffs.items()
    }

    portfolio_means_pct = {
        arm: round(
            float(np.mean([
                out_cells[ek][dur][f"F_Bell_{arm}"]
                for ek in out_cells for dur in out_cells[ek]
            ])) * 100.0,
            4,
        )
        for arm in arm_names
    }

    analysis_payload = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "qpu_seconds": qpu_seconds,
        "ledger_sequence": seq,
        "payload_sha256": payload_sha256,
        "qpy_sha256": qpy_sha256,
        "prereg_216_sha256": EXPECTED_PREREG_216_SHA256,
        "prereg_e3_sha256": EXPECTED_PREREG_E3_SHA256,
        "portfolio_means_pct": portfolio_means_pct,
        "coupler_clustered_inference_df2": coupler_clustered,
        "block_clustered_inference_df2": block_clustered,
        "cells": out_cells,
    }
    (EXP_DIR / "analysis_exp_e3_pilot.json").write_text(json.dumps(analysis_payload, indent=2))
    print("Saved prospective E3 pilot evaluation to analysis_exp_e3_pilot.json")
    print("Portfolio Means (%):", json.dumps(portfolio_means_pct, indent=2))


if __name__ == "__main__":
    main()
