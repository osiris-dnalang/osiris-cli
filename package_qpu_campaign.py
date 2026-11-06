#!/usr/bin/env python3
"""
package_qpu_campaign.py
Bundles the OSIRIS Physical QPU Validation Campaign into distributable release archives with SHA-256 manifests.
"""
import hashlib
import json
import os
import shutil
import tarfile
import zipfile
from pathlib import Path

ROOT = Path("/mnt/c/Users/Ron/osiris-cli")
EXP_DIR = ROOT / "experiments" / "qpu_stag_xy8_v2"
DIST_DIR = ROOT / "dist"
DIST_DIR.mkdir(exist_ok=True, parents=True)

PACKAGE_NAME = "osiris_qpu_stag_xy8_v1.0_evidence_package"
STAGING_DIR = ROOT / PACKAGE_NAME
if STAGING_DIR.exists():
    shutil.rmtree(STAGING_DIR)
STAGING_DIR.mkdir(parents=True)

# Files to include in the bundle:
items_to_copy = [
    # Core Reports & Manuscript
    (EXP_DIR / "OSIRIS_QPU_STAG_XY8_VALIDATION.tex", "OSIRIS_QPU_STAG_XY8_VALIDATION.tex"),
    (EXP_DIR / "EXPERIMENT_REPORT.md", "EXPERIMENT_REPORT.md"),
    (EXP_DIR / "final_synthesis.json", "final_synthesis.json"),
    
    # Audit & Schedules
    (EXP_DIR / "historical_audit_dblr6lhkbkrc73co9h30.json", "historical_audit_dblr6lhkbkrc73co9h30.json"),
    (EXP_DIR / "schedule_audit.json", "schedule_audit.json"),
    (EXP_DIR / "backend_snapshot.json", "backend_snapshot.json"),
    (EXP_DIR / "experiment_config.json", "experiment_config.json"),
    (EXP_DIR / "submitted_circuits.qpy", "submitted_circuits.qpy"),
    
    # Receipts
    (EXP_DIR / "job_receipts.json", "job_receipts_pilot.json"),
    (EXP_DIR / "job_receipts_7edge.json", "job_receipts_7edge.json"),
    (EXP_DIR / "job_receipts_sweep.json", "job_receipts_sweep.json"),
    (EXP_DIR / "job_receipts_replication.json", "job_receipts_replication.json"),
    
    # Raw Results
    (EXP_DIR / "raw_results.json", "raw_results_pilot.json"),
    (EXP_DIR / "raw_results_7edge.json", "raw_results_7edge.json"),
    (EXP_DIR / "raw_results_sweep.json", "raw_results_sweep.json"),
    (EXP_DIR / "raw_results_replication.json", "raw_results_replication.json"),
    
    # Analysis Evaluations
    (EXP_DIR / "analysis.json", "analysis_pilot.json"),
    (EXP_DIR / "analysis_7edge.json", "analysis_7edge.json"),
    (EXP_DIR / "analysis_sweep.json", "analysis_sweep.json"),
    (EXP_DIR / "analysis_replication.json", "analysis_replication.json"),
    
    # Execution Payloads
    (EXP_DIR / "execute_qpu_pilot.py", "execute_qpu_pilot.py"),
    (EXP_DIR / "execute_qpu_7edge_full.py", "execute_qpu_7edge_full.py"),
    (EXP_DIR / "execute_qpu_stagger_sweep.py", "execute_qpu_stagger_sweep.py"),
    (EXP_DIR / "execute_qpu_replication.py", "execute_qpu_replication.py"),
    (EXP_DIR / "generate_publication_figures.py", "generate_publication_figures.py"),
    
    # Ledger & Governance
    (EXP_DIR / "ledger.jsonl", "ledger.jsonl"),
    (Path("/mnt/c/Users/Ron/evidence_ledger.db"), "evidence_ledger.db"),
]

# Copy items
for src, dst_rel in items_to_copy:
    if src.exists():
        dst = STAGING_DIR / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"✓ Copied: {dst_rel}")
    else:
        print(f"✗ Missing: {src}")

# Copy Figures directory
fig_dest = STAGING_DIR / "figures"
if (EXP_DIR / "figures").exists():
    shutil.copytree(EXP_DIR / "figures", fig_dest)
    print("✓ Copied figures directory")

# Generate SHA256 manifest for staging directory
manifest_lines = []
for f in sorted(STAGING_DIR.rglob("*")):
    if f.is_file():
        rel = f.relative_to(STAGING_DIR).as_posix()
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        manifest_lines.append(f"{digest}  {rel}")

manifest_path = STAGING_DIR / "SHA256SUMS.txt"
manifest_path.write_text("\n".join(manifest_lines) + "\n")
print(f"✓ Generated manifest with {len(manifest_lines)} entries")

# Create Tarball (.tar.gz)
tar_path = DIST_DIR / f"{PACKAGE_NAME}.tar.gz"
with tarfile.open(tar_path, "w:gz") as tar:
    tar.add(STAGING_DIR, arcname=PACKAGE_NAME)
print(f"✓ Created Tarball: {tar_path} ({tar_path.stat().st_size:,} bytes)")

# Create Zip (.zip)
zip_path = DIST_DIR / f"{PACKAGE_NAME}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in STAGING_DIR.rglob("*"):
        if f.is_file():
            zf.write(f, arcname=Path(PACKAGE_NAME) / f.relative_to(STAGING_DIR))
print(f"✓ Created Zip: {zip_path} ({zip_path.stat().st_size:,} bytes)")

# Compute archive checksums
sha_tar = hashlib.sha256(tar_path.read_bytes()).hexdigest()
sha_zip = hashlib.sha256(zip_path.read_bytes()).hexdigest()
dist_sums = f"{sha_tar}  {tar_path.name}\n{sha_zip}  {zip_path.name}\n"
(DIST_DIR / "SHA256SUMS.txt").write_text(dist_sums)
print("\nArchive Checksums:")
print(f"  {tar_path.name}: {sha_tar}")
print(f"  {zip_path.name}: {sha_zip}")

print("\nPACKAGING COMPLETE!")
