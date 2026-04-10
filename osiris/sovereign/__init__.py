"""osiris.sovereign — Sovereign execution and proofs."""

from .agent import SovereignAgent, AgentResult
from .quantum_engine import (
    AeternaPorta, LambdaPhiEngine, QuantumMetrics,
    LAMBDA_PHI_M, THETA_LOCK_DEG, PHI_THRESHOLD_FIDELITY,
    GAMMA_CRITICAL_RATE, CHI_PC_QUALITY,
)
from .code_generator import QuantumNLPCodeGenerator, CodeIntent, CodeGenerationResult
from .dev_tools import DeveloperTools, FileSearchResult, CodeAnalysisResult

def get_enhanced_agent():
    from .agent import SovereignAgent
    return SovereignAgent
