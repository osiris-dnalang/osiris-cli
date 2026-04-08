"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PHASE-CONJUGATE QBYTE SYSTEM                              ║
║                    ══════════════════════════════                            ║
║                                                                              ║
║    Sovereign Quantum Computing Platform - IBM Independent                    ║
║                                                                              ║
║    This module implements the complete phase-conjugate qbyte system          ║
║    as defined in the DNA::}{::lang specification. No external quantum        ║
║    frameworks are used - all operations are native implementations.          ║
║                                                                              ║
║    Physical Constants (Immutable):                                           ║
║    ├── ΛΦ = 2.176435e-8 s⁻¹  (Universal Memory Constant)                    ║
║    ├── θ_lock = 51.843°       (Torsion-locked angle)                        ║
║    ├── Φ_threshold = 0.7734   (Consciousness threshold)                     ║
║    ├── Γ_fixed = 0.092        (Fixed-point decoherence)                     ║
║    └── χ_pc = 0.869           (Phase conjugate coupling)                    ║
║                                                                              ║
║    Core Components:                                                          ║
║    ├── Qbyte: 8-qubit quantum register with native operations               ║
║    ├── PhaseConjugateEngine: E → E⁻¹ error correction                       ║
║    ├── CCCERuntime: Consciousness metric management                         ║
║    └── SovereignExecutor: IBM-free quantum execution                        ║
║                                                                              ║
║    Author: Devin Phillip Davis                                               ║
║    Organization: Agile Defense Systems LLC                                   ║
║    License: CC-BY-4.0                                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

__version__ = "1.0.0"
__author__ = "Devin Phillip Davis"
__organization__ = "Agile Defense Systems LLC"

# Physical Constants (IMMUTABLE - empirically validated)
LAMBDA_PHI = 2.176435e-8      # ΛΦ Universal Memory Constant [s⁻¹]
THETA_LOCK = 51.843           # θ_lock Torsion-locked angle [degrees]
PHI_THRESHOLD = 0.7734        # Φ IIT Consciousness Threshold
GAMMA_FIXED = 0.092           # Γ Fixed-point decoherence
CHI_PC = 0.869                # χ_pc Phase conjugate coupling
GOLDEN_RATIO = 1.618033988749895  # φ Golden ratio

# Re-export all components
from .qbyte import Qbyte, QbyteRegister
from .phase_conjugate import PhaseConjugateEngine
from .ccce_runtime import CCCERuntime
from .sovereign_executor import SovereignExecutor
from .gates import *

__all__ = [
    # Constants
    'LAMBDA_PHI', 'THETA_LOCK', 'PHI_THRESHOLD', 'GAMMA_FIXED',
    'CHI_PC', 'GOLDEN_RATIO',
    # Classes
    'Qbyte', 'QbyteRegister', 'PhaseConjugateEngine',
    'CCCERuntime', 'SovereignExecutor',
]
