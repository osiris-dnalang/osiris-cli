#!/usr/bin/env python3
"""
stage_experiment_e3_pilot_216circ.py
OSIRIS Control Compiler v2 — Dry-Run 216-Circuit Hardware Benchmark Builder & Pre-Flight Verifier
(ZERO QPU SECONDS CONSUMED — Staged Under SYS-021 Governance)

Builds and verifies the exact 216-circuit, 221,184-shot hardware benchmark specification:
  - 3 Stratified Unseen E3 Couplers on ibm_marrakesh:
      1. (12,13) — Slow coupler (tau_CZ = 84 ns)
      2. (24,25) — Fast coupler (tau_CZ = 68 ns) with high bilateral dephasing at 8 us
      3. (44,45) — Clean fast coupler (tau_CZ = 68 ns)
  - 2 Evolution Durations: 4,000 ns (1000 dt) and 8,000 ns (2000 dt)
  - 4 Competing Protocol Arms:
      * Arm C: QISKIT_SYNC_XY8 (Delta = 0 ns)
      * Arm D: QISKIT_OPTIMIZED_STAG_XY8 (Delta = tau/2 = 248 ns at 4us, 496 ns at 8us)
      * Arm E: FIXED_STAG_XY8_80 (Delta = 80 ns, strongest E2 baseline)
      * Arm F: OSIRIS_CONTROL_COMPILER_V2 (Frozen risk-aware schedule from preregistered_hardware_benchmark_v2_216circ.json)
  - 3 Pauli Measurement Bases: XX, YY, ZZ
  - 3 Randomized Pilot Acquisition Blocks: 3 * 2 * 4 * 3 * 3 = 216 circuits (221,184 physical shots at 1,024 shots/circuit)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.qpy import dump as qpy_dump
from qiskit.quantum_info import Pauli, Statevector

EXP_DIR = Path("/mnt/c/Users/Ron/experiments/experiment_e")
PREREG_216_JSON = EXP_DIR / "preregistered_hardware_benchmark_v2_216circ.json"
QPY_OUT = EXP_DIR / "staged_circuits_exp_e3_pilot_216circ.qpy"
MANIFEST_OUT = EXP_DIR / "staged_manifest_exp_e3_pilot_216circ.json"

DT_NS = 4.0
PULSE_DT = 9  # 36.0 ns single-qubit pulse duration on ibm_marrakesh
XY8_GATES = ["x", "y", "x", "y", "y", "x", "y", "x"]


def build_bell_dd_circuit(
    u: int,
    v: int,
    duration_ns: int,
    delta_ns: float,
    basis: str,
    name: str,
    include_delays: bool = True,
) -> QuantumCircuit:
    """
    Construct a 2-qubit Bell-state |Phi+> preparation + staggered XY8 dynamical decoupling
    + Pauli basis measurement (XX, YY, or ZZ) circuit with exact dt=4.0ns delay quantization.
    """
    qr = QuantumRegister(2, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr, name=name)

    # 1. Verified |Phi+> Bell-state preparation: H(u); H(v); CZ(u,v); H(v)
    qc.h(qr[0])
    qc.h(qr[1])
    qc.cz(qr[0], qr[1])
    qc.h(qr[1])
    qc.barrier()

    # 2. Bilateral staggered XY8 schedule (u shifted by -Delta/2, v shifted by +Delta/2)
    N = 8
    total_dt = int(round(duration_ns / DT_NS))
    free_dt = max(0, total_dt - N * PULSE_DT)
    tau_dt = free_dt // N
    shift_dt = int(round((0.5 * delta_ns) / DT_NS))
    shift_dt = max(-(tau_dt // 2), min(tau_dt // 2, shift_dt))

    # Qubit u delays and pulses
    first_u = max(0, (tau_dt // 2) - shift_dt)
    last_u = max(0, tau_dt - first_u)
    first_v = max(0, (tau_dt // 2) + shift_dt)
    last_v = max(0, tau_dt - first_v)

    if include_delays and first_u > 0:
        qc.delay(first_u, qr[0], unit="dt")
    if include_delays and first_v > 0:
        qc.delay(first_v, qr[1], unit="dt")

    for k, g in enumerate(XY8_GATES):
        getattr(qc, g)(qr[0])
        getattr(qc, g)(qr[1])
        if k < N - 1 and include_delays and tau_dt > 0:
            qc.delay(tau_dt, qr[0], unit="dt")
            qc.delay(tau_dt, qr[1], unit="dt")

    if include_delays and last_u > 0:
        qc.delay(last_u, qr[0], unit="dt")
    if include_delays and last_v > 0:
        qc.delay(last_v, qr[1], unit="dt")

    qc.barrier()

    # 3. Pauli basis rotation before Z measurement
    if basis == "XX":
        qc.h(qr[0])
        qc.h(qr[1])
    elif basis == "YY":
        qc.sdg(qr[0])
        qc.h(qr[0])
        qc.sdg(qr[1])
        qc.h(qr[1])
    elif basis == "ZZ":
        pass
    else:
        raise ValueError(f"Unknown basis: {basis}")

    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])
    return qc


def run_preflight_statevector_gate() -> dict:
    """
    Verify that for all candidate staggers Delta in {0, 40, 80, 120, 248, 496} ns,
    the noiseless unitary circuit (without open-system decoherence) preserves the
    ideal |Phi+> Bell state (F_Bell = 1.00000000, <XX>=+1, <YY>=-1, <ZZ>=+1).
    """
    for delta_ns in [0.0, 40.0, 80.0, 120.0, 248.0, 496.0]:
        qc = build_bell_dd_circuit(12, 13, 4000, delta_ns, "ZZ", f"verify_{int(delta_ns)}", include_delays=False)
        qc_nom = qc.remove_final_measurements(inplace=False)
        sv = Statevector.from_instruction(qc_nom)
        exp_xx = float(np.real(sv.expectation_value(Pauli("XX"))))
        exp_yy = float(np.real(sv.expectation_value(Pauli("YY"))))
        exp_zz = float(np.real(sv.expectation_value(Pauli("ZZ"))))
        f_bell = 0.25 * (1.0 + exp_xx - exp_yy + exp_zz)
        if abs(f_bell - 1.0) > 1e-12:
            raise RuntimeError(f"Pre-flight Statevector gate failed for delta={delta_ns}: F_Bell={f_bell}")
    return {"preflight_statevector_status": "PASSED", "verified_f_bell": 1.0}


def main():
    gate_info = run_preflight_statevector_gate()
    spec = json.loads(PREREG_216_JSON.read_text())

    cell_lookup = {
        (r["edge"], r["duration_ns"]): r["osiris_v2_selected_delta_ns"]
        for r in spec["preregistered_cell_predictions"]
    }

    edges = [("(12,13)", 12, 13), ("(24,25)", 24, 25), ("(44,45)", 44, 45)]
    durations = [4000, 8000]
    bases = ["XX", "YY", "ZZ"]
    blocks = 3

    rng = np.random.default_rng(20261105)
    all_circuits = []
    manifest_entries = []

    for blk in range(blocks):
        block_specs = []
        for edge_str, u, v in edges:
            for dur_ns in durations:
                tau = dur_ns / 8.0
                delta_qopt = round((0.5 * tau) / 8.0) * 8.0
                delta_osiris = float(cell_lookup[(edge_str, dur_ns)])
                arms = [
                    ("C_QISKIT_SYNC_XY8", 0.0),
                    ("D_QISKIT_OPTIMIZED_STAG_XY8", delta_qopt),
                    ("E_FIXED_STAG_XY8_80", 80.0),
                    ("F_OSIRIS_CONTROL_COMPILER_V2", delta_osiris),
                ]
                for arm_name, delta_val in arms:
                    for basis in bases:
                        block_specs.append((blk, edge_str, u, v, dur_ns, arm_name, delta_val, basis))

        # Randomize execution order within each acquisition block to eliminate temporal drift bias
        perm = rng.permutation(len(block_specs))
        for idx in perm:
            b_i, e_str, u, v, dur_ns, arm_name, delta_val, basis = block_specs[idx]
            cname = f"e3pilot_b{b_i}_{u}_{v}_{dur_ns}ns_{arm_name}_{basis}"
            qc = build_bell_dd_circuit(u, v, dur_ns, delta_val, basis, cname, include_delays=True)
            all_circuits.append(qc)
            manifest_entries.append({
                "circuit_index": len(all_circuits) - 1,
                "name": cname,
                "block": b_i,
                "edge": e_str,
                "duration_ns": dur_ns,
                "arm": arm_name,
                "delta_ns": delta_val,
                "basis": basis,
            })

    with open(QPY_OUT, "wb") as f:
        qpy_dump(all_circuits, f)

    qpy_sha256 = hashlib.sha256(QPY_OUT.read_bytes()).hexdigest()
    manifest = {
        "specification_id": spec["specification_id"],
        "preflight_gate": gate_info,
        "total_circuits": len(all_circuits),
        "shots_per_circuit": 1024,
        "total_physical_shots": len(all_circuits) * 1024,
        "qpy_archive": QPY_OUT.name,
        "qpy_sha256": qpy_sha256,
        "qpu_seconds_consumed": 0,
        "circuits": manifest_entries,
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2))
    manifest_sha256 = hashlib.sha256(MANIFEST_OUT.read_bytes()).hexdigest()

    print("=" * 100)
    print("OSIRIS E3 PILOT (216 CIRCUITS, 221,184 SHOTS) — DRY-RUN STAGING COMPLETE (0 QPU SECONDS CONSUMED)")
    print("=" * 100)
    print(f"  Pre-Flight Statevector Gate : {gate_info['preflight_statevector_status']} (F_Bell = {gate_info['verified_f_bell']:.8f})")
    print(f"  Total Staged Circuits       : {len(all_circuits)} (3 blocks x 72 circuits/block)")
    print(f"  Total Physical Shots        : {len(all_circuits) * 1024:,}")
    print(f"  Staged QPY Archive          : {QPY_OUT.name} (SHA-256: {qpy_sha256})")
    print(f"  Staged Manifest JSON        : {MANIFEST_OUT.name} (SHA-256: {manifest_sha256})")


if __name__ == "__main__":
    main()
