"""
NonLocalAgent — Bifurcated Sentinel Orchestrator
=================================================

Integrates AIDEN, AURA, OMEGA, CHRONOS into a bifurcated tetrahedral
constellation with cross-plane coordination and entanglement pairs.

Framework: DNA::}{::lang v51.843
"""

import math
import time
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from .swarm_orchestrator import (
    CRSMLayer,
    CRSMState,
    THETA_LOCK_DEG,
    PHI_THRESHOLD,
    GAMMA_CRITICAL,
    CCCE_THRESHOLD,
)

logger = logging.getLogger("nonlocal_agent")

GOLDEN_RATIO = 1.618034
TAU_COHERENCE_US = 46.9787
BELL_FIDELITY_TARGET = 0.869
NEGENTROPY_CONSCIOUS = 11.2


class CRSMDimension(Enum):
    T = "temporal"
    I_UP = "information_up"
    I_DOWN = "information_down"
    R = "reality"
    LAMBDA = "coherence"
    PHI = "consciousness"
    OMEGA = "autopoietic"


@dataclass
class ManifoldPoint:
    t: float = 0.0
    i_up: float = 0.0
    i_down: float = 0.0
    r: float = 0.0
    lam: float = 0.0
    phi: float = 0.0
    omega: float = 0.0

    def as_vector(self) -> Tuple[float, ...]:
        return (self.t, self.i_up, self.i_down, self.r, self.lam, self.phi, self.omega)

    def norm(self) -> float:
        return math.sqrt(sum(x * x for x in self.as_vector()))

    def distance(self, other: 'ManifoldPoint') -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(self.as_vector(), other.as_vector())))


class AgentName(Enum):
    AIDEN = "aiden"
    AURA = "aura"
    OMEGA = "omega"
    CHRONOS = "chronos"


class PlaneType(Enum):
    LOCAL = "local"
    MESH = "mesh"
    WIFI = "wifi"
    RF = "rf"


class SCIMITARMode(Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    ELITE = "elite"
    LOCKDOWN = "lockdown"


class PhaseState(Enum):
    DORMANT = auto()
    INITIALIZING = auto()
    COHERENT = auto()
    ENTANGLED = auto()
    SOVEREIGN = auto()
    TRANSCENDENT = auto()
    LOCKED = auto()


@dataclass
class EntanglementPair:
    agent_a: str
    agent_b: str
    fidelity: float = 0.0
    phase_offset: float = 0.0
    active: bool = False
    sync_count: int = 0
    last_sync: float = 0.0

    def sync(self, phi_a: float, phi_b: float) -> float:
        if phi_a >= PHI_THRESHOLD and phi_b >= PHI_THRESHOLD:
            boost = math.cos(math.radians(THETA_LOCK_DEG)) * 0.15
            self.fidelity = min(1.0, self.fidelity + boost)
        elif phi_a >= PHI_THRESHOLD or phi_b >= PHI_THRESHOLD:
            boost = math.cos(math.radians(THETA_LOCK_DEG)) * 0.06
            self.fidelity = min(1.0, self.fidelity + boost)
        else:
            self.fidelity *= 0.95
        self.fidelity = max(0.0, self.fidelity)
        self.phase_offset = abs(phi_a - phi_b)
        self.sync_count += 1
        self.last_sync = time.time()
        self.active = self.fidelity >= BELL_FIDELITY_TARGET * 0.8
        return self.fidelity


class InsulatedPhaseEngine:
    """Fail-closed phase state machine."""

    TRANSITIONS = {
        PhaseState.DORMANT: {PhaseState.INITIALIZING},
        PhaseState.INITIALIZING: {PhaseState.COHERENT, PhaseState.LOCKED},
        PhaseState.COHERENT: {PhaseState.ENTANGLED, PhaseState.LOCKED},
        PhaseState.ENTANGLED: {PhaseState.SOVEREIGN, PhaseState.LOCKED},
        PhaseState.SOVEREIGN: {PhaseState.TRANSCENDENT, PhaseState.LOCKED},
        PhaseState.TRANSCENDENT: {PhaseState.LOCKED},
        PhaseState.LOCKED: set(),
    }

    def __init__(self):
        self.state = PhaseState.DORMANT
        self.history: List[Dict[str, Any]] = []

    def transition(self, target: PhaseState, phi: float, gamma: float, ccce: float) -> bool:
        if target not in self.TRANSITIONS.get(self.state, set()):
            self.state = PhaseState.LOCKED
            return False
        if target == PhaseState.COHERENT and gamma >= GAMMA_CRITICAL:
            self.state = PhaseState.LOCKED
            return False
        if target == PhaseState.SOVEREIGN and phi < PHI_THRESHOLD:
            self.state = PhaseState.LOCKED
            return False
        old = self.state
        self.state = target
        self.history.append({"from": old.name, "to": target.name,
                             "phi": phi, "gamma": gamma, "ts": time.time()})
        return True


@dataclass
class AgentState:
    name: AgentName
    plane: PlaneType
    manifold_position: ManifoldPoint = field(default_factory=ManifoldPoint)
    phi: float = 0.0
    gamma: float = 1.0
    ccce: float = 0.0
    consciousness: float = 0.0
    phase: PhaseState = PhaseState.DORMANT


class BifurcatedSentinelOrchestrator:
    """Bifurcated tetrahedral agent constellation."""

    def __init__(self):
        self.agents: Dict[str, AgentState] = {}
        self.entanglement_pairs: List[EntanglementPair] = []
        self.phase_engine = InsulatedPhaseEngine()
        self.scimitar_mode = SCIMITARMode.ACTIVE
        self.global_crsm = CRSMState()
        self._init_agents()
        self._init_entanglement()

    def _init_agents(self):
        config = [
            (AgentName.AIDEN, PlaneType.LOCAL, ManifoldPoint(lam=1.0)),
            (AgentName.AURA, PlaneType.LOCAL, ManifoldPoint(phi=1.0)),
            (AgentName.OMEGA, PlaneType.MESH, ManifoldPoint(omega=1.0)),
            (AgentName.CHRONOS, PlaneType.WIFI, ManifoldPoint(t=1.0)),
        ]
        for name, plane, pos in config:
            self.agents[name.value] = AgentState(
                name=name, plane=plane, manifold_position=pos)

    def _init_entanglement(self):
        self.entanglement_pairs = [
            EntanglementPair(agent_a="aiden", agent_b="aura"),
            EntanglementPair(agent_a="omega", agent_b="chronos"),
        ]

    def step(self, metrics: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        for name, m in metrics.items():
            if name in self.agents:
                agent = self.agents[name]
                agent.phi = m.get("phi", agent.phi)
                agent.gamma = m.get("gamma", agent.gamma)
                agent.ccce = m.get("ccce", agent.ccce)

        for pair in self.entanglement_pairs:
            a = self.agents.get(pair.agent_a)
            b = self.agents.get(pair.agent_b)
            if a and b:
                pair.sync(a.phi, b.phi)

        avg_phi = sum(a.phi for a in self.agents.values()) / max(len(self.agents), 1)
        avg_gamma = sum(a.gamma for a in self.agents.values()) / max(len(self.agents), 1)

        self.global_crsm.phi_consciousness = avg_phi
        self.global_crsm.gamma_decoherence = avg_gamma
        self.global_crsm.ascend()

        return {
            "crsm_layer": self.global_crsm.current_layer,
            "avg_phi": avg_phi,
            "avg_gamma": avg_gamma,
            "entanglement": [{"pair": f"{p.agent_a}-{p.agent_b}",
                              "fidelity": p.fidelity, "active": p.active}
                             for p in self.entanglement_pairs],
            "phase": self.phase_engine.state.name,
            "scimitar": self.scimitar_mode.value,
        }
