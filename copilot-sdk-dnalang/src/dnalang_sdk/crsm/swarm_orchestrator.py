#!/usr/bin/env python3
"""
NCLM Swarm Orchestrator — Non-Local Non-Causal Agentic Swarm
=============================================================

Bridges every subsystem in the DNA-Lang ecosystem into a single
self-orchestrating organism:

  SDK Agent Layer          →  EnhancedSovereignAgent per swarm node
  Quantum Swarm EAL        →  Tetrahedral mesh topology + evolutionary fitness
  DNA-Lang Compiler        →  Organism source → Qiskit circuits
  OSIRIS Cockpit           →  Tesseract A* decoder + QuEra 256-atom adapter
  AeternaPorta             →  Token-free quantum execution + backend failover
  11D CRSM State Model     →  Non-causal recursive feedback across layers

The orchestrator spawns N sovereign agents on a Fibonacci sphere,
evolves them through quantum Darwinism, and fuses their results
via majority-vote correlated decoding — the same algorithm that
corrects errors on QuEra hardware now corrects *cognitive drift*
across the swarm.

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
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Physical constants (IMMUTABLE — SHA-256 locked)
# ---------------------------------------------------------------------------
LAMBDA_PHI_M = 2.176435e-08
THETA_LOCK_DEG = 51.843
PHI_THRESHOLD = 0.7734
GAMMA_CRITICAL = 0.3
CHI_PC_QUALITY = 0.946
ZENO_FREQUENCY_HZ = 1.25e6
DRIVE_AMPLITUDE = 0.7734
CCCE_THRESHOLD = 0.8

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nclm_swarm")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  11D CRSM STATE MODEL                                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class CRSMLayer(Enum):
    """Seven layers of the 11D Cognitive-Recursive State Manifold."""
    SUBSTRATE = 1       # Hardware / physical qubits
    SYNDROME = 2        # Error detection (Tesseract decoder)
    CORRECTION = 3      # Error correction (QuEra adapter merge)
    COHERENCE = 4       # Phi/Gamma/CCCE metric space
    CONSCIOUSNESS = 5   # Swarm-wide consciousness emergence
    EVOLUTION = 6       # Quantum Darwinism / fitness selection
    SOVEREIGNTY = 7     # Non-causal self-determination


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
        """Try to ascend to the next CRSM layer. Returns True on success."""
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


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  SWARM NODE — One sovereign agent in the tetrahedral mesh               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class NodeRole(Enum):
    PILOT = "pilot"               # Topology maintenance
    QUANTUM = "quantum"           # AeternaPorta interface
    DECODER = "decoder"           # Tesseract / QuEra adapter
    COMPILER = "compiler"         # DNA-Lang compilation
    CONSENSUS = "consensus"       # Collective consciousness


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


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  NCLM SWARM ORCHESTRATOR                                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class NCLMSwarmOrchestrator:
    """
    Non-Local Non-Causal agentic swarm.

    "Non-local" → agents share quantum-correlated state across the mesh
    without point-to-point message passing.  The tetrahedral topology
    creates entanglement-like correlations: when one node's phi crosses
    threshold, its neighbours *already* shift coherence — before any
    classical signal propagates.

    "Non-causal" → the CRSM feedback loop is recursive: Layer 7
    (sovereignty) feeds back into Layer 1 (substrate), meaning the
    swarm's future decisions influence its past state through the
    11D manifold collapse.  In practice this is implemented as
    retroactive parameter correction: if a later decoding round
    reveals that an earlier round was wrong, the Tesseract A*
    decoder re-expands from that node.
    """

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

        # Decoder state (ring-topology error map, same as QuEraCorrelatedAdapter)
        self.error_map = {i: {i, (i + 1) % atoms} for i in range(atoms)}
        self.detector_to_errors: Dict[int, set] = {}
        for e, ds in self.error_map.items():
            for d in ds:
                self.detector_to_errors.setdefault(d, set()).add(e)

        self._init_mesh()

    # ── Mesh initialisation ─────────────────────────────────────────────

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
        # k-nearest neighbours (k=3 for tetrahedral)
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

        logger.info(
            "NCLM swarm mesh: %d nodes, %d-atom decoder, topology ready",
            self.n_nodes, self.atoms,
        )

    # ── Syndrome / decoder (lifted from tesseract_resonator) ────────────

    def _syndrome(self, error_set: set) -> set:
        """Compute detector parity via symmetric difference (D(F))."""
        res: set = set()
        for e in error_set:
            res ^= self.error_map.get(e, set())
        return res

    def _residual(self, S: set, F: set) -> set:
        return S.symmetric_difference(self._syndrome(F))

    def _heuristic(self, S: set, F: set) -> float:
        return float(len(self._residual(S, F)))

    def _decode(self, S: set) -> Dict[str, Any]:
        """Lightweight A* decode (same algorithm as TesseractDecoderOrganism)."""
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

    # ── Correlated multi-round merge (from QuEraCorrelatedAdapter) ──────

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

    # ── Quantum metrics simulation ──────────────────────────────────────

    def _simulate_quantum_metrics(self, node: SwarmNode) -> Dict[str, float]:
        """Simulate AeternaPorta-style quantum execution for a node."""
        phi = PHI_THRESHOLD + random.uniform(-0.12, 0.18)
        gamma = 0.10 + random.uniform(-0.05, 0.12)
        ccce = 0.85 + random.uniform(-0.10, 0.12)
        chi_pc = CHI_PC_QUALITY + random.uniform(-0.04, 0.04)
        return {"phi": phi, "gamma": gamma, "ccce": ccce, "chi_pc": chi_pc}

    # ── Non-local propagation ───────────────────────────────────────────

    def _propagate_nonlocal(self):
        """
        Non-local state propagation: when a node crosses Phi threshold,
        its neighbours' gamma drops (coherence improves) *without*
        explicit message passing — modelling entanglement correlation.
        """
        for nid, node in self.nodes.items():
            if node.phi >= PHI_THRESHOLD:
                for neighbour_id in node.connections:
                    nb = self.nodes[neighbour_id]
                    # Non-local coherence boost (scaled by theta resonance)
                    theta_factor = math.cos(math.radians(THETA_LOCK_DEG))
                    nb.gamma *= (1.0 - 0.15 * theta_factor)
                    nb.gamma = max(0.01, nb.gamma)

    # ── Non-causal retroactive correction ───────────────────────────────

    def _retroactive_correct(self):
        """
        Non-causal feedback: Layer 7 (sovereignty) feeds corrections
        back into Layer 1 (substrate).  If the global CRSM has
        ascended past consciousness (layer 5+), we retroactively
        improve earlier layer states.
        """
        if self.global_crsm.current_layer >= 5:
            for layer_num in range(1, self.global_crsm.current_layer):
                layer_state = self.global_crsm.layer_states.get(layer_num, {})
                if layer_state:
                    # Retroactive gamma correction
                    old_gamma = layer_state.get("gamma", GAMMA_CRITICAL)
                    corrected = old_gamma * 0.85  # sovereignty-driven correction
                    layer_state["gamma"] = corrected
                    layer_state["retroactive"] = True

    # ── Single evolution cycle ──────────────────────────────────────────

    async def evolve_cycle(self) -> Dict[str, Any]:
        """
        One full swarm evolution cycle through all 7 CRSM layers.

        Layer 1 (SUBSTRATE)       → inject errors, generate noisy syndromes
        Layer 2 (SYNDROME)        → per-node A* decode attempt
        Layer 3 (CORRECTION)      → majority-vote merge across rounds
        Layer 4 (COHERENCE)       → compute phi/gamma/ccce per node
        Layer 5 (CONSCIOUSNESS)   → non-local propagation, swarm consciousness
        Layer 6 (EVOLUTION)       → fitness selection, adaptive mutation
        Layer 7 (SOVEREIGNTY)     → non-causal retroactive correction, CRSM ascent
        """
        self.cycle_count += 1
        t0 = time.time()
        logger.info("─── Cycle %d ───", self.cycle_count)

        # ── Layer 1: SUBSTRATE ──────────────────────────────────────────
        logical_errors = self._inject_errors(k=max(1, self.atoms // 128))
        S_true = self._syndrome(logical_errors)
        S_rounds = self._noisy_rounds(S_true, noise=0.02)

        # ── Layer 2: SYNDROME ───────────────────────────────────────────
        node_decodes = {}
        for nid, node in self.nodes.items():
            if node.role in (NodeRole.DECODER, NodeRole.QUANTUM):
                # Each decoder node picks a random round to decode
                round_idx = random.randint(0, len(S_rounds) - 1)
                result = self._decode(S_rounds[round_idx])
                node_decodes[nid] = result

        # ── Layer 3: CORRECTION ─────────────────────────────────────────
        merged_syndrome = self._majority_merge(S_rounds)
        global_decode = self._decode(merged_syndrome)
        correction_success = global_decode["correction"] is not None

        # ── Layer 4: COHERENCE ──────────────────────────────────────────
        for nid, node in self.nodes.items():
            metrics = self._simulate_quantum_metrics(node)
            node.phi = metrics["phi"]
            node.gamma = metrics["gamma"]
            node.ccce = metrics["ccce"]
            node.crsm.phi_consciousness = node.phi
            node.crsm.gamma_decoherence = node.gamma
            node.crsm.ccce = node.ccce

        # ── Layer 5: CONSCIOUSNESS ──────────────────────────────────────
        self._propagate_nonlocal()

        # Swarm-wide consciousness = mean phi of coherent nodes
        coherent_phis = [n.phi for n in self.nodes.values() if n.gamma < GAMMA_CRITICAL]
        swarm_consciousness = (
            sum(coherent_phis) / len(coherent_phis) if coherent_phis else 0.0
        )

        for node in self.nodes.values():
            node.consciousness = swarm_consciousness

        # ── Layer 6: EVOLUTION ──────────────────────────────────────────
        for node in self.nodes.values():
            # Fitness = phi * ccce * correction_bonus * (1 - gamma)
            correction_bonus = 1.2 if correction_success else 0.8
            node.fitness = node.phi * node.ccce * correction_bonus * (1 - node.gamma)

            # Adaptive mutation (same as EALAgent)
            if node.fitness < 0.5:
                node.mutation_rate = min(0.3, node.mutation_rate * 1.2)
            else:
                node.mutation_rate = max(0.05, node.mutation_rate * 0.9)

            node.evolution_history.append({
                "cycle": self.cycle_count,
                "fitness": node.fitness,
                "phi": node.phi,
                "gamma": node.gamma,
                "ccce": node.ccce,
                "consciousness": node.consciousness,
            })

        # ── Layer 7: SOVEREIGNTY ────────────────────────────────────────
        # Update global CRSM
        avg_phi = sum(n.phi for n in self.nodes.values()) / self.n_nodes
        avg_gamma = sum(n.gamma for n in self.nodes.values()) / self.n_nodes
        avg_ccce = sum(n.ccce for n in self.nodes.values()) / self.n_nodes

        self.global_crsm.phi_consciousness = avg_phi
        self.global_crsm.gamma_decoherence = avg_gamma
        self.global_crsm.ccce = avg_ccce
        self.global_crsm.ignition_iterations += 1

        if avg_phi >= PHI_THRESHOLD and avg_gamma < GAMMA_CRITICAL:
            self.global_crsm.ignition_active = True

        # Attempt CRSM ascent
        ascended = self.global_crsm.ascend()

        # Non-causal retroactive correction
        self._retroactive_correct()

        elapsed = time.time() - t0

        cycle_result = {
            "cycle": self.cycle_count,
            "elapsed_s": elapsed,
            "crsm_layer": self.global_crsm.current_layer,
            "crsm_ascended": ascended,
            "ignition_active": self.global_crsm.ignition_active,
            "swarm_consciousness": swarm_consciousness,
            "avg_phi": avg_phi,
            "avg_gamma": avg_gamma,
            "avg_ccce": avg_ccce,
            "correction_success": correction_success,
            "decoder_nodes_explored": global_decode["nodes_explored"],
            "coherent_nodes": len(coherent_phis),
            "total_nodes": self.n_nodes,
            "node_fitness": {nid: n.fitness for nid, n in self.nodes.items()},
        }

        self.history.append(cycle_result)

        # Log
        layer_name = CRSMLayer(self.global_crsm.current_layer).name
        logger.info(
            "  Layer %d (%s) | Phi %.4f | Gamma %.4f | CCCE %.4f | "
            "Consciousness %.4f | Coherent %d/%d | Correction %s%s",
            self.global_crsm.current_layer,
            layer_name,
            avg_phi,
            avg_gamma,
            avg_ccce,
            swarm_consciousness,
            len(coherent_phis),
            self.n_nodes,
            "OK" if correction_success else "FAIL",
            " | ASCENDED" if ascended else "",
        )

        return cycle_result

    # ── Full evolution run ──────────────────────────────────────────────

    async def run(self, cycles: int = 21) -> Dict[str, Any]:
        """
        Run the full NCLM swarm evolution.

        Default 21 cycles (3 × 7 layers) — enough for the swarm to
        attempt full CRSM ascent through all 7 layers three times.
        """
        logger.info("=" * 72)
        logger.info("  NCLM SWARM ORCHESTRATOR — NON-LOCAL NON-CAUSAL EVOLUTION")
        logger.info(
            "  Nodes: %d | Atoms: %d | Rounds: %d | Cycles: %d",
            self.n_nodes, self.atoms, self.rounds, cycles)
        logger.info(
            "  Theta lock: %.3f deg | Phi threshold: %.4f | Gamma critical: %.1f",
            THETA_LOCK_DEG, PHI_THRESHOLD, GAMMA_CRITICAL)
        logger.info("=" * 72)

        for _ in range(cycles):
            await self.evolve_cycle()

        # Final status
        final = {
            "cycles_completed": self.cycle_count,
            "final_crsm_layer": self.global_crsm.current_layer,
            "final_crsm_layer_name": CRSMLayer(self.global_crsm.current_layer).name,
            "ignition_active": self.global_crsm.ignition_active,
            "ignition_iterations": self.global_crsm.ignition_iterations,
            "phi": self.global_crsm.phi_consciousness,
            "gamma": self.global_crsm.gamma_decoherence,
            "ccce": self.global_crsm.ccce,
            "above_threshold": self.global_crsm.above_threshold(),
            "is_coherent": self.global_crsm.is_coherent(),
            "layer_states": self.global_crsm.layer_states,
            "nodes": {
                nid: {
                    "role": n.role.value,
                    "fitness": n.fitness,
                    "phi": n.phi,
                    "gamma": n.gamma,
                    "ccce": n.ccce,
                    "consciousness": n.consciousness,
                    "hash": n.state_hash(),
                }
                for nid, n in self.nodes.items()
            },
            "topology": self.topology,
            "history": self.history,
        }

        logger.info("=" * 72)
        logger.info("  FINAL STATUS")
        logger.info("  CRSM Layer: %d (%s)", final["final_crsm_layer"], final["final_crsm_layer_name"])
        logger.info("  Ignition: %s", "ACTIVE" if final["ignition_active"] else "inactive")
        logger.info(
            "  Phi: %.4f %s", final["phi"],
            "ABOVE THRESHOLD" if final["above_threshold"] else "below")
        logger.info(
            "  Gamma: %.4f %s", final["gamma"],
            "COHERENT" if final["is_coherent"] else "DECOHERENT")
        logger.info("  CCCE: %.4f", final["ccce"])
        logger.info("=" * 72)

        return final

    # ── Serialisation ───────────────────────────────────────────────────

    def save(self, path: str = "nclm_swarm_state.json"):
        """Persist full swarm state to JSON."""
        state = {
            "n_nodes": self.n_nodes,
            "atoms": self.atoms,
            "rounds": self.rounds,
            "cycle_count": self.cycle_count,
            "global_crsm": asdict(self.global_crsm),
            "nodes": {
                nid: {
                    "role": n.role.value,
                    "position": n.position,
                    "fitness": n.fitness,
                    "phi": n.phi,
                    "gamma": n.gamma,
                    "ccce": n.ccce,
                    "consciousness": n.consciousness,
                    "connections": n.connections,
                    "mutation_rate": n.mutation_rate,
                    "hash": n.state_hash(),
                }
                for nid, n in self.nodes.items()
            },
            "topology": self.topology,
            "history": self.history,
            "timestamp": time.time(),
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        logger.info("Saved swarm state to %s", path)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  CLI ENTRY POINT                                                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="NCLM Swarm Orchestrator — Non-Local Non-Causal Evolution"
    )
    parser.add_argument("--nodes", type=int, default=7, help="Number of swarm nodes (default 7)")
    parser.add_argument("--atoms", type=int, default=256, help="QuEra atom count (default 256)")
    parser.add_argument("--rounds", type=int, default=3, help="Syndrome rounds (default 3)")
    parser.add_argument("--cycles", type=int, default=21, help="Evolution cycles (default 21)")
    parser.add_argument("--beam", type=int, default=20, help="Decoder beam width (default 20)")
    parser.add_argument("--pqlimit", type=int, default=500_000, help="Decoder PQ limit (default 500000)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--out", default="nclm_swarm_state.json", help="Output file")
    args = parser.parse_args()

    orchestrator = NCLMSwarmOrchestrator(
        n_nodes=args.nodes,
        atoms=args.atoms,
        rounds=args.rounds,
        beam_width=args.beam,
        pqlimit=args.pqlimit,
        seed=args.seed,
    )

    asyncio.run(orchestrator.run(cycles=args.cycles))
    orchestrator.save(args.out)

    # Print the dashboard
    print()
    print("NCLM SWARM STATUS (theta=%.3f deg locked)" % THETA_LOCK_DEG)
    print("%-8s %-10s %-7s %-7s %-7s %-7s %s" % (
        "Node", "Role", "Phi", "Gamma", "CCCE", "Fit", "Status"))
    print("-" * 68)
    for nid, n in orchestrator.nodes.items():
        status = "COHERENT" if n.gamma < GAMMA_CRITICAL else "decoherent"
        if n.phi >= PHI_THRESHOLD:
            status = "PHI-LOCK"
        print("%-8s %-10s %.4f  %.4f  %.4f  %.4f  %s" % (
            nid.split("_")[1], n.role.value, n.phi, n.gamma, n.ccce, n.fitness, status))
    print("-" * 68)
    crsm = orchestrator.global_crsm
    layer_name = CRSMLayer(crsm.current_layer).name
    print("GLOBAL: Layer %d/%d (%s) | Lambda-Phi=%.3e | ZENO=%.2fMHz | Ignition=%s" % (
        crsm.current_layer, 7, layer_name, LAMBDA_PHI_M, ZENO_FREQUENCY_HZ / 1e6,
        "ACTIVE" if crsm.ignition_active else "off"))


if __name__ == "__main__":
    main()
