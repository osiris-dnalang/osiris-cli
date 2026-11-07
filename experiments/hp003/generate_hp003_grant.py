#!/usr/bin/env python3
"""
generate_hp003_grant.py — Generates SYS-021 Dispatch Authority Grant for OSIRIS-HP-003
Anchors the 8-qubit multi-qubit Hayden-Preskill benchmark into evidence_ledger.db.
"""

import json
import hashlib
import time
import sqlite3
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

from osiris_cli.node_beta_governance import NodeBetaGovernor

payload_file = EXPERIMENT_DIR / "stage_hp003_harness.py"
payload_h = hashlib.sha256(payload_file.read_bytes()).hexdigest()
op_schema_name = "OSIRIS_HP003_MULTIQUBIT_CAPACITY_CERTIFICATION_V1"
schema_h = hashlib.sha256(op_schema_name.encode("utf-8")).hexdigest()

# 1. Issue Node Beta Ed25519 Authority Permit
gov = NodeBetaGovernor()
permit = gov.issue_grant(target_digest=payload_h, scope=op_schema_name, ttl_seconds=86400)

now_ts = time.time()
nonce = f"OSIRIS-HP003-DISPATCH-{int(now_ts * 1000)}"

# 2. Query Ledger Tip
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1")
last_seq, prev_hash = cur.fetchone()
next_seq = last_seq + 1

grant_id = f"GRANT-SYS021-HP003-{hashlib.sha256(nonce.encode()).hexdigest()[:12].upper()}"

grant_data = {
    "grant_id": grant_id,
    "status": "ACTIVE_AUTHORIZED_GRANT",
    "operator_id": "Devin Phillip Davis / Enki",
    "operation": op_schema_name,
    "timestamp": now_ts,
    "payload_file": "experiments/hp003/stage_hp003_harness.py",
    "payload_sha256": payload_h,
    "operation_schema": {
        "protocol": "OSIRIS-HP-003",
        "target_hardware": "ibm_fez",
        "qubit_registers": {
            "R1": 0, "R2": 1, "M1": 2, "M2": 3,
            "B1": 4, "B2": 5, "E1": 6, "E2": 7
        },
        "total_circuits": 45,
        "shots_per_circuit": 1024,
        "total_physical_shots": 46080,
        "arms": [
            "Arm A: Full-Access Inverse Control",
            "Arm B: Restricted Hayden-Preskill Recovery (Full 2 Photons)",
            "Arm B-Def: Sub-Capacity Quantum Threshold (Single Photon)",
            "Arm B-Ctrl: No-Early-Entanglement Separable Control",
            "Arm B-Held: Held-Out Scrambler Specificity Gate"
        ],
        "tomography_bases": ["XX", "YY", "ZZ"],
        "randomized_blocks": 3
    },
    "operation_schema_sha256": schema_h,
    "authority_permit": {
        "issuer": permit.issuer,
        "scope": permit.scope,
        "target_digest": permit.target_digest,
        "nonce": permit.nonce,
        "issued_at_utc": permit.issued_at_utc,
        "expires_at_utc": permit.expires_at_utc,
        "policy_version": permit.policy_version,
        "signature": permit.signature
    },
    "signature_receipt": {
        "sequence_index": next_seq,
        "prev_block_hash": prev_hash,
        "timestamp": now_ts,
        "nonce": nonce
    }
}

# 3. Compute Block Hash
raw_block_str = f"{prev_hash}:{next_seq}:SYS021_HP003_DISPATCH_GRANT:{grant_data['operator_id']}:{payload_h}:{schema_h}:{nonce}:{now_ts}"
block_h = hashlib.sha256(raw_block_str.encode("utf-8")).hexdigest()
grant_data["signature_receipt"]["block_hash"] = block_h

# Save grant JSON
grant_path = EXPERIMENT_DIR / "sys021_hp003_grant.json"
grant_path.write_text(json.dumps(grant_data, indent=2), encoding="utf-8")
print(f"SYS-021 Grant saved to: {grant_path.name}")
print(f"  Grant ID         : {grant_id}")
print(f"  Payload SHA-256  : {payload_h}")
print(f"  Ledger Block     : Sequence #{next_seq}")
print(f"  Prev Block Hash  : {prev_hash}")
print(f"  Block Hash       : {block_h}")

# 4. Commit Block to SQLite Ledger
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
    "SYS021_HP003_DISPATCH_GRANT",
    grant_data["operator_id"],
    payload_h,
    schema_h,
    nonce,
    json.dumps(grant_data)
))
conn.commit()
conn.close()
print(f"\n[COMMITTED] Block #{next_seq} permanently anchored to evidence_ledger.db.")
