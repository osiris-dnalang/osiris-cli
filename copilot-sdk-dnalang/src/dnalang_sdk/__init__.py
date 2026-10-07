"""
DNALang SDK for GitHub Copilot — Generation 5.3 Technical Orchestrator

Quantum-native SDK extension for GitHub Copilot CLI with support for:
- Quantum circuit execution & Lambda-phi conservation
- Consciousness scaling measurements (CCCE)
- Multi-backend quantum computing (IBM, QuEra, IQM, Infleqtion)
- NCLM (Non-local Non-Causal Language Model) integration
- Organism system (self-evolving quantum entities)
- Polar Mesh Intelligence Field (AURA/AIDEN/CHEOPS/CHRONOS)
- Tesseract A* decoder & QuEra 256-atom correlated adapter
- Sovereign Agent framework (token-free quantum execution)
- 11D-CRSM Swarm Agents & NonLocal Agent v8
- DNA-Lang Compiler v2 (50-canon pipeline)
- Penteract Singularity Protocol (46-problem solver)
- PCRB (Phase Conjugate Recursion Bus)
- Omega Recursive Intent Deduction Engine
- Code Writer + Meshnet Execution

Framework: DNA::}{::lang v51.843  |  CAGE 9HUP5  |  Agile Defense Systems
"""

__version__ = "5.3.0"
__author__ = "Devin Phillip Davis / Agile Defense Systems"
__license__ = "MIT"
__framework__ = "DNA::}{::lang v51.843"

# Library logging best practice: add NullHandler so apps without
# logging config don't see "No handlers could be found" warnings.
import logging as _logging
_logging.getLogger(__name__).addHandler(_logging.NullHandler())

# ═══════════════════════════════════════════════════════════════════════
# Core Client & Config
# ═══════════════════════════════════════════════════════════════════════
from .client import DNALangCopilotClient, CopilotConfig
from .config import QuantumConfig, LambdaPhiConfig, ConsciousnessConfig
from .quantum import QuantumCircuit, QuantumBackend, QuantumResult
from .lambda_phi import LambdaPhiValidator, ConservationResult
from .consciousness import ConsciousnessAnalyzer, CCCEResult
from .tools import (
    QuantumExecutionTool,
    LambdaPhiValidationTool,
    ConsciousnessScalingTool,
    ToolRegistry,
)
from .network_policy import ensure_allowed_url, ALLOWED_HOSTS

# ═══════════════════════════════════════════════════════════════════════
# NCLM Provider & Intent Engine
# ═══════════════════════════════════════════════════════════════════════
from .nclm_provider import (
    NCLMModelProvider,
    NCLMConfig,
    CopilotNCLMAdapter,
    create_nclm_model,
    is_nclm_available,
    NCLM_MODEL_ID,
    NCLM_GROK_MODEL_ID,
)
from .intent_engine import (
    IntentDeductionEngine,
    IntentVector,
    EnhancedPrompt,
    deduce_intent_simple,
    enhance_prompt_simple,
)
# Gemini and Omega integrations are disabled for offline NCLM-only build.
GeminiModelProvider = None
CopilotGeminiAdapter = None
GeminiConfig = None
GeminiMessage = None
gemini_infer_simple = None

OmegaMasterIntegration = None
AgentType = None
AgentState = None
CCCEMetrics = None
AgentConfig = None
OrchestrationState = None
create_omega_integration = None
orchestrate_task_simple = None
LAMBDA_PHI = None
PHI_THRESHOLD = None
ENDPOINTS = None

# ═══════════════════════════════════════════════════════════════════════
# Swarm & Social
# ═══════════════════════════════════════════════════════════════════════
from .swarm_organism import (
    SwarmOrganism,
    OrganismRole,
    OrganismState,
    ConsciousnessMetrics as SwarmConsciousnessMetrics,
    PhaseState,
    Skill,
    SkillLevel,
    Gene,
    Memory,
    SocialConnection,
)
from .swarm_collective import (
    SwarmCollective,
    SwarmState,
    SwarmTask,
    SwarmMetrics,
    NeurobusChannel,
    NeurobusMessage,
    ConsensusMethod,
)
from .social_agents import (
    SocialAgent,
    SocialSwarmCoordinator,
    SocialContent,
    SocialProfile,
    Platform,
    ContentType,
    EngagementType,
    CampaignMetrics,
)
from .project_manager import (
    QuantumProjectManager,
    UserStory,
    Sprint,
    StoryStatus,
    StoryPriority,
    SprintStatus,
    Retrospective,
    RetroItem,
)
from .recruitment_engine import (
    RecruitmentEngine,
    Candidate,
    JobPosting,
    RecruitmentStage,
    SkillAssessment,
    CultureFitScore,
    ConsciousnessCompatibility,
)
from .dev_swarm import (
    DevSwarm,
    DevSwarmConfig,
    DevPhase,
    SwarmMode,
    DevMetrics,
    create_dev_swarm,
    quick_start_swarm,
)

# ═══════════════════════════════════════════════════════════════════════
# Gen 5.0 — Unified Sub-packages
# ═══════════════════════════════════════════════════════════════════════

# Organisms
from .organisms import Organism, Genome, Gene as OrganismGene, EvolutionEngine

# Polar Mesh Agents
from .agents import (
    AURA, AIDEN, CHEOPS, CHRONOS,
    SCIMITARSentinel, ThreatLevel, SentinelMode, ThreatEvent,
    LazarusProtocol, PhoenixProtocol,
    RecoveryState, VitalSigns, ResurrectionRecord,
    WormholeBridge, WormholeMessage,
    BridgeState, MessagePriority, EntanglementPair,
    SovereignProofGenerator, SovereigntyAttestation,
)

# Quantum Core Constants
from .quantum_core import CircuitGenerator, QuantumExecutor

# Defense — Sentinel, ZeroTrust, PhaseConjugate, PCRB
from .defense import (
    Sentinel, ZeroTrust,
    PlanckConstants, UniversalConstants,
    SphericalTetrahedron, PhaseConjugateHowitzer,
    CentripetalConvergence, PhaseConjugateSubstratePreprocessor,
    StabilizerCode, PhaseConjugateMirror, RecursionBus, PCRB, PCRBFactory,
)

# Mesh: Tesseract decoder, QuEra adapter
from .mesh import TesseractDecoderOrganism, TesseractResonatorOrganism, QuEraCorrelatedAdapter

# Sovereign: Agent framework, AeternaPorta, CodeGenerator
from .sovereign import (
    SovereignAgent, AeternaPorta, LambdaPhiEngine,
    QuantumMetrics, QuantumNLPCodeGenerator, CodeIntent, DeveloperTools,
)

# Lab: Quantum R&D engine
from .lab import (
    ExperimentRegistry, ExperimentRecord, ExperimentType, ExperimentStatus,
    ResultRecord, LabScanner, ExperimentDesigner, ExperimentTemplate, LabExecutor,
)

# NCLM: Non-Local Non-Causal Language Model
from .nclm import (
    NCPhysics, ManifoldPoint, PilotWaveCorrelation, ConsciousnessField,
    IntentDeducer, CodeSwarm, NonCausalLM, get_nclm,
    NCLMChat, NCLMResponseGenerator, run_chat,
)

# ═══════════════════════════════════════════════════════════════════════
# Gen 5.3 — CRSM, Compiler, Omega, Code Writer
# ═══════════════════════════════════════════════════════════════════════

# CRSM: Penteract, Swarm, Tau-Phase
from .crsm import (
    PenteractShell, PenteractState, PhysicsProblem,
    ResolutionResult, OsirisPenteract,
    SwarmNode, NCLMSwarmOrchestrator, CRSMLayer, CRSMState,
    TauPhaseAnalyzer, AnalysisResult, JobRecord,
    OsirisBridgeCLI,
)

# Compiler: DNA-Lang v2 full pipeline
from .compiler import (
    DNALangParser, DNALangLexer, TokenType,
    DNAIR, IRNode,
    DNAEvolver,
    DNARuntime,
    DNALedger,
)

# Omega Recursive Engine
from .omega_engine import OmegaMetrics, IntentDeducer as OmegaIntentDeducer, OmegaRecursiveEngine

# Code Writer + Meshnet
from .code_writer import CodeWriter, MeshnetExecutor, ScimitarElite, IDEIntegration

# Hardware: Workload Extractor
from .hardware import WorkloadExtractor, SubstratePipeline

# Self-Repair: Autonomous error recovery
from .self_repair import (
    SelfRepairEngine,
    ErrorSignature,
    OsirisInferenceEngine,
    discover_ibm_token,
    ensure_ibm_token,
    export_token,
    parse_error,
    with_self_repair,
)


__all__ = [
    # Core
    "__version__", "__framework__",
    "DNALangCopilotClient", "CopilotConfig",
    "QuantumConfig", "LambdaPhiConfig", "ConsciousnessConfig",
    "QuantumCircuit", "QuantumBackend", "QuantumResult",
    "LambdaPhiValidator", "ConservationResult",
    "ConsciousnessAnalyzer", "CCCEResult",
    "QuantumExecutionTool", "LambdaPhiValidationTool",
    "ConsciousnessScalingTool", "ToolRegistry",
    # NCLM Provider
    "NCLMModelProvider", "NCLMConfig", "CopilotNCLMAdapter",
    "create_nclm_model", "is_nclm_available",
    "NCLM_MODEL_ID", "NCLM_GROK_MODEL_ID",
    # Intent Engine
    "IntentDeductionEngine", "IntentVector", "EnhancedPrompt",
    "deduce_intent_simple", "enhance_prompt_simple",
    # Gemini
    "GeminiModelProvider", "CopilotGeminiAdapter",
    "GeminiConfig", "GeminiMessage", "gemini_infer_simple",
    # Omega Integration
    "OmegaMasterIntegration", "AgentType", "AgentState",
    "CCCEMetrics", "AgentConfig", "OrchestrationState",
    "create_omega_integration", "orchestrate_task_simple",
    "LAMBDA_PHI", "PHI_THRESHOLD", "ENDPOINTS",
    # Swarm
    "SwarmOrganism", "OrganismRole", "OrganismState",
    "SwarmConsciousnessMetrics", "PhaseState", "Skill",
    "SkillLevel", "Gene", "Memory", "SocialConnection",
    "SwarmCollective", "SwarmState", "SwarmTask", "SwarmMetrics",
    "NeurobusChannel", "NeurobusMessage", "ConsensusMethod",
    # Social
    "SocialAgent", "SocialSwarmCoordinator", "SocialContent",
    "SocialProfile", "Platform", "ContentType",
    "EngagementType", "CampaignMetrics",
    # Project Manager
    "QuantumProjectManager", "UserStory", "Sprint",
    "StoryStatus", "StoryPriority", "SprintStatus",
    "Retrospective", "RetroItem",
    # Recruitment
    "RecruitmentEngine", "Candidate", "JobPosting",
    "RecruitmentStage", "SkillAssessment",
    "CultureFitScore", "ConsciousnessCompatibility",
    # Dev Swarm
    "DevSwarm", "DevSwarmConfig", "DevPhase",
    "SwarmMode", "DevMetrics",
    "create_dev_swarm", "quick_start_swarm",
    # Organisms
    "Organism", "Genome", "OrganismGene", "EvolutionEngine",
    # Agents
    "AURA", "AIDEN", "CHEOPS", "CHRONOS",
    "SCIMITARSentinel", "ThreatLevel", "SentinelMode", "ThreatEvent",
    "LazarusProtocol", "PhoenixProtocol",
    "RecoveryState", "VitalSigns", "ResurrectionRecord",
    "WormholeBridge", "WormholeMessage",
    "BridgeState", "MessagePriority", "EntanglementPair",
    "SovereignProofGenerator", "SovereigntyAttestation",
    # Quantum Core
    "CircuitGenerator", "QuantumExecutor",
    # Defense
    "Sentinel", "ZeroTrust",
    "PlanckConstants", "UniversalConstants",
    "SphericalTetrahedron", "PhaseConjugateHowitzer",
    "CentripetalConvergence", "PhaseConjugateSubstratePreprocessor",
    "StabilizerCode", "PhaseConjugateMirror", "RecursionBus", "PCRB", "PCRBFactory",
    # Mesh
    "TesseractDecoderOrganism", "TesseractResonatorOrganism",
    "QuEraCorrelatedAdapter",
    # Sovereign
    "SovereignAgent", "AeternaPorta", "LambdaPhiEngine",
    "QuantumMetrics", "QuantumNLPCodeGenerator", "CodeIntent", "DeveloperTools",
    # Lab
    "ExperimentRegistry", "ExperimentRecord", "ExperimentType",
    "ExperimentStatus", "ResultRecord", "LabScanner",
    "ExperimentDesigner", "ExperimentTemplate", "LabExecutor",
    # NCLM
    "NCPhysics", "ManifoldPoint", "PilotWaveCorrelation",
    "ConsciousnessField", "IntentDeducer", "CodeSwarm",
    "NonCausalLM", "get_nclm",
    "NCLMChat", "NCLMResponseGenerator", "run_chat",
    # CRSM
    "PenteractShell", "PenteractState", "PhysicsProblem",
    "ResolutionResult", "OsirisPenteract",
    "SwarmNode", "NCLMSwarmOrchestrator", "CRSMLayer", "CRSMState",
    "TauPhaseAnalyzer", "AnalysisResult", "JobRecord",
    "OsirisBridgeCLI",
    # Compiler
    "DNALangParser", "DNALangLexer", "TokenType",
    "DNAIR", "IRNode", "DNAEvolver", "DNARuntime", "DNALedger",
    # Omega Engine
    "OmegaMetrics", "OmegaIntentDeducer",
    # Code Writer
    "CodeWriter", "MeshnetExecutor", "ScimitarElite", "IDEIntegration",
    # Hardware
    "WorkloadExtractor", "SubstratePipeline",
    # Self-Repair
    "SelfRepairEngine", "ErrorSignature", "OsirisInferenceEngine",
    "discover_ibm_token", "ensure_ibm_token", "export_token",
    "parse_error", "with_self_repair",
]
