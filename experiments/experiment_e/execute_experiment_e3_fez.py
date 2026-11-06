#!/usr/bin/env python3
"""
OSIRIS EXPERIMENT E3: Cross-Chip Bell-Fidelity Transfer Validation (ibm_fez)
==========================================================================================
Target Processor : ibm_fez (156-qubit IBM Heron r2, dt = 4.0 ns)
Physical Edges   : (87,88)   [Regime I,   eta_phi=0.0103 -> OSIRIS selects SYNC_XY8 (0 ns)]
                   (61,62)   [Regime II,  eta_phi=0.2126 -> OSIRIS selects STAG_XY8_80 (80 ns)]
                   (100,101) [Regime III, eta_phi=0.3705 -> OSIRIS selects SYNC_XY8 (0 ns)]
Initial State    : Certified |Phi+> = (|00> + |11>)/sqrt(2) via qc.h(u); qc.h(v); qc.cz(u,v); qc.h(v)
Evolution Window : 8,000 ns (2,000 dt)
Protocols        : SYNC_XY8 (0 ns), STAG_XY8_80 (80 ns), OSIRIS_ADAPTIVE_V1 (frozen per edge)
Pauli Bases      : XX, YY, ZZ
Blocks & Shots   : 3 randomized blocks x 27 circuits/block = 81 ISA circuits x 1,024 shots = 82,944 shots
Primary Estimand : Delta_F_transfer = F(OSIRIS_ADAPTIVE_V1) - F(STAG_XY8_80)
==========================================================================================
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

from qiskit import QuantumCircuit, qpy, transpile
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

EXP_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXP_DIR.parents[1]
LEDGER_DB = REPO_ROOT / "evidence_ledger.db"
CRED_PATH = REPO_ROOT / "Downloads" / "dnalang.json"
PREREG_PATH = EXP_DIR / "preregistered_predictions_exp_e3_fez.json"

TARGET_BACKEND = "ibm_fez"
DT_NS = 4.0
DURATION_NS = 8000
TOTAL_DT = 2000  # 8,000 ns / 4.0 ns
PULSE_DT = 8     # 32.0 ns native sx/x gate duration on Heron r2
NUM_PULSES = 8
SHOTS = 1024
NUM_BLOCKS = 3

EDGES_FEZ = [
    (87, 88),    # Regime I   (eta_phi = 0.0103 -> OSIRIS Adaptive v1 selects 0 ns)
    (61, 62),    # Regime II  (eta_phi = 0.2126 -> OSIRIS Adaptive v1 selects 80 ns)
    (100, 101),  # Regime III (eta_phi = 0.3705 -> OSIRIS Adaptive v1 selects 0 ns)
]

PROTOCOLS = ["SYNC_XY8", "STAG_XY8_80", "OSIRIS_ADAPTIVE_V1"]
PAULI_BASES = ["XX", "YY", "ZZ"]

OSIRIS_FROZEN_OFFSETS_NS = {
    "(87,88)": 0,
    "(61,62)": 80,
    "(100,101)": 0,
}


def compute_xy8_delays_dt(total_dt: int, offset_dt: int):
    """
    Computes antisymmetric bilateral XY8 delay intervals in units of dt (4.0 ns):
      delta_u = -offset_dt // 2
      delta_v = +offset_dt - (offset_dt // 2)
    Guarantees identical total evolution duration (total_dt) on both qubits and
    strictly positive boundary delays.
    """
    free_dt = total_dt - NUM_PULSES * PULSE_DT
    tau_dt = free_dt // NUM_PULSES
    rem_dt = free_dt - (NUM_PULSES - 1) * tau_dt
    lead_base = rem_dt // 2
    trail_base = rem_dt - lead_base

    delta_u = -(offset_dt // 2)
    delta_v = offset_dt - (offset_dt // 2)

    lead_u = lead_base + delta_u
    trail_u = trail_base - delta_u
    lead_v = lead_base + delta_v
    trail_v = trail_base - delta_v

    assert lead_u > 0 and trail_u > 0, f"Invalid u boundary delays: {lead_u}, {trail_u}"
    assert lead_v > 0 and trail_v > 0, f"Invalid v boundary delays: {lead_v}, {trail_v}"

    sum_u = lead_u + (NUM_PULSES - 1) * tau_dt + trail_u + NUM_PULSES * PULSE_DT
    sum_v = lead_v + (NUM_PULSES - 1) * tau_dt + trail_v + NUM_PULSES * PULSE_DT
    assert sum_u == total_dt and sum_v == total_dt, f"Duration mismatch: {sum_u}, {sum_v} != {total_dt}"

    return {
        "tau_dt": tau_dt,
        "lead_u": lead_u,
        "trail_u": trail_u,
        "lead_v": lead_v,
        "trail_v": trail_v,
        "total_dt": total_dt,
    }


def append_1q_xy8_pulse(qc: QuantumCircuit, q: int, axis: str):
    if axis == "X":
        qc.x(q)
    elif axis == "Y":
        qc.rz(-math.pi / 2, q)
        qc.x(q)
        qc.rz(math.pi / 2, q)
    else:
        raise ValueError(f"Unknown axis: {axis}")


def build_e3_circuit(u: int, v: int, protocol: str, basis: str, block_idx: int) -> QuantumCircuit:
    edge_key = f"({u},{v})"
    if protocol == "SYNC_XY8":
        offset_ns = 0
    elif protocol == "STAG_XY8_80":
        offset_ns = 80
    elif protocol == "OSIRIS_ADAPTIVE_V1":
        offset_ns = OSIRIS_FROZEN_OFFSETS_NS[edge_key]
    else:
        raise ValueError(f"Unknown protocol: {protocol}")

    offset_dt = int(round(offset_ns / DT_NS))
    sched = compute_xy8_delays_dt(TOTAL_DT, offset_dt)

    qc = QuantumCircuit(156, 2)
    qc.name = f"E3_FEZ_b{block_idx}_{u}_{v}_{protocol}_{basis}"

    # 1. Certified E0 Bell |Phi+> state preparation
    qc.h(u)
    qc.h(v)
    qc.cz(u, v)
    qc.h(v)
    qc.barrier(u, v)

    # 2. Dynamical decoupling window (exact 2,000 dt = 8,000 ns)
    xy8_axes = ["X", "Y", "X", "Y", "Y", "X", "Y", "X"]

    qc.delay(sched["lead_u"], u, unit="dt")
    for idx, ax in enumerate(xy8_axes):
        append_1q_xy8_pulse(qc, u, ax)
        if idx < NUM_PULSES - 1:
            qc.delay(sched["tau_dt"], u, unit="dt")
    qc.delay(sched["trail_u"], u, unit="dt")

    qc.delay(sched["lead_v"], v, unit="dt")
    for idx, ax in enumerate(xy8_axes):
        append_1q_xy8_pulse(qc, v, ax)
        if idx < NUM_PULSES - 1:
            qc.delay(sched["tau_dt"], v, unit="dt")
    qc.delay(sched["trail_v"], v, unit="dt")

    qc.barrier(u, v)

    # 3. Pauli basis rotation & measurement
    if basis == "XX":
        qc.h(u)
        qc.h(v)
    elif basis == "YY":
        qc.sdg(u)
        qc.h(u)
        qc.sdg(v)
        qc.h(v)
    elif basis == "ZZ":
        pass
    else:
        raise ValueError(f"Unknown Pauli basis: {basis}")

    qc.measure(u, 0)
    qc.measure(v, 1)
    return qc


def run_preflight_verification():
    print("Verifying Frozen Pre-Registration Lock & Statevector Gate...")
    prereg_bytes = PREREG_PATH.read_bytes()
    prereg_sha = hashlib.sha256(prereg_bytes).hexdigest()
    prereg_data = json.loads(prereg_bytes.decode("utf-8"))
    assert prereg_data["experiment_id"] == "OSIRIS_EXPERIMENT_E3_CROSS_CHIP_TRANSFER"
    assert prereg_data["target_qpu"] == "ibm_fez"
    assert prereg_data["model_sha256"] == "1f6e55f500e7e0f5ffc38bd3786a278da83450d715eef2bfa2290aa75852980d"

    # Verify Statevector |Phi+> preparation and XY8 identity preservation on a 2-qubit test circuit
    for offset_ns in [0, 80]:
        qc_test = QuantumCircuit(2)
        qc_test.h(0)
        qc_test.h(1)
        qc_test.cz(0, 1)
        qc_test.h(1)
        for ax in ["X", "Y", "X", "Y", "Y", "X", "Y", "X"]:
            append_1q_xy8_pulse(qc_test, 0, ax)
            append_1q_xy8_pulse(qc_test, 1, ax)
        sv = Statevector.from_instruction(qc_test)
        probs = sv.probabilities_dict()
        f_bell = 0.5 * (probs.get("00", 0.0) + probs.get("11", 0.0)) + abs(sv.data[0] * sv.data[3].conjugate())
        assert abs(f_bell - 1.0) < 1e-12, f"Statevector Bell fidelity failed: {f_bell}"

    print(f"  [PASS] Pre-registration manifest locked: {prereg_sha}")
    print("  [PASS] Certified |Phi+> preparation and XY8 unitary preservation verified.")
    return prereg_sha


def build_all_e3_circuits():
    all_circuits = []
    manifest = []
    rng = random.Random(2026110504)

    for b in range(NUM_BLOCKS):
        block_specs = []
        for u, v in EDGES_FEZ:
            for proto in PROTOCOLS:
                for basis in PAULI_BASES:
                    block_specs.append((u, v, proto, basis))
        rng.shuffle(block_specs)

        for u, v, proto, basis in block_specs:
            qc = build_e3_circuit(u, v, proto, basis, b)
            all_circuits.append(qc)
            manifest.append({
                "circuit_index": len(all_circuits) - 1,
                "name": qc.name,
                "block": b,
                "edge": f"({u},{v})",
                "u": u,
                "v": v,
                "protocol": proto,
                "basis": basis,
                "effective_offset_ns": (
                    0 if proto == "SYNC_XY8"
                    else 80 if proto == "STAG_XY8_80"
                    else OSIRIS_FROZEN_OFFSETS_NS[f"({u},{v})"]
                ),
            })

    assert len(all_circuits) == 81, f"Expected 81 circuits, got {len(all_circuits)}"
    return all_circuits, manifest


def parity_expectation(counts: dict) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    even = counts.get("00", 0) + counts.get("11", 0)
    odd = counts.get("01", 0) + counts.get("10", 0)
    return (even - odd) / total


def main():
    print("=" * 90)
    print("OSIRIS EXPERIMENT E3: CROSS-CHIP TRANSFER TO IBM_FEZ — GOVERNED EXECUTION")
    print("=" * 90)

    prereg_sha = run_preflight_verification()
    payload_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(f"Operational Payload SHA-256: {payload_sha}")

    all_circuits, manifest = build_all_e3_circuits()

    creds = json.loads(CRED_PATH.read_text())
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=creds["apikey"])
    backend = service.backend(TARGET_BACKEND)

    # Verify physical coupling edges on target backend
    cmap_edges = set(tuple(e) for e in backend.coupling_map.get_edges())
    for u, v in EDGES_FEZ:
        assert (u, v) in cmap_edges or (v, u) in cmap_edges, f"Edge ({u},{v}) not on {TARGET_BACKEND}"

    print(f"Transpiling {len(all_circuits)} circuits to {TARGET_BACKEND} ISA (dt={backend.dt*1e9:.1f} ns)...")
    isa_circuits = transpile(
        all_circuits,
        backend=backend,
        optimization_level=0,
        scheduling_method="alap",
    )

    # Freeze QPY before submission
    qpy_path = EXP_DIR / "submitted_circuits_exp_e3_fez.qpy"
    with open(qpy_path, "wb") as f:
        qpy.dump(isa_circuits, f)
    qpy_sha = hashlib.sha256(qpy_path.read_bytes()).hexdigest()
    print(f"Frozen QPY Archive: {qpy_path.name} (SHA-256: {qpy_sha})")

    # Record runtime execution receipt in evidence_ledger.db under SYS-021
    conn = sqlite3.connect(str(LEDGER_DB))
    cur = conn.cursor()
    prev_seq, prev_hash = cur.execute(
        "SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1"
    ).fetchone()
    next_seq = prev_seq + 1
    ts = time.time()
    nonce = f"EXP-E3-FEZ-RUNTIME-{int(ts * 1000)}"
    raw_grant = {
        "sequence_index": next_seq,
        "prev_block_hash": prev_hash,
        "timestamp": ts,
        "event_type": "SYS021_EXP_E3_FEZ_RUNTIME_EXECUTION",
        "operator_id": "Devin Phillip Davis / Enki",
        "payload_sha256": payload_sha,
        "prereg_sha256": prereg_sha,
        "qpy_sha256": qpy_sha,
        "target_backend": TARGET_BACKEND,
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
            "SYS021_EXP_E3_FEZ_RUNTIME_EXECUTION",
            "Devin Phillip Davis / Enki",
            payload_sha,
            prereg_sha,
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
        "prereg_sha256": prereg_sha,
        "qpy_sha256": qpy_sha,
        "circuits_count": len(isa_circuits),
        "shots_per_circuit": SHOTS,
        "total_shots": len(isa_circuits) * SHOTS,
    }
    receipt_path = EXP_DIR / "job_receipt_exp_e3_fez.json"
    receipt_path.write_text(json.dumps(job_receipt, indent=2))
    print(f"Job receipt written to: {receipt_path.name}")

    while True:
        status = str(job.status())
        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"  [{now_str}] Job {job_id} Status: {status}")
        if status in ["DONE", "ERROR", "CANCELLED"]:
            break
        time.sleep(10)

    if str(job.status()) != "DONE":
        print(f"Job terminated with status: {job.status()}")
        sys.exit(1)

    res = job.result()
    metrics = job.metrics() if hasattr(job, "metrics") else {}
    qpu_seconds = metrics.get("usage", {}).get("quantum_seconds", None)
    print(f"Real QPU compute consumed: {qpu_seconds} s")

    raw_records = []
    for idx, meta in enumerate(manifest):
        pub_res = res[idx]
        counts = pub_res.data.c.get_counts()
        exp_val = parity_expectation(counts)
        rec = dict(meta)
        rec["counts"] = counts
        rec["expectation"] = exp_val
        raw_records.append(rec)

    raw_out = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "qpu_seconds": qpu_seconds,
        "payload_sha256": payload_sha,
        "prereg_sha256": prereg_sha,
        "qpy_sha256": qpy_sha,
        "records": raw_records,
    }
    raw_path = EXP_DIR / "raw_results_exp_e3_fez.json"
    raw_path.write_text(json.dumps(raw_out, indent=2))

    # Compute block-level Bell state fidelities & primary/secondary transfer estimands
    # F_Bell = 0.25 * (1 + <XX> - <YY> + <ZZ>)
    by_cell_block = {}
    for rec in raw_records:
        key = (rec["edge"], rec["protocol"], rec["block"])
        by_cell_block.setdefault(key, {})[rec["basis"]] = rec["expectation"]

    edge_summaries = {}
    all_transfer_blocks = []
    all_stag_blocks = []

    for u, v in EDGES_FEZ:
        edge_key = f"({u},{v})"
        f_sync_blks = []
        f_stag_blks = []
        f_osiris_blks = []
        delta_transfer_blks = []
        delta_stag_blks = []

        for b in range(NUM_BLOCKS):
            p_sync = by_cell_block[(edge_key, "SYNC_XY8", b)]
            p_stag = by_cell_block[(edge_key, "STAG_XY8_80", b)]
            p_osiris = by_cell_block[(edge_key, "OSIRIS_ADAPTIVE_V1", b)]

            f_sync = 0.25 * (1.0 + p_sync["XX"] - p_sync["YY"] + p_sync["ZZ"])
            f_stag = 0.25 * (1.0 + p_stag["XX"] - p_stag["YY"] + p_stag["ZZ"])
            f_osiris = 0.25 * (1.0 + p_osiris["XX"] - p_osiris["YY"] + p_osiris["ZZ"])

            f_sync_blks.append(f_sync)
            f_stag_blks.append(f_stag)
            f_osiris_blks.append(f_osiris)

            d_trans = f_osiris - f_stag
            d_stag = f_stag - f_sync
            delta_transfer_blks.append(d_trans)
            delta_stag_blks.append(d_stag)
            all_transfer_blocks.append(d_trans)
            all_stag_blocks.append(d_stag)

        def mean_se(vals):
            m = sum(vals) / len(vals)
            sd = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
            return m, sd / math.sqrt(len(vals)) if len(vals) > 1 else 0.0

        m_trans, se_trans = mean_se(delta_transfer_blks)
        m_stag, se_stag = mean_se(delta_stag_blks)

        edge_summaries[edge_key] = {
            "osiris_selected_offset_ns": OSIRIS_FROZEN_OFFSETS_NS[edge_key],
            "F_Bell_SYNC_mean": sum(f_sync_blks) / NUM_BLOCKS,
            "F_Bell_STAG_80_mean": sum(f_stag_blks) / NUM_BLOCKS,
            "F_Bell_OSIRIS_ADAPTIVE_mean": sum(f_osiris_blks) / NUM_BLOCKS,
            "Delta_F_transfer_mean": m_trans,
            "Delta_F_transfer_SE": se_trans,
            "Delta_F_transfer_blocks": delta_transfer_blks,
            "Delta_F_stag_mean": m_stag,
            "Delta_F_stag_SE": se_stag,
            "Delta_F_stag_blocks": delta_stag_blks,
        }

    def global_stats(vals):
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
        se = sd / math.sqrt(len(vals)) if len(vals) > 1 else 0.0
        t_val = m / se if se > 0 else 0.0
        return {"mean": m, "se": se, "t_stat": t_val, "df": len(vals) - 1}

    analysis_out = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "qpu_seconds": qpu_seconds,
        "qpu_ru": round(qpu_seconds / 60.0, 4) if qpu_seconds is not None else None,
        "prereg_sha256": prereg_sha,
        "payload_sha256": payload_sha,
        "qpy_sha256": qpy_sha,
        "primary_outcome_Delta_F_transfer": global_stats(all_transfer_blocks),
        "secondary_outcome_Delta_F_stag": global_stats(all_stag_blocks),
        "edges": edge_summaries,
    }
    analysis_path = EXP_DIR / "analysis_exp_e3_fez.json"
    analysis_path.write_text(json.dumps(analysis_out, indent=2))
    print(f"Saved E3 cross-chip analysis to {analysis_path.name}")


if __name__ == "__main__":
    main()
