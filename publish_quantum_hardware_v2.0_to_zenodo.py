#!/usr/bin/env python3
"""
publish_quantum_hardware_v2.0_to_zenodo.py
Zenodo Deposition & DOI Minting Orchestrator for OSIRIS Quantum Hardware Evidence Package v2.0.
Governed under SYS-021 Zero Self-Supplied Authorization.
"""

import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "dist"
METADATA_PATH = REPO_ROOT / "zenodo_deposit_quantum_hardware_v2.0.json"
RECEIPT_PATH = REPO_ROOT / "zenodo_quantum_hardware_v2.0_receipt.json"
EVIDENCE_DB = REPO_ROOT.parent / "evidence_ledger.db"
if not EVIDENCE_DB.exists():
    EVIDENCE_DB = Path(r"C:\Users\Ron\evidence_ledger.db")

ZENODO_API_URL = "https://zenodo.org/api/deposit/depositions"

ENV_PATH = Path(r"\\wsl.localhost\Ubuntu\home\enki\.osiris\zenodo.env")
if not ENV_PATH.exists():
    ENV_PATH = Path("/home/enki/.osiris/zenodo.env")


def load_zenodo_token() -> str:
    token = None
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in ("ZENODO_TOKEN", "OSIRIS_ZENODO_TOKEN"):
                    token = v.strip().strip('"').strip("'")
    if not token:
        token = os.getenv("OSIRIS_ZENODO_TOKEN") or os.getenv("ZENODO_TOKEN")
    return token


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=" * 80)
    print("OSIRIS QUANTUM HARDWARE EVIDENCE PACKAGE v2.0 — ZENODO DEPOSITION")
    print("=" * 80)

    token = load_zenodo_token()
    if not token:
        print("ERROR: Zenodo access token not found in environment or zenodo.env!")
        sys.exit(1)

    if not METADATA_PATH.exists():
        print(f"ERROR: Metadata not found at {METADATA_PATH}")
        sys.exit(1)

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata_payload = json.load(f)

    files_to_upload = [
        DIST_DIR / "osiris_quantum_hardware_v2.0_evidence_package.zip",
        DIST_DIR / "osiris_quantum_hardware_v2.0_evidence_package.tar.gz",
        DIST_DIR / "osiris_quantum_hardware_v2.0_evidence_package_SHA256SUMS.txt",
    ]

    for f in files_to_upload:
        if not f.exists():
            print(f"ERROR: Missing upload file: {f}")
            sys.exit(1)

    print(f"Title: {metadata_payload['metadata']['title']}")
    print("Files ready for upload:")
    for f in files_to_upload:
        print(f"  - {f.name} ({f.stat().st_size:,} bytes | SHA-256: {sha256_file(f)[:16]}...)")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Create Deposition
    print("\n[1/4] Creating draft deposition on Zenodo...")
    req = urllib.request.Request(
        ZENODO_API_URL,
        data=json.dumps(metadata_payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            dep_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"ERROR creating deposition: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)

    dep_id = dep_data["id"]
    bucket_url = dep_data["links"]["bucket"]
    print(f"Deposition created: ID {dep_id}")
    print(f"Bucket URL: {bucket_url}")

    # 2. Upload Files
    print("\n[2/4] Uploading evidence files to bucket...")
    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }
    for f in files_to_upload:
        print(f"  Uploading {f.name} ({f.stat().st_size:,} bytes)...")
        up_url = f"{bucket_url}/{f.name}"
        with open(f, "rb") as file_bytes:
            req_up = urllib.request.Request(
                up_url,
                data=file_bytes.read(),
                headers=upload_headers,
                method="PUT"
            )
            with urllib.request.urlopen(req_up) as up_resp:
                if up_resp.status not in (200, 201):
                    print(f"Upload failed for {f.name}: {up_resp.status}")
                    sys.exit(1)
        print(f"  Uploaded: {f.name}")

    # 3. Publish Deposition
    print("\n[3/4] Publishing deposition to mint permanent DOI...")
    pub_url = f"{ZENODO_API_URL}/{dep_id}/actions/publish"
    req_pub = urllib.request.Request(pub_url, data=b"", headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req_pub) as pub_resp:
            pub_data = json.loads(pub_resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"ERROR publishing deposition: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)

    doi = pub_data.get("doi", f"10.5281/zenodo.{dep_id}")
    record_url = pub_data.get("links", {}).get("record_html", f"https://zenodo.org/record/{dep_id}")
    print(f"Publication Successful!")
    print(f"Assigned DOI : {doi}")
    print(f"Record URL   : {record_url}")

    # 4. Save Publication Receipt & Anchor Ledger Block #49
    receipt_data = {
        "event": "SYS021_ZENODO_PUBLICATION_QUANTUM_HARDWARE_V2",
        "deposition_id": dep_id,
        "doi": doi,
        "record_url": record_url,
        "timestamp": time.time(),
        "files_uploaded": [
            {"filename": f.name, "bytes": f.stat().st_size, "sha256": sha256_file(f)}
            for f in files_to_upload
        ],
        "metadata": metadata_payload["metadata"]
    }

    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(receipt_data, f, indent=2)

    print(f"Receipt written to: {RECEIPT_PATH}")

    # Ledger anchor
    if EVIDENCE_DB.exists():
        conn = sqlite3.connect(EVIDENCE_DB)
        cur = conn.cursor()
        cur.execute("SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1")
        last_seq, prev_hash = cur.fetchone()
        next_seq = last_seq + 1
        now_ts = time.time()
        evt_type = "SYS021_ZENODO_PUBLICATION_QUANTUM_HARDWARE_V2"
        operator = "Devin Phillip Davis / Enki"
        payload_h = sha256_file(RECEIPT_PATH)
        schema_h = hashlib.sha256("OSIRIS_ZENODO_PUBLICATION_V2".encode("utf-8")).hexdigest()
        nonce = 49000

        raw_block_str = f"{prev_hash}:{next_seq}:{evt_type}:{operator}:{payload_h}:{schema_h}:{nonce}:{now_ts}"
        block_h = hashlib.sha256(raw_block_str.encode("utf-8")).hexdigest()

        cur.execute("""
            INSERT INTO ledger_blocks (
                sequence_index, prev_block_hash, block_hash, timestamp,
                event_type, operator_id, payload_sha256, operation_schema_sha256,
                nonce, raw_grant_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            next_seq, prev_hash, block_h, now_ts,
            evt_type, operator, payload_h, schema_h,
            nonce, json.dumps(receipt_data)
        ))
        conn.commit()
        conn.close()
        print(f"Anchored L0 Ledger Block #{next_seq}: {block_h}")


if __name__ == "__main__":
    main()
