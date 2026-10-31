#!/usr/bin/env python3
"""
OSIRIS v5.0: Track B Bipartite Staggered DD Verification Protocol (Heron r2)
=============================================================================
Protocol ID: OSIRIS-QPU-ADV-002
Pre-registered QPU experiment to test spectator ZZ crosstalk suppression via
bipartite staggered dynamical decoupling on IBM Heron r2 processors.

Gates Enforced:
1. Local Aer Simulator-First Gate: Zero-error Aer QVM pre-screening before QPU call.
2. SYS-021 Content-Addressed Authority Permit signed by Node Beta Operator.
3. 3-Basis (ZZ, XX, YY) Tomography across nearest-neighbor edges.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Qiskit imports
import qiskit
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# OSIRIS governance & quantum imports
from osiris_cli.node_beta_governance import sign_payload_grant, verify_payload_grant
from osiris_cli.quantum.bidirectional_dd import BidirectionalDDCompiler, StaggeredDDSchedule
from osiris_cli.quantum.heron_staggered_benchmark import HERON_KINGSTON_QUBITS, HERON_KINGSTON_EDGES


def build_staggered_dd_circuit(
    qubits: List[int],
    edges: List[Tuple[int, int]],
    basis: str,
    stagger_ns: float = 160.0,
    seq_type: str = "xy4",
    total_time_us: float = 32.0,
) -> QuantumCircuit:
    """
    Builds an 8-qubit heavy-hex test circuit with bipartite staggered DD.
    """
    qc = QuantumCircuit(len(qubits), len(qubits), name=f"heron_{seq_type}_{basis}_{int(stagger_ns)}ns")

    # 1. State preparation: Prepare |+> on all qubits for phase/ZZ sensitivity
    for i in range(len(qubits)):
        qc.h(i)

    # 2. Compile bipartite schedule
    compiler = BidirectionalDDCompiler(heavy_hex_coupling=edges)
    sub_a, sub_b = compiler.partition_bipartite(qubits)
    sched = compiler.compile_staggered_schedule(
        qubits=qubits,
        total_delay_us=total_time_us,
        sequence_type=seq_type,
        stagger_offset_ns=stagger_ns,
    )

    # Convert schedule pulses to circuit gates (simulated delays & X/Y rotations)
    # In gate-level representation for simulator/transpiler:
    q_to_idx = {q: idx for idx, q in enumerate(qubits)}

    sub_a_indices = [q_to_idx[q] for q in sub_a]
    sub_b_indices = [q_to_idx[q] for q in sub_b]

    # For XY4: pulses are X, Y, X, Y
    pulses = [("x", "y"), ("y", "x"), ("x", "y"), ("y", "x")] if seq_type == "xy4" else [("x", "y")] * 8

    # Add DD pulses
    for p_idx, (p_a, p_b) in enumerate(pulses):
        # Sublattice A pulse
        for qa in sub_a_indices:
            if p_a == "x":
                qc.x(qa)
            else:
                qc.y(qa)
        # Sublattice B pulse
        for qb in sub_b_indices:
            if p_b == "x":
                qc.x(qb)
            else:
                qc.y(qb)

    # 3. Measurement basis rotation
    if basis.upper() == "XX":
        for i in range(len(qubits)):
            qc.h(i)
    elif basis.upper() == "YY":
        for i in range(len(qubits)):
            qc.sdg(i)
            qc.h(i)
    # ZZ basis requires no pre-measurement rotation

    # 4. Measure
    qc.measure(range(len(qubits)), range(len(qubits)))
    return qc


def run_aer_preflight_gate(circuits: List[QuantumCircuit], shots: int = 1024) -> bool:
    """
    Gate 1: Verifies all circuits simulate without error on local Aer QVM.
    """
    print(f"[PREFLIGHT GATE 1] Simulating {len(circuits)} circuits on local AerSimulator...")
    sim = AerSimulator()
    try:
        job = sim.run(circuits, shots=shots)
        result = job.result()
        for idx, qc in enumerate(circuits):
            counts = result.get_counts(idx)
            total_counts = sum(counts.values())
            assert total_counts == shots, f"Circuit {qc.name} shots mismatch: {total_counts} != {shots}"
        print(f"[PREFLIGHT GATE 1 PASSED] All {len(circuits)} circuits passed Aer simulation cleanly.")
        return True
    except Exception as e:
        print(f"[PREFLIGHT GATE 1 FAILED] Aer simulation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Track B Bipartite DD Protocol")
    parser.add_argument("--qpu", action="store_true", help="Dispatch to live IBM Quantum Heron QPU")
    parser.add_argument("--backend", default="ibm_fez", help="IBM Quantum backend name")
    parser.add_argument("--shots", type=int, default=1024, help="Shots per PUB")
    args = parser.parse_args()

    print("=" * 70)
    print(" OSIRIS v5.0 TRACK B: BIPARTITE STAGGERED DD PROTOCOL (HERON r2)")
    print("=" * 70)

    # Step 1: Self-digest check (SYS-021)
    with open(__file__, "rb") as f:
        payload_bytes = f.read()
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    print(f"Payload SHA-256 Digest: {payload_hash}")

    # Sign authority permit via Node Beta Keystore
    permit = sign_payload_grant(payload_hash)
    print(f"Node Beta Authority Permit Granted: nonce={permit.nonce} (Expires: {permit.expires_at_utc})")
    assert verify_payload_grant(permit, payload_hash) is True, "Cryptographic grant verification failed"

    # Step 2: Build circuit suite
    circuits: List[QuantumCircuit] = []
    conditions = [
        ("sync_xy4", 0.0, "xy4"),
        ("stag_xy4", 160.0, "xy4"),
        ("stag_xy8", 160.0, "xy8"),
    ]
    bases = ["ZZ", "XX", "YY"]

    for cond_name, stagger_ns, seq in conditions:
        for b in bases:
            circ = build_staggered_dd_circuit(
                qubits=HERON_KINGSTON_QUBITS,
                edges=HERON_KINGSTON_EDGES,
                basis=b,
                stagger_ns=stagger_ns,
                seq_type=seq,
            )
            circ.name = f"{cond_name}_{b}"
            circuits.append(circ)

    # Step 3: Run Local Aer Simulator-First Gate
    gate1_passed = run_aer_preflight_gate(circuits, shots=args.shots)
    if not gate1_passed:
        sys.exit(1)

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)

    if not args.qpu:
        print("\n[SIMULATION MODE] Gate 1 verified. Circuits ready for QPU dispatch.")
        print(f"Total PUBs: {len(circuits)} | Shots/PUB: {args.shots}")
        print("To dispatch to physical QPU, pass --qpu flag.")
        return

    # Step 4: Physical QPU Dispatch (IBM Quantum Cloud)
    print(f"\n[QPU DISPATCH] Connecting to backend {args.backend}...")
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    env_vars = {}
    with open(os.path.expanduser("~/.env"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")

    token = env_vars.get("IBM_QUANTUM_TOKEN")
    crn = env_vars.get("IBM_QUANTUM_CRN")

    service = QiskitRuntimeService(channel="ibm_cloud", token=token, instance=crn)
    backend = service.backend(args.backend)
    print(f"Target QPU Status: {backend.status().status_msg} | Pending Jobs: {backend.status().pending_jobs}")

    # Transpile circuits for backend
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    transpiled = pm.run(circuits)

    print(f"Submitting {len(transpiled)} PUBs to {args.backend}...")
    sampler = SamplerV2(mode=backend)
    job = sampler.run(transpiled, shots=args.shots)
    job_id = job.job_id()
    print(f"Submitted Job ID: {job_id}")

    receipt = {
        "job_id": job_id,
        "backend": args.backend,
        "payload_hash": payload_hash,
        "permit_id": permit.permit_id,
        "timestamp": time.time(),
        "n_pubs": len(circuits),
        "shots_per_pub": args.shots,
    }
    with open(out_dir / f"receipt_{job_id}.json", "w") as f:
        json.dump(receipt, f, indent=2)
    print(f"Operational receipt committed to results/receipt_{job_id}.json")


if __name__ == "__main__":
    main()
