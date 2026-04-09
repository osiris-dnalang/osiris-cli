#!/usr/bin/env python3
"""
OSIRIS Smoke Tests — Validate all modules load and core functions execute.
"""

import sys
import traceback

PASS = 0
FAIL = 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  PASS  {name}")
        PASS += 1
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        traceback.print_exc()
        FAIL += 1


# ── Module imports ──────────────────────────────────────────────────

def t_import_forge():
    from osiris_forge import (
        OsirisForge, PrinterHardware, ForgeJob, ForgeResult,
        CentauriCarbon2Bridge, ShannonMapGenerator, GCodeSanitizer,
        PRINTER_PROFILES, PrinterProfile,
    )
    assert PrinterHardware.ELEGOO_CC2.value == "elegoo_cc2"
    profile = PRINTER_PROFILES[PrinterHardware.ELEGOO_CC2]
    assert profile.max_nozzle_temp == 350
    assert profile.supports_canvas is True
    assert profile.canvas_extruders == 4
    assert profile.enclosed is True
    assert profile.ai_camera is True
    assert profile.firmware == "klipper"
    assert profile.protocol == "moonraker"

def t_import_bridges():
    from osiris_physics_bridges import (
        PropulsionBridge, EnergyBridge, CosmologicalBridge,
        BridgeExecutor, BridgeReport, BridgeResult,
    )

def t_import_torsion():
    from osiris_torsion_core_py import (
        Quaternion, dielectric_lock_energy, torsion_coupling_strength,
        negentropic_efficiency, tetrahedral_vertices,
        poynting_flux_torsion, tetrahedral_resonance_freq,
        substrate_pressure,
    )


# ── Torsion Core functions ──────────────────────────────────────────

def t_torsion_quaternion():
    from osiris_torsion_core_py import Quaternion
    q = Quaternion(1, 0, 0, 0)
    assert abs(q.norm() - 1.0) < 1e-10
    q2 = q.multiply(q)
    assert abs(q2.w - 1.0) < 1e-10

def t_torsion_dielectric():
    from osiris_torsion_core_py import dielectric_lock_energy, THETA_LOCK
    e_at_lock = dielectric_lock_energy(THETA_LOCK)
    assert e_at_lock < 1e-20, "Energy at lock angle should be ~0"
    e_off = dielectric_lock_energy(90.0)
    assert e_off > 0, "Energy off-lock should be positive"

def t_torsion_poynting():
    from osiris_torsion_core_py import poynting_flux_torsion
    flux = poynting_flux_torsion(0.05, 0.031, 4.5, 1000.0, n_samples=16)
    assert flux > 0, f"Poynting flux should be positive, got {flux}"

def t_torsion_resonance():
    from osiris_torsion_core_py import tetrahedral_resonance_freq
    f1 = tetrahedral_resonance_freq(0.01, 4.5, mode_n=1)
    assert f1 > 1e6, f"Resonance should be > 1 MHz, got {f1}"
    f2 = tetrahedral_resonance_freq(0.01, 4.5, mode_n=2)
    assert abs(f2 / f1 - 2.0) < 1e-10, "f2 should be 2*f1"

def t_torsion_substrate():
    from osiris_torsion_core_py import substrate_pressure
    p0 = substrate_pressure(0, 1e-10, 1e20)
    assert p0 > 0
    p_far = substrate_pressure(1e22, 1e-10, 1e20)
    assert p_far < p0, "Pressure should decrease with distance"


# ── Physics Bridges ─────────────────────────────────────────────────

def t_propulsion_bridge():
    from osiris_physics_bridges import PropulsionBridge
    bridge = PropulsionBridge()
    results = bridge.compute(assembly_mass=1.0, n_bootstrap=50)
    assert len(results) == 3
    assert results[0].bridge == "Propulsion"
    assert results[0].unit == "W"
    assert results[0].p_value is not None

def t_energy_bridge():
    from osiris_physics_bridges import EnergyBridge
    bridge = EnergyBridge()
    results = bridge.compute()
    assert len(results) == 5
    assert results[0].bridge == "Energy"
    freqs = bridge.resonance_frequencies()
    assert len(freqs) == 20

def t_cosmological_bridge():
    from osiris_physics_bridges import CosmologicalBridge
    bridge = CosmologicalBridge()
    results = bridge.compute()
    assert len(results) == 4
    assert results[0].bridge == "Cosmological"
    curve = bridge.rotation_curve(n_points=20)
    assert len(curve["radii_kpc"]) == 20

def t_bridge_executor():
    from osiris_physics_bridges import BridgeExecutor
    ex = BridgeExecutor()
    report = ex.run_all()
    assert len(report.results) == 12  # 3 + 5 + 4
    summary = report.summary()
    assert "Propulsion" in summary
    assert "Energy" in summary
    assert "Cosmological" in summary


# ── Forge CC2 ───────────────────────────────────────────────────────

def t_forge_cc2_profile():
    from osiris_forge import PrinterHardware, PRINTER_PROFILES
    p = PRINTER_PROFILES[PrinterHardware.ELEGOO_CC2]
    assert p.build_volume_mm == (320, 320, 350)
    assert p.supports_canvas is True
    assert p.canvas_extruders == 4

def t_forge_cc2_bridge_classify():
    from osiris_forge import CentauriCarbon2Bridge
    mapping = CentauriCarbon2Bridge.CANVAS_SHANNON_MAP
    assert len(mapping) == 4
    assert mapping[0]["role"] == "structural"
    assert mapping[1]["role"] == "bifurcation"
    assert mapping[2]["role"] == "entropy_suppression"

def t_forge_shannon_classify():
    from osiris_forge import ShannonMapGenerator
    gen = ShannonMapGenerator("nonexistent.csv")
    assert gen.classify_extruder(5.0, "PhaseTransition") == 1
    assert gen.classify_extruder(-3.0, "EntropySuppression") == 2
    assert gen.classify_extruder(0.5, "periodic") == 3
    assert gen.classify_extruder(0.5, "none") == 0

def t_forge_canvas_header():
    from osiris_forge import ShannonMapGenerator
    gen = ShannonMapGenerator("test.csv")
    header = gen.generate_canvas_gcode_header()
    assert "CANVAS" in header
    assert "T0:" in header
    assert "PA-CF" in header
    assert "G28" in header

def t_forge_job_cc2():
    from osiris_forge import ForgeJob, PrinterHardware
    job = ForgeJob(
        target_printer=PrinterHardware.ELEGOO_CC2,
        geometry="tetrahedral_lattice",
        scale_cm=10.0,
    )
    assert job.layer_height == 0.20
    assert job.job_id  # auto-generated


# ── Run all tests ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  OSIRIS Smoke Tests")
    print("=" * 60 + "\n")

    tests = [
        ("Import: osiris_forge", t_import_forge),
        ("Import: osiris_physics_bridges", t_import_bridges),
        ("Import: osiris_torsion_core_py", t_import_torsion),
        ("Torsion: Quaternion ops", t_torsion_quaternion),
        ("Torsion: Dielectric lock energy", t_torsion_dielectric),
        ("Torsion: Poynting flux", t_torsion_poynting),
        ("Torsion: Resonance frequency", t_torsion_resonance),
        ("Torsion: Substrate pressure", t_torsion_substrate),
        ("Bridge: Propulsion", t_propulsion_bridge),
        ("Bridge: Energy", t_energy_bridge),
        ("Bridge: Cosmological", t_cosmological_bridge),
        ("Bridge: Executor (all 3)", t_bridge_executor),
        ("Forge: CC2 profile", t_forge_cc2_profile),
        ("Forge: CC2 bridge classify", t_forge_cc2_bridge_classify),
        ("Forge: Shannon classifier", t_forge_shannon_classify),
        ("Forge: CANVAS G-code header", t_forge_canvas_header),
        ("Forge: ForgeJob CC2", t_forge_job_cc2),
    ]

    for name, fn in tests:
        test(name, fn)

    print(f"\n{'=' * 60}")
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}\n")

    sys.exit(1 if FAIL > 0 else 0)
