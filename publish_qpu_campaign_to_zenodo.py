#!/usr/bin/env python3
"""
publish_qpu_campaign_to_zenodo.py
Publishes the OSIRIS Physical QPU Validation Campaign to Zenodo via API.
"""
import json
import os
import sys
from pathlib import Path
from osiris_zenodo_publisher import ZenodoPubisher

ROOT = Path("/mnt/c/Users/Ron/osiris-cli")
EXP_DIR = ROOT / "experiments" / "qpu_stag_xy8_v2"
DIST_DIR = ROOT / "dist"
METADATA_PATH = ROOT / "zenodo_deposit_qpu_validation_v1.0.json"
ENV_PATH = Path("/home/enki/.osiris/zenodo.env")

# Load token
token = None
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            k, v = line.split('=', 1)
            if k.strip() in ('ZENODO_TOKEN', 'OSIRIS_ZENODO_TOKEN'):
                token = v.strip().strip('"').strip("'")

if not token:
    token = os.getenv("OSIRIS_ZENODO_TOKEN") or os.getenv("ZENODO_TOKEN")

if not token:
    print("ERROR: Zenodo access token not found!")
    sys.exit(1)

if not METADATA_PATH.exists():
    print(f"ERROR: Metadata not found at {METADATA_PATH}")
    sys.exit(1)

metadata = json.loads(METADATA_PATH.read_text())

files_to_upload = [
    DIST_DIR / "osiris_qpu_stag_xy8_v1.0_evidence_package.tar.gz",
    DIST_DIR / "osiris_qpu_stag_xy8_v1.0_evidence_package.zip",
    DIST_DIR / "SHA256SUMS.txt",
    EXP_DIR / "OSIRIS_QPU_STAG_XY8_VALIDATION.tex",
    EXP_DIR / "EXPERIMENT_REPORT.md",
    EXP_DIR / "final_synthesis.json",
    EXP_DIR / "figures" / "fig1_pulse_schedules.png",
    EXP_DIR / "figures" / "fig2_7edge_correlation_matched.png",
    EXP_DIR / "figures" / "fig3_stagger_offset_sweep.png",
    EXP_DIR / "figures" / "fig4_bootstrap_synthesis_forest.png",
]

for f in files_to_upload:
    if not f.exists():
        print(f"ERROR: Missing upload file: {f}")
        sys.exit(1)

print("=" * 80)
print("OSIRIS PHYSICAL QPU VALIDATION CAMPAIGN — ZENODO PUBLICATION")
print("=" * 80)
print(f"Title   : {metadata['metadata']['title']}")
print(f"Creator : {metadata['metadata']['creators'][0]['name']}")
print(f"Files to upload ({len(files_to_upload)} files):")
for f in files_to_upload:
    print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

publisher = ZenodoPubisher(token)
if not publisher.test_connection():
    print("ERROR: Cannot connect to Zenodo API!")
    sys.exit(1)

print("\n1. Creating Zenodo deposition...")
dep_id = publisher.create_deposition(metadata)
if not dep_id:
    print("ERROR: Failed to create deposition!")
    sys.exit(1)
print(f"✓ Deposition created successfully: ID = {dep_id}")

print("\n2. Uploading publication files...")
for f in files_to_upload:
    print(f"  Uploading {f.name} ({f.stat().st_size:,} bytes)...")
    ok = publisher.upload_file(dep_id, str(f))
    if not ok:
        print(f"  WARNING: Upload returned non-success for {f.name}")
    else:
        print(f"  ✓ {f.name} uploaded.")

print("\n3. Publishing deposition (making DOI permanent)...")
res = publisher.publish_deposition(dep_id)
if res:
    print("\n" + "=" * 80)
    print("✓ SUCCESS: ZENODO RECORD PUBLISHED PERMANENTLY!")
    print(f"  Record ID : {res.get('id')}")
    print(f"  DOI       : {res.get('doi')}")
    print(f"  URL       : {res.get('url', f'https://zenodo.org/record/{dep_id}')}")
    print("=" * 80)
    
    receipt_data = {
        "deposition_id": dep_id,
        "record_id": res.get("id"),
        "doi": res.get("doi"),
        "url": res.get("url", f"https://zenodo.org/record/{dep_id}"),
        "title": metadata["metadata"]["title"],
        "files_uploaded": [f.name for f in files_to_upload],
        "status": "published"
    }
    (ROOT / "zenodo_qpu_publication_receipt.json").write_text(json.dumps(receipt_data, indent=2))
    (EXP_DIR / "zenodo_qpu_publication_receipt.json").write_text(json.dumps(receipt_data, indent=2))
else:
    print(f"\nDeposition ID {dep_id} created with files uploaded as draft.")
