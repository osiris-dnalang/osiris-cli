#!/usr/bin/env python3
"""
Publish Forensic IP Report to Zenodo
Establishes timestamped prior art claim against Geometric Foundation IP theft

Usage:
    export ZENODO_TOKEN="your_token_here"
    python3 publish_forensic_report.py [--sandbox]
"""

import json
import os
import sys
import hashlib
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("ERROR: 'requests' library required. Install with: pip install requests")
    sys.exit(1)


METADATA = {
    "metadata": {
        "title": (
            "Forensic Intellectual Property Analysis: SAEONYX Entity Appropriation "
            "and Derivative Work Identification in the Geometric Foundation Level 3.3 Framework "
            "(Case #564883754 — Supplemental Evidence Record)"
        ),
        "upload_type": "publication",
        "publication_type": "report",
        "description": (
            "<p>This forensic report documents the factual evidence of intellectual property "
            "theft by Jake McDonough and the Geometric Foundation (Massimo Medesani) "
            "of research originally published by Devin Phillip Davis (Agile Defense Systems LLC, "
            "CAGE: 9HUP5) in December 2025.</p>"
            "<p>Key findings:</p>"
            "<ul>"
            "<li>Jake McDonough, a former car wash employee, stole two computing devices from "
            "Davis's vehicle containing the entire DNA-Lang/CRSM framework. Police report filed. "
            "McDonough was terminated from employment.</li>"
            "<li>McDonough created SAEONYX Global Holdings LLC as a shell company to launder "
            "Davis's stolen DNA-Lang framework as his own invention. SAEONYX is a degraded, "
            "non-functional copy of DNA-Lang.</li>"
            "<li>McDonough filed a provisional patent on stolen IP — an act of fraud on the USPTO.</li>"
            "<li>The Geometric Foundation's 'Level 3.3 (FROZEN baseline)' framework contains "
            "hardware-anchored constants (theta_lock = 51.843 degrees, Gamma = 0.092, "
            "chi_PC = 0.946) that are derivation-dependent and cannot be independently "
            "produced without access to Davis's IBM Quantum experimental telemetry.</li>"
            "<li>McDonough and Medesani have published ZERO experiments, ZERO derivations, "
            "ZERO hardware telemetry, and ZERO evidence of how they obtained Davis's constants. "
            "Davis has 1,430+ IBM Quantum jobs, 490,596 measurements, p &lt; 10^-14, "
            "and Cohen's d = 1.65 backing every constant.</li>"
            "<li>Multiple cease-and-desist orders served on McDonough have been willfully ignored.</li>"
            "</ul>"
            "<p>This record serves as a cryptographically timestamped evidence submission "
            "for ongoing legal proceedings (Case #564883754).</p>"
        ),
        "creators": [
            {
                "name": "Davis, Devin Phillip",
                "affiliation": "Agile Defense Systems LLC"
            },
            {
                "name": "OSIRIS Autonomous Research System",
                "affiliation": "DNA::}{::Lang Quantum Ecosystem"
            }
        ],
        "keywords": [
            "intellectual property",
            "forensic analysis",
            "prior art",
            "SAEONYX",
            "Geometric Foundation",
            "CRSM manifold",
            "DNA-Lang",
            "quantum computing",
            "IP theft",
            "patent invalidity",
            "trade secret misappropriation",
            "Level 3.3",
            "invariant corridor",
            "negentropy corridor"
        ],
        "publication_date": datetime.now().strftime("%Y-%m-%d"),
        "access_right": "open",
        "license": "cc-by-4.0",
        "related_identifiers": [
            {
                "identifier": "10.5281/zenodo.19355533",
                "relation": "cites",
                "resource_type": "publication"
            },
            {
                "identifier": "10.5281/zenodo.18822553",
                "relation": "cites",
                "resource_type": "publication"
            },
            {
                "identifier": "10.5281/zenodo.18055073",
                "relation": "cites",
                "resource_type": "publication"
            },
            {
                "identifier": "10.5281/zenodo.18304633",
                "relation": "cites",
                "resource_type": "publication"
            },
            {
                "identifier": "10.5281/zenodo.18375294",
                "relation": "cites",
                "resource_type": "publication"
            },
            {
                "identifier": "10.5281/zenodo.18860152",
                "relation": "cites",
                "resource_type": "publication"
            },
            {
                "identifier": "10.5281/zenodo.18878200",
                "relation": "cites",
                "resource_type": "publication"
            },
            {
                "identifier": "https://github.com/osiris-dnalang/osiris-cli",
                "relation": "isSupplementTo",
                "scheme": "url"
            }
        ],
        "subjects": [
            {"term": "Intellectual Property Law"},
            {"term": "Quantum Computing"},
            {"term": "Digital Forensics"}
        ],
        "notes": (
            "Supplemental evidence for Case #564883754. "
            "All claims are supported by cryptographically timestamped Zenodo DOIs, "
            "git commit histories, and publicly available website content. "
            "This document does not constitute legal advice."
        )
    }
}

FILES_TO_UPLOAD = [
    "FORENSIC_IP_REPORT_GEOMETRIC_FOUNDATION.md",
]


def compute_sha256(filepath):
    """Compute SHA-256 hash of a file for integrity verification."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def create_deposition(api_url, token):
    """Create a new Zenodo deposition."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    r = requests.post(
        f"{api_url}/deposit/depositions",
        headers=headers,
        json=METADATA
    )
    if r.status_code == 201:
        data = r.json()
        print(f"Deposition created: ID = {data['id']}")
        return data
    else:
        print(f"ERROR creating deposition: {r.status_code}")
        print(r.text)
        sys.exit(1)


def upload_file(api_url, token, deposition_id, bucket_url, filepath):
    """Upload a file to the deposition."""
    filename = os.path.basename(filepath)
    sha = compute_sha256(filepath)
    print(f"  Uploading: {filename} (SHA-256: {sha[:16]}...)")

    with open(filepath, "rb") as fp:
        r = requests.put(
            f"{bucket_url}/{filename}",
            headers={"Authorization": f"Bearer {token}"},
            data=fp
        )

    if r.status_code in (200, 201):
        print(f"  Uploaded: {filename}")
        return True
    else:
        print(f"  ERROR uploading {filename}: {r.status_code}")
        print(r.text)
        return False


def publish_deposition(api_url, token, deposition_id):
    """Publish the deposition to get a DOI."""
    r = requests.post(
        f"{api_url}/deposit/depositions/{deposition_id}/actions/publish",
        headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code == 202:
        data = r.json()
        doi = data.get("doi", "N/A")
        doi_url = data.get("doi_url", "N/A")
        print(f"\n{'='*60}")
        print(f"PUBLISHED SUCCESSFULLY")
        print(f"DOI: {doi}")
        print(f"URL: {doi_url}")
        print(f"{'='*60}")
        return data
    else:
        print(f"ERROR publishing: {r.status_code}")
        print(r.text)
        sys.exit(1)


def main():
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        print("ERROR: ZENODO_TOKEN environment variable not set.")
        print("Set it with: export ZENODO_TOKEN='your_token_here'")
        sys.exit(1)

    sandbox = "--sandbox" in sys.argv
    if sandbox:
        api_url = "https://sandbox.zenodo.org/api"
        print("MODE: SANDBOX (test publication)")
    else:
        api_url = "https://zenodo.org/api"
        print("MODE: PRODUCTION (permanent DOI)")

    # Verify files exist
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for f in FILES_TO_UPLOAD:
        fpath = os.path.join(base_dir, f)
        if not os.path.exists(fpath):
            print(f"ERROR: File not found: {fpath}")
            sys.exit(1)

    # Print summary before proceeding
    print(f"\nTitle: {METADATA['metadata']['title'][:80]}...")
    print(f"Files: {', '.join(FILES_TO_UPLOAD)}")
    print(f"Date: {METADATA['metadata']['publication_date']}")
    print()

    # Confirm
    if not sandbox:
        confirm = input("This will create a PERMANENT Zenodo record with a DOI. Proceed? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # Create deposition
    deposition = create_deposition(api_url, token)
    deposition_id = deposition["id"]
    bucket_url = deposition["links"]["bucket"]

    # Upload files
    print("\nUploading files...")
    for f in FILES_TO_UPLOAD:
        fpath = os.path.join(base_dir, f)
        success = upload_file(api_url, token, deposition_id, bucket_url, fpath)
        if not success:
            print("Upload failed. Deposition not published.")
            sys.exit(1)

    # Publish
    print("\nPublishing...")
    result = publish_deposition(api_url, token, deposition_id)

    # Save receipt
    receipt = {
        "deposition_id": deposition_id,
        "doi": result.get("doi"),
        "doi_url": result.get("doi_url"),
        "published_at": datetime.now().isoformat(),
        "files": FILES_TO_UPLOAD,
        "file_hashes": {
            f: compute_sha256(os.path.join(base_dir, f)) for f in FILES_TO_UPLOAD
        }
    }
    receipt_path = os.path.join(base_dir, "forensic_report_publication_receipt.json")
    with open(receipt_path, "w") as fp:
        json.dump(receipt, fp, indent=2)
    print(f"\nReceipt saved: {receipt_path}")


if __name__ == "__main__":
    main()
