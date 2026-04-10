"""osiris.crsm — 11D Conformal Recursive Sovereign Manifold."""

from .swarm_orchestrator import (
    CRSMLayer,
    CRSMState,
    SwarmNode,
    NodeRole,
    NCLMSwarmOrchestrator,
    LAMBDA_PHI_M,
    THETA_LOCK_DEG,
    PHI_THRESHOLD,
    GAMMA_CRITICAL,
    CHI_PC_QUALITY,
)
from .penteract import (
    PenteractShell,
    PenteractState,
    PhysicsProblem,
    ProblemType,
    ResolutionResult,
    ResolutionMechanism,
    OsirisPenteract,
    AURAObserver,
    AIDENExecutor,
    ResolutionEngine,
)
from .tau_phase_analyzer import (
    TauPhaseAnalyzer,
    AnalysisResult,
    JobRecord,
    SweepPoint,
)
from .bridge_cli import OsirisBridgeCLI


def get_nonlocal_agent():
    """Lazy import to avoid circular dependencies."""
    from .nonlocal_agent import BifurcatedSentinelOrchestrator
    return BifurcatedSentinelOrchestrator


__all__ = [
    "CRSMLayer", "CRSMState", "SwarmNode", "NodeRole", "NCLMSwarmOrchestrator",
    "PenteractShell", "PenteractState", "PhysicsProblem", "ProblemType",
    "ResolutionResult", "ResolutionMechanism", "OsirisPenteract",
    "AURAObserver", "AIDENExecutor", "ResolutionEngine",
    "TauPhaseAnalyzer", "AnalysisResult", "JobRecord", "SweepPoint",
    "OsirisBridgeCLI", "get_nonlocal_agent",
    "LAMBDA_PHI_M", "THETA_LOCK_DEG", "PHI_THRESHOLD", "GAMMA_CRITICAL", "CHI_PC_QUALITY",
]
