#!/usr/bin/env python3
"""
OSIRIS v5.3.2 Publication & Deposition Orchestrator
===================================================
1. Bundles v5.3.2 peer-audited research evidence package into .zip and .tar.gz with SHA256SUMS.txt.
2. Creates Zenodo deposition and uploads evidence files.
3. Publishes Zenodo deposition to mint permanent DOI.
4. Records cryptographic grant to evidence_ledger.db (Block Sequence #27) under SYS-021.
5. Saves publication receipt and creates GitHub release tag.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path
import urllib.request
import urllib.error

REPO_ROOT = Path(r"C:\Users\Ron")
CLI_ROOT = REPO_ROOT / "osiris-cli"
DIST_DIR = CLI_ROOT / "dist"
EVIDENCE_DB = REPO_ROOT / "evidence_ledger.db"

ENV_PATH = Path(r"\\wsl.localhost\Ubuntu\home\enki\.osiris\zenodo.env")
if not ENV_PATH.exists():
    ENV_PATH = Path("/home/enki/.osiris/zenodo.env")

METADATA_PATH = CLI_ROOT / "zenodo_deposit_v5.3.2.json"
RELEASE_NOTES_PATH = CLI_ROOT / "github_release_notes_v5.3.2.md"

BUNDLE_NAME = "osiris_research_evidence_v5.3.2"
BUNDLE_DIR = DIST_DIR / BUNDLE_NAME
ZIP_PATH = DIST_DIR / f"{BUNDLE_NAME}.zip"
TAR_PATH = DIST_DIR / f"{BUNDLE_NAME}.tar.gz"
SHA_SUMS_PATH = BUNDLE_DIR / "SHA256SUMS.txt"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


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
    if not token:
        raise RuntimeError("Zenodo token not found in environment or zenodo.env")
    return token


def zenodo_api_request(url: str, method: str = "GET", data: bytes = None, headers: dict = None) -> dict:
    req_headers = headers or {}
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"HTTPError {e.code} on {method} {url}: {err_body}")
        raise


def upload_zenodo_file(bucket_url: str, file_path: Path, token: str):
    url = f"{bucket_url}/{file_path.name}"
    content = file_path.read_bytes()
    req = urllib.request.Request(
        url,
        data=content,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_evidence_bundle():
    print("\n--- Building OSIRIS v5.3.2 Evidence Bundle ---")
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Authority directory
    auth_dir = BUNDLE_DIR / "authority"
    auth_dir.mkdir(exist_ok=True)
    if EVIDENCE_DB.exists():
        shutil.copy2(EVIDENCE_DB, auth_dir / "evidence_ledger.db")

    # 2. Manual & Guides
    desktop_md = REPO_ROOT / "Desktop" / "OSIRIS_100_ADVANCED_BASH_COMMANDS.md"
    desktop_pdf = REPO_ROOT / "Desktop" / "OSIRIS_100_ADVANCED_BASH_COMMANDS.pdf"
    if desktop_md.exists():
        shutil.copy2(desktop_md, BUNDLE_DIR / desktop_md.name)
    if desktop_pdf.exists():
        shutil.copy2(desktop_pdf, BUNDLE_DIR / desktop_pdf.name)

    # 3. DNA-Lang MAXQ & W2 assertions
    test_w2 = REPO_ROOT / "dnalang-core" / "tests" / "test_maxq_w2_assertions.py"
    if test_w2.exists():
        shutil.copy2(test_w2, BUNDLE_DIR / test_w2.name)

    # 4. Release notes & metadata
    shutil.copy2(RELEASE_NOTES_PATH, BUNDLE_DIR / RELEASE_NOTES_PATH.name)
    shutil.copy2(METADATA_PATH, BUNDLE_DIR / METADATA_PATH.name)

    # 5. OSIRIS 6.0 Roadmap
    roadmap_path = CLI_ROOT / "docs" / "PATHWAY_TO_OSIRIS_6.0.md"
    if roadmap_path.exists():
        shutil.copy2(roadmap_path, BUNDLE_DIR / roadmap_path.name)

    # 6. Hayden-Preskill HP-001 Benchmark
    hp001_src = CLI_ROOT / "experiments" / "hp001"
    hp001_dst = BUNDLE_DIR / "hp001"
    if hp001_src.exists():
        hp001_dst.mkdir(exist_ok=True)
        for f in hp001_src.glob("*.py"):
            shutil.copy2(f, hp001_dst / f.name)

    # Compute SHA256SUMS.txt
    print("Computing SHA256SUMS.txt for all files in bundle...")
    manifest_lines = []
    for f in sorted(BUNDLE_DIR.rglob("*")):
        if f.is_file() and f.name != "SHA256SUMS.txt":
            rel = f.relative_to(BUNDLE_DIR).as_posix()
            h = sha256_file(f)
            manifest_lines.append(f"{h}  {rel}")
    SHA_SUMS_PATH.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"  Indexed {len(manifest_lines)} files in SHA256SUMS.txt")

    # Create ZIP archive
    print(f"Creating {ZIP_PATH.name}...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(BUNDLE_DIR.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=f"{BUNDLE_NAME}/{f.relative_to(BUNDLE_DIR).as_posix()}")

    # Create TAR.GZ archive
    print(f"Creating {TAR_PATH.name}...")
    with tarfile.open(TAR_PATH, "w:gz") as tf:
        tf.add(BUNDLE_DIR, arcname=BUNDLE_NAME)

    print(f"  ZIP: {ZIP_PATH.stat().st_size:,} bytes (SHA-256: {sha256_file(ZIP_PATH)})")
    print(f"  TAR.GZ: {TAR_PATH.stat().st_size:,} bytes (SHA-256: {sha256_file(TAR_PATH)})")
    return sha256_file(ZIP_PATH)


def publish():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 80)
    print("OSIRIS v5.3.2: ZENODO PUBLICATION & GITHUB RELEASE ORCHESTRATION")
    print("=" * 80)

    # Step 0: Build bundle
    payload_hash = build_evidence_bundle()

    token = load_zenodo_token()
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    files_to_upload = [
        ZIP_PATH,
        TAR_PATH,
        SHA_SUMS_PATH,
        RELEASE_NOTES_PATH,
        REPO_ROOT / "Desktop" / "OSIRIS_100_ADVANCED_BASH_COMMANDS.pdf",
        CLI_ROOT / "docs" / "PATHWAY_TO_OSIRIS_6.0.md",
    ]

    for f in files_to_upload:
        if not f.exists():
            raise FileNotFoundError(f"Missing required upload file: {f}")
        print(f"  [FOUND] {f.name} ({f.stat().st_size:,} bytes, SHA-256: {sha256_file(f)[:16]}...)")

    # Step 1: Create New Deposition Draft on Zenodo
    print("\n1. Creating Zenodo Deposition for v5.3.2...")
    url = "https://zenodo.org/api/deposit/depositions"
    dep_res = zenodo_api_request(
        url,
        method="POST",
        data=json.dumps(metadata).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    dep_id = dep_res["id"]
    bucket_url = dep_res["links"]["bucket"]
    print(f"  [PASS] Created Deposition ID: {dep_id}")
    print(f"  [PASS] Bucket URL: {bucket_url}")

    # Step 2: Upload Files
    print(f"\n2. Uploading {len(files_to_upload)} files to Zenodo bucket...")
    for f in files_to_upload:
        print(f"  Uploading {f.name} ({f.stat().st_size / 1024:.1f} KB)...")
        upload_zenodo_file(bucket_url, f, token)
        print(f"  [PASS] {f.name} uploaded.")

    # Step 3: Publish Deposition
    print("\n3. Publishing Deposition (Minting Permanent DOI)...")
    pub_url = f"https://zenodo.org/api/deposit/depositions/{dep_id}/actions/publish"
    pub_res = zenodo_api_request(
        pub_url,
        method="POST",
        headers={"Authorization": f"Bearer {token}"},
    )
    permanent_doi = pub_res.get("doi", f"10.5281/zenodo.{dep_id}")
    record_url = pub_res.get("links", {}).get("record_html", f"https://zenodo.org/record/{dep_id}")
    print(f"  [SUCCESS] Permanent DOI Minted: {permanent_doi}")
    print(f"  [SUCCESS] Record URL: {record_url}")

    receipt_data = {
        "deposition_id": dep_id,
        "record_id": pub_res.get("id", dep_id),
        "doi": permanent_doi,
        "url": record_url,
        "title": metadata["metadata"]["title"],
        "version": "v5.3.2",
        "files_uploaded": [f.name for f in files_to_upload],
        "file_hashes": {f.name: sha256_file(f) for f in files_to_upload},
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "published",
    }
    receipt_path = CLI_ROOT / "zenodo_v532_publication_receipt.json"
    receipt_path.write_text(json.dumps(receipt_data, indent=2))
    print(f"  Saved receipt to: {receipt_path.name}")

    # Step 4: Record Cryptographic Grant in evidence_ledger.db (Block #27)
    print("\n4. Recording Cryptographic Release Receipt in evidence_ledger.db...")
    conn = sqlite3.connect(str(EVIDENCE_DB))
    cur = conn.cursor()
    prev_seq, prev_hash = cur.execute(
        "SELECT sequence_index, block_hash FROM ledger_blocks ORDER BY sequence_index DESC LIMIT 1"
    ).fetchone()
    next_seq = prev_seq + 1
    ts = time.time()
    nonce = f"OSIRIS-V532-RELEASE-{int(ts * 1000)}"

    op_schema = {
        "event": "SYS021_V532_ZENODO_AND_GITHUB_RELEASE",
        "tag": "v5.3.2",
        "zenodo_doi": permanent_doi,
        "zenodo_deposition_id": dep_id,
        "evidence_zip_sha256": sha256_file(ZIP_PATH),
        "evidence_tar_sha256": sha256_file(TAR_PATH),
        "file_count": len(files_to_upload),
    }
    op_schema_json = json.dumps(op_schema, sort_keys=True)
    op_schema_sha256 = hashlib.sha256(op_schema_json.encode("utf-8")).hexdigest()

    raw_grant = {
        "sequence_index": next_seq,
        "prev_block_hash": prev_hash,
        "timestamp": ts,
        "event_type": "SYS021_V532_ZENODO_AND_GITHUB_RELEASE_GRANT",
        "operator_id": "Devin Phillip Davis / Enki",
        "payload_sha256": sha256_file(ZIP_PATH),
        "operation_schema_sha256": op_schema_sha256,
        "operation_schema": op_schema,
        "nonce": nonce,
    }
    raw_grant_json = json.dumps(raw_grant, sort_keys=True)
    block_hash = hashlib.sha256(raw_grant_json.encode("utf-8")).hexdigest()

    cur.execute(
        """
        INSERT INTO ledger_blocks (
            prev_block_hash, block_hash, timestamp, event_type,
            operator_id, payload_sha256, operation_schema_sha256,
            nonce, raw_grant_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prev_hash,
            block_hash,
            ts,
            "SYS021_V532_ZENODO_AND_GITHUB_RELEASE_GRANT",
            "Devin Phillip Davis / Enki",
            sha256_file(ZIP_PATH),
            op_schema_sha256,
            nonce,
            raw_grant_json,
        ),
    )
    conn.commit()
    conn.close()
    print(f"  [PASS] Committed Sequence #{next_seq} to evidence_ledger.db (Block Hash: {block_hash[:16]}...)")

    # Step 5: Create GitHub Release via gh CLI
    print("\n5. Creating GitHub Release via gh CLI...")
    pdf_path = REPO_ROOT / "Desktop" / "OSIRIS_100_ADVANCED_BASH_COMMANDS.pdf"
    roadmap_doc = CLI_ROOT / "docs" / "PATHWAY_TO_OSIRIS_6.0.md"
    
    # Check if native gh is available; else use WSL /snap/bin/gh
    has_native_gh = shutil.which("gh") is not None
    if has_native_gh:
        cmd = [
            "gh", "release", "create", "v5.3.2",
            str(ZIP_PATH),
            str(TAR_PATH),
            str(pdf_path),
            str(roadmap_doc),
            "--title", "OSIRIS v5.3.2: C-SIMD Parity, MAXQ Subgraph Routing, and Hayden-Preskill Benchmark",
            "--notes-file", str(RELEASE_NOTES_PATH),
            "--repo", "osiris-dnalang/osiris-cli"
        ]
    else:
        # Translate paths to WSL /mnt/c/...
        def to_wsl(p: Path) -> str:
            s = str(p.resolve()).replace("\\", "/")
            if s[1:3] == ":/":
                return f"/mnt/{s[0].lower()}/{s[3:]}"
            return s

        cmd = [
            "wsl.exe", "-d", "Ubuntu", "-e", "/snap/bin/gh", "release", "create", "v5.3.2",
            to_wsl(ZIP_PATH),
            to_wsl(TAR_PATH),
            to_wsl(pdf_path),
            to_wsl(roadmap_doc),
            "--title", "OSIRIS v5.3.2: C-SIMD Parity, MAXQ Subgraph Routing, and Hayden-Preskill Benchmark",
            "--notes-file", to_wsl(RELEASE_NOTES_PATH),
            "--repo", "osiris-dnalang/osiris-cli"
        ]

    try:
        subprocess.run(cmd, check=True)
        print("  [PASS] GitHub Release created successfully.")
    except Exception as e:
        print(f"  [WARN] gh release create returned: {e}")

    return {
        "dep_id": dep_id,
        "doi": permanent_doi,
        "url": record_url,
        "block_hash": block_hash,
        "seq": next_seq,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--build-only":
        build_evidence_bundle()
    else:
        publish()
