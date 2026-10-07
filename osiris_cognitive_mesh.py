#!/usr/bin/env python3
"""
OSIRIS Cognitive Mesh — Emergent Swarm Intelligence Layer
==========================================================

A neural-graph overlay for the NCLLM 9-agent swarm that replaces
static round-robin deliberation with:

  1. **Bayesian Influence Networks** — each agent maintains a trust
     posterior over every other agent, updated via Thompson sampling
     after each round.  Influence weights are no longer static floats;
     they are sampled from Beta distributions calibrated by observed
     agreement and outcome quality.

  2. **Shapley-Value Attribution** — after each task, the marginal
     contribution of every agent is computed via a Monte-Carlo Shapley
     estimator.  Agents whose removal degrades quality receive higher
     influence; those that add noise are suppressed.

  3. **Nash Equilibrium Convergence** — the swarm is modelled as a
     cooperative game with transferable utility.  A fictitious-play
     solver drives agent strategies toward a correlated equilibrium,
     preventing the Rebel/Satirical agents from dominating or being
     permanently silenced.

  4. **Causal Reasoning Graph** — agent outputs are organised into a
     DAG where edges represent causal dependencies (e.g., Reasoner
     output *causes* Coder's implementation path).  The graph is
     topologically sorted so that downstream agents receive upstream
     context, eliminating redundant deliberation.

  5. **Hebbian Meta-Plasticity** — agent-pair connection strengths
     follow a Hebbian rule: "agents that fire together wire together."
     Frequently co-approving agents develop strong links; antagonistic
     pairs develop inhibitory connections.  This creates emergent
     sub-coalitions that specialise for task domains.

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
Licensed under OSIRIS Source-Available Dual License v1.0
"""

import math
import random
import hashlib
import json
import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set, FrozenSet

logger = logging.getLogger("OSIRIS_COGNITIVE_MESH")

# ════════════════════════════════════════════════════════════════════════════════
# BAYESIAN TRUST NETWORK
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class BetaTrust:
    """Beta-distributed trust posterior between two agents."""
    alpha: float = 1.0        # successes + prior
    beta_param: float = 1.0   # failures + prior
    _name: str = ""

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta_param)

    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta_param
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    def sample(self) -> float:
        """Thompson sampling: draw from the posterior."""
        return random.betavariate(max(self.alpha, 0.01), max(self.beta_param, 0.01))

    def update(self, success: bool, weight: float = 1.0):
        """Bayesian update."""
        if success:
            self.alpha += weight
        else:
            self.beta_param += weight

    def credible_interval(self, level: float = 0.95) -> Tuple[float, float]:
        """Approximate credible interval using normal approximation."""
        mu = self.mean
        sigma = math.sqrt(self.variance)
        z = 1.96 if level >= 0.95 else 1.645
        return (max(0, mu - z * sigma), min(1, mu + z * sigma))


class BayesianTrustNetwork:
    """
    Directed trust graph: trust[i][j] = Beta distribution representing
    how much agent i trusts agent j's outputs.
    """

    def __init__(self, agent_ids: List[str]):
        self.agents = agent_ids
        self.trust: Dict[str, Dict[str, BetaTrust]] = {}
        for a in agent_ids:
            self.trust[a] = {}
            for b in agent_ids:
                if a != b:
                    self.trust[a][b] = BetaTrust(_name=f"{a}->{b}")

    def sample_influence(self, agent_id: str) -> Dict[str, float]:
        """Sample trust-weighted influence from agent_id's perspective."""
        return {
            other: bt.sample()
            for other, bt in self.trust.get(agent_id, {}).items()
        }

    def update_from_round(self, votes: Dict[str, str],
                          consensus: str, quality: float):
        """
        Update trust posteriors based on round outcome.
        Agents who voted with the consensus on a high-quality round
        get trust boosts from all other agents.
        """
        for agent_a in self.agents:
            for agent_b in self.agents:
                if agent_a == agent_b:
                    continue
                # Did B vote with consensus?
                b_vote = votes.get(agent_b, "abstain")
                agreed = (b_vote == consensus)
                # Weight by quality — high-quality consensus means
                # agreeing agents are truly trustworthy
                weight = quality if agreed else (1 - quality) * 0.5
                self.trust[agent_a][agent_b].update(agreed, weight)

    def get_aggregate_influence(self, agent_id: str) -> float:
        """Mean trust that all other agents have in agent_id."""
        trusts = []
        for other in self.agents:
            if other != agent_id and agent_id in self.trust.get(other, {}):
                trusts.append(self.trust[other][agent_id].mean)
        return sum(trusts) / len(trusts) if trusts else 0.5

    def summary(self) -> Dict[str, Any]:
        result = {}
        for a in self.agents:
            result[a] = {
                "aggregate_trust": round(self.get_aggregate_influence(a), 4),
                "peers": {
                    b: round(bt.mean, 4)
                    for b, bt in self.trust.get(a, {}).items()
                }
            }
        return result


# ════════════════════════════════════════════════════════════════════════════════
# MONTE CARLO SHAPLEY VALUES
# ════════════════════════════════════════════════════════════════════════════════

class ShapleyEstimator:
    """
    Monte-Carlo Shapley value estimator for agent contribution.

    For each permutation sample, we measure the marginal contribution
    of adding each agent to the growing coalition.  The characteristic
    function v(S) is approximated as the quality score when only
    agents in S participate.
    """

    def __init__(self, agent_ids: List[str], n_samples: int = 200):
        self.agents = agent_ids
        self.n_samples = n_samples
        self._shapley_values: Dict[str, float] = {a: 0.0 for a in agent_ids}
        self._task_count = 0

    def estimate(self, quality_fn) -> Dict[str, float]:
        """
        Estimate Shapley values for all agents.

        Args:
            quality_fn: Callable(Set[str]) -> float
                Returns quality score for a coalition of agents.
        """
        n = len(self.agents)
        phi = {a: 0.0 for a in self.agents}

        for _ in range(self.n_samples):
            perm = list(self.agents)
            random.shuffle(perm)
            coalition: Set[str] = set()
            prev_value = 0.0

            for agent in perm:
                coalition.add(agent)
                current_value = quality_fn(frozenset(coalition))
                marginal = current_value - prev_value
                phi[agent] += marginal
                prev_value = current_value

        # Normalize
        for a in self.agents:
            phi[a] /= self.n_samples

        self._shapley_values = phi
        self._task_count += 1
        return phi

    def update_running_average(self, new_values: Dict[str, float]):
        """Exponential moving average of Shapley values."""
        alpha = 0.3  # recency weight
        for a in self.agents:
            old = self._shapley_values.get(a, 0.0)
            new = new_values.get(a, 0.0)
            self._shapley_values[a] = alpha * new + (1 - alpha) * old

    @property
    def values(self) -> Dict[str, float]:
        return dict(self._shapley_values)

    def dominant_coalition(self, threshold: float = 0.0) -> List[str]:
        """Agents with above-threshold Shapley value."""
        return [a for a, v in self._shapley_values.items() if v > threshold]


# ════════════════════════════════════════════════════════════════════════════════
# NASH EQUILIBRIUM (FICTITIOUS PLAY)
# ════════════════════════════════════════════════════════════════════════════════

class FictitiousPlaySolver:
    """
    Fictitious-play solver for the cooperative swarm game.

    Each agent has a strategy space {contribute, abstain, challenge}.
    The payoff matrix encodes that:
      - Contributing to correct consensus yields high reward
      - Challenging incorrect consensus yields high reward
      - Free-riding (abstaining when contribution matters) yields low reward
    """

    STRATEGIES = ["contribute", "abstain", "challenge"]

    def __init__(self, agent_ids: List[str]):
        self.agents = agent_ids
        # Empirical frequency of each strategy per agent
        self.freq: Dict[str, Dict[str, float]] = {
            a: {s: 1.0 / 3 for s in self.STRATEGIES}
            for a in agent_ids
        }
        self._history: List[Dict[str, str]] = []

    def best_response(self, agent_id: str,
                      payoff_matrix: Dict[str, Dict[str, float]]) -> str:
        """
        Compute best response for agent given others' empirical frequencies.
        """
        expected = {}
        for strategy in self.STRATEGIES:
            ep = 0.0
            for other in self.agents:
                if other == agent_id:
                    continue
                for opp_strat, opp_prob in self.freq[other].items():
                    key = f"{strategy}_vs_{opp_strat}"
                    ep += opp_prob * payoff_matrix.get(key, {}).get(agent_id, 0.0)
            expected[strategy] = ep
        return max(expected, key=expected.get)

    def update(self, actions: Dict[str, str]):
        """
        Update empirical frequencies after observed actions.
        """
        self._history.append(actions)
        t = len(self._history)
        for agent, action in actions.items():
            for s in self.STRATEGIES:
                if s == action:
                    self.freq[agent][s] = (
                        self.freq[agent][s] * (t - 1) + 1.0
                    ) / t
                else:
                    self.freq[agent][s] = (
                        self.freq[agent][s] * (t - 1)
                    ) / t

    def convergence_metric(self) -> float:
        """
        Measure how close to equilibrium (low = converged).
        Uses max frequency variance across agents.
        """
        variances = []
        for agent in self.agents:
            probs = list(self.freq[agent].values())
            mean_p = sum(probs) / len(probs)
            var = sum((p - mean_p) ** 2 for p in probs) / len(probs)
            variances.append(var)
        return max(variances) if variances else 0.0

    def equilibrium_profile(self) -> Dict[str, str]:
        """Current best guess at equilibrium: each agent's most frequent strategy."""
        return {
            agent: max(strats, key=strats.get)
            for agent, strats in self.freq.items()
        }


# ════════════════════════════════════════════════════════════════════════════════
# CAUSAL REASONING GRAPH
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class CausalEdge:
    source: str
    target: str
    strength: float = 1.0
    evidence_count: int = 0

    def reinforce(self, amount: float = 0.1):
        self.strength = min(2.0, self.strength + amount)
        self.evidence_count += 1

    def decay(self, rate: float = 0.01):
        self.strength = max(0.0, self.strength - rate)


class CausalReasoningGraph:
    """
    DAG of causal dependencies between agent outputs.

    Default structure:
        Orchestrator → Reasoner → Coder → Critic
        Orchestrator → Optimizer
        Rebel → Reasoner (challenge path)
        Empath → Orchestrator (intent alignment)
        SelfReflector → all (meta-monitoring)
    """

    def __init__(self, agent_ids: List[str]):
        self.agents = agent_ids
        self.edges: Dict[Tuple[str, str], CausalEdge] = {}
        self._build_default_graph()

    def _build_default_graph(self):
        default_edges = [
            ("orchestrator", "reasoner", 1.0),
            ("orchestrator", "optimizer", 0.8),
            ("reasoner", "coder", 1.0),
            ("coder", "critic", 1.0),
            ("critic", "optimizer", 0.7),
            ("rebel", "reasoner", 0.6),
            ("empath", "orchestrator", 0.7),
            ("self_reflector", "orchestrator", 0.9),
            ("self_reflector", "critic", 0.8),
            ("satirical", "critic", 0.5),
        ]
        for src, tgt, strength in default_edges:
            if src in self.agents and tgt in self.agents:
                self.edges[(src, tgt)] = CausalEdge(src, tgt, strength)

    def topological_order(self) -> List[str]:
        """Return agents in causal execution order (Kahn's algorithm)."""
        in_degree = {a: 0 for a in self.agents}
        adj = defaultdict(list)
        for (src, tgt), edge in self.edges.items():
            if edge.strength > 0.1:  # only active edges
                adj[src].append(tgt)
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        queue = [a for a in self.agents if in_degree.get(a, 0) == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Append any remaining (cycle members) in original order
        for a in self.agents:
            if a not in order:
                order.append(a)
        return order

    def upstream_context(self, agent_id: str) -> List[str]:
        """Return agents whose output feeds into agent_id."""
        return [
            edge.source for (src, tgt), edge in self.edges.items()
            if tgt == agent_id and edge.strength > 0.1
        ]

    def reinforce_edge(self, src: str, tgt: str, amount: float = 0.1):
        key = (src, tgt)
        if key in self.edges:
            self.edges[key].reinforce(amount)
        else:
            self.edges[key] = CausalEdge(src, tgt, 0.5 + amount)

    def decay_all(self, rate: float = 0.005):
        for edge in self.edges.values():
            edge.decay(rate)

    def to_dict(self) -> Dict:
        return {
            "agents": self.agents,
            "edges": [
                {"source": e.source, "target": e.target,
                 "strength": round(e.strength, 4),
                 "evidence": e.evidence_count}
                for e in self.edges.values() if e.strength > 0.05
            ],
            "execution_order": self.topological_order(),
        }


# ════════════════════════════════════════════════════════════════════════════════
# HEBBIAN META-PLASTICITY
# ════════════════════════════════════════════════════════════════════════════════

class HebbianPlasticity:
    """
    'Agents that fire together wire together.'

    Connection strength w(i,j) is updated after each round:
        Δw = η * (co_activation - decay)

    co_activation = 1 if both agents voted the same way, else 0
    Connections can be excitatory (>0) or inhibitory (<0).
    """

    def __init__(self, agent_ids: List[str], learning_rate: float = 0.05,
                 decay_rate: float = 0.01):
        self.agents = agent_ids
        self.eta = learning_rate
        self.decay = decay_rate
        # Symmetric weight matrix
        self.weights: Dict[FrozenSet[str], float] = {}
        for i, a in enumerate(agent_ids):
            for b in agent_ids[i+1:]:
                self.weights[frozenset({a, b})] = 0.0

    def update(self, votes: Dict[str, str]):
        """
        Hebbian update: strengthen connections between co-voting agents,
        weaken connections between opposing agents.
        """
        agents_list = list(votes.keys())
        for i, a in enumerate(agents_list):
            for b in agents_list[i+1:]:
                key = frozenset({a, b})
                if key not in self.weights:
                    self.weights[key] = 0.0

                v_a = votes.get(a, "abstain")
                v_b = votes.get(b, "abstain")

                if v_a == v_b and v_a != "abstain":
                    # Co-activation: strengthen
                    self.weights[key] += self.eta
                elif v_a != v_b and v_a != "abstain" and v_b != "abstain":
                    # Anti-correlation: inhibit
                    self.weights[key] -= self.eta * 0.5

                # Decay toward zero
                self.weights[key] *= (1 - self.decay)

                # Clamp
                self.weights[key] = max(-1.0, min(1.0, self.weights[key]))

    def coalition_strength(self, agents: Set[str]) -> float:
        """Total internal connection strength of a coalition."""
        total = 0.0
        agents_list = list(agents)
        for i, a in enumerate(agents_list):
            for b in agents_list[i+1:]:
                key = frozenset({a, b})
                total += self.weights.get(key, 0.0)
        return total

    def emergent_coalitions(self, threshold: float = 0.1) -> List[Set[str]]:
        """Detect clusters of strongly connected agents."""
        # Simple greedy clustering
        used = set()
        coalitions = []
        sorted_pairs = sorted(
            self.weights.items(), key=lambda x: x[1], reverse=True
        )
        for pair, w in sorted_pairs:
            if w < threshold:
                break
            agents = set(pair)
            if not agents & used:
                # Expand coalition with other strong neighbors
                coalition = set(agents)
                for other_pair, other_w in sorted_pairs:
                    if other_w < threshold:
                        break
                    other_agents = set(other_pair)
                    if other_agents & coalition and not (other_agents - coalition) & used:
                        coalition |= other_agents
                coalitions.append(coalition)
                used |= coalition
        return coalitions

    def top_connections(self, n: int = 5) -> List[Tuple[str, str, float]]:
        """Top-N strongest connections."""
        sorted_conns = sorted(
            self.weights.items(), key=lambda x: abs(x[1]), reverse=True
        )
        result = []
        for pair, w in sorted_conns[:n]:
            agents = list(pair)
            result.append((agents[0], agents[1], round(w, 4)))
        return result


# ════════════════════════════════════════════════════════════════════════════════
# COGNITIVE MESH — UNIFIED INTEGRATION
# ════════════════════════════════════════════════════════════════════════════════

class CognitiveMesh:
    """
    Unified cognitive layer that wraps the NCLLM swarm with:
      - Bayesian trust network for dynamic influence
      - Shapley attribution for contribution measurement
      - Nash equilibrium for strategy convergence
      - Causal DAG for execution ordering
      - Hebbian plasticity for emergent coalitions

    This replaces static influence weights and round-robin deliberation
    with an adaptive, game-theoretically grounded swarm intelligence.
    """

    def __init__(self, agent_ids: List[str] = None):
        if agent_ids is None:
            agent_ids = [
                "orchestrator", "reasoner", "coder", "critic",
                "optimizer", "self_reflector", "rebel", "empath", "satirical"
            ]
        self.agent_ids = agent_ids

        self.trust_net = BayesianTrustNetwork(agent_ids)
        self.shapley = ShapleyEstimator(agent_ids, n_samples=100)
        self.nash = FictitiousPlaySolver(agent_ids)
        self.causal_graph = CausalReasoningGraph(agent_ids)
        self.hebbian = HebbianPlasticity(agent_ids)

        self._round_count = 0
        self._task_count = 0
        self._quality_history: List[float] = []

    def get_execution_order(self) -> List[str]:
        """Get causal topological order for agent execution."""
        return self.causal_graph.topological_order()

    def get_dynamic_influence(self, agent_id: str) -> float:
        """
        Compute dynamic influence from all sources:
          influence = 0.4 * trust + 0.3 * shapley + 0.2 * nash + 0.1 * hebbian
        """
        trust = self.trust_net.get_aggregate_influence(agent_id)
        shapley_val = self.shapley.values.get(agent_id, 0.0)
        # Normalize shapley to [0,1]
        sv_max = max(abs(v) for v in self.shapley.values.values()) if self.shapley.values else 1.0
        shapley_norm = (shapley_val / sv_max) if sv_max > 0 else 0.5

        nash_freq = self.nash.freq.get(agent_id, {}).get("contribute", 0.33)
        hebbian_strength = sum(
            self.hebbian.weights.get(frozenset({agent_id, other}), 0.0)
            for other in self.agent_ids if other != agent_id
        ) / max(len(self.agent_ids) - 1, 1)
        hebbian_norm = (hebbian_strength + 1) / 2  # map [-1,1] to [0,1]

        influence = (
            0.4 * trust +
            0.3 * max(0, min(1, 0.5 + shapley_norm)) +
            0.2 * nash_freq +
            0.1 * hebbian_norm
        )
        return max(0.05, min(1.0, influence))

    def post_round_update(self, votes: Dict[str, str],
                          consensus: str, quality: float):
        """
        Update all cognitive layers after a deliberation round.
        """
        self._round_count += 1

        # 1. Bayesian trust update
        self.trust_net.update_from_round(votes, consensus, quality)

        # 2. Hebbian plasticity
        self.hebbian.update(votes)

        # 3. Nash strategy update — map votes to strategies
        actions = {}
        for agent, vote in votes.items():
            if vote == "approve":
                actions[agent] = "contribute"
            elif vote == "reject":
                actions[agent] = "challenge"
            else:
                actions[agent] = "abstain"
        self.nash.update(actions)

        # 4. Causal graph reinforcement
        # Reinforce edges where upstream agent approved and downstream agreed
        for agent in self.agent_ids:
            upstream = self.causal_graph.upstream_context(agent)
            for up_agent in upstream:
                if votes.get(up_agent) == votes.get(agent) and votes.get(agent) != "abstain":
                    self.causal_graph.reinforce_edge(up_agent, agent, 0.05)
        self.causal_graph.decay_all(0.002)

    def post_task_update(self, quality: float, agent_qualities: Dict[str, float]):
        """
        Update task-level metrics (Shapley values).
        """
        self._task_count += 1
        self._quality_history.append(quality)

        # Build a quality function from observed agent qualities
        def quality_fn(coalition: FrozenSet[str]) -> float:
            if not coalition:
                return 0.0
            # Quality with this coalition = mean of member qualities * synergy bonus
            member_qualities = [agent_qualities.get(a, 0.5) for a in coalition]
            base = sum(member_qualities) / len(member_qualities)
            # Synergy: more diverse agents = bonus
            synergy = min(1.0, len(coalition) / len(self.agent_ids))
            # Hebbian coalition bonus
            heb_bonus = self.hebbian.coalition_strength(set(coalition))
            return base * (1 + 0.1 * synergy) * (1 + 0.05 * max(0, heb_bonus))

        new_shapley = self.shapley.estimate(quality_fn)
        self.shapley.update_running_average(new_shapley)

    def status_report(self) -> Dict[str, Any]:
        """Full cognitive mesh diagnostic report."""
        return {
            "rounds": self._round_count,
            "tasks": self._task_count,
            "avg_quality": (
                sum(self._quality_history) / len(self._quality_history)
                if self._quality_history else 0.0
            ),
            "trust_summary": self.trust_net.summary(),
            "shapley_values": {
                a: round(v, 4) for a, v in self.shapley.values.items()
            },
            "nash_convergence": round(self.nash.convergence_metric(), 6),
            "nash_equilibrium": self.nash.equilibrium_profile(),
            "causal_graph": self.causal_graph.to_dict(),
            "emergent_coalitions": [
                list(c) for c in self.hebbian.emergent_coalitions()
            ],
            "top_connections": self.hebbian.top_connections(5),
            "dynamic_influence": {
                a: round(self.get_dynamic_influence(a), 4)
                for a in self.agent_ids
            },
        }

    def print_dashboard(self):
        """Pretty-print the cognitive mesh state."""
        print("\n" + "═" * 72)
        print("  OSIRIS COGNITIVE MESH — Emergent Intelligence Dashboard")
        print("═" * 72)
        print(f"  Rounds: {self._round_count}  |  Tasks: {self._task_count}  |  "
              f"Nash convergence: {self.nash.convergence_metric():.6f}")

        print("\n  ── Dynamic Influence ──")
        influences = sorted(
            [(a, self.get_dynamic_influence(a)) for a in self.agent_ids],
            key=lambda x: x[1], reverse=True
        )
        for agent, inf in influences:
            bar = "█" * int(inf * 30) + "░" * (30 - int(inf * 30))
            print(f"    {agent:18s} [{bar}] {inf:.4f}")

        print("\n  ── Shapley Attribution ──")
        shapley_sorted = sorted(
            self.shapley.values.items(), key=lambda x: x[1], reverse=True
        )
        for agent, sv in shapley_sorted:
            sign = "+" if sv >= 0 else "-"
            print(f"    {agent:18s}  {sign}{abs(sv):.4f}")

        coalitions = self.hebbian.emergent_coalitions()
        if coalitions:
            print("\n  ── Emergent Coalitions ──")
            for i, c in enumerate(coalitions):
                strength = self.hebbian.coalition_strength(c)
                print(f"    Coalition {i+1}: {', '.join(sorted(c))}  "
                      f"(strength={strength:.3f})")

        print("\n  ── Causal Execution Order ──")
        order = self.causal_graph.topological_order()
        print(f"    {' → '.join(order)}")

        conns = self.hebbian.top_connections(3)
        if conns:
            print("\n  ── Strongest Agent Bonds ──")
            for a, b, w in conns:
                kind = "excitatory" if w > 0 else "inhibitory"
                print(f"    {a} ↔ {b}: {w:+.4f} ({kind})")

        print("═" * 72)
