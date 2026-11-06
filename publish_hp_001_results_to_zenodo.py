#!/usr/bin/env python3
"""
publish_hp_001_results_to_zenodo.py
Zenodo Deposition & Publication Runner for OSIRIS-HP-001 Stage 1 Empirical Dataset
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METADATA_PATH = ROOT / "zenodo_deposit_hp_001_results.json"
RECORD_OUTPUT = ROOT / "zenodo_record_hp_001_results.json"
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
        with urllib.request.urlopen(req, timeout=180) as r:
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

def upload_file(bucket_url: str, filepath: Path, token: str):
    fname = filepath.name
    url = f"{bucket_url}/{fname}"
    content = filepath.read_bytes()
    print(f"  Uploading {fname} ({len(content):,} bytes)...")
    st, res = call("PUT", url, token, raw=content, ctype="application/octet-stream")
    if st not in (200, 201):
        print(f"  FAILED to upload {fname} (HTTP {st}): {res}")
        return False
    print(f"  ✓ {fname} uploaded successfully.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Publish OSIRIS-HP-001 Stage 1 Results to Zenodo")
    parser.add_argument("--dry-run", action="store_true", help="Validate without uploading")
    args = parser.parse_args()

    token = get_token()
    if not token:
        print("ERROR: Zenodo token not found.")
        sys.exit(1)

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta_doc = json.load(f)

    files_to_upload = [
        ROOT / "docs" / "research" / "OSIRIS_HP_001_FAKEMARRAKESH_REPORT.pdf",
        ROOT / "docs" / "research" / "OSIRIS_HP_001_FAKEMARRAKESH_REPORT.md",
        ROOT / "experiments" / "experiment_hp" / "results_hp_001_fakemarrakesh.json",
        ROOT / "experiments" / "experiment_hp" / "run_fake_marrakesh_hp_benchmark.py",
        ROOT / "experiments" / "experiment_hp" / "hp_001_fakemarrakesh_violin_comparison.png",
        ROOT / "experiments" / "experiment_hp" / "hp_001_fakemarrakesh_page_transition.png",
        ROOT / "experiments" / "experiment_hp" / "hp_001_fakemarrakesh_w1_vs_fidelity.png",
        ROOT / "experiments" / "experiment_hp" / "hp_001_fakemarrakesh_noise_scaling.png"
    ]

    print("=" * 60)
    print("ZENODO STAGE 1 BENCHMARK DATASET DEPOSIT RUNNER")
    print("=" * 60)
    print(f"Title: {meta_doc['metadata']['title']}")
    for f in files_to_upload:
        if not f.exists():
            print(f"ERROR: Missing file {f}")
            sys.exit(1)
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        print(f"  - {f.name} ({f.stat().st_size:,} bytes, SHA-256: {sha[:16]}...)")

    if args.dry_run:
        print("\nDry-run complete. Exiting.")
        return

    print("\n1. Creating empty deposition on Zenodo...")
    st, dep = call("POST", API_BASE, token, data={})
    if st not in (200, 201):
        print(f"Failed to create deposition (HTTP {st}): {dep}")
        sys.exit(1)

    dep_id = dep["id"]
    bucket_url = dep["links"]["bucket"]
    print(f"✓ Deposition created! ID: {dep_id}")

    print("\n2. Uploading files to deposition bucket...")
    for f in files_to_upload:
        ok = upload_file(bucket_url, f, token)
        if not ok:
            print("Aborting.")
            sys.exit(1)

    print("\n3. Setting deposition metadata...")
    st, meta_res = call("PUT", f"{API_BASE}/{dep_id}", token, data=meta_doc)
    if st not in (200, 201):
        print(f"Failed to set metadata (HTTP {st}): {meta_res}")
        sys.exit(1)
    print("✓ Metadata set successfully.")

    print(f"\n4. Publishing deposition ID {dep_id} to Zenodo...")
    st, pub = call("POST", f"{API_BASE}/{dep_id}/actions/publish", token)
    if st not in (200, 201, 202):
        print(f"Publication failed (HTTP {st}): {pub}")
        sys.exit(1)

    doi = pub.get("doi")
    record_url = pub.get("links", {}).get("record_html", f"https://zenodo.org/record/{dep_id}")
    print("\n" + "=" * 60)
    print("✓ SUCCESS: OSIRIS-HP-001 Stage 1 Results Published to Zenodo!")
    print(f"  Record ID : {dep_id}")
    print(f"  DOI       : {doi}")
    print(f"  URL       : {record_url}")
    print("=" * 60)

    RECORD_OUTPUT.write_text(json.dumps(pub, indent=2), encoding="utf-8")
    # Also write to artifact dir
    artifact_copy = Path(r"/mnt/c/Users/Ron/.gemini/antigravity-cli/brain/7c32c8e2-435d-4e26-8461-c863e8b48925/zenodo_record_hp_001_results.json")
    artifact_copy.write_text(json.dumps(pub, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
