#!/usr/bin/env python3
"""
OSIRIS Hardware Mesh & Dual-Node Auto-Detection Engine
======================================================

Sovereign hardware detection and execution layer for the OSIRIS organism.
Dynamically classifies the execution substrate into:

- Node Alpha (Mobile): ARM64 Termux userland (e.g., Google Pixel Fold).
  * Constraints: Strict 300s temporal lock, aggressive AST sandboxing,
    memory-conscious allocation, NEON vectorization.
- Node Beta (Compute Laptop): x86_64 Intel Core i7 / Ultra 7 + Intel Arc Graphics.
  * Capabilities: Extended execution horizons, AVX2/AVX-VNNI tensor acceleration,
    Intel GPU/OpenVINO delegation, batch QPU simulation.

Invariant:
Coherence floor Gamma_floor = 0.092 and theta_lock = 51.843 degrees are
rigorously maintained across both physical nodes.
"""

from __future__ import annotations

import enum
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class NodeType(enum.Enum):
    ALPHA_MOBILE = "NODE_ALPHA_MOBILE"        # ARM64 Termux / Android Pixel Fold
    BETA_COMPUTE = "NODE_BETA_COMPUTE"        # x86_64 Intel Core i7/Ultra 7 + Arc Graphics
    GENERIC_EDGE = "NODE_GENERIC_EDGE"        # Unclassified POSIX node


@dataclass
class HardwareProfile:
    node_type: NodeType
    machine_arch: str
    cpu_model: str
    cpu_cores: int
    is_termux: bool
    is_android: bool
    has_intel_arc: bool
    has_neon: bool
    has_avx2: bool
    has_avx_vnni: bool
    execution_timeout_s: float
    allow_extended_horizons: bool
    coherence_floor: float = 0.092
    resonance_angle_deg: float = 51.843
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": self.node_type.value,
            "machine_arch": self.machine_arch,
            "cpu_model": self.cpu_model,
            "cpu_cores": self.cpu_cores,
            "is_termux": self.is_termux,
            "is_android": self.is_android,
            "has_intel_arc": self.has_intel_arc,
            "has_neon": self.has_neon,
            "has_avx2": self.has_avx2,
            "has_avx_vnni": self.has_avx_vnni,
            "execution_timeout_s": self.execution_timeout_s,
            "allow_extended_horizons": self.allow_extended_horizons,
            "coherence_floor": self.coherence_floor,
            "resonance_angle_deg": self.resonance_angle_deg,
            "metadata": self.metadata,
        }


class HardwareMeshDetector:
    """
    Auto-detects physical hardware capabilities and provisions the appropriate
    execution parameters for the OSIRIS organism.
    """

    @staticmethod
    def detect() -> HardwareProfile:
        arch = platform.machine().lower()
        system = platform.system().lower()
        cores = os.cpu_count() or 1

        # Check for Termux / Android indicators
        is_termux = bool(
            os.environ.get("TERMUX_VERSION") or
            os.path.exists("/data/data/com.termux") or
            "com.termux" in os.environ.get("PREFIX", "")
        )
        is_android = is_termux or os.path.exists("/system/build.prop") or "android" in system

        # Parse CPU info
        cpu_model = ""
        flags = set()
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("model name") and not cpu_model:
                            cpu_model = line.split(":", 1)[1].strip()
                        elif line.startswith("flags") or line.startswith("Features"):
                            flags.update(line.split(":", 1)[1].strip().split())
            except Exception:
                pass

        if not cpu_model:
            cpu_model = platform.processor() or "Unknown Processor"

        # Check vector instruction sets
        has_neon = ("neon" in flags or "asimd" in flags or arch in ("aarch64", "arm64"))
        has_avx2 = "avx2" in flags
        has_avx_vnni = "avx_vnni" in flags

        # Check for Intel Arc / Xe GPU
        has_intel_arc = False
        if "intel" in cpu_model.lower():
            # Lunar Lake / Meteor Lake / Core Ultra / Arc identifiers
            if any(k in cpu_model.lower() for k in ["ultra", "arc", "i7", "i9"]):
                has_intel_arc = True

        # Check render devices if accessible
        if os.path.exists("/dev/dri"):
            try:
                for entry in os.listdir("/dev/dri"):
                    if "render" in entry:
                        has_intel_arc = True
            except Exception:
                pass

        # Determine Node Classification
        if is_termux or is_android or arch in ("aarch64", "arm64"):
            node_type = NodeType.ALPHA_MOBILE
            timeout_s = 300.0  # Strict 300s lock for Termux
            extended = False
        elif arch in ("x86_64", "amd64") and ("intel" in cpu_model.lower() or has_intel_arc):
            node_type = NodeType.BETA_COMPUTE
            timeout_s = 1800.0  # Extended 30m horizon for high-compute Node Beta
            extended = True
        else:
            node_type = NodeType.GENERIC_EDGE
            timeout_s = 300.0
            extended = False

        return HardwareProfile(
            node_type=node_type,
            machine_arch=arch,
            cpu_model=cpu_model,
            cpu_cores=cores,
            is_termux=is_termux,
            is_android=is_android,
            has_intel_arc=has_intel_arc,
            has_neon=has_neon,
            has_avx2=has_avx2,
            has_avx_vnni=has_avx_vnni,
            execution_timeout_s=timeout_s,
            allow_extended_horizons=extended,
            coherence_floor=0.092,
            resonance_angle_deg=51.843,
            metadata={
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "detected_at": time.time(),
            }
        )


# Global singleton profile
CURRENT_PROFILE: HardwareProfile = HardwareMeshDetector.detect()


def get_current_profile() -> HardwareProfile:
    """Returns the cached singleton hardware profile."""
    return CURRENT_PROFILE


def is_node_alpha() -> bool:
    """Returns True if running on Node Alpha (ARM64 Mobile / Termux)."""
    return CURRENT_PROFILE.node_type == NodeType.ALPHA_MOBILE


def is_node_beta() -> bool:
    """Returns True if running on Node Beta (Intel Core i7/Ultra 7 + Arc Graphics)."""
    return CURRENT_PROFILE.node_type == NodeType.BETA_COMPUTE


if __name__ == "__main__":
    profile = HardwareMeshDetector.detect()
    print("=" * 65)
    print("OSIRIS HARDWARE MESH DETECTOR — TOPOLOGY REPORT")
    print("=" * 65)
    print(f"Classification  : {profile.node_type.value}")
    print(f"Machine Arch    : {profile.machine_arch}")
    print(f"CPU Model       : {profile.cpu_model}")
    print(f"Cores Available : {profile.cpu_cores}")
    print(f"Termux Userland : {profile.is_termux}")
    print(f"Intel Arc Accel : {profile.has_intel_arc}")
    print(f"AVX2 / AVX-VNNI : {profile.has_avx2} / {profile.has_avx_vnni}")
    print(f"NEON SIMD       : {profile.has_neon}")
    print(f"Timeout Horizon : {profile.execution_timeout_s}s (Extended={profile.allow_extended_horizons})")
    print(f"Coherence Floor : {profile.coherence_floor}")
    print(f"Resonance Lock  : {profile.resonance_angle_deg}°")
    print("=" * 65)
