#!/usr/bin/env python3
"""
OSIRIS Sovereign CAD & Additive Manufacturing Invariants
=========================================================
Formal definitions for geometric, kinematic, slicer, and multi-material invariants.
Enforces SYS-021: Zero self-supplied authorization & deterministic dimensional bounds.

Copyright (c) 2026 Devin Phillip Davis / Agile Defense Systems LLC
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class MaterialFamily(str, Enum):
    PLA = "PLA"
    PETG = "PETG"
    TPU = "TPU"
    ABS = "ABS"
    ASA = "ASA"
    PLA_CF = "PLA-CF"
    SUPPORT_MATERIAL = "SUPPORT"


@dataclass(frozen=True)
class ThermalFlowProfile:
    family: MaterialFamily
    nozzle_temp_c_min: int
    nozzle_temp_c_max: int
    bed_temp_c: int
    max_volumetric_speed_mm3_s: float
    flow_ratio: float
    retraction_length_mm: float
    chamber_fan_speed_pct: int


# Fleet calibrated profiles matching Bambu Lab X1C / P1S / A1 Mini / ZEUS
FLEET_THERMAL_PROFILES: Dict[MaterialFamily, ThermalFlowProfile] = {
    MaterialFamily.PLA: ThermalFlowProfile(
        family=MaterialFamily.PLA,
        nozzle_temp_c_min=205,
        nozzle_temp_c_max=225,
        bed_temp_c=55,
        max_volumetric_speed_mm3_s=21.0,
        flow_ratio=0.98,
        retraction_length_mm=0.8,
        chamber_fan_speed_pct=80,
    ),
    MaterialFamily.PETG: ThermalFlowProfile(
        family=MaterialFamily.PETG,
        nozzle_temp_c_min=235,
        nozzle_temp_c_max=255,
        bed_temp_c=70,
        max_volumetric_speed_mm3_s=12.0,
        flow_ratio=0.95,
        retraction_length_mm=1.0,
        chamber_fan_speed_pct=50,
    ),
    MaterialFamily.TPU: ThermalFlowProfile(
        family=MaterialFamily.TPU,
        nozzle_temp_c_min=210,
        nozzle_temp_c_max=230,
        bed_temp_c=45,
        max_volumetric_speed_mm3_s=3.5,
        flow_ratio=0.98,
        retraction_length_mm=0.4,
        chamber_fan_speed_pct=40,
    ),
    MaterialFamily.ABS: ThermalFlowProfile(
        family=MaterialFamily.ABS,
        nozzle_temp_c_min=240,
        nozzle_temp_c_max=270,
        bed_temp_c=90,
        max_volumetric_speed_mm3_s=15.0,
        flow_ratio=0.96,
        retraction_length_mm=0.8,
        chamber_fan_speed_pct=0,
    ),
}


@dataclass(frozen=True)
class BeamInterlockingConfig:
    """Bambu Studio Beam Interlocking parameters for rigid-soft or multi-color boundaries."""
    enabled: bool = True
    beam_width_mm: float = 0.8
    orientation_deg: float = 22.5
    beam_layers: int = 2
    interlocking_depth: int = 2
    boundary_avoidance_mm: float = 2.0


@dataclass(frozen=True)
class FoldableCaseTolerances:
    """Tolerances for foldable devices (Google Pixel 10 Pro Fold: 155.2 x 76.3 x 10.8 mm)."""
    hinge_spine_clearance_min_mm: float = 0.40
    hinge_spine_clearance_max_mm: float = 0.80
    snap_fit_lip_overhang_min_mm: float = 0.50
    snap_fit_lip_overhang_max_mm: float = 0.80
    button_port_radial_clearance_mm: float = 0.30
    rigid_wall_thickness_min_mm: float = 1.20
    rigid_wall_thickness_max_mm: float = 1.60
    tpu_bumper_thickness_min_mm: float = 1.80
    tpu_bumper_thickness_max_mm: float = 2.00
    bottom_inlay_depth_max_mm: float = 0.64  # First 4 layers at 0.16mm layer height


@dataclass(frozen=True)
class ArticulatedSpecimenInvariants:
    """Metrological invariants for the Articulated Rainbow Trout reference design."""
    total_shells: int = 10
    axial_joints_count: int = 7
    nominal_axial_clearance_mm: float = 0.7931
    dorsal_scale_overlap_clearance_mm: float = 0.4421
    registration_pin_lateral_clearance_mm: float = 0.1000
    registration_pin_axial_clearance_mm: float = 1.1000
    medial_plane_z_bed_mm: float = 0.0000
    scale_crown_relief_baseline_mm: float = 0.2835
    scale_crown_relief_target_mm: float = 0.5282  # Target amplified relief (+86.3%)
    eye_corneal_dome_relief_mm: float = 0.3200
    eye_iris_sulcus_relief_mm: float = -0.0800


def evaluate_flushing_volume(from_material: MaterialFamily, to_material: MaterialFamily) -> int:
    """Calculate required purge volume (mm3) for zero cross-contamination."""
    if from_material == to_material:
        return 180  # Default intra-material color swap baseline
    if from_material == MaterialFamily.PETG and to_material == MaterialFamily.TPU:
        return 420  # High-temp copolyester -> soft elastomer purge
    if from_material == MaterialFamily.TPU and to_material == MaterialFamily.PETG:
        return 450  # Complete elastomer purge to prevent PETG delamination
    if from_material == MaterialFamily.PLA and to_material == MaterialFamily.SUPPORT_MATERIAL:
        return 280
    return 300
