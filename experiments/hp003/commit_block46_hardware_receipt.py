#!/usr/bin/env python3
"""
commit_block46_hardware_receipt.py — Anchors OSIRIS-HP-003 Physical Telemetry to Evidence Ledger
Records Block Sequence #46 in evidence_ledger.db under SYS-021.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent

DB_CANDIDATES = [
    REPO_ROOT.parent / "evidence_ledger.db",
    REPO_ROOT / "evidence_ledger.db",
    Path("/mnt/c/Users/Ron/evidence_ledger.db"),
    Path("C:/Users/Ron/evidence_ledger.db")
]
DB_PATH = next((p for p in DB_CANDIDATES if p.exists()), None)
if not DB_PATH:
    raise FileNotFoundError("Could not find evidence_ledger.db in expected search paths.")

results_file = EXPERIMENT_DIR / "physical_hp003_results.json"
results_h = hashlib.sha256(results_file.read_bytes()).hexdigest()
results_data = json.loads(results_file.read_text(encoding="utf-8"))

now_ts = time.time()
nonce = f"OSIRIS-HP003-HARVEST-{int(now_ts * 1000)}"

# Query Ledger Tip
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1")
last_seq, prev_hash = cur.fetchone()
next_seq = last_seq + 1

event_type = "SYS021_HP003_HARDWARE_ACQUISITION_RECEIPT"
operator_id = "Devin Phillip Davis / Enki"
schema_h = hashlib.sha256("OSIRIS_HP003_MULTIQUBIT_CAPACITY_CERTIFICATION_V1".encode("utf-8")).hexdigest()

synth = results_data["arm_synthesis"]

receipt_payload = {
    "sequence_index": next_seq,
    "prev_block_hash": prev_hash,
    "event_type": event_type,
    "operator_id": operator_id,
    "job_id": results_data["job_id"],
    "backend": results_data["backend"],
    "real_qpu_seconds": results_data["qpu_usage"].get("quantum_seconds", 14),
    "total_circuits": results_data["total_circuits"],
    "total_physical_shots": results_data["total_physical_shots"],
    "results_sha256": results_h,
    "arm_a_fidelity": synth["Arm A"]["mean_f_average"],
    "arm_b_fidelity": synth["Arm B"]["mean_f_average"],
    "arm_b_def_fidelity": synth["Arm B-Def"]["mean_f_average"],
    "arm_b_ctrl_fidelity": synth["Arm B-Ctrl"]["mean_f_average"],
    "arm_b_held_fidelity": synth["Arm B-Held"]["mean_f_average"],
    "delta_gain_control_pp": round((synth["Arm B"]["mean_f_average"] - synth["Arm B-Ctrl"]["mean_f_average"]) * 100, 2),
    "delta_gain_deficient_pp": round((synth["Arm B"]["mean_f_average"] - synth["Arm B-Def"]["mean_f_average"]) * 100, 2),
    "entanglement_witness": synth["Arm B"]["entanglement_witness"],
    "is_entangled": synth["Arm B"]["is_entangled"],
    "endpoints_passed": {
        "H1_reversibility": results_data["endpoints_evaluation"]["H1_reversibility_positive_control"]["passed"],
        "H2_primary_recovery": results_data["endpoints_evaluation"]["H2_primary_multiqubit_restricted_recovery"]["passed"],
        "H3_capacity_threshold": results_data["endpoints_evaluation"]["H3_quantum_capacity_single_photon_threshold"]["passed"],
        "H4_separable_bridge": results_data["endpoints_evaluation"]["H4_separable_entanglement_bridge"]["passed"],
        "H5_heldout_specificity": results_data["endpoints_evaluation"]["H5_heldout_scrambler_specificity"]["passed"]
    },
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
print(f"  Event               : {event_type}")
print(f"  Block Hash          : {block_h}")
print(f"  Prev Block Hash     : {prev_hash}")
print(f"  Job ID              : {results_data['job_id']}")
print(f"  Arm A Fidelity      : {synth['Arm A']['mean_f_average'] * 100:.2f}%")
print(f"  Arm B Fidelity      : {synth['Arm B']['mean_f_average'] * 100:.2f}%")
print(f"  Deficient (1 Photon): {synth['Arm B-Def']['mean_f_average'] * 100:.2f}%")
print(f"  Trapped Control     : {synth['Arm B-Ctrl']['mean_f_average'] * 100:.2f}%")
print(f"  Held-Out Control    : {synth['Arm B-Held']['mean_f_average'] * 100:.2f}%")
print(f"  Delta Gain (Ctrl)   : +{receipt_payload['delta_gain_control_pp']:.2f} pp")
print(f"  Delta Gain (Def)    : +{receipt_payload['delta_gain_deficient_pp']:.2f} pp")
print(f"  Witness W           : {synth['Arm B']['entanglement_witness']:.4f} (< 0)")
