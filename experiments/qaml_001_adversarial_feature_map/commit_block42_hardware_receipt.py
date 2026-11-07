#!/usr/bin/env python3
"""
commit_block41_hardware_receipt.py — Anchors OSIRIS-QAML-001 Hardware Acquisition Receipt to evidence_ledger.db
Records physical QPU execution on ibm_marrakesh (Job ID: dbn9e8s4148s7390i0h0) as Block #41.
"""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
DB_PATH = Path(r"C:\Users\Ron\evidence_ledger.db")

results_file = EXPERIMENT_DIR / "physical_qpu_benchmark_results.json"
results_h = hashlib.sha256(results_file.read_bytes()).hexdigest()
results_data = json.loads(results_file.read_text(encoding="utf-8"))

circuits_file = EXPERIMENT_DIR / "submitted_isa_circuits.qpy"
circuits_h = hashlib.sha256(circuits_file.read_bytes()).hexdigest() if circuits_file.exists() else None

now_ts = time.time()
nonce = f"OSIRIS-QAML-001-HARVEST-{int(now_ts * 1000)}"

# Query current tip of the ledger
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1")
last_seq, prev_hash = cur.fetchone()
next_seq = last_seq + 1

event_type = "SYS021_QAML_001_HARDWARE_ACQUISITION_RECEIPT"
operator_id = "Devin Phillip Davis / Enki"
schema_h = hashlib.sha256("OSIRIS_QAML_001_PHYSICAL_DISPATCH_V1".encode("utf-8")).hexdigest()

receipt_payload = {
    "sequence_index": next_seq,
    "prev_block_hash": prev_hash,
    "event_type": event_type,
    "operator_id": operator_id,
    "grant_reference": "GRANT-SYS021-QAML001-2B4F9D4F1AE2 (Block #33)",
    "benchmark_id": results_data["benchmark_id"],
    "job_id": results_data["job_id"],
    "backend": results_data["backend"],
    "qpu_seconds": results_data["qpu_usage"].get("qpu_charge_time_seconds", 25),
    "total_circuits": results_data["total_circuits"],
    "shots_per_circuit": results_data["shots_per_circuit"],
    "total_physical_shots": results_data["total_physical_shots"],
    "qpy_circuits_sha256": circuits_h,
    "results_sha256": results_h,
    "arm_results": results_data["arm_results"],
    "hypotheses_evaluation": results_data["hypotheses_evaluation"],
    "nonce": nonce,
    "timestamp": now_ts
}

raw_block_str = f"{prev_hash}:{next_seq}:{event_type}:{operator_id}:{results_h}:{schema_h}:{nonce}:{now_ts}"
block_h = hashlib.sha256(raw_block_str.encode("utf-8")).hexdigest()
receipt_payload["block_hash"] = block_h

cur.execute("""
    INSERT INTO ledger_blocks (
        sequence_index, prev_block_hash, block_hash, timestamp,
        event_type, operator_id, payload_sha256, operation_schema_sha256,
        nonce, raw_grant_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    next_seq,
    prev_hash,
    block_h,
    now_ts,
    event_type,
    operator_id,
    results_h,
    schema_h,
    nonce,
    json.dumps(receipt_payload, indent=2)
))
conn.commit()
conn.close()

# Save receipt artifact locally
receipt_out = EXPERIMENT_DIR / f"block_{next_seq}_ledger_receipt.json"
receipt_out.write_text(json.dumps(receipt_payload, indent=2), encoding="utf-8")

print(f"[COMMITTED] Block #{next_seq} successfully anchored to evidence_ledger.db.")
print(f"  Event            : {event_type}")
print(f"  Block Hash       : {block_h}")
print(f"  Prev Block Hash  : {prev_hash}")
print(f"  Job ID           : {results_data['job_id']}")
print(f"  Backend          : {results_data['backend']}")
print(f"  Total Shots      : {results_data['total_physical_shots']:,}")
print(f"  Receipt File     : {receipt_out.name}")
