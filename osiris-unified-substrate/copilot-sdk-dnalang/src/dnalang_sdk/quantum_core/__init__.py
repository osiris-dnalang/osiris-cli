"""DNA-Lang Quantum Core — circuits, constants, execution."""
from .constants import (
    LAMBDA_PHI, THETA_LOCK, THETA_PC_RAD, PHI_THRESHOLD,
    GAMMA_CRITICAL, CHI_PC, PHI_GOLDEN,
    PLANCK_LENGTH, PLANCK_TIME, PLANCK_MASS,
    HBAR, C, G, KB,
    ZENO_FREQ_DEFAULT, FLOQUET_FREQ_DEFAULT,
)
from .circuits import CircuitGenerator, to_circuit
from .execution import QuantumExecutor, QuantumResult

__all__ = [
    'LAMBDA_PHI', 'THETA_LOCK', 'THETA_PC_RAD', 'PHI_THRESHOLD',
    'GAMMA_CRITICAL', 'CHI_PC', 'PHI_GOLDEN',
    'PLANCK_LENGTH', 'PLANCK_TIME', 'PLANCK_MASS',
    'HBAR', 'C', 'G', 'KB',
    'ZENO_FREQ_DEFAULT', 'FLOQUET_FREQ_DEFAULT',
    'CircuitGenerator', 'to_circuit',
    'QuantumExecutor', 'QuantumResult',
]
