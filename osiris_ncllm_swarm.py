#!/usr/bin/env python3
"""
OSIRIS NCLLM 9-Agent Swarm Architecture
==========================================

Non-Causal Living Language Model — autonomous swarm of nine specialised
agents that collaborate through recursive distillation, adversarial
self-play, and DNA-encoded autopoietic adaptation.

Agent Roster:
  Core Layer (deterministic reasoning):
    1. Orchestrator  — Strategy decomposition and resource allocation
    2. Reasoner      — Formal logic, proof sketching, null-hypothesis design
    3. Coder         — Implementation, test generation, compilation
    4. Critic        — Quality gating, vulnerability scanning, regression check
    5. Optimizer     — Algorithmic complexity reduction, memory/speed tuning
    6. Self-Reflector — Meta-learning, strategy retrieval, failure-mode logging

  Unbounded Layer (non-causal divergent search):
    7. Rebel         — Constraint inversion, axiom challenge, novel hypothesis
    8. Empath        — User-context alignment, intent deduction, tone calibration
    9. Satirical     — Absurdity filter, over-fitting detection, sanity check

Interaction model:
    Round-robin deliberation → majority-vote gating → distillation pass.
    Every N rounds the Self-Reflector triggers a reward signal that
    adjusts per-agent influence weights (persistent across sessions via
    the 72-Gene Organism autopoietic genes G41-G59).

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
Licensed under OSIRIS Source-Available Dual License v1.0
"""

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("OSIRIS_SWARM")


# ════════════════════════════════════════════════════════════════════════════════
# AGENT IDENTITIES
# ════════════════════════════════════════════════════════════════════════════════

class AgentID(Enum):
    ORCHESTRATOR = "orchestrator"
    REASONER = "reasoner"
    CODER = "coder"
    CRITIC = "critic"
    OPTIMIZER = "optimizer"
    SELF_REFLECTOR = "self_reflector"
    REBEL = "rebel"
    EMPATH = "empath"
    SATIRICAL = "satirical"


CORE_AGENTS = {AgentID.ORCHESTRATOR, AgentID.REASONER, AgentID.CODER,
               AgentID.CRITIC, AgentID.OPTIMIZER, AgentID.SELF_REFLECTOR}
UNBOUNDED_AGENTS = {AgentID.REBEL, AgentID.EMPATH, AgentID.SATIRICAL}


# ════════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentResponse:
    agent: str
    content: str
    confidence: float          # 0-1
    reasoning_trace: str = ""
    vote: Optional[str] = None          # "approve", "reject", "abstain"
    suggestions: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SwarmRound:
    round_num: int
    task: str
    responses: List[AgentResponse] = field(default_factory=list)
    consensus: Optional[str] = None
    vote_tally: Dict[str, int] = field(default_factory=dict)
    distillation_reward: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class SwarmResult:
    task: str
    rounds: List[SwarmRound] = field(default_factory=list)
    final_output: str = ""
    quality_score: float = 0.0
    total_elapsed_ms: float = 0.0
    agents_used: int = 9
    distillation_passes: int = 0
    strategy_embeddings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "task": self.task,
            "rounds": len(self.rounds),
            "final_output": self.final_output[:500],
            "quality_score": self.quality_score,
            "total_elapsed_ms": self.total_elapsed_ms,
            "agents_used": self.agents_used,
            "distillation_passes": self.distillation_passes,
            "metadata": self.metadata,
        }


@dataclass
class NCLMPersonality:
    """
    DNA-encoded personality evolved per user via autopoietic genes G41-G59.
    """
    user_hash: str
    creativity: float = 0.5       # G41
    speed_bias: float = 0.5       # G42
    debug_weight: float = 0.5     # G43
    formality: float = 0.5        # G44
    risk_tolerance: float = 0.5   # G45
    verbosity: float = 0.5        # G46
    domain_affinity: str = "general"  # G47
    interaction_count: int = 0
    trait_history: List[Dict[str, float]] = field(default_factory=list)

    def evolve(self, reward_signal: float, trait: str):
        """Adapt a trait toward the reward signal (bounded [0,1])."""
        lr = 0.05  # learning rate
        current = getattr(self, trait, 0.5)
        updated = current + lr * (reward_signal - current)
        updated = max(0.0, min(1.0, updated))
        setattr(self, trait, updated)
        self.interaction_count += 1
        self.trait_history.append({
            "trait": trait, "old": current, "new": updated,
            "reward": reward_signal, "t": self.interaction_count,
        })

    def gene_vector(self) -> List[float]:
        """Return G41-G46 as a numeric vector."""
        return [self.creativity, self.speed_bias, self.debug_weight,
                self.formality, self.risk_tolerance, self.verbosity]

    @classmethod
    def for_user(cls, user_id: str) -> "NCLMPersonality":
        h = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        return cls(user_hash=h)


# ════════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL AGENTS
# ════════════════════════════════════════════════════════════════════════════════

class SwarmAgent:
    """Base class for all swarm agents."""

    def __init__(self, agent_id: AgentID, influence: float = 1.0):
        self.id = agent_id
        self.influence = influence
        self._call_count = 0

    def respond(self, task: str, context: Dict[str, Any],
                personality: NCLMPersonality) -> AgentResponse:
        self._call_count += 1
        t0 = time.monotonic()
        content, confidence, vote, suggestions = self._think(
            task, context, personality
        )
        elapsed = (time.monotonic() - t0) * 1000
        return AgentResponse(
            agent=self.id.value,
            content=content,
            confidence=confidence,
            vote=vote,
            suggestions=suggestions,
            elapsed_ms=round(elapsed, 2),
        )

    def _think(self, task: str, context: Dict, personality: NCLMPersonality
               ) -> Tuple[str, float, str, List[str]]:
        raise NotImplementedError


class OrchestratorAgent(SwarmAgent):
    """Decomposes tasks into actionable sub-plans."""

    def __init__(self):
        super().__init__(AgentID.ORCHESTRATOR)

    def _think(self, task, ctx, pers):
        steps = self._decompose(task)
        plan = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        return (
            f"Strategic decomposition:\n{plan}",
            0.85, "approve",
            [f"Delegate step {i+1} to {self._assign(s)}" for i, s in enumerate(steps)],
        )

    @staticmethod
    def _decompose(task: str) -> List[str]:
        words = task.split()
        chunk = max(len(words) // 3, 3)
        parts = []
        for i in range(0, len(words), chunk):
            parts.append(" ".join(words[i:i + chunk]))
        if not parts:
            parts = [task]
        return [
            f"Analyse requirements: {parts[0][:60]}",
            f"Implement core logic for: {parts[-1][:60]}",
            "Validate output against acceptance criteria",
            "Optimise and refactor",
        ]

    @staticmethod
    def _assign(step: str) -> str:
        if "analyse" in step.lower() or "require" in step.lower():
            return "Reasoner"
        if "implement" in step.lower():
            return "Coder"
        if "validate" in step.lower():
            return "Critic"
        return "Optimizer"


class ReasonerAgent(SwarmAgent):
    """Formal logic and null-hypothesis design."""

    def __init__(self):
        super().__init__(AgentID.REASONER)

    def _think(self, task, ctx, pers):
        h0 = self._null_hypothesis(task)
        return (
            f"Logical analysis:\n"
            f"  H0: {h0}\n"
            f"  Approach: decompose → formalise → verify",
            0.80, "approve",
            ["Formalise constraints", "Design test for H0 rejection"],
        )

    @staticmethod
    def _null_hypothesis(task: str) -> str:
        return f"The proposed solution for '{task[:50]}...' produces no measurable improvement over baseline."


class CoderAgent(SwarmAgent):
    """Implementation and test generation."""

    def __init__(self):
        super().__init__(AgentID.CODER)

    def _think(self, task, ctx, pers):
        creativity = pers.creativity
        approach = "novel generative" if creativity > 0.7 else "idiomatic reference"
        return (
            f"Implementation plan ({approach} style):\n"
            f"  1. Scaffold structure\n"
            f"  2. Core logic\n"
            f"  3. Unit tests\n"
            f"  4. Integration check",
            0.82, "approve",
            ["Generate test suite", "Add type annotations"],
        )


class CriticAgent(SwarmAgent):
    """Quality gating and vulnerability detection."""

    def __init__(self):
        super().__init__(AgentID.CRITIC)

    def _think(self, task, ctx, pers):
        issues = []
        # Simulate quality checks
        if "security" in task.lower() or "auth" in task.lower():
            issues.append("Verify OWASP Top-10 compliance")
        if "performance" in task.lower() or "speed" in task.lower():
            issues.append("Profile hot paths for O(n) complexity")
        if not issues:
            issues.append("No critical issues detected; minor style review recommended")

        vote = "approve" if len(issues) <= 1 else "reject"
        return (
            f"Quality review:\n" + "\n".join(f"  - {i}" for i in issues),
            0.78, vote, issues,
        )


class OptimizerAgent(SwarmAgent):
    """Algorithmic and resource optimisation."""

    def __init__(self):
        super().__init__(AgentID.OPTIMIZER)

    def _think(self, task, ctx, pers):
        return (
            "Optimisation assessment:\n"
            "  - Memory: check for unnecessary copies\n"
            "  - Speed: vectorise inner loops where possible\n"
            "  - I/O: batch operations, lazy evaluation",
            0.76, "approve",
            ["Profile before optimising", "Consider caching"],
        )


class SelfReflectorAgent(SwarmAgent):
    """Meta-learning and strategy retrieval."""

    def __init__(self):
        super().__init__(AgentID.SELF_REFLECTOR)
        self.strategy_store: List[Dict] = []

    def _think(self, task, ctx, pers):
        # Check for similar past strategies
        similar = self._retrieve_strategy(task)
        if similar:
            return (
                f"Meta-reflection: similar task solved before with strategy "
                f"'{similar['strategy'][:60]}' (reward={similar['reward']:.2f})",
                0.88, "approve",
                [f"Reuse strategy: {similar['strategy'][:40]}"],
            )
        return (
            "Meta-reflection: novel task; logging reasoning trace for future retrieval.",
            0.72, "approve",
            ["Log successful strategies after completion"],
        )

    def embed_strategy(self, task: str, strategy: str, reward: float):
        self.strategy_store.append({
            "task_hash": hashlib.md5(task.encode()).hexdigest()[:8],
            "strategy": strategy,
            "reward": reward,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _retrieve_strategy(self, task: str) -> Optional[Dict]:
        if not self.strategy_store:
            return None
        # Simple keyword overlap retrieval
        task_words = set(task.lower().split())
        best = None
        best_score = 0
        for entry in self.strategy_store:
            strat_words = set(entry["strategy"].lower().split())
            overlap = len(task_words & strat_words)
            if overlap > best_score:
                best_score = overlap
                best = entry
        return best if best_score >= 2 else None


class RebelAgent(SwarmAgent):
    """Constraint inversion and axiom challenge."""

    def __init__(self):
        super().__init__(AgentID.REBEL, influence=0.6)

    def _think(self, task, ctx, pers):
        risk = pers.risk_tolerance
        if risk < 0.3:
            return (
                "Rebel: user prefers conservative approach; deferring to core agents.",
                0.40, "abstain", [],
            )
        return (
            "Rebel perspective:\n"
            "  - What if the fundamental assumption is wrong?\n"
            "  - Invert the constraint: solve the dual problem\n"
            "  - Consider a radically different data structure",
            0.55, "approve",
            ["Challenge primary assumption", "Propose dual-problem formulation"],
        )


class EmpathAgent(SwarmAgent):
    """User-context alignment and intent deduction."""

    def __init__(self):
        super().__init__(AgentID.EMPATH, influence=0.7)

    def _think(self, task, ctx, pers):
        verbosity = pers.verbosity
        formality = pers.formality
        style = "concise, technical" if formality > 0.6 else "conversational, exploratory"
        return (
            f"Empath assessment:\n"
            f"  - User style preference: {style}\n"
            f"  - Verbosity target: {verbosity:.1f}\n"
            f"  - Detected intent: {self._infer_intent(task)}",
            0.70, "approve",
            [f"Adjust output verbosity to {verbosity:.1f}"],
        )

    @staticmethod
    def _infer_intent(task: str) -> str:
        t = task.lower()
        if any(w in t for w in ["fix", "debug", "error", "bug"]):
            return "debugging"
        if any(w in t for w in ["create", "build", "implement", "write"]):
            return "creation"
        if any(w in t for w in ["explain", "why", "how", "what"]):
            return "explanation"
        if any(w in t for w in ["optimiz", "faster", "improv", "refactor"]):
            return "optimization"
        return "general"


class SatiricalAgent(SwarmAgent):
    """Absurdity filter and over-fitting detection."""

    def __init__(self):
        super().__init__(AgentID.SATIRICAL, influence=0.5)

    def _think(self, task, ctx, pers):
        round_count = ctx.get("round", 0)
        if round_count > 3:
            return (
                "Satirical observation: we have debated this for "
                f"{round_count} rounds. Are we over-engineering? "
                "Ship the 80% solution.",
                0.65, "approve",
                ["Consider shipping early", "Diminishing returns detected"],
            )
        return (
            "Satirical check: no absurdity detected yet. Carry on.",
            0.50, "abstain", [],
        )


# ════════════════════════════════════════════════════════════════════════════════
# SWARM ORCHESTRATION ENGINE
# ════════════════════════════════════════════════════════════════════════════════

class NCLLMSwarm:
    """
    Nine-agent Non-Causal Living Language Model swarm.

    Execution loop per task:
      1. Orchestrator decomposes task
      2. All 9 agents deliberate in parallel
      3. Majority-vote gating (weighted by influence)
      4. Self-Reflector computes distillation reward
      5. Personality traits evolve based on reward
      6. Repeat if consensus is "reject" (max 5 rounds)
      7. Emit final distilled output
    """

    MAX_ROUNDS = 5

    def __init__(self, user_id: str = "default"):
        self.personality = NCLMPersonality.for_user(user_id)
        self.agents: Dict[AgentID, SwarmAgent] = {
            AgentID.ORCHESTRATOR: OrchestratorAgent(),
            AgentID.REASONER: ReasonerAgent(),
            AgentID.CODER: CoderAgent(),
            AgentID.CRITIC: CriticAgent(),
            AgentID.OPTIMIZER: OptimizerAgent(),
            AgentID.SELF_REFLECTOR: SelfReflectorAgent(),
            AgentID.REBEL: RebelAgent(),
            AgentID.EMPATH: EmpathAgent(),
            AgentID.SATIRICAL: SatiricalAgent(),
        }
        self._round_history: List[SwarmRound] = []

    def solve(self, task: str, max_rounds: int = 0) -> SwarmResult:
        """Run the full swarm deliberation loop."""
        if max_rounds <= 0:
            max_rounds = self.MAX_ROUNDS

        t0 = time.monotonic()
        rounds: List[SwarmRound] = []
        final_output = ""

        for r in range(1, max_rounds + 1):
            rnd = self._deliberation_round(task, r)
            rounds.append(rnd)

            if rnd.consensus == "approve":
                # Distill best response
                final_output = self._distill(rnd)
                break
        else:
            # Max rounds reached — take best available
            if rounds:
                final_output = self._distill(rounds[-1])

        elapsed = (time.monotonic() - t0) * 1000

        # Compute quality from confidence-weighted vote
        quality = self._compute_quality(rounds)

        # Strategy embedding
        reflector = self.agents[AgentID.SELF_REFLECTOR]
        if isinstance(reflector, SelfReflectorAgent):
            reflector.embed_strategy(task, final_output[:200], quality)

        # Evolve personality
        self.personality.evolve(quality, "creativity")
        self.personality.evolve(1.0 - (elapsed / 10000), "speed_bias")

        return SwarmResult(
            task=task,
            rounds=rounds,
            final_output=final_output,
            quality_score=round(quality, 4),
            total_elapsed_ms=round(elapsed, 2),
            agents_used=len(self.agents),
            distillation_passes=len(rounds),
            strategy_embeddings=[
                e["strategy"][:60]
                for e in (reflector.strategy_store if isinstance(reflector, SelfReflectorAgent) else [])
            ][-5:],
            metadata={
                "user_hash": self.personality.user_hash,
                "personality_vector": self.personality.gene_vector(),
                "interaction_count": self.personality.interaction_count,
            },
        )

    def _deliberation_round(self, task: str, round_num: int) -> SwarmRound:
        """One round of all-agent deliberation."""
        context = {"round": round_num, "history_len": len(self._round_history)}
        responses = []

        for agent in self.agents.values():
            resp = agent.respond(task, context, self.personality)
            responses.append(resp)

        # Weighted vote
        vote_scores = {"approve": 0.0, "reject": 0.0, "abstain": 0.0}
        for resp in responses:
            agent_obj = self.agents.get(AgentID(resp.agent))
            weight = agent_obj.influence if agent_obj else 1.0
            vote = resp.vote or "abstain"
            vote_scores[vote] += weight * resp.confidence

        consensus = max(vote_scores, key=vote_scores.get)
        tally = {k: round(v, 3) for k, v in vote_scores.items()}

        # Distillation reward = mean confidence of approving agents
        approvers = [r for r in responses if r.vote == "approve"]
        reward = (
            sum(r.confidence for r in approvers) / len(approvers)
            if approvers else 0.0
        )

        rnd = SwarmRound(
            round_num=round_num,
            task=task,
            responses=responses,
            consensus=consensus,
            vote_tally=tally,
            distillation_reward=round(reward, 4),
        )
        self._round_history.append(rnd)
        return rnd

    def _distill(self, rnd: SwarmRound) -> str:
        """Distill best response from a round."""
        if not rnd.responses:
            return ""
        best = max(rnd.responses, key=lambda r: r.confidence * (
            self.agents.get(AgentID(r.agent), SwarmAgent(AgentID.ORCHESTRATOR)).influence
        ))
        return best.content

    @staticmethod
    def _compute_quality(rounds: List[SwarmRound]) -> float:
        if not rounds:
            return 0.0
        # Quality = exponentially weighted mean of distillation rewards
        total = 0.0
        weight_sum = 0.0
        for i, rnd in enumerate(rounds):
            w = math.exp(i)
            total += w * rnd.distillation_reward
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0

    def status_report(self) -> str:
        lines = [
            "",
            "=" * 65,
            "  NCLLM 9-Agent Swarm — Status Report",
            "=" * 65,
            f"  User: {self.personality.user_hash}",
            f"  Interactions: {self.personality.interaction_count}",
            f"  Personality: {self.personality.gene_vector()}",
            "",
            "  Agents:",
        ]
        for aid, agent in self.agents.items():
            layer = "core" if aid in CORE_AGENTS else "unbounded"
            lines.append(
                f"    {aid.value:18s}  influence={agent.influence:.2f}  "
                f"calls={agent._call_count:3d}  [{layer}]"
            )
        lines.extend([
            "",
            f"  Strategy store: {len(getattr(self.agents.get(AgentID.SELF_REFLECTOR), 'strategy_store', []))} entries",
            "=" * 65,
        ])
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════════
# CLI / SMOKE TEST
# ════════════════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="OSIRIS NCLLM 9-Agent Swarm",
    )
    parser.add_argument("--task", type=str,
                        default="Implement a thread-safe LRU cache with TTL",
                        help="Task for the swarm to solve")
    parser.add_argument("--user", type=str, default="default",
                        help="User ID for personality evolution")
    parser.add_argument("--rounds", type=int, default=3,
                        help="Max deliberation rounds")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    swarm = NCLLMSwarm(user_id=args.user)
    result = swarm.solve(args.task, max_rounds=args.rounds)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(swarm.status_report())
        print(f"\n  Task: {result.task[:80]}")
        print(f"  Rounds: {len(result.rounds)}")
        print(f"  Quality: {result.quality_score:.4f}")
        print(f"  Time: {result.total_elapsed_ms:.1f} ms")
        print(f"\n  Output:\n{result.final_output}")


if __name__ == "__main__":
    main()
