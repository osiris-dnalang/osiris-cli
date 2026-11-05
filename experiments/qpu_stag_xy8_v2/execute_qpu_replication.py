#!/usr/bin/env python3
"""
execute_qpu_replication.py
OSIRIS Physical QPU Validation Campaign — Experiment D (Independent Replication)
Target: IBM Marrakesh (Heron r2)

Operator: Devin Phillip Davis / Enki
Invariants: SYS-021 (Zero Self-Supplied Authorization, Payload-Bound Grants)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

EXP_DIR = Path("/mnt/c/Users/Ron/osiris-cli/experiments/qpu_stag_xy8_v2")
LEDGER_JSONL = EXP_DIR / "ledger.jsonl"
EVIDENCE_DB = Path("/mnt/c/Users/Ron/evidence_ledger.db")

KEY_FILE = Path("/mnt/c/Users/Ron/Downloads/dnalang.json")
with open(KEY_FILE) as f:
    key_info = json.load(f)
TOKEN = key_info["apikey"]

OPERATOR_ID = "Devin Phillip Davis / Enki"
OP_SCHEMA = "OSIRIS_QPU_REPLICATION_V1"
TARGET_BACKEND = "ibm_marrakesh"

# 3 Primary Benchmark Edges:
# (14, 15): top performer with +0.0228 gain
# (33, 32): central lattice edge
# (19, 35): bridge boundary edge
EDGES = [(14, 15), (33, 32), (19, 35)]
PROTOCOLS = ["IDLE", "SYNC_XY8", "STAG_XY8", "SHIFT_XY8"]
BASES = ["XX", "YY", "ZZ"]
TOTAL_DT = 1000       # 4000.0 ns
STAGGER_DT = 40       # 160.0 ns
PULSE_DT = 9          # 36.0 ns
TAU_DT = 116          # 464.0 ns
TAU_HALF_DT = 58      # 232.0 ns
SHOTS = 1024
REPS = 4              # 4 independent randomized acquisition blocks
XY8_PULSES = ["x", "y", "x", "y", "y", "x", "y", "x"]

def append_jsonl(entry_kind: str, data: dict):
    prev_hash = "0" * 64
    if LEDGER_JSONL.exists() and LEDGER_JSONL.stat().st_size > 0:
        lines = [l.strip() for l in LEDGER_JSONL.read_text().splitlines() if l.strip()]
        if lines:
            last = json.loads(lines[-1])
            prev_hash = last.get("hash", "0" * 64)
            
    record = {
        "kind": entry_kind,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prev": prev_hash,
        **data
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    record["hash"] = hashlib.sha256(raw).hexdigest()
    
    line = json.dumps(record, separators=(",", ":")) + "\n"
    with open(LEDGER_JSONL, "a") as f:
        f.write(line)
    return record

def main():
    print("=" * 80)
    print("OSIRIS PHYSICAL QPU VALIDATION CAMPAIGN — EXPERIMENT D (REPLICATION)")
    print("=" * 80)
    
    self_path = Path(__file__).resolve()
    payload_bytes = self_path.read_bytes()
    payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    schema_sha256 = hashlib.sha256(OP_SCHEMA.encode("utf-8")).hexdigest()
    print(f"Operational Payload SHA-256: {payload_sha256}")
    
    # Operator grant (SYS-021)
    priv_key_path = Path("/home/enki/.osiris/keystore/node_beta_operator.key")
    priv_seed = priv_key_path.read_bytes()
    priv = Ed25519PrivateKey.from_private_bytes(priv_seed)
    pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    
    now = time.time()
    nonce = f"ads-sys021-rep-{uuid.uuid4().hex}"
    grant_data = {
        "expires_at": now + 86400,
        "nonce": nonce,
        "operation_schema_sha256": schema_sha256,
        "operator_id": OPERATOR_ID,
        "payload_sha256": payload_sha256,
        "public_key": pub_hex,
        "timestamp": now,
    }
    canonical_grant_bytes = json.dumps(grant_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    grant_data["signature"] = priv.sign(canonical_grant_bytes).hex()
    
    # Commit to evidence_ledger.db
    conn = sqlite3.connect(EVIDENCE_DB)
    with conn:
        latest = conn.execute("SELECT block_hash, sequence_index FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1").fetchone()
        prev_hash = latest[0] if latest else "0" * 64
        seq = (latest[1] + 1) if latest else 1
        
        block_content = {
            "sequence_index": seq,
            "prev_block_hash": prev_hash,
            "timestamp": now,
            "event_type": "SYS021_REPLICATION_DISPATCH_GRANT",
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
        """, (
            prev_hash, b_hash, now, "SYS021_REPLICATION_DISPATCH_GRANT",
            OPERATOR_ID, payload_sha256, schema_sha256,
            nonce, json.dumps(grant_data, sort_keys=True, separators=(",", ":"))
        ))
    print(f"[GOVERNANCE COMMIT] Operator grant committed to evidence_ledger.db sequence #{seq}")
    
    append_jsonl("preregistration", {
        "operator_id": OPERATOR_ID,
        "payload_sha256": payload_sha256,
        "backend": TARGET_BACKEND,
        "edges": EDGES,
        "protocols": PROTOCOLS,
        "bases": BASES,
        "shots": SHOTS,
        "reps": REPS,
        "ledger_sequence_index": seq
    })
    
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=TOKEN)
    backend = service.backend(TARGET_BACKEND)
    
    n_expected = len(EDGES) * len(PROTOCOLS) * len(BASES) * REPS
    print(f"Transpiling {n_expected} ISA replication circuits on {TARGET_BACKEND}...")
    circuits = []
    specs = []
    rng = random.Random(20261105)
    
    for r in range(REPS):
        block = [(u, v, p, b) for (u, v) in EDGES for p in PROTOCOLS for b in BASES]
        rng.shuffle(block)
        for u, v, p, b in block:
            qc = QuantumCircuit(backend.num_qubits, 2, name=f"REP_{p}_{b}_q{u}_q{v}_r{r}")
            qc.h(u)
            qc.cx(u, v)
            qc.barrier([u, v])
            
            if p == "IDLE":
                qc.delay(TOTAL_DT, u, unit="dt")
                qc.delay(TOTAL_DT, v, unit="dt")
            elif p == "SYNC_XY8":
                for q in [u, v]:
                    qc.delay(TAU_HALF_DT, q, unit="dt")
                    for idx, op in enumerate(XY8_PULSES):
                        if op == "x":
                            qc.x(q)
                        else:
                            qc.y(q)
                        if idx < 7:
                            qc.delay(TAU_DT, q, unit="dt")
                        else:
                            qc.delay(TAU_HALF_DT, q, unit="dt")
            elif p == "STAG_XY8":
                qc.delay(TAU_HALF_DT, u, unit="dt")
                for idx, op in enumerate(XY8_PULSES):
                    if op == "x":
                        qc.x(u)
                    else:
                        qc.y(u)
                    if idx < 7:
                        qc.delay(TAU_DT, u, unit="dt")
                    else:
                        qc.delay(TAU_HALF_DT, u, unit="dt")
                lead_v = TAU_HALF_DT + STAGGER_DT
                trail_v = TAU_HALF_DT - STAGGER_DT
                qc.delay(lead_v, v, unit="dt")
                for idx, op in enumerate(XY8_PULSES):
                    if op == "x":
                        qc.x(v)
                    else:
                        qc.y(v)
                    if idx < 7:
                        qc.delay(TAU_DT, v, unit="dt")
                    else:
                        qc.delay(trail_v, v, unit="dt")
            elif p == "SHIFT_XY8":
                lead = TAU_HALF_DT + STAGGER_DT
                trail = TAU_HALF_DT - STAGGER_DT
                for q in [u, v]:
                    qc.delay(lead, q, unit="dt")
                    for idx, op in enumerate(XY8_PULSES):
                        if op == "x":
                            qc.x(q)
                        else:
                            qc.y(q)
                        if idx < 7:
                            qc.delay(TAU_DT, q, unit="dt")
                        else:
                            qc.delay(trail, q, unit="dt")
            qc.barrier([u, v])
            
            if b == "XX":
                qc.h(u)
                qc.h(v)
            elif b == "YY":
                qc.sdg(u)
                qc.h(u)
                qc.sdg(v)
                qc.h(v)
            elif b == "ZZ":
                pass
                
            qc.measure(u, 0)
            qc.measure(v, 1)
            
            tqc = transpile(qc, backend=backend, optimization_level=0, scheduling_method="asap")
            circuits.append(tqc)
            specs.append({
                "rep": r,
                "edge": [u, v],
                "protocol": p,
                "basis": b,
                "name": qc.name
            })
            
    print(f"Transpiled {len(circuits)} circuits successfully.")
    
    intent = append_jsonl("submit-intent", {
        "backend": TARGET_BACKEND,
        "n_circuits": len(circuits),
        "shots": SHOTS,
        "reps": REPS,
        "circuit_hashes": [hashlib.sha256(str(c).encode()).hexdigest()[:16] for c in circuits]
    })
    
    print(f"Submitting replication job with {len(circuits)} circuits via SamplerV2...")
    sampler = SamplerV2(mode=backend)
    job = sampler.run(circuits, shots=SHOTS)
    job_id = job.job_id()
    print(f"JOB SUBMITTED! Job ID: {job_id}")
    
    append_jsonl("submitted", {
        "job_id": job_id,
        "intent_hash": intent["hash"]
    })
    
    # Save receipt
    (EXP_DIR / "job_receipts_replication.json").write_text(json.dumps({
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "circuits": len(circuits),
        "shots": SHOTS,
        "edges": EDGES,
        "protocols": PROTOCOLS,
        "reps": REPS
    }, indent=2))
    
    print("Waiting for QPU execution...")
    last_status = None
    while True:
        st = str(job.status())
        if st != last_status:
            print(f"  [{time.strftime('%H:%M:%S')}] Job {job_id} status: {st}")
            last_status = st
        if "DONE" in st.upper() or "CANCEL" in st.upper() or "ERROR" in st.upper():
            break
        time.sleep(5)
        
    if "DONE" not in last_status.upper():
        print(f"Failed with status: {last_status}")
        return 1
        
    print("Execution complete! Ingesting shot counts...")
    result = job.result()
    raw_counts = [pub_res.data.c.get_counts() for pub_res in result]
    (EXP_DIR / "raw_results_replication.json").write_text(json.dumps(raw_counts))
    
    qpu_seconds = None
    try:
        qpu_seconds = job.usage()
    except Exception:
        pass
        
    counts_hash = hashlib.sha256(json.dumps(raw_counts, sort_keys=True).encode()).hexdigest()
    append_jsonl("result", {
        "job_id": job_id,
        "qpu_seconds": qpu_seconds,
        "counts_sha256": counts_hash
    })
    
    def calc_exp(cnts: dict[str, int]) -> float:
        n = sum(cnts.values())
        if n == 0:
            return 0.0
        p = 0
        for bs, c in cnts.items():
            b_clean = bs.replace(" ", "")
            b0 = int(b_clean[-1])
            b1 = int(b_clean[-2])
            sign = 1 if b0 == b1 else -1
            p += sign * c
        return p / n

    # Group results
    rep_results = {}
    for spec, cnts in zip(specs, raw_counts):
        edge_key = f"({spec['edge'][0]},{spec['edge'][1]})"
        prot = spec["protocol"]
        basis = spec["basis"]
        exp_val = calc_exp(cnts)
        rep_results.setdefault(edge_key, {}).setdefault(prot, {}).setdefault(basis, []).append(exp_val)
        
    analysis = {
        "job_id": job_id,
        "backend": TARGET_BACKEND,
        "qpu_seconds": qpu_seconds,
        "edges": EDGES,
        "protocols": PROTOCOLS,
        "reps": REPS,
        "edge_summaries": {}
    }
    
    print("\n" + "=" * 80)
    print("EXPERIMENT D: INDEPENDENT REPLICATION RESULTS:")
    print("=" * 80)
    for edge_key, prot_dict in rep_results.items():
        print(f"\n--- Edge {edge_key} (Replication) ---")
        analysis["edge_summaries"][edge_key] = {}
        for prot, basis_dict in prot_dict.items():
            analysis["edge_summaries"][edge_key][prot] = {}
            row_str = f"  {prot:10} | "
            for b in ["XX", "YY", "ZZ"]:
                vals = basis_dict[b]
                mean = float(np.mean(vals))
                std = float(np.std(vals))
                analysis["edge_summaries"][edge_key][prot][b] = {"mean": mean, "std": std, "values": vals}
                row_str += f"<{b}>: {mean:+.4f} (±{std:.4f})  "
            print(row_str)
            
    (EXP_DIR / "analysis_replication.json").write_text(json.dumps(analysis, indent=2))
    append_jsonl("analysis", {
        "job_id": job_id,
        "analysis_sha256": hashlib.sha256(json.dumps(analysis, sort_keys=True).encode()).hexdigest()
    })
    print("\nEXPERIMENT D REPLICATION COMPLETE!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
