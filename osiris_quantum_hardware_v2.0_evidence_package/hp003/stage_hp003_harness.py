#!/usr/bin/env python3
"""
stage_hp003_harness.py — OSIRIS-HP-003 Multi-Qubit Hayden-Preskill Staging Harness
Constructs, compiles, and freezes the 45-circuit certified benchmark for 2-qubit message recovery.
"""

import hashlib
import json
import os
import random
import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(EXPERIMENT_DIR))

from qiskit import QuantumCircuit, qpy, transpile
from qiskit.quantum_info import Clifford, Pauli, Statevector, DensityMatrix, partial_trace, state_fidelity
from qiskit_ibm_runtime import QiskitRuntimeService

from find_hp003_scrambler_decoder import build_candidate_scrambler

BENCHMARK_ID = "OSIRIS-HP-003"
TARGET_BACKEND = "ibm_fez"
FALLBACK_BACKEND = "ibm_kingston"
N_QUBITS = 8
N_BLOCKS = 3
SHOTS_PER_CIRCUIT = 1024

# Build Scrambler U1 (seed 128) - Verified 4-qubit scrambler
SCRAMBLER_U1 = build_candidate_scrambler(seed=128)
# Build Held-Out Scrambler U2 (seed 158) - Audited independent scrambler
SCRAMBLER_U2 = build_candidate_scrambler(seed=158)

# Exact Clifford Decoder Table on (D1, D2, E1, E2) = (0, 1, 2, 3)
DECODER_TABLE = {
    'destabilizer': ['-IYIX', '-IXIZ', '+IXYZ', '+XXIZ'],
    'stabilizer':   ['-XXYI', '+YIXX', '+IYXX', '+YYIX']
}
DECODER_CLIFFORD = Clifford.from_dict(DECODER_TABLE).adjoint()
DECODER_CIRC = DECODER_CLIFFORD.to_circuit().decompose()

# Optimal Sub-Capacity Single-Photon Decoder Table on (D1, E1, E2) = (0, 1, 2)
# Operates on (2, 6, 7). Maximizes recovery of R1-M1' to theoretical capacity limit F1 = 0.5000 (W1 >= 0)
SINGLE_PHOTON_DECODER_TABLE = {
    'stabilizer':   ['-IXY', '-XYZ', '+ZXI'],
    'destabilizer': ['-YZI', '-ZXY', '+IZX']
}
SINGLE_PHOTON_DECODER_CLIFFORD = Clifford.from_dict(SINGLE_PHOTON_DECODER_TABLE)
SINGLE_PHOTON_DECODER_CIRC = SINGLE_PHOTON_DECODER_CLIFFORD.to_circuit().decompose()


def build_hp003_circuit(arm_name: str, basis: str) -> QuantumCircuit:
    """
    Builds an 8-qubit HP-003 circuit:
    Qubits:
      0: R1 (Reference 1)
      1: R2 (Reference 2)
      2: M1 -> D1 (Message 1 / Late Radiation 1)
      3: M2 -> D2 (Message 2 / Late Radiation 2)
      4: B1 -> C1 (Black Hole Remnant 1)
      5: B2 -> C2 (Black Hole Remnant 2)
      6: E1 (Early Radiation 1)
      7: E2 (Early Radiation 2)
    Classical Bits: 4 bits
      c[0]: R1
      c[1]: M1' (D1)
      c[2]: R2
      c[3]: M2' (D2)
    """
    qc = QuantumCircuit(8, 4, name=f"{arm_name}_{basis}")
    
    # 1. State Preparation
    # Reference-Message Bell pairs: (R1, M1) and (R2, M2)
    qc.h(0); qc.cx(0, 2)
    qc.h(1); qc.cx(1, 3)
    
    if arm_name != "Arm B-Ctrl":
        # Early Entanglement: (B1, E1) and (B2, E2)
        qc.h(4); qc.cx(4, 6)
        qc.h(5); qc.cx(5, 7)
    else:
        # Arm B-Ctrl: Separable Trapped (|0000> on B and E)
        pass
        
    # 2. Black Hole Scrambling Dynamics U_MB on (M1, M2, B1, B2)
    if arm_name == "Arm B-Held":
        qc.compose(SCRAMBLER_U2.decompose(), qubits=[2, 3, 4, 5], inplace=True)
    else:
        qc.compose(SCRAMBLER_U1.decompose(), qubits=[2, 3, 4, 5], inplace=True)
        
    # 3. Decoding Dynamics
    if arm_name == "Arm A":
        # Full-Access Positive Control: Invert scrambler directly on (2, 3, 4, 5)
        # CRITICAL BARRIER: Prevents compiler from canceling U1 * U1^dagger into identity
        qc.barrier([2, 3, 4, 5])
        qc.compose(SCRAMBLER_U1.inverse().decompose(), qubits=[2, 3, 4, 5], inplace=True)
    elif arm_name in ["Arm B", "Arm B-Ctrl", "Arm B-Held"]:
        # Restricted Decoder: acts strictly on (D1, D2, E1, E2) -> qubits (2, 3, 6, 7)
        # Remnants (4, 5) are strictly quarantined!
        qc.compose(DECODER_CIRC, qubits=[2, 3, 6, 7], inplace=True)
    elif arm_name == "Arm B-Def":
        # Sub-Capacity Deficient Arm: Only D1 is available; D2 is quarantined!
        # Applies optimal single-photon Clifford decoder on available radiation (D1, E1, E2) -> qubits (2, 6, 7)
        # Remnants C1, C2 (4, 5) and late photon D2 (3) are strictly unaccessed and quarantined
        qc.compose(SINGLE_PHOTON_DECODER_CIRC, qubits=[2, 6, 7], inplace=True)
    else:
        raise ValueError(f"Unknown arm: {arm_name}")
        
    # 4. Tomographic Basis Rotation on (R1, M1') = (0, 2) and (R2, M2') = (1, 3)
    if basis == "XX":
        qc.h(0); qc.h(2)
        qc.h(1); qc.h(3)
    elif basis == "YY":
        qc.sdg(0); qc.h(0)
        qc.sdg(2); qc.h(2)
        qc.sdg(1); qc.h(1)
        qc.sdg(3); qc.h(3)
    elif basis == "ZZ":
        pass  # Standard computational basis
    else:
        raise ValueError(f"Unknown basis: {basis}")
        
    # 5. Observable Measurement
    qc.measure([0, 2, 1, 3], [0, 1, 2, 3])
    return qc


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
    print("OSIRIS-HP-003: MULTI-QUBIT HAYDEN-PRESKILL STAGING HARNESS")
    print("=" * 80)
    
    arms = ["Arm A", "Arm B", "Arm B-Def", "Arm B-Ctrl", "Arm B-Held"]
    bases = ["XX", "YY", "ZZ"]
    
    raw_circuits = []
    circuit_metadata = []
    
    for block_idx in range(N_BLOCKS):
        block_items = []
        for arm in arms:
            for b in bases:
                c_name = f"hp003_b{block_idx}_{arm.lower().replace(' ', '_').replace('-', '_')}_{b.lower()}"
                qc = build_hp003_circuit(arm, b)
                qc.name = c_name
                block_items.append((qc, {
                    "block_index": block_idx,
                    "arm": arm,
                    "basis": b,
                    "circuit_name": c_name
                }))
        # Block-level randomization to protect against systematic calibration drift
        rng = random.Random(42 + block_idx * 100)
        rng.shuffle(block_items)
        
        for qc, meta in block_items:
            raw_circuits.append(qc)
            circuit_metadata.append(meta)
            
    print(f"Total logical circuits assembled: {len(raw_circuits)} (3 blocks x 5 arms x 3 bases)")
    
    # Initialize service for transpilation target
    creds = load_credentials()
    try:
        service = QiskitRuntimeService(channel=creds["channel"], token=creds["token"])
    except Exception as e:
        service = QiskitRuntimeService()
        
    try:
        backend = service.backend(TARGET_BACKEND)
    except Exception:
        backend = service.backend(FALLBACK_BACKEND)
    print(f"Targeting backend: {backend.name}")
    
    print("\nTranspiling circuits to native Heron r2 ISA...")
    isa_circuits = transpile(
        raw_circuits,
        backend=backend,
        optimization_level=3,
        seed_transpiler=42
    )
    
    # Gate audit
    max_cz = 0
    max_depth = 0
    cz_counts = []
    for c in isa_circuits:
        ops = c.count_ops()
        cz = ops.get("cz", 0)
        cz_counts.append(cz)
        if cz > max_cz: max_cz = cz
        if c.depth() > max_depth: max_depth = c.depth()
        
    MAX_CZ_THRESHOLD = 55
    MAX_DEPTH_THRESHOLD = 110

    print(f"Compilation complete:")
    print(f"  Circuits : {len(isa_circuits)}")
    print(f"  Max CZ   : {max_cz} (Threshold: <= {MAX_CZ_THRESHOLD})")
    print(f"  Mean CZ  : {np.mean(cz_counts):.1f}")
    print(f"  Max Depth: {max_depth} (Threshold: <= {MAX_DEPTH_THRESHOLD})")
    
    assert max_cz <= MAX_CZ_THRESHOLD, f"MAXQ Violation: CZ {max_cz} exceeds {MAX_CZ_THRESHOLD}"
    assert max_depth <= MAX_DEPTH_THRESHOLD, f"MAXQ Violation: Depth {max_depth} exceeds {MAX_DEPTH_THRESHOLD}"
    print("  [PASS] All MAXQ hardware invariants verified!")
    
    # Serialize to QPY
    qpy_path = EXPERIMENT_DIR / "hp003_staged_circuits.qpy"
    with open(qpy_path, "wb") as f:
        qpy.dump(isa_circuits, f)
    qpy_hash = hashlib.sha256(qpy_path.read_bytes()).hexdigest()
    print(f"\nStaged QPY written: {qpy_path.name}")
    print(f"QPY SHA-256: {qpy_hash}")
    
    # Staging manifest
    manifest = {
        "benchmark_id": BENCHMARK_ID,
        "backend": backend.name,
        "total_circuits": len(isa_circuits),
        "shots_per_circuit": SHOTS_PER_CIRCUIT,
        "total_shots": len(isa_circuits) * SHOTS_PER_CIRCUIT,
        "qpy_sha256": qpy_hash,
        "max_cz": max_cz,
        "max_depth": max_depth,
        "arms": arms,
        "bases": bases,
        "n_blocks": N_BLOCKS,
        "circuit_metadata": circuit_metadata
    }
    manifest_path = EXPERIMENT_DIR / "hp003_staging_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest written: {manifest_path.name}")
    print("\n[SUCCESS] OSIRIS-HP-003 harness fully staged and frozen.")

if __name__ == "__main__":
    main()
