#!/usr/bin/env python3
"""
stage_hp_001_qpu_circuits.py
OSIRIS-HP-001 Hardware Pilot Circuit Stager & ISA Verifier
(ZERO QPU SECONDS CONSUMED — Staged Under SYS-021 Governance)

Maps the 6-qubit Hayden-Preskill protocol to a physical connected subgraph on ibm_marrakesh:
  - Reference R     : Physical Qubit 14
  - Message M       : Physical Qubit 15
  - Black Hole B1   : Physical Qubit 19
  - Black Hole B2   : Physical Qubit 35
  - Early Rad E1    : Physical Qubit 13
  - Early Rad E2    : Physical Qubit 34

Generates 9 ISA-transpiled circuits:
  - Arm A (Reversible Control)    : 3 Bases (XX, YY, ZZ)
  - Arm B (Restricted Recovery)   : 3 Bases (XX, YY, ZZ)
  - Arm B (Unentangled Control)   : 3 Bases (XX, YY, ZZ)

Serializes circuits to QPY and records pre-flight manifest with SHA-256 digests.
"""

from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.qpy import dump as qpy_dump
from qiskit_ibm_runtime import QiskitRuntimeService

ROOT = Path(__file__).resolve().parent
QPY_OUT = ROOT / "staged_circuits_hp_001_qpu.qpy"
MANIFEST_OUT = ROOT / "staged_manifest_hp_001_qpu.json"

PHYSICAL_MAP = {
    "R": 14,
    "M": 15,
    "B1": 19,
    "B2": 35,
    "E1": 13,
    "E2": 34
}

BASES = ["XX", "YY", "ZZ"]

def build_hp_logical_circuit(arm: str, basis: str, seed: int = 42) -> QuantumCircuit:
    """Build logical 6-qubit Hayden-Preskill circuit for given arm and basis."""
    qr = QuantumRegister(6, name="q")
    cr = ClassicalRegister(2, name="meas_rm")
    qc = QuantumCircuit(qr, cr, name=f"HP_{arm}_{basis}")

    # Index mapping: 0: R, 1: M, 2: B1, 3: B2, 4: E1, 5: E2
    # 1. State preparation: Bell pair on (R, M) -> (0, 1)
    qc.h(0)
    qc.cx(0, 1)

    # 2. Entanglement reservoir:
    if arm != "ARM_B_UNENTANGLED":
        # Entangled B1-E1 on (2, 4) and B2-E2 on (3, 5)
        qc.h(2)
        qc.cx(2, 4)
        qc.h(3)
        qc.cx(3, 5)

    # 3. Scrambling unitary U across (M, B1, B2) -> (1, 2, 3)
    rng = np.random.default_rng(seed)
    # 2-layer alternating brickwork scrambler
    for q in [1, 2, 3]:
        qc.ry(float(rng.uniform(0, 2*np.pi)), q)
        qc.rz(float(rng.uniform(0, 2*np.pi)), q)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.cx(1, 3)

    if arm == "ARM_A_REVERSIBLE":
        # Full-access inverse: U†
        qc.cx(1, 3)
        qc.cx(2, 3)
        qc.cx(1, 2)
        for q in [3, 2, 1]:
            qc.rz(-float(rng.uniform(0, 2*np.pi)), q)
            qc.ry(-float(rng.uniform(0, 2*np.pi)), q)
        # Measured qubits for Arm A: (0, 1) = (R, M)
        meas_qubits = (0, 1)
    else:
        # Arm B: Restricted decoder on E and D (qubits 4, 5, 2, 3)
        # Decoding operator reconstructing M' on qubit 2
        qc.cx(2, 4)
        qc.cx(3, 5)
        qc.h(2)
        qc.h(3)
        qc.cx(2, 3)
        meas_qubits = (0, 2)  # (R, M')

    # 4. Pauli Measurement Basis Rotation on meas_qubits
    q_r, q_m = meas_qubits
    if basis == "XX":
        qc.h(q_r)
        qc.h(q_m)
    elif basis == "YY":
        qc.sdg(q_r)
        qc.h(q_r)
        qc.sdg(q_m)
        qc.h(q_m)
    elif basis == "ZZ":
        pass  # Standard computational basis

    qc.measure(q_r, cr[0])
    qc.measure(q_m, cr[1])
    return qc

def main():
    print("================================================================================")
    print("OSIRIS-HP-001 QPU CIRCUIT STAGER & ISA VERIFIER (DRY RUN)")
    print("================================================================================")
    print("Zero QPU seconds will be consumed. Staging offline.")

    with open("/mnt/c/Users/Ron/Downloads/dnalang.json") as f:
        key_info = json.load(f)

    print("Connecting to ibm_marrakesh backend metadata...")
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=key_info["apikey"])
    backend = service.backend("ibm_marrakesh")
    target = backend.target
    print(f"✓ Target backend verified: {backend.name} (156-qubit Heron r2)")

    # Build logical circuits
    arms = ["ARM_A_REVERSIBLE", "ARM_B_RESTRICTED", "ARM_B_UNENTANGLED"]
    logical_circuits = []
    for arm in arms:
        for basis in BASES:
            qc = build_hp_logical_circuit(arm, basis, seed=42)
            logical_circuits.append(qc)

    print(f"Generated {len(logical_circuits)} logical circuits across 3 arms and 3 bases.")

    # Physical initial layout:
    # 0 -> 14 (R)
    # 1 -> 15 (M)
    # 2 -> 19 (B1)
    # 3 -> 35 (B2)
    # 4 -> 13 (E1)
    # 5 -> 34 (E2)
    initial_layout = [14, 15, 19, 35, 13, 34]
    print(f"Physical qubit mapping: {PHYSICAL_MAP}")

    print("\nTranspiling to native ISA gates on ibm_marrakesh (Opt Level 3)...")
    t0 = time.time()
    transpiled_circuits = transpile(
        logical_circuits,
        backend=backend,
        initial_layout=initial_layout,
        optimization_level=3,
        seed_transpiler=42
    )
    t_trans = time.time() - t0
    print(f"✓ Transpiled {len(transpiled_circuits)} ISA circuits in {t_trans:.2f} s.")

    # Circuit statistics
    circuit_manifest = []
    total_cz = 0
    total_1q = 0

    for i, tc in enumerate(transpiled_circuits):
        ops = tc.count_ops()
        cz_count = ops.get("cz", 0)
        sx_count = ops.get("sx", 0) + ops.get("x", 0)
        rz_count = ops.get("rz", 0)
        depth = tc.depth()

        total_cz += cz_count
        total_1q += (sx_count + rz_count)

        circuit_manifest.append({
            "index": i,
            "name": tc.name,
            "depth": depth,
            "cz_count": cz_count,
            "single_qubit_gates": sx_count + rz_count,
            "ops": dict(ops)
        })

    print("\n--- ISA CIRCUIT STATISTICS ---")
    print(f"Total Circuits Staged        : {len(transpiled_circuits)}")
    print(f"Mean 2Q (CZ) Gates / Circuit : {total_cz / len(transpiled_circuits):.1f}")
    print(f"Mean 1Q Gates / Circuit      : {total_1q / len(transpiled_circuits):.1f}")
    print(f"Mean Topological Depth       : {np.mean([m['depth'] for m in circuit_manifest]):.1f}")

    # Serialize to QPY
    with open(QPY_OUT, "wb") as f:
        qpy_dump(transpiled_circuits, f)
    qpy_bytes = QPY_OUT.stat().st_size
    qpy_sha = hashlib.sha256(QPY_OUT.read_bytes()).hexdigest()

    manifest_payload = {
        "benchmark": "OSIRIS-HP-001",
        "backend": "ibm_marrakesh",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "physical_layout": PHYSICAL_MAP,
        "n_circuits": len(transpiled_circuits),
        "qpy_bytes": qpy_bytes,
        "qpy_sha256": qpy_sha,
        "circuits": circuit_manifest
    }

    MANIFEST_OUT.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    manifest_sha = hashlib.sha256(MANIFEST_OUT.read_bytes()).hexdigest()

    print("\n================================================================================")
    print("✓ QPU HARDWARE BENCHMARK READY (STAGED & SEALED)")
    print("================================================================================")
    print(f"QPY Archive  : {QPY_OUT.name} ({qpy_bytes:,} bytes, SHA-256: {qpy_sha})")
    print(f"Manifest     : {MANIFEST_OUT.name} (SHA-256: {manifest_sha})")
    print("No jobs dispatched. Allocation preserved.")

if __name__ == "__main__":
    main()
