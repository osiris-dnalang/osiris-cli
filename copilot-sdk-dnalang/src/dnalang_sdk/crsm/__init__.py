"""CRSM subsystem — 11D Cognitive-Recursive State Manifold."""

from .penteract import (
    PenteractShell,
    PenteractState,
    PhysicsProblem,
    ResolutionResult,
    OsirisPenteract,
)
from .swarm_orchestrator import (
    SwarmNode,
    NCLMSwarmOrchestrator,
    CRSMLayer,
    CRSMState,
)
from .tau_phase_analyzer import TauPhaseAnalyzer, AnalysisResult, JobRecord
from .bridge_cli import OsirisBridgeCLI

# Lazy import for nonlocal_agent (heavy, circular-safe)
def get_nonlocal_agent():
    from .nonlocal_agent import BifurcatedSentinelOrchestrator
    return BifurcatedSentinelOrchestrator

__all__ = [
    "PenteractShell", "PenteractState", "PhysicsProblem",
    "ResolutionResult", "OsirisPenteract",
    "SwarmNode", "NCLMSwarmOrchestrator", "CRSMLayer", "CRSMState",
    "TauPhaseAnalyzer", "AnalysisResult", "JobRecord",
    "OsirisBridgeCLI",
    "get_nonlocal_agent",
]
