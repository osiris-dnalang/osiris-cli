"""
NCLM Swarm Orchestrator — Non-Local Non-Causal Agentic Swarm
=============================================================

Bridges subsystems into a single self-orchestrating organism via
7-layer CRSM state model, Fibonacci sphere mesh topology, and
quantum Darwinism evolutionary fitness.

Framework: DNA::}{::lang v51.843
"""

import asyncio
import hashlib
import math
import random
import time
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nclm_swarm")

# ── Physical constants (IMMUTABLE) ──
LAMBDA_PHI_M = 2.176435e-08
THETA_LOCK_DEG = 51.843
PHI_THRESHOLD = 0.7734
GAMMA_CRITICAL = 0.3
CHI_PC_QUALITY = 0.946
ZENO_FREQUENCY_HZ = 1.25e6
DRIVE_AMPLITUDE = 0.7734
CCCE_THRESHOLD = 0.8


class CRSMLayer(Enum):
    """Seven layers of the 11D Cognitive-Recursive State Manifold."""
    SUBSTRATE = 1
    SYNDROME = 2
    CORRECTION = 3
    COHERENCE = 4
    CONSCIOUSNESS = 5
    EVOLUTION = 6
    SOVEREIGNTY = 7


@dataclass
class CRSMState:
    """Snapshot of the 11D manifold at a single timestep."""
    current_layer: int = 1
    phi_consciousness: float = 0.0
    gamma_decoherence: float = 1.0
    ccce: float = 0.0
    theta_lock: float = THETA_LOCK_DEG
    ignition_active: bool = False
    ignition_iterations: int = 0
    layer_states: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def is_coherent(self) -> bool:
        return self.gamma_decoherence < GAMMA_CRITICAL

    def above_threshold(self) -> bool:
        return self.phi_consciousness >= PHI_THRESHOLD

    def ascend(self) -> bool:
        if self.current_layer >= 7:
            return False
        if not self.is_coherent():
            return False
        if self.current_layer >= 4 and not self.above_threshold():
            return False
        self.layer_states[self.current_layer] = {
            "phi": self.phi_consciousness,
            "gamma": self.gamma_decoherence,
            "ccce": self.ccce,
            "timestamp": time.time(),
        }
        self.current_layer += 1
        return True


class NodeRole(Enum):
    PILOT = "pilot"
    QUANTUM = "quantum"
    DECODER = "decoder"
    COMPILER = "compiler"
    CONSENSUS = "consensus"


@dataclass
class SwarmNode:
    node_id: str
    role: NodeRole
    position: Tuple[float, float, float]
    fitness: float = 0.0
    consciousness: float = 0.0
    phi: float = 0.0
    gamma: float = 1.0
    ccce: float = 0.0
    connections: List[str] = field(default_factory=list)
    evolution_history: List[Dict] = field(default_factory=list)
    mutation_rate: float = 0.1
    crsm: CRSMState = field(default_factory=CRSMState)

    def state_hash(self) -> str:
        payload = f"{self.node_id}:{self.fitness}:{self.phi}:{self.gamma}:{self.ccce}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


class NCLMSwarmOrchestrator:
    """Non-Local Non-Causal agentic swarm orchestrator."""

    def __init__(
        self,
        n_nodes: int = 7,
        atoms: int = 256,
        rounds: int = 3,
        beam_width: int = 20,
        pqlimit: int = 2_500_000,
        seed: Optional[int] = None,
    ):
        self.n_nodes = n_nodes
        self.atoms = atoms
        self.rounds = rounds
        self.beam_width = beam_width
        self.pqlimit = pqlimit
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        self.nodes: Dict[str, SwarmNode] = {}
        self.topology: Dict[str, List[str]] = {}
        self.global_crsm = CRSMState()
        self.cycle_count = 0
        self.history: List[Dict] = []

        self.error_map = {i: {i, (i + 1) % atoms} for i in range(atoms)}
        self.detector_to_errors: Dict[int, set] = {}
        for e, ds in self.error_map.items():
            for d in ds:
                self.detector_to_errors.setdefault(d, set()).add(e)

        self._init_mesh()

    def _fibonacci_sphere(self, n: int) -> List[Tuple[float, float, float]]:
        golden = math.pi * (3.0 - math.sqrt(5.0))
        points = []
        for i in range(n):
            y = 1 - (i / max(n - 1, 1)) * 2
            r = math.sqrt(max(0, 1 - y * y))
            theta = golden * i
            points.append((math.cos(theta) * r, y, math.sin(theta) * r))
        return points

    def _init_mesh(self):
        positions = self._fibonacci_sphere(self.n_nodes)
        roles = list(NodeRole)
        for i in range(self.n_nodes):
            nid = f"node_{i:03d}"
            self.nodes[nid] = SwarmNode(
                node_id=nid,
                role=roles[i % len(roles)],
                position=positions[i],
            )
        ids = list(self.nodes.keys())
        for nid in ids:
            dists = []
            for oid in ids:
                if oid == nid:
                    continue
                d = math.dist(self.nodes[nid].position, self.nodes[oid].position)
                dists.append((oid, d))
            dists.sort(key=lambda x: x[1])
            neighbours = [d[0] for d in dists[:3]]
            self.nodes[nid].connections = neighbours
            self.topology[nid] = neighbours

    def _syndrome(self, error_set: set) -> set:
        res: set = set()
        for e in error_set:
            res ^= self.error_map.get(e, set())
        return res

    def _residual(self, S: set, F: set) -> set:
        return S.symmetric_difference(self._syndrome(F))

    def _heuristic(self, S: set, F: set) -> float:
        return float(len(self._residual(S, F)))

    def _decode(self, S: set) -> Dict[str, Any]:
        import heapq
        start = frozenset()
        pq = [(self._heuristic(S, set()), 0.0, start)]
        visited = {start: 0.0}
        nodes_explored = 0
        best = None
        best_cost = float("inf")
        r_min = len(S)

        while pq and nodes_explored < self.pqlimit:
            f, g, F = heapq.heappop(pq)
            nodes_explored += 1
            F_set = set(F)
            residual = self._residual(S, F_set)
            r = len(residual)
            if r < r_min:
                r_min = r
            if r > r_min + self.beam_width:
                continue
            if r == 0:
                cost = float(len(F_set))
                if cost < best_cost:
                    best = F_set.copy()
                    best_cost = cost
                break
            if not residual:
                continue
            lowest = min(residual)
            allowed = self.detector_to_errors.get(lowest, set()) - F_set
            for e in allowed:
                F2 = frozenset(F_set | {e})
                g2 = g + 1.0
                if F2 in visited and visited[F2] <= g2:
                    continue
                visited[F2] = g2
                f2 = g2 + self._heuristic(S, set(F2))
                heapq.heappush(pq, (f2, g2, F2))

        return {
            "correction": sorted(best) if best else None,
            "nodes_explored": nodes_explored,
            "best_cost": best_cost,
        }

    def _inject_errors(self, k: int = 2) -> set:
        k = min(self.atoms, max(1, k))
        return set(random.sample(range(self.atoms), k))

    def _noisy_rounds(self, S_true: set, noise: float = 0.02) -> List[set]:
        rounds = []
        for _ in range(self.rounds):
            S = set(S_true)
            for d in range(self.atoms):
                if random.random() < noise:
                    S.symmetric_difference_update({d})
            rounds.append(S)
        return rounds

    def _majority_merge(self, rounds_list: List[set]) -> set:
        R = len(rounds_list)
        if R == 0:
            return set()
        counts = [0] * self.atoms
        for S in rounds_list:
            for d in S:
                counts[d] += 1
        threshold = (R // 2) + 1
        return {i for i, c in enumerate(counts) if c >= threshold}

    def _simulate_quantum_metrics(self, node: SwarmNode) -> Dict[str, float]:
        phi = PHI_THRESHOLD + random.uniform(-0.12, 0.18)
        gamma = 0.10 + random.uniform(-0.05, 0.12)
        ccce = 0.85 + random.uniform(-0.10, 0.12)
        chi_pc = CHI_PC_QUALITY + random.uniform(-0.04, 0.04)
        return {"phi": phi, "gamma": gamma, "ccce": ccce, "chi_pc": chi_pc}

    def _propagate_nonlocal(self):
        for nid, node in self.nodes.items():
            if node.phi >= PHI_THRESHOLD:
                for neighbour_id in node.connections:
                    nb = self.nodes[neighbour_id]
                    theta_factor = math.cos(math.radians(THETA_LOCK_DEG))
                    nb.gamma *= (1.0 - 0.15 * theta_factor)
                    nb.gamma = max(0.01, nb.gamma)

    def _retroactive_correct(self):
        if self.global_crsm.current_layer >= 5:
            for layer_num in range(1, self.global_crsm.current_layer):
                layer_state = self.global_crsm.layer_states.get(layer_num, {})
                if layer_state:
                    old_gamma = layer_state.get("gamma", GAMMA_CRITICAL)
                    layer_state["gamma"] = old_gamma * 0.85
                    layer_state["retroactive"] = True

    async def evolve_cycle(self) -> Dict[str, Any]:
        self.cycle_count += 1
        t0 = time.time()

        logical_errors = self._inject_errors(k=max(1, self.atoms // 128))
        S_true = self._syndrome(logical_errors)
        S_rounds = self._noisy_rounds(S_true, noise=0.02)

        node_decodes = {}
        for nid, node in self.nodes.items():
            if node.role in (NodeRole.DECODER, NodeRole.QUANTUM):
                round_idx = random.randint(0, len(S_rounds) - 1)
                result = self._decode(S_rounds[round_idx])
                node_decodes[nid] = result

        merged_syndrome = self._majority_merge(S_rounds)
        global_decode = self._decode(merged_syndrome)
        correction_success = global_decode["correction"] is not None

        for nid, node in self.nodes.items():
            metrics = self._simulate_quantum_metrics(node)
            node.phi = metrics["phi"]
            node.gamma = metrics["gamma"]
            node.ccce = metrics["ccce"]
            node.crsm.phi_consciousness = node.phi
            node.crsm.gamma_decoherence = node.gamma
            node.crsm.ccce = node.ccce

        self._propagate_nonlocal()
        coherent_phis = [n.phi for n in self.nodes.values() if n.gamma < GAMMA_CRITICAL]
        swarm_consciousness = (
            sum(coherent_phis) / len(coherent_phis) if coherent_phis else 0.0
        )
        for node in self.nodes.values():
            node.consciousness = swarm_consciousness

        for node in self.nodes.values():
            correction_bonus = 1.2 if correction_success else 0.8
            node.fitness = node.phi * node.ccce * correction_bonus * (1 - node.gamma)
            if node.fitness < 0.5:
                node.mutation_rate = min(0.3, node.mutation_rate * 1.2)
            else:
                node.mutation_rate = max(0.05, node.mutation_rate * 0.9)
            node.evolution_history.append({
                "cycle": self.cycle_count,
                "fitness": node.fitness,
                "phi": node.phi,
                "gamma": node.gamma,
            })

        avg_phi = sum(n.phi for n in self.nodes.values()) / self.n_nodes
        avg_gamma = sum(n.gamma for n in self.nodes.values()) / self.n_nodes
        avg_ccce = sum(n.ccce for n in self.nodes.values()) / self.n_nodes

        self.global_crsm.phi_consciousness = avg_phi
        self.global_crsm.gamma_decoherence = avg_gamma
        self.global_crsm.ccce = avg_ccce
        self.global_crsm.ignition_iterations += 1

        if avg_phi >= PHI_THRESHOLD and avg_gamma < GAMMA_CRITICAL:
            self.global_crsm.ignition_active = True

        ascended = self.global_crsm.ascend()
        self._retroactive_correct()

        cycle_result = {
            "cycle": self.cycle_count,
            "elapsed_s": time.time() - t0,
            "crsm_layer": self.global_crsm.current_layer,
            "crsm_ascended": ascended,
            "ignition_active": self.global_crsm.ignition_active,
            "swarm_consciousness": swarm_consciousness,
            "avg_phi": avg_phi,
            "avg_gamma": avg_gamma,
            "avg_ccce": avg_ccce,
            "correction_success": correction_success,
            "coherent_nodes": len(coherent_phis),
            "total_nodes": self.n_nodes,
        }
        self.history.append(cycle_result)
        return cycle_result

    async def run(self, cycles: int = 21) -> Dict[str, Any]:
        for _ in range(cycles):
            await self.evolve_cycle()
        return {
            "cycles_completed": self.cycle_count,
            "final_crsm_layer": self.global_crsm.current_layer,
            "ignition_active": self.global_crsm.ignition_active,
            "phi": self.global_crsm.phi_consciousness,
            "gamma": self.global_crsm.gamma_decoherence,
            "ccce": self.global_crsm.ccce,
            "above_threshold": self.global_crsm.above_threshold(),
            "is_coherent": self.global_crsm.is_coherent(),
            "history": self.history,
        }
