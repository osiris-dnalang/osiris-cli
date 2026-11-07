#!/usr/bin/env python3
"""
dispatch_hp003.py — Hardware Dispatcher for OSIRIS-HP-003 Multi-Qubit Hayden-Preskill Benchmark
Executes under SYS-021 payload-bound authority grant.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EXPERIMENT_DIR))

from qiskit import qpy
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2


def load_credentials() -> Dict[str, str]:
    cred_paths = [
        Path.home() / ".qiskit" / "qiskit-ibm.json",
        Path(r"/mnt/c/Users/Ron/Downloads/dnalang.json"),
        Path(r"C:\Users\Ron\Downloads\dnalang.json"),
        Path.home() / "Downloads" / "dnalang.json"
    ]
    for p in cred_paths:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if "apikey" in data:
                return {"token": data["apikey"], "channel": "ibm_quantum_platform"}
            if "token" in data:
                return {"token": data["token"], "channel": data.get("channel", "ibm_quantum_platform")}
    token = os.environ.get("IBM_QUANTUM_TOKEN") or os.environ.get("QISKIT_IBM_TOKEN")
    if token:
        return {"token": token, "channel": "ibm_quantum_platform"}
    raise RuntimeError("No IBM Quantum credentials found.")


def main():
    print("=" * 80)
    print("OSIRIS-HP-003: PHYSICAL QPU DISPATCH ENGINE")
    print("=" * 80)

    # 1. Verify Grant
    grant_file = EXPERIMENT_DIR / "sys021_hp003_grant.json"
    if not grant_file.exists():
        raise RuntimeError("CRITICAL [SYS-021]: Missing sys021_hp003_grant.json. Execution rejected.")
    grant = json.loads(grant_file.read_text(encoding="utf-8"))
    print(f"Verified Grant ID  : {grant.get('grant_id')}")
    print(f"Target Operator    : {grant.get('operator_id')}")

    # 2. Verify QPY Integrity
    qpy_file = EXPERIMENT_DIR / "hp003_staged_circuits.qpy"
    if not qpy_file.exists():
        raise FileNotFoundError(f"Missing staged QPY file: {qpy_file}")
    actual_qpy_hash = hashlib.sha256(qpy_file.read_bytes()).hexdigest()
    manifest_file = EXPERIMENT_DIR / "hp003_staging_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if actual_qpy_hash != manifest["qpy_sha256"]:
        raise ValueError(f"QPY Hash mismatch: {actual_qpy_hash} != {manifest['qpy_sha256']}")
    print(f"Verified QPY Digest : {actual_qpy_hash}")

    with open(qpy_file, "rb") as f:
        isa_circuits = qpy.load(f)
    print(f"Loaded {len(isa_circuits)} frozen ISA circuits.")

    # 3. Initialize Runtime Service (Prioritizing Default Active Account)
    try:
        service = QiskitRuntimeService()
    except Exception:
        creds = load_credentials()
        service = QiskitRuntimeService(channel=creds["channel"], token=creds["token"])

    backend_name = manifest["backend"]
    backend = service.backend(backend_name)
    b_status = backend.status()
    print(f"Target Backend     : {backend_name} (operational={b_status.operational}, pending={b_status.pending_jobs})")

    # 4. Dispatch via SamplerV2
    shots = manifest["shots_per_circuit"]
    print(f"Submitting 45 circuits ({shots} shots/circuit, total {len(isa_circuits) * shots} shots)...")
    sampler = SamplerV2(mode=backend)
    job = sampler.run(isa_circuits, shots=shots)
    job_id = job.job_id()
    print(f"\n[DISPATCHED] Physical QPU Job successfully submitted!")
    print(f"  Job ID       : {job_id}")
    print(f"  Backend      : {backend_name}")
    print(f"  Total Shots  : {len(isa_circuits) * shots}")

    # 5. Write Job Receipt
    receipt = {
        "job_id": job_id,
        "backend": backend_name,
        "total_circuits": len(isa_circuits),
        "shots_per_circuit": shots,
        "total_physical_shots": len(isa_circuits) * shots,
        "qpy_sha256": actual_qpy_hash,
        "grant_id": grant.get("grant_id"),
        "dispatch_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "QUEUED"
    }
    receipt_file = EXPERIMENT_DIR / "job_receipt_hp003.json"
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Job receipt saved to: {receipt_file.name}")


if __name__ == "__main__":
    main()
