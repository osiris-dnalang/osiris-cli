#!/usr/bin/env python3
"""
package_evidence_v2.py
Bundles osiris_quantum_hardware_v2.0_evidence_package into .zip and .tar.gz archives
and computes their SHA-256 checksums in dist/.
"""

import hashlib
import shutil
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "dist"
DIST_DIR.mkdir(exist_ok=True)

PKG_DIR = REPO_ROOT / "osiris_quantum_hardware_v2.0_evidence_package"
BUNDLE_NAME = "osiris_quantum_hardware_v2.0_evidence_package"

ZIP_PATH = DIST_DIR / f"{BUNDLE_NAME}.zip"
TAR_PATH = DIST_DIR / f"{BUNDLE_NAME}.tar.gz"
SUMS_PATH = DIST_DIR / f"{BUNDLE_NAME}_SHA256SUMS.txt"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    print(f"Creating .zip archive: {ZIP_PATH} ...")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PKG_DIR.rglob("*")):
            if p.is_file():
                arcname = f"{BUNDLE_NAME}/{p.relative_to(PKG_DIR).as_posix()}"
                zf.write(p, arcname)

    print(f"Creating .tar.gz archive: {TAR_PATH} ...")
    with tarfile.open(TAR_PATH, "w:gz") as tf:
        tf.add(PKG_DIR, arcname=BUNDLE_NAME)

    zip_hash = sha256_file(ZIP_PATH)
    tar_hash = sha256_file(TAR_PATH)

    lines = [
        f"{zip_hash}  {ZIP_PATH.name}",
        f"{tar_hash}  {TAR_PATH.name}"
    ]
    SUMS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 80)
    print("DISTRIBUTION PACKAGE CREATED SUCCESSFULLY")
    print("=" * 80)
    print(f"ZIP:    {ZIP_PATH} ({ZIP_PATH.stat().st_size:,} bytes) | SHA-256: {zip_hash}")
    print(f"TAR.GZ: {TAR_PATH} ({TAR_PATH.stat().st_size:,} bytes) | SHA-256: {tar_hash}")
    print(f"SUMS:   {SUMS_PATH}")


if __name__ == "__main__":
    main()
