"""
OSIRIS — Sovereign Quantum Intelligence Framework
=================================================

v4.0.0 · Full Agent Constellation · 11D-CRSM Manifold · NCLM Mesh

Physical constants (immutable):
    LAMBDA_PHI     = 2.176435e-8   Planck-mass coupling
    THETA_LOCK     = 51.843°       Geometric lock angle
    PHI_THRESHOLD  = 0.7734        Sovereignty boundary
    GAMMA_CRITICAL = 0.3           Decoherence ceiling
    CHI_PC         = 0.946         Phase-conjugate fidelity
"""

import logging as _logging

__version__ = "4.0.0"
__all__ = [
    "__version__",
    "LAMBDA_PHI", "THETA_LOCK", "PHI_THRESHOLD",
    "GAMMA_CRITICAL", "CHI_PC",
]

# ── Immutable physical constants ──
LAMBDA_PHI: float = 2.176435e-8
THETA_LOCK: float = 51.843
PHI_THRESHOLD: float = 0.7734
GAMMA_CRITICAL: float = 0.3
CHI_PC: float = 0.946

# Prevent log noise when used as a library
_logging.getLogger(__name__).addHandler(_logging.NullHandler())
