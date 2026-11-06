#!/usr/bin/env python3
"""
Zenodo Deposition & Publication Runner for OSIRIS v4.8.0

Sovereign Dual-Substrate Architecture Monograph and Evidence Package
Target DOI: 10.5281/zenodo.23300480
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
DIST_DIR = ROOT / "dist"
METADATA_PATH = ROOT / "zenodo_deposit_v4.8.0.json"
RECORD_OUTPUT = ROOT / "zenodo_record_v4.8.0.json"

API_BASE = "https://zenodo.org/api/deposit/depositions"

def get_token() -> str:
    token = os.environ.get("OSIRIS_ZENODO_TOKEN") or os.environ.get("ZENODO_TOKEN")
    if token:
        return token
    for p in [Path.home() / ".env", Path.home() / ".osiris" / "zenodo.env", ROOT / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(("OSIRIS_ZENODO_TOKEN=", "ZENODO_TOKEN=")):
                    tok = line.split("=", 1)[1].strip(" \"'")
                    if tok:
                        return tok
    return ""

def call(method: str, url: str, token: str, data: dict = None, raw: bytes = None, ctype: str = "application/json"):
    body = raw if raw is not None else (json.dumps(data).encode("utf-8") if data is not None else None)
    headers = {"Authorization": f"Bearer {token}"}
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode("utf-8")
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8")
        try:
            err_json = json.loads(txt)
        except Exception:
            err_json = {"raw": txt}
        return e.code, err_json
    except Exception as e:
        return 500, {"message": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Publish OSIRIS v4.8.0 to Zenodo")
    parser.add_argument("--dry-run", action="store_true", help="Validate files and metadata without uploading")
    parser.add_argument("--draft-only", action="store_true", help="Create deposition and upload files, but do not publish")
    parser.add_argument("--publish-id", type=str, default="", help="Publish an existing deposition draft ID")
    args = parser.parse_args()

    token = get_token()
    if not token:
        print("ERROR: Zenodo access token not found in environment or configuration files.")
        sys.exit(1)

    if args.publish_id:
        did = args.publish_id
        print(f"Publishing existing deposition draft ID: {did}...")
        st, pub = call("POST", f"{API_BASE}/{did}/actions/publish", token)
        if st not in (200, 201, 202):
            print(f"Publication did not return 20x (HTTP {st}): {pub}")
            sys.exit(1)

        doi = pub.get("doi")
        record_url = pub.get("links", {}).get("record_html", f"https://zenodo.org/record/{did}")
        print("\n==================================================")
        print("✓ SUCCESS: Zenodo Record Published!")
        print(f"  Record ID : {pub.get('id')}")
        print(f"  DOI       : {doi}")
        print(f"  URL       : {record_url}")
        print("==================================================")

        RECORD_OUTPUT.write_text(json.dumps(pub, indent=2), encoding="utf-8")
        print(f"Publication record saved to {RECORD_OUTPUT.name}")
        return

    if not METADATA_PATH.exists():
        print(f"ERROR: Metadata file not found: {METADATA_PATH}")
        sys.exit(1)

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta_doc = json.load(f)
    metadata = meta_doc.get("metadata", meta_doc)

    files_to_upload = [
        DOCS_DIR / "SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.pdf",
        DOCS_DIR / "SOVEREIGN_DUAL_SUBSTRATE_MONOGRAPH.md",
        DIST_DIR / "MANIFEST_SHA256_v4.8.0.txt",
        DIST_DIR / "osiris_v4.8.0_frontier_quantum_control_release.tar.gz",
        DIST_DIR / "osiris_v4.8.0_frontier_quantum_control_release.zip",
    ]

    print("==================================================")
    print("OSIRIS v4.8.0 ZENODO DEPOSITION RUNNER")
    print("==================================================")
    print(f"Title   : {metadata.get('title')}")
    print(f"Version : {metadata.get('version')}")
    print(f"Files to upload ({len(files_to_upload)}):")
    for f in files_to_upload:
        if not f.exists():
            print(f"ERROR: Required file missing: {f}")
            sys.exit(1)
        print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

    print("\nTesting Zenodo API connectivity...")
    st, res = call("GET", API_BASE, token)
    if st != 200:
        print(f"ERROR: Zenodo API connection failed (HTTP {st}): {res}")
        sys.exit(1)
    print("✓ Zenodo API connection verified (HTTP 200)")

    if args.dry_run:
        print("\n[DRY RUN]: Validation complete. No deposition created.")
        return

    print("\n1. Creating new deposition draft...")
    st, dep = call("POST", API_BASE, token, data={})
    if st not in (200, 201):
        print(f"ERROR: Failed to create deposition (HTTP {st}): {dep}")
        sys.exit(1)

    did = dep["id"]
    print(f"✓ Deposition created successfully: Draft ID = {did}")

    print("\n2. Setting deposition metadata...")
    st, meta_res = call("PUT", f"{API_BASE}/{did}", token, data={"metadata": metadata})
    if st not in (200, 201):
        print(f"ERROR: Failed to set metadata (HTTP {st}): {meta_res}")
        print("Cleaning up draft...")
        call("DELETE", f"{API_BASE}/{did}", token)
        sys.exit(1)
    print("✓ Metadata set successfully.")

    bucket = dep.get("links", {}).get("bucket")
    if not bucket:
        print("ERROR: Deposition response missing bucket link. Falling back to files API...")
        files_url = f"{API_BASE}/{did}/files"
        use_bucket = False
    else:
        print(f"✓ Target bucket located: {bucket}")
        use_bucket = True

    print("\n3. Uploading release files...")
    for f in files_to_upload:
        print(f"Uploading {f.name} ({f.stat().st_size:,} bytes)...")
        raw_bytes = f.read_bytes()
        if use_bucket:
            upload_url = f"{bucket}/{f.name}"
            st, up_res = call("PUT", upload_url, token, raw=raw_bytes, ctype="application/octet-stream")
        else:
            upload_url = f"{API_BASE}/{did}/files"
            print("ERROR: Bucket API required for uploads.")
            sys.exit(1)
        
        if st not in (200, 201):
            print(f"ERROR: File upload failed for {f.name} (HTTP {st}): {up_res}")
            print(f"Draft {did} preserved for manual inspection: https://zenodo.org/deposit/{did}")
            sys.exit(1)
        print(f"  ✓ Uploaded {f.name} (checksum: {up_res.get('checksum', 'ok')})")

    if args.draft_only:
        print("\n==================================================")
        print("✓ SUCCESS: Deposition Draft Created & Files Uploaded!")
        print(f"  Draft ID  : {did}")
        print(f"  Draft URL : https://zenodo.org/deposit/{did}")
        print("==================================================")
        return

    print("\n4. Publishing deposition (making record permanent)...")
    st, pub = call("POST", f"{API_BASE}/{did}/actions/publish", token)
    if st not in (200, 201, 202):
        print(f"Publication did not return 20x (HTTP {st}): {pub}")
        print(f"Deposition preserved as draft: https://zenodo.org/deposit/{did}")
        sys.exit(1)

    doi = pub.get("doi")
    record_url = pub.get("links", {}).get("record_html", f"https://zenodo.org/record/{did}")
    print("\n==================================================")
    print("✓ SUCCESS: Zenodo Record Published!")
    print(f"  Record ID : {pub.get('id')}")
    print(f"  DOI       : {doi}")
    print(f"  URL       : {record_url}")
    print("==================================================")

    RECORD_OUTPUT.write_text(json.dumps(pub, indent=2), encoding="utf-8")
    print(f"Publication record saved to {RECORD_OUTPUT.name}")

if __name__ == "__main__":
    main()
