#!/usr/bin/env python3
"""
publish_zenodo.py — Publish the OSIRIS Quantum Advantage Hardware Dataset
(from experiments/osiris_advantage_marrakesh) to Zenodo.

Adheres strictly to the adversarial epistemic protocol and links to previous Heron r2 records:
- 10.5281/zenodo.22870287 (Heron r2 E1/E2 dataset, Sept 2026)
- 10.5281/zenodo.22862567 (dnalang 0.1.0 compiler)
- 10.5281/zenodo.22855102 (Tetrahedral correction test dataset)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Load token from ~/.osiris/zenodo.env if not set in os.environ
if "ZENODO_TOKEN" not in os.environ:
    env_file = Path.home() / ".osiris" / "zenodo.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("ZENODO_TOKEN="):
                    os.environ["ZENODO_TOKEN"] = line.strip().split("=", 1)[1]

TOK = os.environ.get("ZENODO_TOKEN")
API = "https://zenodo.org/api/deposit/depositions"
BUNDLE = HERE / "osiris_quantum_advantage_marrakesh_2026.zip"
README = HERE / "README.md"


def call(method, url, data=None, raw=None, ctype="application/json"):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(
        url,
        method=method,
        data=body,
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": ctype}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        return e.code, (json.loads(txt) if txt else {"message": str(e)})


def md_to_html(md: str) -> str:
    out = []
    for line in md.splitlines():
        if line.startswith("# "):
            out.append(f"<h2>{line[2:]}</h2>")
        elif line.startswith("## "):
            out.append(f"<h3>{line[3:]}</h3>")
        elif line.startswith("- "):
            out.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            out.append(f"<p>{line}</p>")
    return "\n".join(out)


def create_bundle():
    print(f"Creating zip bundle: {BUNDLE}...")
    files_to_pack = [
        "pre_registration_manifest.json",
        "ledger.jsonl",
        "dau0q3qhcrkc73durtgg.counts.json",
        "dau0q3qhcrkc73durtgg.meta.json",
        "dau0q3qhcrkc73durtgg.analysis.json",
        "run_marrakesh_advantage.py",
        "README.md"
    ]
    with zipfile.ZipFile(BUNDLE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname in files_to_pack:
            p = HERE / fname
            if p.exists():
                zf.write(p, arcname=fname)
                print(f"  Added {fname} ({p.stat().st_size:,} bytes)")
            else:
                print(f"  WARNING: {fname} does not exist!")
    print(f"Bundle created: {BUNDLE.stat().st_size:,} bytes.")


METADATA = {
    "title": "Pre-registered Hardware Demonstration of OSIRIS Bipartite-Staggered Dynamical Decoupling on IBM Heron r2 (ibm_marrakesh): Coherence Retention (+30.5% over idle, +6.5% over textbook DD)",
    "upload_type": "dataset",
    "creators": [{"name": "Davis, Devin Phillip", "affiliation": "Agile Defense Systems LLC"}],
    "access_right": "open",
    "license": "cc-by-4.0",
    "keywords": [
        "IBM Quantum",
        "ibm_marrakesh",
        "Heron r2",
        "dynamical decoupling",
        "quantum advantage",
        "coherence preservation",
        "ZZ crosstalk suppression",
        "pre-registration",
        "OSIRIS",
        "write-ahead ledger"
    ],
    "related_identifiers": [
        {"identifier": "10.5281/zenodo.22870287", "relation": "continues", "resource_type": "dataset"},
        {"identifier": "10.5281/zenodo.22862567", "relation": "isSupplementTo", "resource_type": "software"},
        {"identifier": "10.5281/zenodo.22855102", "relation": "references", "resource_type": "dataset"},
    ],
    "version": "1.0.0",
    "notes": (
        "Pre-registration manifest (sha256 2d4c19a4a53301a1ac42459acd8b5b0d8cba0d588fa2523ed0994e5e1612d2f9) "
        "was hashed into the write-ahead ledger before submission to ibm_marrakesh (Job dau0q3qhcrkc73durtgg, 5 s QPU). "
        "No fitted constants; all metrics computed from included raw hardware counts."
    )
}


def main():
    parser = argparse.ArgumentParser(description="Publish OSIRIS Quantum Advantage run to Zenodo")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without uploading")
    args = parser.parse_args()

    if not TOK:
        print("ERROR: ZENODO_TOKEN not found!")
        sys.exit(1)

    create_bundle()

    metadata = dict(METADATA, description=md_to_html(README.read_text()))
    print("\nMetadata preview:")
    print(json.dumps({k: v for k, v in metadata.items() if k != "description"}, indent=2))

    if args.dry_run:
        print("\n--dry-run enabled: No deposition created.")
        return

    print("\nInitiating Zenodo deposition...")
    st, dep = call("POST", API, {})
    print(f"1. Create deposition -> HTTP {st}, ID: {dep.get('id')}")
    if st >= 400:
        print("Deposit creation failed:", dep)
        return

    did = dep["id"]

    st, u = call("PUT", f"{API}/{did}", {"metadata": metadata})
    print(f"2. Set metadata -> HTTP {st}, status: {'ok' if st < 400 else json.dumps(u)[:400]}")
    if st >= 400:
        call("DELETE", f"{API}/{did}")
        print("Draft deleted due to metadata error.")
        return

    bucket = dep["links"]["bucket"]
    print(f"3. Uploading bundle to bucket {bucket}...")
    st, f = call("PUT", f"{bucket}/{BUNDLE.name}", raw=BUNDLE.read_bytes(), ctype="application/octet-stream")
    print(f"   Upload status -> HTTP {st}, checksum: {f.get('checksum')}")
    if st >= 400:
        call("DELETE", f"{API}/{did}")
        print("Draft deleted due to upload error.")
        return

    print("4. Publishing deposition...")
    st, pub = call("POST", f"{API}/{did}/actions/publish")
    print(f"   Publish status -> HTTP {st}")
    if st < 400:
        doi = pub.get("doi")
        record_url = pub["links"]["record_html"]
        print("\n" + "=" * 80)
        print("ZENODO PUBLICATION SUCCESSFUL!")
        print(f"DOI: {doi}")
        print(f"Record URL: {record_url}")
        print("=" * 80)
        (HERE / "zenodo_record.json").write_text(json.dumps(pub, indent=2))
        print(f"Record metadata saved to {HERE / 'zenodo_record.json'}")
    else:
        print("Publishing error:", pub)


if __name__ == "__main__":
    main()
