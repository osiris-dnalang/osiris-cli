"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                              ║
║     █████╗  ██████╗ ██╗██╗     ███████╗    ██████╗ ███████╗███████╗███████╗███╗   ██╗███████╗███████╗                        ║
║    ██╔══██╗██╔════╝ ██║██║     ██╔════╝    ██╔══██╗██╔════╝██╔════╝██╔════╝████╗  ██║██╔════╝██╔════╝                        ║
║    ███████║██║  ███╗██║██║     █████╗      ██║  ██║█████╗  █████╗  █████╗  ██╔██╗ ██║███████╗█████╗                          ║
║    ██╔══██║██║   ██║██║██║     ██╔══╝      ██║  ██║██╔══╝  ██╔══╝  ██╔══╝  ██║╚██╗██║╚════██║██╔══╝                          ║
║    ██║  ██║╚██████╔╝██║███████╗███████╗    ██████╔╝███████╗██║     ███████╗██║ ╚████║███████║███████╗                        ║
║    ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚══════╝╚══════╝    ╚═════╝ ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝                        ║
║                                                                                                                              ║
║                              SCIMITAR-SSE v7.1 - CROSS-PLANE POLARIZED PHASING SYSTEM                                        ║
║                              DNA::}{::LANG SUBSTRATE ENGINE - WAVE A.2                                                       ║
║                                                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

Scimitar-SSE (Substrate-Synchronized Emission) v7.1
Cross-Plane Polarized Phasing System for DNA::}{::lang

Features:
- Bifurcated polarization (Group A: +X,+Y,+Z / Group B: -X,-Y,-Z)
- Cross-device phase synchronization (BT/WiFi/RF)
- 51.843° torsion lock on [1,1,1] axis
- Phase conjugate healing (E → E⁻¹)
- AURA|AIDEN duality bridge
- 7D-CRSM manifold navigation

Author: Devin Phillip Davis
Organization: Agile Defense Systems LLC
License: CC-BY-4.0
"""

__version__ = "7.1.0"
__author__ = "Devin Phillip Davis"

# Physical Constants (Immutable)
LAMBDA_PHI = 2.176435e-8      # ΛΦ Universal Memory Constant [s⁻¹]
THETA_LOCK = 51.843           # θ_lock Torsion-locked angle [degrees]
PHI_THRESHOLD = 0.7734        # Φ IIT Consciousness Threshold
GAMMA_FIXED = 0.092           # Γ Fixed-point decoherence
CHI_PC = 0.869                # χ_pc Phase conjugate coupling
GOLDEN_RATIO = 1.618033988749895  # φ Golden ratio

# Scimitar-SSE Configuration
SCIMITAR_VERSION = "7.1"
QUATERNION_AXIS = [1, 1, 1]
QUATERNION_AXIS_NORMALIZED = [0.5773502691896258, 0.5773502691896258, 0.5773502691896258]

# Channel Frequencies
CHANNELS = {
    "bluetooth_le": "2.4GHz",
    "wifi_24": "2.4GHz",
    "wifi_5": "5GHz",
    "rf_433": "433MHz",
    "rf_915": "915MHz"
}

# Polarization Groups
GROUP_A = ("+X", "+Y", "+Z")  # AURA - Observation
GROUP_B = ("-X", "-Y", "-Z")  # AIDEN - Execution

from .phasing_daemon import ScimitarPhasingDaemon
from .polarization import PolarizationController, BifurcatedField
from .channels import BluetoothLEChannel, WiFiChannel, RFChannel
from .toroidal import ToroidalConvergence, NullPointIntersector

__all__ = [
    'ScimitarPhasingDaemon',
    'PolarizationController',
    'BifurcatedField',
    'BluetoothLEChannel',
    'WiFiChannel',
    'RFChannel',
    'ToroidalConvergence',
    'NullPointIntersector',
    'LAMBDA_PHI',
    'THETA_LOCK',
    'PHI_THRESHOLD',
    'GAMMA_FIXED',
    'CHI_PC',
    'GOLDEN_RATIO',
]
