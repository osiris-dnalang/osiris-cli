#!/usr/bin/env python3
"""
Automated Zenodo Dataset Upload

This script automates uploading the DNA-Lang Quantum Corpus to Zenodo
and obtaining a DOI for citation.

Author: DNA-Lang Framework
License: Apache 2.0

Setup:
1. Create Zenodo account at https://zenodo.org
2. Get API token from https://zenodo.org/account/settings/applications/tokens/new/
3. Set environment variable: export ZENODO_TOKEN=your_token_here
"""

import os
import sys
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Zenodo API endpoints
ZENODO_API = "https://zenodo.org/api"
ZENODO_SANDBOX_API = "https://sandbox.zenodo.org/api"  # For testing


class ZenodoUploader:
    """Handles Zenodo API interactions."""

    def __init__(self, token: str, sandbox: bool = False):
        self.token = token
        self.base_url = ZENODO_SANDBOX_API if sandbox else ZENODO_API
        self.headers = {"Authorization": f"Bearer {token}"}
        self.deposition_id = None

    def create_deposition(self) -> Dict:
        """Create a new empty deposition."""
        response = requests.post(
            f"{self.base_url}/deposit/depositions",
            headers=self.headers,
            json={}
        )
        response.raise_for_status()
        data = response.json()
        self.deposition_id = data["id"]
        print(f"✓ Created deposition: {self.deposition_id}")
        return data

    def upload_file(self, filepath: Path, bucket_url: str) -> Dict:
        """Upload a file to the deposition."""
        filename = filepath.name
        filesize = filepath.stat().st_size

        print(f"  Uploading {filename} ({filesize:,} bytes)...")

        with open(filepath, "rb") as f:
            response = requests.put(
                f"{bucket_url}/{filename}",
                headers=self.headers,
                data=f
            )
        response.raise_for_status()
        print(f"  ✓ Uploaded {filename}")
        return response.json()

    def set_metadata(self, metadata: Dict) -> Dict:
        """Set deposition metadata."""
        response = requests.put(
            f"{self.base_url}/deposit/depositions/{self.deposition_id}",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"metadata": metadata}
        )
        response.raise_for_status()
        print("✓ Metadata set")
        return response.json()

    def publish(self) -> Dict:
        """Publish the deposition (assigns DOI)."""
        response = requests.post(
            f"{self.base_url}/deposit/depositions/{self.deposition_id}/actions/publish",
            headers=self.headers
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ Published! DOI: {data['doi']}")
        return data


def create_metadata() -> Dict:
    """Create Zenodo metadata for the dataset."""
    return {
        "title": "DNA-Lang Quantum Execution Corpus: 490K Shots on IBM Quantum Hardware",
        "upload_type": "dataset",
        "description": """
<p>This dataset contains 490,596 quantum shots executed on IBM Quantum hardware
(ibm_fez, ibm_torino) during November 5-16, 2025. The data was collected as part
of the DNA-Lang Quantum Independence Framework (QIF) validation experiments.</p>

<h3>Key Results</h3>
<ul>
<li>Bell State Fidelity: 0.869 ± 0.023 (k=2)</li>
<li>Total Shots: 490,596</li>
<li>Job Success Rate: 95.0%</li>
<li>Effect Size (Cohen's d): 1.4758 (Large)</li>
<li>Statistical Significance: p < 0.000001</li>
</ul>

<h3>Claimed Universal Constant</h3>
<p>This dataset was used to validate the claimed constant:</p>
<p><strong>ΛΦ = 2.176435×10⁻⁸ s⁻¹</strong></p>
<p>This value requires independent confirmation on non-IBM hardware
(IonQ, Rigetti, etc.) before it can be considered a universal physical constant.</p>

<h3>Contents</h3>
<ul>
<li>103 IBM Quantum job result files (JSON)</li>
<li>Bell state preparation circuits (OpenQASM 3.0)</li>
<li>Analysis scripts (Python)</li>
<li>ΛΦ measurement protocol for independent labs</li>
</ul>
        """,
        "creators": [
            {
                "name": "Davis, Devin Phillip",
                "affiliation": "Agile Defense Systems LLC",
                "orcid": ""  # Add ORCID if available
            }
        ],
        "keywords": [
            "quantum computing",
            "IBM Quantum",
            "Bell state",
            "fidelity",
            "coherence",
            "DNA-Lang",
            "quantum benchmarking",
            "DARPA QBI"
        ],
        "license": "CC-BY-4.0",
        "access_right": "open",
        "communities": [
            {"identifier": "quantum-computing"}  # Request to join this community
        ],
        "related_identifiers": [
            {
                "relation": "isSupplementTo",
                "identifier": "https://github.com/dnalang/quantum-corpus",
                "resource_type": "software",
                "scheme": "url"
            }
        ],
        "version": "1.0.0",
        "language": "eng",
        "notes": "CAGE Code: 9HUP5 | DFARS 252.227-7014 Compliant"
    }


def create_archive(corpus_dir: Path, output_path: Path) -> Path:
    """Create a zip archive of the corpus."""
    import zipfile

    print(f"Creating archive: {output_path}")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filepath in corpus_dir.rglob('*'):
            if filepath.is_file():
                arcname = filepath.relative_to(corpus_dir.parent)
                zf.write(filepath, arcname)
                print(f"  Added: {arcname}")

    size = output_path.stat().st_size
    print(f"✓ Archive created: {size:,} bytes")

    # Calculate checksum
    sha256 = hashlib.sha256()
    with open(output_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    checksum = sha256.hexdigest()
    print(f"  SHA256: {checksum}")

    return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Upload DNA-Lang Corpus to Zenodo")
    parser.add_argument("--corpus-dir", type=str,
                       default=str(Path.home() / "dnalang-quantum-corpus-v1.0"),
                       help="Path to corpus directory")
    parser.add_argument("--sandbox", action="store_true",
                       help="Use Zenodo sandbox for testing")
    parser.add_argument("--token", type=str,
                       default=os.environ.get("ZENODO_TOKEN"),
                       help="Zenodo API token")
    parser.add_argument("--dry-run", action="store_true",
                       help="Create archive but don't upload")

    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.exists():
        print(f"Error: Corpus directory not found: {corpus_dir}")
        sys.exit(1)

    # Create archive
    archive_path = corpus_dir.parent / "dnalang-quantum-corpus-v1.0.zip"
    create_archive(corpus_dir, archive_path)

    if args.dry_run:
        print("\n[DRY RUN] Archive created but not uploaded.")
        print(f"Archive: {archive_path}")
        return 0

    if not args.token:
        print("\nError: ZENODO_TOKEN not set")
        print("Get token from: https://zenodo.org/account/settings/applications/tokens/new/")
        print("Then: export ZENODO_TOKEN=your_token_here")
        print("\nOr upload manually at: https://zenodo.org/deposit/new")
        sys.exit(1)

    # Upload to Zenodo
    print(f"\n{'='*60}")
    print("UPLOADING TO ZENODO")
    print(f"{'='*60}")

    uploader = ZenodoUploader(args.token, sandbox=args.sandbox)

    try:
        # Create deposition
        deposition = uploader.create_deposition()
        bucket_url = deposition["links"]["bucket"]

        # Upload archive
        uploader.upload_file(archive_path, bucket_url)

        # Set metadata
        metadata = create_metadata()
        uploader.set_metadata(metadata)

        # Publish
        print("\nReady to publish. This will assign a DOI.")
        confirm = input("Publish now? [y/N]: ")

        if confirm.lower() == 'y':
            result = uploader.publish()
            doi = result["doi"]
            doi_url = result["doi_url"]

            print(f"\n{'='*60}")
            print("SUCCESS!")
            print(f"{'='*60}")
            print(f"DOI: {doi}")
            print(f"URL: {doi_url}")
            print(f"\nCitation:")
            print(f"Davis, D.P. (2025). DNA-Lang Quantum Execution Corpus: ")
            print(f"490K Shots on IBM Quantum Hardware. Zenodo. {doi_url}")

            # Update README with DOI
            readme_path = corpus_dir / "README.md"
            if readme_path.exists():
                content = readme_path.read_text()
                content = content.replace("10.5281/zenodo.XXXXXXX", doi.replace("10.5281/zenodo/", ""))
                readme_path.write_text(content)
                print(f"\n✓ Updated README.md with DOI")
        else:
            print("\nDeposition saved as draft.")
            print(f"Edit at: https://{'sandbox.' if args.sandbox else ''}zenodo.org/deposit/{uploader.deposition_id}")

    except requests.HTTPError as e:
        print(f"\nError: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
