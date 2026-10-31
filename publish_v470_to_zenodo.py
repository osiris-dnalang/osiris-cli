#!/usr/bin/env python3
"""Zenodo Deposition & Publication Runner for OSIRIS v4.7.0

Sovereign Dual-Substrate Architecture Monograph and Evidence Package
"""

import json
import os
from pathlib import Path
import sys
from osiris_zenodo_publisher import ZenodoPubisher

ROOT = Path(__file__).resolve().parent
TOKEN = os.getenv("OSIRIS_ZENODO_TOKEN") or os.getenv("ZENODO_TOKEN")
METADATA_PATH = ROOT / "zenodo_deposit_v4.7.0.json"
DIST_DIR = ROOT / "dist"

if not TOKEN:
  print("ERROR: OSIRIS_ZENODO_TOKEN or ZENODO_TOKEN environment variable not set.")
  print("Export it before running:")
  print('  export OSIRIS_ZENODO_TOKEN="your_token"')
  sys.exit(1)

if not METADATA_PATH.exists():
  print(f"ERROR: Metadata file not found at {METADATA_PATH}")
  sys.exit(1)

metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
files_to_upload = [
    ROOT / "docs" / "SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.md",
    DIST_DIR / "MANIFEST_SHA256.txt",
    DIST_DIR / "osiris_v4.7.0_sovereign_dual_substrate_release.tar.gz",
    DIST_DIR / "osiris_v4.7.0_sovereign_dual_substrate_release.zip",
]

for f in files_to_upload:
  if not f.exists():
    print(f"ERROR: Required release file missing: {f}")
    sys.exit(1)

print(f"=== OSIRIS v4.7.0 ZENODO DEPOSITION RUNNER ===")
print(f"Title   : {metadata['metadata']['title']}")
print(f"Creator : {metadata['metadata']['creators'][0]['name']}")
print(f"Files to upload ({len(files_to_upload)}):")
for f in files_to_upload:
  print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

publisher = ZenodoPubisher(TOKEN)
if not publisher.test_connection():
  print("ERROR: Could not connect to Zenodo API. Check token validity.")
  sys.exit(1)

print("\n1. Creating deposition...")
dep_id = publisher.create_deposition(metadata)
if not dep_id:
  print("ERROR: Failed to create deposition.")
  sys.exit(1)
print(f"Deposition created successfully: ID = {dep_id}")

print("\n2. Uploading release files...")
for f in files_to_upload:
  print(f"Uploading {f.name}...")
  ok = publisher.upload_file(dep_id, str(f))
  if not ok:
    print(f"WARNING: File upload failed for {f.name}")

print("\n3. Publishing deposition (making DOI permanent)...")
res = publisher.publish_deposition(dep_id)
if res:
  print("\n==================================================")
  print("✓ SUCCESS: Zenodo Record Published!")
  print(f"  Record ID : {res.get('id')}")
  print(f"  DOI       : {res.get('doi')}")
  print(f"  URL       : {res.get('url')}")
  print("==================================================")
else:
  print(
      f"Deposition created (Draft ID {dep_id}) but publication step did not"
      " return 202."
  )
  print(f"Check your drafts on Zenodo: https://zenodo.org/deposit/{dep_id}")
