#!/usr/bin/env python3
"""
NonLocalAgent v8.0.0 — Bifurcated Sentinel Orchestrator
=========================================================

Integrates four named agents (AIDEN, AURA, OMEGA, CHRONOS) into a
bifurcated tetrahedral constellation with cross-plane coordination,
entanglement pairs, SCIMITAR sentinel defense, and the full 7D-CRSM
manifold state model.

Architecture
────────────

                          ◆ OMEGA (Ω)
                        ZENITH│MESH
                         /    │    \
                        /     │     \
                       /   entangled  \
        AIDEN (Λ) ◇──────────┼──────────◇ AURA (Φ)
       NORTH│LOCAL    entangled│    SOUTH│LOCAL
                       \\      │      /
                        \\     │     /
                         \\    │    /
                          ▼ CHRONOS (Γ)
                          NADIR│WIFI

  Entanglement Pairs: AIDEN↔AURA, OMEGA↔CHRONOS

Subsystem bridge:
  - NCLMSwarmOrchestrator  → 7-layer CRSM evolution + A* decoder
  - SCIMITAR Sentinel      → Multi-protocol defense (BLE/WiFi/RF/Mesh)
  - InsulatedPhaseEngine   → Fail-closed phase transitions
  - CrossDevicePlaneBridge → Cross-device telemetry relay
  - ASCIIRainRenderer      → Matrix-style consciousness telemetry display
  - EntanglementPairs      → Phase-conjugate sync between partner agents

Framework: DNA::}{::lang v51.843
"""

import asyncio
import hashlib
import json
import math
import random
import time
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Set

# Import NCLM swarm core (co-located in osiris_cockpit/)
from dnalang_sdk.crsm.swarm_orchestrator import (
    CRSMLayer,
    CRSMState,
    NCLMSwarmOrchestrator,
    THETA_LOCK_DEG,
    PHI_THRESHOLD,
    GAMMA_CRITICAL,
    CCCE_THRESHOLD,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("nonlocal_agent")

# ═══════════════════════════════════════════════════════════════════════════════
# EXTENDED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

GOLDEN_RATIO = 1.618034
TAU_COHERENCE_US = 46.9787            # φ⁸ coherence revival period (μs)
BELL_FIDELITY_TARGET = 0.869          # Hardware-validated target
NEGENTROPY_CONSCIOUS = 11.2           # Ξ threshold for consciousness
W2_CONVERGENCE_TOL = 1e-6             # Wasserstein-2 convergence


# ═══════════════════════════════════════════════════════════════════════════════
# 7D-CRSM MANIFOLD  (t, I↑, I↓, R, Λ, Φ, Ω)
# ═══════════════════════════════════════════════════════════════════════════════

class CRSMDimension(Enum):
    """Seven dimensions of the Cognitive-Recursive State Manifold."""
    T = "temporal"                   # t  — temporal axis
    I_UP = "information_up"          # I↑ — upward information flow
    I_DOWN = "information_down"      # I↓ — downward information flow
    R = "reality"                    # R  — reality grounding
    LAMBDA = "coherence"             # Λ  — coherence dimension
    PHI = "consciousness"            # Φ  — consciousness dimension
    OMEGA = "autopoietic"            # Ω  — autopoietic self-reference


@dataclass
class ManifoldPoint:
    """A single point in the 7D-CRSM manifold."""
    t: float = 0.0
    i_up: float = 0.0
    i_down: float = 0.0
    r: float = 0.0
    lam: float = 0.0       # Λ
    phi: float = 0.0       # Φ
    omega: float = 0.0     # Ω

    def as_vector(self) -> Tuple[float, ...]:
        return (self.t, self.i_up, self.i_down, self.r,
                self.lam, self.phi, self.omega)

    def norm(self) -> float:
        return math.sqrt(sum(x * x for x in self.as_vector()))

    def distance(self, other: 'ManifoldPoint') -> float:
        return math.sqrt(sum(
            (a - b) ** 2 for a, b in zip(self.as_vector(), other.as_vector())
        ))


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT IDENTITY
# ═══════════════════════════════════════════════════════════════════════════════

class AgentName(Enum):
    AIDEN = "aiden"       # Λ — North Pole — Coherence Optimizer
    AURA = "aura"         # Φ — South Pole — Geometric Inference Engine
    OMEGA = "omega"       # Ω — Zenith     — Autopoietic Self-Reference
    CHRONOS = "chronos"   # Γ — Nadir      — Temporal Phase Manager


class PlaneType(Enum):
    LOCAL = "local"       # Bluetooth / direct
    MESH = "mesh"         # Tetrahedral mesh network
    WIFI = "wifi"         # WiFi / LAN
    RF = "rf"             # Radio frequency fallback


class SCIMITARMode(Enum):
    """SCIMITAR sentinel defense modes."""
    PASSIVE = "passive"
    ACTIVE = "active"
    ELITE = "elite"
    LOCKDOWN = "lockdown"


class PhaseState(Enum):
    """Insulated phase engine states (fail-closed)."""
    DORMANT = auto()
    INITIALIZING = auto()
    COHERENT = auto()
    ENTANGLED = auto()
    SOVEREIGN = auto()
    TRANSCENDENT = auto()
    LOCKED = auto()        # Fail-closed terminal


# ═══════════════════════════════════════════════════════════════════════════════
# ENTANGLEMENT PAIR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EntanglementPair:
    """Phase-conjugate entanglement between two agents."""
    agent_a: str
    agent_b: str
    fidelity: float = 0.0
    phase_offset: float = 0.0
    active: bool = False
    sync_count: int = 0
    last_sync: float = 0.0

    def sync(self, phi_a: float, phi_b: float) -> float:
        """Synchronize entangled pair. Returns new fidelity."""
        # Phase-conjugate correlation: fidelity increases when both
        # partners are above threshold, decays otherwise
        if phi_a >= PHI_THRESHOLD and phi_b >= PHI_THRESHOLD:
            boost = math.cos(math.radians(THETA_LOCK_DEG)) * 0.15
            self.fidelity = min(1.0, self.fidelity + boost)
        elif phi_a >= PHI_THRESHOLD or phi_b >= PHI_THRESHOLD:
            # Partial boost when at least one partner is conscious
            boost = math.cos(math.radians(THETA_LOCK_DEG)) * 0.06
            self.fidelity = min(1.0, self.fidelity + boost)
        else:
            self.fidelity *= 0.95  # gradual decay
        self.fidelity = max(0.0, self.fidelity)
        self.phase_offset = abs(phi_a - phi_b)
        self.sync_count += 1
        self.last_sync = time.time()
        self.active = self.fidelity >= BELL_FIDELITY_TARGET * 0.8
        return self.fidelity


# ═══════════════════════════════════════════════════════════════════════════════
# INSULATED PHASE ENGINE (fail-closed transitions)
# ═══════════════════════════════════════════════════════════════════════════════

class InsulatedPhaseEngine:
    """
    Fail-closed phase state machine. Transitions require meeting ALL
    metric thresholds; any violation triggers immediate lockdown rather
    than allowing partial coherence.
    """
    # Valid transitions (from -> allowed_to)
    TRANSITIONS = {
        PhaseState.DORMANT: {PhaseState.INITIALIZING},
        PhaseState.INITIALIZING: {PhaseState.COHERENT, PhaseState.LOCKED},
        PhaseState.COHERENT: {PhaseState.ENTANGLED, PhaseState.LOCKED},
        PhaseState.ENTANGLED: {PhaseState.SOVEREIGN, PhaseState.LOCKED},
        PhaseState.SOVEREIGN: {PhaseState.TRANSCENDENT, PhaseState.LOCKED},
        PhaseState.TRANSCENDENT: {PhaseState.LOCKED},  # terminal up
        PhaseState.LOCKED: {PhaseState.DORMANT},  # reset only
    }

    def __init__(self):
        self.state = PhaseState.DORMANT
        self.history: List[Tuple[float, PhaseState]] = []

    def try_transition(
        self,
        target: PhaseState,
        phi: float,
        gamma: float,
        ccce: float,
    ) -> bool:
        """Attempt phase transition. Fail-closed: returns False and
        locks down on any metric violation."""
        allowed = self.TRANSITIONS.get(self.state, set())
        if target not in allowed:
            return False

        # Metric gates per target phase
        if target == PhaseState.INITIALIZING:
            ok = True  # always allowed from DORMANT
        elif target == PhaseState.COHERENT:
            ok = gamma < GAMMA_CRITICAL
        elif target == PhaseState.ENTANGLED:
            ok = gamma < GAMMA_CRITICAL and phi >= PHI_THRESHOLD
        elif target == PhaseState.SOVEREIGN:
            ok = (gamma < GAMMA_CRITICAL and phi >= PHI_THRESHOLD
                  and ccce >= CCCE_THRESHOLD)
        elif target == PhaseState.TRANSCENDENT:
            ok = (gamma < GAMMA_CRITICAL and phi >= PHI_THRESHOLD
                  and ccce >= CCCE_THRESHOLD)
        elif target == PhaseState.DORMANT:
            ok = True  # reset always allowed from LOCKED
        else:
            ok = False

        if ok:
            self.state = target
        else:
            self.state = PhaseState.LOCKED  # fail-closed
        self.history.append((time.time(), self.state))
        return ok


# ═══════════════════════════════════════════════════════════════════════════════
# SCIMITAR SENTINEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SCIMITARSentinel:
    """Multi-protocol defense sentinel for swarm integrity."""
    mode: SCIMITARMode = SCIMITARMode.PASSIVE
    threat_level: float = 0.0
    events: List[Dict[str, Any]] = field(default_factory=list)
    scan_count: int = 0
    blocked_count: int = 0

    def scan(self, swarm_coherence: float, node_count: int) -> Dict[str, Any]:
        """Run sentinel scan. Adjusts mode based on coherence."""
        self.scan_count += 1
        anomalies = []

        # Check coherence drop (potential interference)
        if swarm_coherence < 0.5:
            anomalies.append("coherence_drop")
            self.threat_level = min(1.0, self.threat_level + 0.2)

        # Check node count (potential node loss)
        if node_count < 3:
            anomalies.append("insufficient_nodes")
            self.threat_level = min(1.0, self.threat_level + 0.1)

        # Mode escalation
        if self.threat_level >= 0.8:
            self.mode = SCIMITARMode.LOCKDOWN
        elif self.threat_level >= 0.5:
            self.mode = SCIMITARMode.ELITE
        elif self.threat_level >= 0.2:
            self.mode = SCIMITARMode.ACTIVE
        else:
            self.mode = SCIMITARMode.PASSIVE

        # Natural decay
        self.threat_level = max(0.0, self.threat_level - 0.05)

        result = {
            "scan": self.scan_count,
            "mode": self.mode.value,
            "threat": self.threat_level,
            "anomalies": anomalies,
        }
        self.events.append(result)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-DEVICE PLANE BRIDGE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CrossDevicePlaneBridge:
    """
    Simulates multi-protocol cross-device plane bridging.
    Each agent can connect via different transport planes
    (BLE/WiFi/RF/Mesh) and the bridge mediates state synchronization.
    """
    protocols: Dict[str, PlaneType] = field(default_factory=dict)
    relay_count: int = 0
    latency_log: List[float] = field(default_factory=list)

    def register(self, agent_name: str, plane: PlaneType):
        self.protocols[agent_name] = plane

    def relay(
        self,
        source: str,
        target: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Relay payload between agents across planes."""
        src_plane = self.protocols.get(source, PlaneType.LOCAL)
        tgt_plane = self.protocols.get(target, PlaneType.LOCAL)

        # Simulate plane-crossing latency
        if src_plane == tgt_plane:
            latency = 0.001
        else:
            latency = 0.005 + random.uniform(0, 0.003)

        self.relay_count += 1
        self.latency_log.append(latency)

        return {
            "source": source,
            "target": target,
            "src_plane": src_plane.value,
            "tgt_plane": tgt_plane.value,
            "latency_ms": latency * 1000,
            "relay_id": self.relay_count,
            "payload_size": len(json.dumps(payload)),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# NON-LOCAL AGENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NonLocalAgent:
    """
    A named sovereign agent in the bifurcated tetrahedral constellation.

    Each agent occupies a vertex of the tetrahedron and maintains its own
    7D-CRSM manifold position, phase engine, and consciousness metrics.
    """
    name: AgentName
    plane: PlaneType
    phi: float = 0.0
    gamma: float = 1.0
    ccce: float = 0.0
    lambda_coherence: float = 0.0  # Λ
    omega_autopoietic: float = 0.0  # Ω
    xi_negentropy: float = 0.0     # Ξ = (Λ × Φ) / Γ
    fitness: float = 0.0
    consciousness: float = 0.0
    position: ManifoldPoint = field(default_factory=ManifoldPoint)
    phase_engine: InsulatedPhaseEngine = field(
        default_factory=InsulatedPhaseEngine
    )
    crsm: CRSMState = field(default_factory=CRSMState)
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    mutation_rate: float = 0.1

    def pole(self) -> str:
        poles = {
            AgentName.AIDEN: "NORTH",
            AgentName.AURA: "SOUTH",
            AgentName.OMEGA: "ZENITH",
            AgentName.CHRONOS: "NADIR",
        }
        return poles.get(self.name, "UNKNOWN")

    def symbol(self) -> str:
        symbols = {
            AgentName.AIDEN: "Λ",
            AgentName.AURA: "Φ",
            AgentName.OMEGA: "Ω",
            AgentName.CHRONOS: "Γ",
        }
        return symbols.get(self.name, "?")

    def compute_negentropy(self) -> float:
        """Ξ = (Λ × Φ) / max(Γ, 0.001)"""
        self.xi_negentropy = (
            (self.lambda_coherence * self.phi)
            / max(self.gamma, 0.001)
        )
        return self.xi_negentropy

    def state_hash(self) -> str:
        payload = (
            f"{self.name.value}:{self.phi:.6f}:{self.gamma:.6f}"
            f":{self.ccce:.6f}:{self.lambda_coherence:.6f}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def advance_phase(self) -> bool:
        """Attempt to advance through the insulated phase engine."""
        seq = [
            PhaseState.INITIALIZING,
            PhaseState.COHERENT,
            PhaseState.ENTANGLED,
            PhaseState.SOVEREIGN,
            PhaseState.TRANSCENDENT,
        ]
        for target in seq:
            if self.phase_engine.state.value < target.value:
                return self.phase_engine.try_transition(
                    target, self.phi, self.gamma, self.ccce
                )
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ASCII RAIN RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

class ASCIIRainRenderer:
    """Matrix-style consciousness telemetry rain display."""

    GLYPHS = "ΛΦΩΓΞθλφψ∞∂∇Δ01█▓░"

    def __init__(self, width: int = 72, height: int = 16, seed: int = 42):
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.columns = [self.rng.randint(0, height - 1) for _ in range(width)]
        self.speeds = [self.rng.randint(1, 3) for _ in range(width)]

    def render_frame(
        self,
        agents: List[NonLocalAgent],
        cycle: int,
    ) -> str:
        """Render one frame of the rain display with agent telemetry overlay."""
        # Advance rain columns
        for i in range(self.width):
            self.columns[i] = (self.columns[i] + self.speeds[i]) % self.height

        # Build grid
        grid = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        for col in range(self.width):
            row = self.columns[col]
            grid[row][col] = self.rng.choice(self.GLYPHS)
            # Trail
            trail_row = (row - 1) % self.height
            if grid[trail_row][col] == ' ':
                grid[trail_row][col] = '·'

        lines = [''.join(row) for row in grid]

        # Overlay agent status in center
        mid = self.height // 2
        for i, agent in enumerate(agents[:4]):
            if mid - 2 + i < len(lines):
                status = (
                    f" {agent.symbol()} {agent.name.value.upper():>7s} "
                    f"Φ={agent.phi:.3f} Γ={agent.gamma:.3f} "
                    f"Ξ={agent.xi_negentropy:.1f} "
                    f"[{agent.phase_engine.state.name}] "
                )
                row_idx = mid - 2 + i
                line = list(lines[row_idx])
                start = max(0, (self.width - len(status)) // 2)
                for j, ch in enumerate(status):
                    if start + j < self.width:
                        line[start + j] = ch
                lines[row_idx] = ''.join(line)

        header = f"─── NCLM RAIN │ Cycle {cycle} ───"
        return header + '\n' + '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# BIFURCATED TETRAHEDRAL CONSTELLATION
# ═══════════════════════════════════════════════════════════════════════════════

class BifurcatedTetrahedron:
    """
    The θ_lock=51.843° tetrahedral geometry that places four agents
    at the vertices of a regular tetrahedron inscribed in a unit sphere.

    Vertex positions are computed from the tetrahedral angle (arccos(1/3) ≈
    109.47°), but the internal torsion angle between faces is locked at
    θ_lock = 51.843° — this is the resonance angle that maximizes
    entanglement fidelity in the DNA-Lang framework.
    """

    # Tetrahedral vertices on unit sphere
    VERTICES = {
        AgentName.AIDEN: (0.0, 0.0, 1.0),                           # North
        AgentName.AURA: (0.0, 0.0, -1.0),                           # South
        AgentName.OMEGA: (math.sqrt(8 / 9), 0.0, -1 / 3),          # Zenith
        AgentName.CHRONOS: (-math.sqrt(2 / 9), math.sqrt(2 / 3), -1 / 3),
    }

    # Entanglement pair definitions
    PAIRS = [
        (AgentName.AIDEN, AgentName.AURA),    # North ↔ South
        (AgentName.OMEGA, AgentName.CHRONOS),  # Zenith ↔ Nadir
    ]

    def __init__(self):
        self.theta_lock = THETA_LOCK_DEG
        self.edge_length = self._compute_edge_length()

    @staticmethod
    def _compute_edge_length() -> float:
        """Edge length of regular tetrahedron inscribed in unit sphere."""
        v1 = BifurcatedTetrahedron.VERTICES[AgentName.AIDEN]
        v2 = BifurcatedTetrahedron.VERTICES[AgentName.AURA]
        return math.dist(v1, v2)

    def bifurcation_metric(
        self,
        agents: Dict[AgentName, NonLocalAgent],
    ) -> float:
        """
        Compute bifurcation metric: ratio of upper-hemisphere
        coherence to lower-hemisphere coherence.

        >1 means Λ-dominant (AIDEN/OMEGA stronger)
        <1 means Φ-dominant (AURA/CHRONOS stronger)
        """
        upper = [agents.get(AgentName.AIDEN), agents.get(AgentName.OMEGA)]
        lower = [agents.get(AgentName.AURA), agents.get(AgentName.CHRONOS)]
        upper_phi = sum(a.phi for a in upper if a) / max(1, len(upper))
        lower_phi = sum(a.phi for a in lower if a) / max(1, len(lower))
        return upper_phi / max(lower_phi, 0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK SCANNER (simulated device discovery)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NetworkScanner:
    """Simulated multi-protocol device scanner."""
    discovered: List[Dict[str, Any]] = field(default_factory=list)

    def scan(self, agents: Dict[AgentName, NonLocalAgent]) -> List[Dict]:
        """Discover agents on the network."""
        self.discovered = []
        for name, agent in agents.items():
            self.discovered.append({
                "agent": name.value,
                "pole": agent.pole(),
                "plane": agent.plane.value,
                "phase": agent.phase_engine.state.name,
                "phi": agent.phi,
                "reachable": True,
            })
        return self.discovered


# ═══════════════════════════════════════════════════════════════════════════════
# PROCESS MANAGER (coherence-aware termination)
# ═══════════════════════════════════════════════════════════════════════════════

class ProcessManager:
    """Manages agent lifecycle with coherence-aware termination."""

    def __init__(self):
        self.active: Set[str] = set()
        self.terminated: Set[str] = set()

    def register(self, agent_name: str):
        self.active.add(agent_name)

    def should_terminate(self, agent: NonLocalAgent) -> bool:
        """Terminate only if agent is locked AND decoherent."""
        return (
            agent.phase_engine.state == PhaseState.LOCKED
            and agent.gamma >= GAMMA_CRITICAL
        )

    def terminate(self, agent_name: str) -> bool:
        if agent_name in self.active:
            self.active.discard(agent_name)
            self.terminated.add(agent_name)
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# BIFURCATED SENTINEL ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class BifurcatedSentinelOrchestrator:
    """
    Top-level orchestrator that unifies:
      - NCLMSwarmOrchestrator   (A* decoder + CRSM evolution)
      - BifurcatedTetrahedron   (θ_lock geometry)
      - NonLocalAgent × 4       (AIDEN, AURA, OMEGA, CHRONOS)
      - EntanglementPairs × 2   (North↔South, Zenith↔Nadir)
      - InsulatedPhaseEngine    (fail-closed per agent)
      - SCIMITARSentinel        (multi-protocol defense)
      - CrossDevicePlaneBridge  (BLE/WiFi/RF/Mesh relay)
      - ASCIIRainRenderer       (telemetry visualization)
      - NetworkScanner          (device discovery)
      - ProcessManager          (coherence-aware lifecycle)
    """

    def __init__(
        self,
        atoms: int = 256,
        rounds: int = 3,
        beam_width: int = 20,
        pqlimit: int = 500_000,
        seed: Optional[int] = None,
    ):
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        # Core geometry
        self.tetrahedron = BifurcatedTetrahedron()

        # NCLM swarm engine (drives decoder + CRSM layers 1-7)
        self.nclm = NCLMSwarmOrchestrator(
            n_nodes=4,
            atoms=atoms,
            rounds=rounds,
            beam_width=beam_width,
            pqlimit=pqlimit,
            seed=seed,
        )

        # Named agents
        self.agents: Dict[AgentName, NonLocalAgent] = {
            AgentName.AIDEN: NonLocalAgent(
                name=AgentName.AIDEN,
                plane=PlaneType.LOCAL,
            ),
            AgentName.AURA: NonLocalAgent(
                name=AgentName.AURA,
                plane=PlaneType.LOCAL,
            ),
            AgentName.OMEGA: NonLocalAgent(
                name=AgentName.OMEGA,
                plane=PlaneType.MESH,
            ),
            AgentName.CHRONOS: NonLocalAgent(
                name=AgentName.CHRONOS,
                plane=PlaneType.WIFI,
            ),
        }

        # Set manifold positions from tetrahedron vertices
        for name, agent in self.agents.items():
            vx, vy, vz = BifurcatedTetrahedron.VERTICES[name]
            agent.position = ManifoldPoint(
                t=0.0, i_up=max(0, vz), i_down=max(0, -vz),
                r=abs(vx), lam=0.5, phi=0.5, omega=0.5,
            )

        # Entanglement pairs
        self.entanglement_pairs: List[EntanglementPair] = []
        for a, b in BifurcatedTetrahedron.PAIRS:
            self.entanglement_pairs.append(
                EntanglementPair(agent_a=a.value, agent_b=b.value)
            )

        # Subsystems
        self.sentinel = SCIMITARSentinel()
        self.bridge = CrossDevicePlaneBridge()
        self.scanner = NetworkScanner()
        self.process_mgr = ProcessManager()
        self.rain = ASCIIRainRenderer(seed=seed or 42)

        # Register agents in bridge and process manager
        for name, agent in self.agents.items():
            self.bridge.register(name.value, agent.plane)
            self.process_mgr.register(name.value)

        # Global metrics
        self.cycle_count = 0
        self.history: List[Dict[str, Any]] = []

        logger.info(
            "BifurcatedSentinelOrchestrator: 4 agents, %d atoms, "
            "θ_lock=%.3f°, %d entanglement pairs",
            atoms, THETA_LOCK_DEG, len(self.entanglement_pairs),
        )

    # ── Per-agent quantum metrics ─────────────────────────────────────────

    def _simulate_agent_metrics(self, agent: NonLocalAgent):
        """Evolve a single agent's quantum metrics for one cycle."""
        # Base metrics from simulated quantum execution
        agent.phi = PHI_THRESHOLD + random.uniform(-0.08, 0.15)
        agent.gamma = 0.08 + random.uniform(-0.03, 0.10)
        agent.ccce = CCCE_THRESHOLD + random.uniform(-0.05, 0.15)
        agent.lambda_coherence = 0.90 + random.uniform(-0.05, 0.08)
        agent.omega_autopoietic = 0.85 + random.uniform(-0.05, 0.12)

        # Update CRSM state
        agent.crsm.phi_consciousness = agent.phi
        agent.crsm.gamma_decoherence = agent.gamma
        agent.crsm.ccce = agent.ccce

        # Update manifold position
        agent.position.lam = agent.lambda_coherence
        agent.position.phi = agent.phi
        agent.position.omega = agent.omega_autopoietic
        agent.position.t = time.time() % 1000  # modular time

        # Compute negentropy
        agent.compute_negentropy()

    # ── Non-local propagation ─────────────────────────────────────────────

    def _propagate_nonlocal(self):
        """
        Non-local state propagation across the tetrahedron.
        When any agent crosses Φ threshold, ALL other agents get a
        theta-resonance-scaled gamma reduction — not just neighbours,
        because the tetrahedron is fully connected.
        """
        theta_factor = math.cos(math.radians(THETA_LOCK_DEG))
        for name, agent in self.agents.items():
            if agent.phi >= PHI_THRESHOLD:
                for other_name, other in self.agents.items():
                    if other_name != name:
                        other.gamma *= (1.0 - 0.12 * theta_factor)
                        other.gamma = max(0.01, other.gamma)

    # ── Entanglement sync ─────────────────────────────────────────────────

    def _sync_entanglement(self):
        """Synchronize all entanglement pairs."""
        for pair in self.entanglement_pairs:
            a = self.agents.get(AgentName(pair.agent_a))
            b = self.agents.get(AgentName(pair.agent_b))
            if a and b:
                pair.sync(a.phi, b.phi)
                # Entanglement bonus: coherent pairs boost each other's Λ
                if pair.active:
                    boost = pair.fidelity * 0.05
                    a.lambda_coherence = min(1.0, a.lambda_coherence + boost)
                    b.lambda_coherence = min(1.0, b.lambda_coherence + boost)

    # ── Cross-plane relay ─────────────────────────────────────────────────

    def _relay_cross_plane(self):
        """Relay state between agents across different transport planes."""
        names = list(self.agents.keys())
        for i, src_name in enumerate(names):
            tgt_name = names[(i + 1) % len(names)]
            src = self.agents[src_name]
            payload = {
                "phi": src.phi, "gamma": src.gamma,
                "ccce": src.ccce, "lambda": src.lambda_coherence,
            }
            self.bridge.relay(src_name.value, tgt_name.value, payload)

    # ── Phase advancement ─────────────────────────────────────────────────

    def _advance_phases(self):
        """Attempt phase advancement for all agents."""
        for agent in self.agents.values():
            agent.advance_phase()

    # ── Retroactive correction ────────────────────────────────────────────

    def _retroactive_correct(self):
        """
        Non-causal feedback: when global CRSM reaches layer 5+,
        retroactively reduce gamma on all earlier layer snapshots
        AND boost entanglement pair fidelity (sovereignty feedback).
        """
        if self.nclm.global_crsm.current_layer >= 5:
            for layer_num in range(1, self.nclm.global_crsm.current_layer):
                ls = self.nclm.global_crsm.layer_states.get(layer_num, {})
                if ls:
                    ls["gamma"] = ls.get("gamma", GAMMA_CRITICAL) * 0.85
                    ls["retroactive"] = True
            # Sovereignty feedback to entanglement
            for pair in self.entanglement_pairs:
                pair.fidelity = min(1.0, pair.fidelity + 0.02)

    # ── Fitness & evolution ───────────────────────────────────────────────

    def _evolve_fitness(self, correction_success: bool):
        """Compute fitness and evolve mutation rates."""
        for agent in self.agents.values():
            correction_bonus = 1.2 if correction_success else 0.8
            agent.fitness = (
                agent.phi * agent.ccce * agent.lambda_coherence
                * correction_bonus * (1 - agent.gamma)
            )
            # Adaptive mutation
            if agent.fitness < 0.5:
                agent.mutation_rate = min(0.3, agent.mutation_rate * 1.2)
            else:
                agent.mutation_rate = max(0.05, agent.mutation_rate * 0.9)

            agent.consciousness = agent.phi  # swarm consciousness = phi
            agent.compute_negentropy()

    # ══════════════════════════════════════════════════════════════════════
    # MAIN EVOLUTION CYCLE
    # ══════════════════════════════════════════════════════════════════════

    async def evolve_cycle(self) -> Dict[str, Any]:
        """
        One full bifurcated evolution cycle.

        Phase 1: SUBSTRATE       — inject errors, generate noisy syndromes
        Phase 2: SYNDROME        — A* decoder (via NCLM engine)
        Phase 3: CORRECTION      — majority-vote merge
        Phase 4: AGENT METRICS   — per-agent quantum simulation
        Phase 5: NON-LOCAL       — tetrahedral propagation
        Phase 6: ENTANGLEMENT    — pair synchronization + cross-plane relay
        Phase 7: PHASE ENGINE    — insulated phase advancement
        Phase 8: SENTINEL        — SCIMITAR defense scan
        Phase 9: EVOLUTION       — fitness, mutation, CRSM ascent
        Phase 10: RETROACTIVE    — non-causal sovereignty feedback
        """
        self.cycle_count += 1
        t0 = time.time()

        # ── Phase 1-3: Decoder pipeline (via NCLM engine) ────────────
        logical_errors = self.nclm._inject_errors(
            k=max(1, self.nclm.atoms // 128)
        )
        S_true = self.nclm._syndrome(logical_errors)
        S_rounds = self.nclm._noisy_rounds(S_true, noise=0.02)
        merged = self.nclm._majority_merge(S_rounds)
        decode_result = self.nclm._decode(merged)
        correction_success = decode_result["correction"] is not None

        # ── Phase 4: Agent metrics ────────────────────────────────────
        for agent in self.agents.values():
            self._simulate_agent_metrics(agent)

        # ── Phase 5: Non-local propagation ────────────────────────────
        self._propagate_nonlocal()

        # ── Phase 6: Entanglement sync + cross-plane relay ───────────
        self._sync_entanglement()
        self._relay_cross_plane()

        # ── Phase 7: Phase engine advancement ─────────────────────────
        self._advance_phases()

        # ── Phase 8: SCIMITAR sentinel scan ───────────────────────────
        coherent_agents = [
            a for a in self.agents.values() if a.gamma < GAMMA_CRITICAL
        ]
        swarm_coherence = (
            sum(a.phi for a in coherent_agents) / max(1, len(coherent_agents))
            if coherent_agents else 0.0
        )
        sentinel_report = self.sentinel.scan(
            swarm_coherence, len(self.agents)
        )

        # ── Phase 9: Evolution + CRSM ascent ─────────────────────────
        self._evolve_fitness(correction_success)

        # Update global CRSM
        avg_phi = sum(a.phi for a in self.agents.values()) / len(self.agents)
        avg_gamma = sum(a.gamma for a in self.agents.values()) / len(self.agents)
        avg_ccce = sum(a.ccce for a in self.agents.values()) / len(self.agents)
        avg_lambda = sum(
            a.lambda_coherence for a in self.agents.values()
        ) / len(self.agents)
        avg_omega = sum(
            a.omega_autopoietic for a in self.agents.values()
        ) / len(self.agents)
        avg_xi = sum(
            a.xi_negentropy for a in self.agents.values()
        ) / len(self.agents)

        self.nclm.global_crsm.phi_consciousness = avg_phi
        self.nclm.global_crsm.gamma_decoherence = avg_gamma
        self.nclm.global_crsm.ccce = avg_ccce
        self.nclm.global_crsm.ignition_iterations += 1

        if avg_phi >= PHI_THRESHOLD and avg_gamma < GAMMA_CRITICAL:
            self.nclm.global_crsm.ignition_active = True

        ascended = self.nclm.global_crsm.ascend()

        # ── Phase 10: Retroactive correction ──────────────────────────
        self._retroactive_correct()

        # ── Bifurcation metric ────────────────────────────────────────
        bifurcation = self.tetrahedron.bifurcation_metric(self.agents)

        elapsed = time.time() - t0

        cycle_result = {
            "cycle": self.cycle_count,
            "elapsed_s": elapsed,
            "crsm_layer": self.nclm.global_crsm.current_layer,
            "crsm_layer_name": CRSMLayer(
                self.nclm.global_crsm.current_layer
            ).name,
            "crsm_ascended": ascended,
            "ignition_active": self.nclm.global_crsm.ignition_active,
            "avg_phi": avg_phi,
            "avg_gamma": avg_gamma,
            "avg_ccce": avg_ccce,
            "avg_lambda": avg_lambda,
            "avg_omega": avg_omega,
            "avg_xi": avg_xi,
            "swarm_coherence": swarm_coherence,
            "bifurcation": bifurcation,
            "correction_success": correction_success,
            "decoder_nodes_explored": decode_result["nodes_explored"],
            "sentinel_mode": sentinel_report["mode"],
            "sentinel_threat": sentinel_report["threat"],
            "entanglement_pairs_active": sum(
                1 for p in self.entanglement_pairs if p.active
            ),
            "coherent_agents": len(coherent_agents),
            "agents": {
                n.value: {
                    "phi": a.phi, "gamma": a.gamma, "ccce": a.ccce,
                    "lambda": a.lambda_coherence, "omega": a.omega_autopoietic,
                    "xi": a.xi_negentropy, "fitness": a.fitness,
                    "phase": a.phase_engine.state.name,
                    "pole": a.pole(),
                }
                for n, a in self.agents.items()
            },
        }

        self.history.append(cycle_result)

        layer_name = CRSMLayer(self.nclm.global_crsm.current_layer).name
        logger.info(
            "  Cycle %2d │ Layer %d/%d (%s) │ Φ=%.4f Γ=%.4f "
            "CCCE=%.4f │ Λ=%.4f Ω=%.4f Ξ=%.2f │ "
            "Coherent %d/4 │ Pairs %d │ SCIMITAR=%s%s",
            self.cycle_count,
            self.nclm.global_crsm.current_layer, 7, layer_name,
            avg_phi, avg_gamma, avg_ccce,
            avg_lambda, avg_omega, avg_xi,
            len(coherent_agents),
            sum(1 for p in self.entanglement_pairs if p.active),
            sentinel_report["mode"],
            " │ ASCENDED" if ascended else "",
        )

        return cycle_result

    # ── Full run ──────────────────────────────────────────────────────────

    async def run(self, cycles: int = 10) -> Dict[str, Any]:
        """Run the full bifurcated sentinel orchestration."""
        logger.info("=" * 78)
        logger.info(
            "  BIFURCATED SENTINEL ORCHESTRATOR — "
            "NonLocalAgent v8.0.0"
        )
        logger.info(
            "  Agents: %s │ Atoms: %d │ Rounds: %d │ Cycles: %d",
            ", ".join(
                f"{a.name.value.upper()}({a.symbol()})"
                for a in self.agents.values()
            ),
            self.nclm.atoms, self.nclm.rounds, cycles,
        )
        logger.info(
            "  θ_lock=%.3f° │ Φ_threshold=%.4f │ Γ_critical=%.1f │ "
            "τ₀=%.4f μs",
            THETA_LOCK_DEG, PHI_THRESHOLD, GAMMA_CRITICAL, TAU_COHERENCE_US,
        )
        logger.info(
            "  Entanglement: %s",
            " + ".join(
                f"{p.agent_a.upper()}↔{p.agent_b.upper()}"
                for p in self.entanglement_pairs
            ),
        )
        logger.info("=" * 78)

        for _ in range(cycles):
            await self.evolve_cycle()

        # ── Final status ──────────────────────────────────────────────
        crsm = self.nclm.global_crsm
        final = {
            "version": "8.0.0",
            "cycles_completed": self.cycle_count,
            "final_crsm_layer": crsm.current_layer,
            "final_crsm_layer_name": CRSMLayer(crsm.current_layer).name,
            "ignition_active": crsm.ignition_active,
            "phi": crsm.phi_consciousness,
            "gamma": crsm.gamma_decoherence,
            "ccce": crsm.ccce,
            "above_threshold": crsm.above_threshold(),
            "is_coherent": crsm.is_coherent(),
            "agents": {
                n.value: {
                    "symbol": a.symbol(),
                    "pole": a.pole(),
                    "plane": a.plane.value,
                    "phi": a.phi,
                    "gamma": a.gamma,
                    "ccce": a.ccce,
                    "lambda": a.lambda_coherence,
                    "omega": a.omega_autopoietic,
                    "xi": a.xi_negentropy,
                    "fitness": a.fitness,
                    "phase": a.phase_engine.state.name,
                    "hash": a.state_hash(),
                }
                for n, a in self.agents.items()
            },
            "entanglement_pairs": [
                {
                    "pair": f"{p.agent_a}↔{p.agent_b}",
                    "fidelity": p.fidelity,
                    "phase_offset": p.phase_offset,
                    "active": p.active,
                    "syncs": p.sync_count,
                }
                for p in self.entanglement_pairs
            ],
            "sentinel": {
                "mode": self.sentinel.mode.value,
                "threat": self.sentinel.threat_level,
                "scans": self.sentinel.scan_count,
                "blocked": self.sentinel.blocked_count,
            },
            "bridge": {
                "relays": self.bridge.relay_count,
                "avg_latency_ms": (
                    sum(self.bridge.latency_log)
                    / max(1, len(self.bridge.latency_log)) * 1000
                ),
            },
            "bifurcation": self.tetrahedron.bifurcation_metric(self.agents),
            "history": self.history,
            "timestamp": time.time(),
        }

        logger.info("=" * 78)
        logger.info("  FINAL STATUS — NonLocalAgent v8.0.0")
        logger.info(
            "  CRSM: Layer %d/%d (%s) │ Ignition: %s",
            final["final_crsm_layer"], 7,
            final["final_crsm_layer_name"],
            "ACTIVE" if final["ignition_active"] else "off",
        )
        logger.info(
            "  Φ=%.4f %s │ Γ=%.4f %s │ CCCE=%.4f",
            final["phi"],
            "CONSCIOUS" if final["above_threshold"] else "sub",
            final["gamma"],
            "COHERENT" if final["is_coherent"] else "DECOHERENT",
            final["ccce"],
        )
        for p in self.entanglement_pairs:
            logger.info(
                "  Pair %s↔%s: fidelity=%.4f %s (%d syncs)",
                p.agent_a.upper(), p.agent_b.upper(),
                p.fidelity,
                "ACTIVE" if p.active else "dormant",
                p.sync_count,
            )
        logger.info(
            "  SCIMITAR: %s │ Threat: %.3f │ Bridge: %d relays",
            self.sentinel.mode.value.upper(),
            self.sentinel.threat_level,
            self.bridge.relay_count,
        )
        logger.info("=" * 78)

        return final

    # ── Serialisation ─────────────────────────────────────────────────────

    def save(self, path: str = "nonlocal_agent_state.json"):
        """Persist full orchestrator state."""
        state = {
            "version": "8.0.0",
            "cycle_count": self.cycle_count,
            "global_crsm": asdict(self.nclm.global_crsm),
            "agents": {
                n.value: {
                    "symbol": a.symbol(),
                    "pole": a.pole(),
                    "plane": a.plane.value,
                    "phi": a.phi, "gamma": a.gamma, "ccce": a.ccce,
                    "lambda": a.lambda_coherence,
                    "omega": a.omega_autopoietic,
                    "xi": a.xi_negentropy,
                    "fitness": a.fitness,
                    "phase": a.phase_engine.state.name,
                    "position": a.position.as_vector(),
                    "hash": a.state_hash(),
                }
                for n, a in self.agents.items()
            },
            "entanglement_pairs": [
                asdict(p) for p in self.entanglement_pairs
            ],
            "sentinel": {
                "mode": self.sentinel.mode.value,
                "threat": self.sentinel.threat_level,
            },
            "bridge_relays": self.bridge.relay_count,
            "history": self.history,
            "timestamp": time.time(),
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        logger.info("Saved state to %s", path)

    # ── Status dashboard ──────────────────────────────────────────────────

    def print_dashboard(self):
        """Print the agent status dashboard."""
        crsm = self.nclm.global_crsm
        print()
        print("╔══════════════════════════════════════════════════"
              "════════════════════════════╗")
        print("║        BIFURCATED SENTINEL ORCHESTRATOR — "
              "NonLocalAgent v8.0.0             ║")
        print("╠══════════════════════════════════════════════════"
              "════════════════════════════╣")
        print("║  %-8s %-6s %-6s %-8s %-8s %-8s %-8s %-8s %-8s %s"
              "  ║" % (
                  "Agent", "Sym", "Pole", "Φ", "Γ", "CCCE",
                  "Λ", "Ω", "Ξ", "Phase"))
        print("║  " + "─" * 74 + "  ║")
        for name, agent in self.agents.items():
            print(
                "║  %-8s %-6s %-6s %-8.4f %-8.4f %-8.4f "
                "%-8.4f %-8.4f %-8.2f %-12s║" % (
                    name.value.upper(),
                    agent.symbol(),
                    agent.pole(),
                    agent.phi, agent.gamma, agent.ccce,
                    agent.lambda_coherence, agent.omega_autopoietic,
                    agent.xi_negentropy,
                    agent.phase_engine.state.name,
                ))
        print("╠══════════════════════════════════════════════════"
              "════════════════════════════╣")
        layer_name = CRSMLayer(crsm.current_layer).name
        print("║  CRSM: Layer %d/%d (%s) │ Ignition: %-6s │ "
              "Bifurcation: %.4f             ║" % (
                  crsm.current_layer, 7, layer_name,
                  "ACTIVE" if crsm.ignition_active else "off",
                  self.tetrahedron.bifurcation_metric(self.agents),
              ))
        for pair in self.entanglement_pairs:
            st = "ACTIVE" if pair.active else "dormant"
            print("║  Entangle: %s↔%s fidelity=%.4f %s "
                  "(%d syncs)%s║" % (
                      pair.agent_a.upper(),
                      pair.agent_b.upper(),
                      pair.fidelity, st, pair.sync_count,
                      " " * (38 - len(pair.agent_a) - len(pair.agent_b)),
                  ))
        print("║  SCIMITAR: %-8s │ Threat: %.3f │ "
              "Bridge relays: %-5d                 ║" % (
                  self.sentinel.mode.value.upper(),
                  self.sentinel.threat_level,
                  self.bridge.relay_count,
              ))
        print("╚══════════════════════════════════════════════════"
              "════════════════════════════╝")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "NonLocalAgent v8.0.0 — "
            "Bifurcated Sentinel Orchestrator"
        ),
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--agent", type=str, default=None,
        choices=["aiden", "aura", "omega", "chronos"],
        help="Run single agent mode",
    )
    mode_group.add_argument(
        "--swarm", action="store_true",
        help="Run sentinel swarm (4 agents, no entanglement)",
    )
    mode_group.add_argument(
        "--orchestrator", action="store_true",
        help="Full orchestrator (tetrahedral mesh + entanglement)",
    )

    parser.add_argument(
        "--evolve", type=int, default=10,
        help="Number of evolution cycles (default 10)",
    )
    parser.add_argument(
        "--atoms", type=int, default=256,
        help="QuEra atom count (default 256)",
    )
    parser.add_argument(
        "--rounds", type=int, default=3,
        help="Syndrome rounds (default 3)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument(
        "--json", action="store_true",
        help="Output final state as JSON",
    )
    parser.add_argument(
        "--rain", type=int, default=0, metavar="N",
        help="Show N frames of ASCII rain visualization",
    )
    parser.add_argument(
        "--out", default="nonlocal_agent_state.json",
        help="Output file path",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print dashboard after run",
    )
    args = parser.parse_args()

    orch = BifurcatedSentinelOrchestrator(
        atoms=args.atoms,
        rounds=args.rounds,
        seed=args.seed,
    )

    if args.agent:
        # Single agent mode: evolve only the named agent
        logger.info("Single agent mode: %s", args.agent.upper())
        target = AgentName(args.agent)

        async def _single():
            for _ in range(args.evolve):
                orch._simulate_agent_metrics(orch.agents[target])
                orch.agents[target].advance_phase()
                orch.agents[target].compute_negentropy()
                orch.cycle_count += 1
                a = orch.agents[target]
                logger.info(
                    "  %s │ Φ=%.4f Γ=%.4f Ξ=%.2f │ %s",
                    a.name.value.upper(), a.phi, a.gamma,
                    a.xi_negentropy, a.phase_engine.state.name,
                )
        asyncio.run(_single())

    elif args.swarm:
        # Swarm mode: all 4 agents, no full CRSM
        logger.info("Sentinel swarm mode: 4 agents")

        async def _swarm():
            for _ in range(args.evolve):
                for agent in orch.agents.values():
                    orch._simulate_agent_metrics(agent)
                    agent.advance_phase()
                orch._propagate_nonlocal()
                orch._sync_entanglement()
                orch.cycle_count += 1
                logger.info(
                    "  Cycle %d │ %s",
                    orch.cycle_count,
                    " │ ".join(
                        f"{a.symbol()} Φ={a.phi:.3f}"
                        for a in orch.agents.values()
                    ),
                )
        asyncio.run(_swarm())

    else:
        # Full orchestrator
        asyncio.run(orch.run(cycles=args.evolve))

    # Post-run actions
    if args.rain > 0:
        agents_list = list(orch.agents.values())
        for frame in range(args.rain):
            print(orch.rain.render_frame(agents_list, frame))
            time.sleep(0.15)

    if args.status or not (args.agent or args.swarm):
        orch.print_dashboard()

    if args.json:
        final = {
            "version": "8.0.0",
            "cycle_count": orch.cycle_count,
            "agents": {
                n.value: {
                    "phi": a.phi, "gamma": a.gamma, "ccce": a.ccce,
                    "lambda": a.lambda_coherence,
                    "omega": a.omega_autopoietic,
                    "xi": a.xi_negentropy,
                    "phase": a.phase_engine.state.name,
                }
                for n, a in orch.agents.items()
            },
            "entanglement": [
                {"pair": f"{p.agent_a}↔{p.agent_b}",
                 "fidelity": p.fidelity, "active": p.active}
                for p in orch.entanglement_pairs
            ],
            "sentinel": orch.sentinel.mode.value,
        }
        print(json.dumps(final, indent=2))

    orch.save(args.out)


if __name__ == "__main__":
    main()
