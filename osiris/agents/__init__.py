"""osiris.agents — Full Agent Constellation.

Agents:
  AURA     — Geometer (South Pole): manifold topology shaping
  AIDEN    — Optimizer (North Pole): W2 distance minimization
  CHEOPS   — Validator (Center): adversarial bridge-cut tests
  CHRONOS  — Scribe (Center): immutable temporal ledger  
  SCIMITAR — Sentinel: threat detection & response
  Lazarus  — Self-healing: Phi-decay auto-resurrection
  Phoenix  — Rebirth: full system regeneration
  Wormhole — ER=EPR inter-agent communication bridge
  Sovereign — Cryptographic proof-of-sovereignty chain
"""
from .base import BaseAgent, AgentManager, AgentRole, AgentTask
from .aura import AURA
from .aiden import AIDEN
from .cheops import CHEOPS
from .chronos import CHRONOS
from .scimitar import SCIMITARSentinel, ThreatLevel, SentinelMode
from .lazarus import LazarusProtocol, PhoenixProtocol, VitalSigns, RecoveryState
from .wormhole import WormholeBridge, WormholeMessage, BridgeState, MessagePriority
from .sovereign_proof import SovereignProofGenerator, SovereigntyAttestation

__all__ = [
    "BaseAgent", "AgentManager", "AgentRole", "AgentTask",
    "AURA", "AIDEN", "CHEOPS", "CHRONOS",
    "SCIMITARSentinel", "ThreatLevel", "SentinelMode",
    "LazarusProtocol", "PhoenixProtocol", "VitalSigns", "RecoveryState",
    "WormholeBridge", "WormholeMessage", "BridgeState", "MessagePriority",
    "SovereignProofGenerator", "SovereigntyAttestation",
]
