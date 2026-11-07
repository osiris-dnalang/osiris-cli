import json
import hashlib
import time
import sqlite3
from pathlib import Path

EXPERIMENT_DIR = Path("/mnt/c/Users/Ron/osiris-cli/experiments/hp001")
DB_PATH = Path("/mnt/c/Users/Ron/evidence_ledger.db")

results_file = EXPERIMENT_DIR / "physical_hp001_phase2_results.json"
results_h = hashlib.sha256(results_file.read_bytes()).hexdigest()
results_data = json.loads(results_file.read_text(encoding="utf-8"))

now_ts = time.time()
nonce = f"OSIRIS-HP001-P2-HARVEST-{int(now_ts * 1000)}"

# Query Ledger Tip
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1")
last_seq, prev_hash = cur.fetchone()
next_seq = last_seq + 1

event_type = "SYS021_HP001_PHASE2_HARDWARE_ACQUISITION_RECEIPT"
operator_id = "Devin Phillip Davis / Enki"
schema_h = hashlib.sha256("OSIRIS_HP001_PHASE2_RECONSTRUCTED_RECOVERY_V1".encode("utf-8")).hexdigest()

receipt_payload = {
    "sequence_index": next_seq,
    "prev_block_hash": prev_hash,
    "event_type": event_type,
    "operator_id": operator_id,
    "job_id": results_data["job_id"],
    "backend": results_data["backend"],
    "real_qpu_seconds": results_data["qpu_usage"].get("quantum_seconds", 12),
    "total_circuits": results_data["total_circuits"],
    "total_physical_shots": results_data["total_physical_shots"],
    "results_sha256": results_h,
    "arm_a_fidelity": results_data["arms"]["Arm A (Full-Access Inverse)"]["fidelity"],
    "arm_b_fidelity": results_data["arms"]["Arm B (Restricted Recovery - Early Ent)"]["fidelity"],
    "arm_b_control_fidelity": results_data["arms"]["Arm B Control (Separable Trapped)"]["fidelity"],
    "delta_gain_pp": results_data["delta_recovery_gain"] * 100,
    "entanglement_witness": results_data["arms"]["Arm B (Restricted Recovery - Early Ent)"]["entanglement_witness"],
    "is_entangled": results_data["arms"]["Arm B (Restricted Recovery - Early Ent)"]["is_entangled"],
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
    json.dumps(receipt_payload)
))
conn.commit()
conn.close()

print(f"[COMMITTED] Block #{next_seq} successfully anchored to evidence_ledger.db.")
print(f"  Event            : {event_type}")
print(f"  Block Hash       : {block_h}")
print(f"  Prev Block Hash  : {prev_hash}")
print(f"  Job ID           : {results_data['job_id']}")
print(f"  Arm B Fidelity   : {results_data['arms']['Arm B (Restricted Recovery - Early Ent)']['fidelity'] * 100:.2f}%")
print(f"  Delta Gain       : {results_data['delta_recovery_gain'] * 100:+.2f} pp")
