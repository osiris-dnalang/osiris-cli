#!/usr/bin/env python3
"""
OSIRIS NCLLM Introspection Engine
====================================

Recursive tridirectional self-awareness layer for the 9-agent swarm.
Three axes of introspection operating simultaneously:

  Axis 1 — TEMPORAL: How is the swarm evolving over time?
    • Confidence drift detection (CUSUM algorithm)
    • Quality trajectory forecasting (exponential smoothing)
    • Agent decay detection (agents losing effectiveness)

  Axis 2 — STRUCTURAL: How are agents relating to each other?
    • Cognitive entropy measurement (information-theoretic diversity)
    • Echo-chamber detection (agents converging too tightly)
    • Contrarian value estimation (measuring Rebel/Satirical impact)

  Axis 3 — SEMANTIC: What is the swarm actually learning?
    • Strategy fingerprinting (LSH of successful strategies)
    • Capability boundary mapping (what tasks succeed/fail)
    • Blind-spot detection (systematic failure patterns)

The introspection engine feeds back into:
  → Cognitive mesh (adjusts trust/Shapley/Nash)
  → Intent engine (adjusts confidence/routing)
  → TUI/CLI (surfaces diagnostics to user)

Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC
Licensed under OSIRIS Source-Available Dual License v1.0
"""

import math
import time
import json
import hashlib
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set

logger = logging.getLogger("OSIRIS_INTROSPECTION")


# ════════════════════════════════════════════════════════════════════════════════
# AXIS 1 — TEMPORAL INTROSPECTION
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class DriftAlert:
    """A detected anomaly in agent performance trajectory."""
    agent_id: str
    metric: str          # "confidence", "quality", "consensus_rate"
    direction: str       # "degrading", "improving", "oscillating"
    severity: float      # 0-1
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    context: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class CUSUMDetector:
    """
    Cumulative Sum (CUSUM) change-point detector.
    Detects sustained shifts in a time series — more robust than
    simple threshold checks because it accumulates evidence.

    H+ tracks upward shifts, H- tracks downward shifts.
    When either exceeds the threshold, a drift is declared.
    """

    def __init__(self, target: float = 0.0, threshold: float = 4.0,
                 drift_weight: float = 1.0):
        self.target = target
        self.threshold = threshold
        self.drift_weight = drift_weight
        self.s_hi = 0.0
        self.s_lo = 0.0
        self._observations: List[float] = []

    def update(self, value: float) -> Optional[str]:
        """
        Feed a new observation. Returns drift direction or None.
        """
        self._observations.append(value)

        # Estimate running mean if no target specified
        if len(self._observations) > 10:
            recent_mean = sum(self._observations[-10:]) / 10
        else:
            recent_mean = self.target

        residual = value - recent_mean

        self.s_hi = max(0, self.s_hi + residual - self.drift_weight)
        self.s_lo = max(0, self.s_lo - residual - self.drift_weight)

        if self.s_hi > self.threshold:
            self.s_hi = 0  # reset after detection
            return "improving"
        if self.s_lo > self.threshold:
            self.s_lo = 0
            return "degrading"
        return None

    @property
    def cumulative_sum(self) -> Tuple[float, float]:
        return (self.s_hi, self.s_lo)


class TemporalIntrospector:
    """
    Monitors agent performance over time to detect:
    - Confidence drift (agent becoming over/under-confident)
    - Quality degradation (solutions getting worse)
    - Consensus fatigue (agent always agreeing — lost utility)
    """

    def __init__(self, agent_ids: List[str], window: int = 50):
        self.agents = agent_ids
        self.window = window

        # Per-agent CUSUM detectors
        self._confidence_cusum: Dict[str, CUSUMDetector] = {
            a: CUSUMDetector(target=0.7, threshold=3.0)
            for a in agent_ids
        }
        self._quality_cusum = CUSUMDetector(target=0.75, threshold=3.0)

        # Sliding windows
        self._confidence_history: Dict[str, deque] = {
            a: deque(maxlen=window) for a in agent_ids
        }
        self._quality_history: deque = deque(maxlen=window)
        self._consensus_rate: Dict[str, deque] = {
            a: deque(maxlen=window) for a in agent_ids
        }

        self._alerts: List[DriftAlert] = []

    def observe_round(self, responses: List[Dict[str, Any]],
                      consensus: str, quality: float):
        """
        Feed one round of swarm output into the temporal tracker.

        Args:
            responses: list of {"agent": str, "confidence": float, "vote": str}
            consensus: the consensus vote for this round
            quality: overall quality score
        """
        self._quality_history.append(quality)
        drift = self._quality_cusum.update(quality)
        if drift:
            self._alerts.append(DriftAlert(
                agent_id="swarm",
                metric="quality",
                direction=drift,
                severity=0.8,
                context=f"Quality CUSUM triggered ({drift}), q={quality:.3f}"
            ))

        for resp in responses:
            agent = resp["agent"]
            conf = resp.get("confidence", 0.5)
            vote = resp.get("vote", "abstain")

            if agent not in self._confidence_history:
                continue

            self._confidence_history[agent].append(conf)
            self._consensus_rate[agent].append(
                1.0 if vote == consensus else 0.0
            )

            # Check confidence drift
            cdrift = self._confidence_cusum[agent].update(conf)
            if cdrift:
                self._alerts.append(DriftAlert(
                    agent_id=agent,
                    metric="confidence",
                    direction=cdrift,
                    severity=0.6,
                    context=f"Confidence {cdrift}: {conf:.3f}"
                ))

            # Check consensus fatigue (always agreeing = low utility)
            if len(self._consensus_rate[agent]) >= 10:
                rate = sum(self._consensus_rate[agent]) / len(
                    self._consensus_rate[agent]
                )
                if rate > 0.95:
                    self._alerts.append(DriftAlert(
                        agent_id=agent,
                        metric="consensus_rate",
                        direction="degrading",
                        severity=0.5,
                        context=f"Consensus fatigue: {agent} agrees {rate:.0%} "
                                f"of the time (rubber-stamping)"
                    ))

    def quality_forecast(self, horizon: int = 5) -> List[float]:
        """
        Exponential smoothing forecast of quality trajectory.
        Uses Holt's linear method (level + trend).
        """
        if len(self._quality_history) < 3:
            mean = sum(self._quality_history) / max(len(self._quality_history), 1)
            return [mean] * horizon

        data = list(self._quality_history)
        alpha = 0.3  # level smoothing
        beta = 0.1   # trend smoothing

        level = data[0]
        trend = data[1] - data[0]

        for val in data[1:]:
            prev_level = level
            level = alpha * val + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        forecast = []
        for h in range(1, horizon + 1):
            forecast.append(max(0.0, min(1.0, level + h * trend)))
        return forecast

    def agent_health(self) -> Dict[str, Dict[str, float]]:
        """Per-agent health metrics."""
        health = {}
        for agent in self.agents:
            conf_vals = list(self._confidence_history[agent])
            cons_vals = list(self._consensus_rate[agent])

            avg_conf = sum(conf_vals) / max(len(conf_vals), 1)
            avg_cons = sum(cons_vals) / max(len(cons_vals), 1)

            # Stability = inverse of variance
            if len(conf_vals) >= 3:
                mean = avg_conf
                var = sum((x - mean) ** 2 for x in conf_vals) / len(conf_vals)
                stability = max(0, 1 - math.sqrt(var) * 3)
            else:
                stability = 0.5

            health[agent] = {
                "avg_confidence": round(avg_conf, 4),
                "consensus_agreement": round(avg_cons, 4),
                "stability": round(stability, 4),
                "observations": len(conf_vals),
            }
        return health

    def recent_alerts(self, n: int = 10) -> List[DriftAlert]:
        return self._alerts[-n:]

    def clear_alerts(self):
        self._alerts.clear()


# ════════════════════════════════════════════════════════════════════════════════
# AXIS 2 — STRUCTURAL INTROSPECTION
# ════════════════════════════════════════════════════════════════════════════════

class StructuralIntrospector:
    """
    Monitors the structural dynamics of agent interactions:

    1. Cognitive Entropy — Shannon entropy of the vote distribution.
       High entropy = diverse opinions (healthy).
       Near-zero entropy = echo chamber (pathological).

    2. Echo-Chamber Score — measures how often agents cluster
       into fixed voting blocs across rounds.

    3. Contrarian Value — estimates the marginal information gain
       from agents that vote against majority. If rebels never
       change outcomes, they're useless. If they occasionally
       flip decisions that turn out better, they're invaluable.
    """

    def __init__(self, agent_ids: List[str]):
        self.agents = agent_ids
        self._vote_ledger: List[Dict[str, str]] = []
        self._quality_ledger: List[float] = []
        self._flip_events: List[Dict[str, Any]] = []

    def observe_round(self, votes: Dict[str, str], consensus: str,
                      quality: float):
        """Record votes from one round."""
        self._vote_ledger.append(votes)
        self._quality_ledger.append(quality)

        # Detect flip events: rounds where contrarian agents changed
        # the consensus vs what majority-only would have produced
        majority_votes = {
            a: v for a, v in votes.items()
            if a not in ("rebel", "satirical", "empath")
        }
        core_consensus = self._majority(majority_votes)
        if core_consensus != consensus:
            self._flip_events.append({
                "round": len(self._vote_ledger),
                "core_would_have": core_consensus,
                "actual": consensus,
                "quality": quality,
                "agents_who_flipped": [
                    a for a, v in votes.items()
                    if a in ("rebel", "satirical", "empath")
                    and v == consensus and v != core_consensus
                ]
            })

    def cognitive_entropy(self) -> float:
        """
        Shannon entropy of the aggregate vote distribution
        across all rounds. Measures opinion diversity.

        H = -Σ p(v) * log2(p(v))

        Returns entropy in bits. Max = log2(3) ≈ 1.585 for 3 vote types.
        """
        if not self._vote_ledger:
            return 0.0

        vote_counts: Dict[str, int] = defaultdict(int)
        total = 0
        for round_votes in self._vote_ledger:
            for vote in round_votes.values():
                vote_counts[vote] += 1
                total += 1

        if total == 0:
            return 0.0

        entropy = 0.0
        for count in vote_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    def echo_chamber_score(self) -> float:
        """
        Measures voting-bloc rigidity across rounds.
        For each pair of agents, compute the fraction of rounds
        where they voted identically. Average across all pairs.

        Score near 1.0 = severe echo chamber.
        Score near 0.33 = random/independent voting.
        """
        if len(self._vote_ledger) < 3:
            return 0.0

        pair_agreement: Dict[tuple, List[float]] = {}
        for rnd in self._vote_ledger:
            agents_list = list(rnd.keys())
            for i, a in enumerate(agents_list):
                for b in agents_list[i+1:]:
                    key = tuple(sorted([a, b]))
                    agreed = 1.0 if rnd.get(a) == rnd.get(b) else 0.0
                    pair_agreement.setdefault(key, []).append(agreed)

        if not pair_agreement:
            return 0.0

        pair_rates = [
            sum(agreements) / len(agreements)
            for agreements in pair_agreement.values()
        ]
        return sum(pair_rates) / len(pair_rates)

    def contrarian_value(self) -> Dict[str, float]:
        """
        Marginal information gain from each contrarian agent.

        For each flip event (round where unbounded agents changed
        the outcome), compare quality to the running average.
        If flipped rounds have higher quality → positive contrarian value.
        """
        if not self._quality_ledger:
            return {}

        avg_quality = sum(self._quality_ledger) / len(self._quality_ledger)
        agent_values: Dict[str, List[float]] = defaultdict(list)

        for event in self._flip_events:
            delta = event["quality"] - avg_quality
            for agent in event["agents_who_flipped"]:
                agent_values[agent].append(delta)

        result = {}
        for agent, deltas in agent_values.items():
            result[agent] = round(sum(deltas) / max(len(deltas), 1), 4)
        return result

    def voting_pattern_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Co-voting frequency matrix for all agent pairs.
        Returns: {agent_a: {agent_b: agreement_rate}}
        """
        if len(self._vote_ledger) < 2:
            return {}

        matrix: Dict[str, Dict[str, float]] = {
            a: {} for a in self.agents
        }
        counts: Dict[tuple, List[float]] = {}

        for rnd in self._vote_ledger:
            for i, a in enumerate(self.agents):
                for b in self.agents[i+1:]:
                    key = (a, b)
                    agreed = 1.0 if rnd.get(a) == rnd.get(b) else 0.0
                    counts.setdefault(key, []).append(agreed)

        for (a, b), vals in counts.items():
            rate = sum(vals) / len(vals)
            matrix[a][b] = round(rate, 3)
            matrix[b][a] = round(rate, 3)

        return matrix

    @staticmethod
    def _majority(votes: Dict[str, str]) -> str:
        counts: Dict[str, int] = defaultdict(int)
        for v in votes.values():
            counts[v] += 1
        return max(counts, key=counts.get) if counts else "abstain"


# ════════════════════════════════════════════════════════════════════════════════
# AXIS 3 — SEMANTIC INTROSPECTION
# ════════════════════════════════════════════════════════════════════════════════

class SemanticIntrospector:
    """
    Tracks what the swarm is learning at a semantic level:

    1. Strategy Fingerprints — LSH-based hashing of successful
       strategies to detect reuse and novelty.

    2. Capability Boundaries — maps task categories to success
       rates, identifying systematic strengths and weaknesses.

    3. Blind Spots — detects patterns in failed tasks that the
       swarm consistently can't solve.
    """

    # Task category keywords for classification
    CATEGORIES = {
        "debugging": ["fix", "bug", "error", "crash", "debug", "issue"],
        "creation": ["build", "create", "write", "generate", "implement"],
        "optimization": ["optimize", "faster", "improve", "refactor", "speed"],
        "analysis": ["analyze", "explain", "why", "understand", "compare"],
        "security": ["security", "auth", "encrypt", "owasp", "vulnerability"],
        "quantum": ["quantum", "qubit", "circuit", "gate", "fidelity"],
        "research": ["hypothesis", "experiment", "publish", "paper", "data"],
        "architecture": ["design", "architect", "pattern", "structure", "module"],
    }

    def __init__(self):
        self._task_log: List[Dict[str, Any]] = []
        self._strategy_hashes: Dict[str, List[str]] = defaultdict(list)
        self._category_scores: Dict[str, List[float]] = defaultdict(list)
        self._failure_patterns: List[Dict[str, Any]] = []

    def observe_task(self, task: str, final_output: str,
                     quality: float, success: bool):
        """Record a completed task for semantic analysis."""
        category = self._classify_task(task)
        fingerprint = self._fingerprint(final_output)

        self._task_log.append({
            "task_hash": hashlib.md5(task.encode()).hexdigest()[:12],
            "category": category,
            "quality": quality,
            "success": success,
            "fingerprint": fingerprint,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        self._category_scores[category].append(quality)
        self._strategy_hashes[category].append(fingerprint)

        if not success or quality < 0.5:
            self._failure_patterns.append({
                "task_snippet": task[:100],
                "category": category,
                "quality": quality,
                "keywords": self._extract_keywords(task),
            })

    def capability_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a capability boundary map:
        {category: {avg_quality, n_tasks, trend, strength_rating}}
        """
        result = {}
        for cat, scores in self._category_scores.items():
            n = len(scores)
            avg = sum(scores) / n if n else 0
            # Trend: compare first half to second half
            if n >= 4:
                first_half = scores[:n//2]
                second_half = scores[n//2:]
                trend = (sum(second_half) / len(second_half)) - \
                        (sum(first_half) / len(first_half))
            else:
                trend = 0.0

            if avg >= 0.8:
                rating = "strong"
            elif avg >= 0.6:
                rating = "moderate"
            elif avg >= 0.4:
                rating = "developing"
            else:
                rating = "weak"

            result[cat] = {
                "avg_quality": round(avg, 4),
                "n_tasks": n,
                "trend": round(trend, 4),
                "strength_rating": rating,
            }
        return result

    def blind_spots(self, min_failures: int = 2) -> List[Dict[str, Any]]:
        """
        Detect systematic failure patterns.
        Groups failures by category and extracts common keywords.
        """
        category_failures: Dict[str, List[Dict]] = defaultdict(list)
        for fp in self._failure_patterns:
            category_failures[fp["category"]].append(fp)

        spots = []
        for cat, failures in category_failures.items():
            if len(failures) < min_failures:
                continue

            # Find common keywords across failures
            keyword_counts: Dict[str, int] = defaultdict(int)
            for f in failures:
                for kw in f["keywords"]:
                    keyword_counts[kw] += 1

            common_keywords = [
                kw for kw, count in keyword_counts.items()
                if count >= min_failures
            ]

            scores = self._category_scores.get(cat, [])
            avg_quality = sum(scores) / len(scores) if scores else 0

            spots.append({
                "category": cat,
                "n_failures": len(failures),
                "common_keywords": common_keywords[:5],
                "avg_quality": round(avg_quality, 4),
                "recommendation": self._recommend_fix(cat, common_keywords),
            })

        return sorted(spots, key=lambda x: x["n_failures"], reverse=True)

    def strategy_novelty(self) -> Dict[str, float]:
        """
        For each category, measure what fraction of strategies are novel
        (vs. reused from previous tasks). Higher = more creative.
        """
        result = {}
        for cat, hashes in self._strategy_hashes.items():
            if not hashes:
                result[cat] = 1.0
                continue
            unique = len(set(hashes))
            result[cat] = round(unique / len(hashes), 4)
        return result

    def _classify_task(self, task: str) -> str:
        """Classify task into a capability category."""
        text = task.lower()
        scores: Dict[str, int] = {}
        for cat, keywords in self.CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[cat] = score
        if scores:
            return max(scores, key=scores.get)
        return "general"

    @staticmethod
    def _fingerprint(text: str) -> str:
        """
        Locality-sensitive hash of strategy text.
        Uses 4-gram character shingling + min-hash.
        """
        if len(text) < 4:
            return hashlib.md5(text.encode()).hexdigest()[:8]

        # Generate shingles
        shingles = set()
        normalized = text.lower().strip()
        for i in range(len(normalized) - 3):
            shingles.add(normalized[i:i+4])

        if not shingles:
            return hashlib.md5(text.encode()).hexdigest()[:8]

        # Min-hash with 4 hash functions
        min_hashes = []
        for seed in [42, 137, 256, 512]:
            min_val = float('inf')
            for shingle in shingles:
                h = int(hashlib.md5(
                    (shingle + str(seed)).encode()
                ).hexdigest()[:8], 16)
                if h < min_val:
                    min_val = h
            min_hashes.append(min_val)

        combined = hashlib.md5(
            str(min_hashes).encode()
        ).hexdigest()[:8]
        return combined

    @staticmethod
    def _extract_keywords(task: str) -> List[str]:
        """Extract meaningful keywords from a task description."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "up", "about", "into", "through", "during", "before", "after",
            "and", "but", "or", "nor", "not", "so", "yet", "both", "each",
            "this", "that", "these", "those", "it", "its", "my", "your",
        }
        words = task.lower().split()
        return [
            w for w in words
            if len(w) > 2 and w.isalpha() and w not in stop_words
        ]

    @staticmethod
    def _recommend_fix(category: str, keywords: List[str]) -> str:
        """Generate a recommendation for a detected blind spot."""
        recommendations = {
            "debugging": "Increase Critic agent influence; add static analysis layer",
            "security": "Enable OWASP pattern matching in Critic; add security-focused Rebel challenges",
            "optimization": "Feed profiling data to Optimizer; increase Reasoner weight for complexity analysis",
            "quantum": "Verify circuit fidelity with simulator; add Qiskit validation step",
            "research": "Strengthen hypothesis formulation in Reasoner; add p-value thresholds",
            "architecture": "Enable causal graph reinforcement for design patterns; add Rebel structural challenges",
        }
        return recommendations.get(
            category,
            f"Analyze failure patterns in '{category}': {', '.join(keywords[:3])}"
        )


# ════════════════════════════════════════════════════════════════════════════════
# RECURSIVE SELF-IMPROVEMENT LOOP
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class ImprovementAction:
    """A concrete action the swarm can take to improve itself."""
    action_type: str           # "reweight", "retrain", "restructure", "alert"
    target: str                # agent_id or "swarm" or "mesh"
    parameter: str             # what to change
    current_value: float
    recommended_value: float
    rationale: str
    priority: float            # 0-1

    def to_dict(self) -> Dict:
        return asdict(self)


class RecursiveSelfImprover:
    """
    The introspection loop that turns observations into actions.

    Observe → Diagnose → Prescribe → Apply → Verify → Repeat

    This is recursive: the self-improver monitors its own improvement
    actions and adjusts its strategy if improvements aren't working.
    """

    def __init__(self, temporal: TemporalIntrospector,
                 structural: StructuralIntrospector,
                 semantic: SemanticIntrospector):
        self.temporal = temporal
        self.structural = structural
        self.semantic = semantic

        self._actions_taken: List[Dict[str, Any]] = []
        self._improvement_success: List[float] = []
        self._iteration = 0

    def diagnose(self) -> List[ImprovementAction]:
        """
        Analyze all three axes and generate concrete improvement actions.
        """
        self._iteration += 1
        actions = []

        # === TEMPORAL AXIS ===
        # Check for degrading agents
        health = self.temporal.agent_health()
        for agent, metrics in health.items():
            if metrics["stability"] < 0.3 and metrics["observations"] >= 5:
                actions.append(ImprovementAction(
                    action_type="reweight",
                    target=agent,
                    parameter="influence",
                    current_value=metrics["avg_confidence"],
                    recommended_value=max(0.3, metrics["avg_confidence"] - 0.1),
                    rationale=f"Agent '{agent}' is unstable "
                              f"(stability={metrics['stability']:.2f}). "
                              f"Reducing influence until stabilised.",
                    priority=0.8,
                ))

            # Consensus fatigue
            if metrics["consensus_agreement"] > 0.95 and metrics["observations"] >= 10:
                actions.append(ImprovementAction(
                    action_type="alert",
                    target=agent,
                    parameter="consensus_rate",
                    current_value=metrics["consensus_agreement"],
                    recommended_value=0.7,
                    rationale=f"Agent '{agent}' rubber-stamps everything "
                              f"({metrics['consensus_agreement']:.0%} agreement). "
                              f"Consider increasing adversarial weight.",
                    priority=0.6,
                ))

        # Quality forecast
        forecast = self.temporal.quality_forecast(3)
        if forecast and forecast[-1] < 0.5:
            actions.append(ImprovementAction(
                action_type="alert",
                target="swarm",
                parameter="quality_trajectory",
                current_value=forecast[0],
                recommended_value=0.7,
                rationale=f"Quality forecast declining: "
                          f"{' → '.join(f'{f:.2f}' for f in forecast)}. "
                          f"Recommend increasing deliberation rounds.",
                priority=0.9,
            ))

        # === STRUCTURAL AXIS ===
        entropy = self.structural.cognitive_entropy()
        max_entropy = math.log2(3) if math.log2(3) > 0 else 1.0
        normalised_entropy = entropy / max_entropy

        if normalised_entropy < 0.3:
            actions.append(ImprovementAction(
                action_type="restructure",
                target="swarm",
                parameter="cognitive_entropy",
                current_value=normalised_entropy,
                recommended_value=0.6,
                rationale=f"Low cognitive entropy ({normalised_entropy:.2f}). "
                          f"Agents have collapsed into group-think. "
                          f"Recommend boosting Rebel/Satirical influence.",
                priority=0.85,
            ))

        echo = self.structural.echo_chamber_score()
        if echo > 0.8:
            actions.append(ImprovementAction(
                action_type="restructure",
                target="swarm",
                parameter="echo_chamber_score",
                current_value=echo,
                recommended_value=0.5,
                rationale=f"Echo chamber detected (score={echo:.2f}). "
                          f"Agents vote in rigid blocs. "
                          f"Introduce randomised execution order.",
                priority=0.7,
            ))

        # === SEMANTIC AXIS ===
        blind_spots = self.semantic.blind_spots(min_failures=2)
        for spot in blind_spots[:3]:
            actions.append(ImprovementAction(
                action_type="retrain",
                target="swarm",
                parameter=f"blind_spot_{spot['category']}",
                current_value=spot["avg_quality"],
                recommended_value=0.7,
                rationale=f"Blind spot in '{spot['category']}' "
                          f"({spot['n_failures']} failures, "
                          f"avg quality={spot['avg_quality']:.2f}). "
                          f"{spot['recommendation']}",
                priority=0.75,
            ))

        # Novelty check
        novelty = self.semantic.strategy_novelty()
        for cat, nov_score in novelty.items():
            if nov_score < 0.3 and len(self.semantic._strategy_hashes.get(cat, [])) >= 5:
                actions.append(ImprovementAction(
                    action_type="alert",
                    target="swarm",
                    parameter=f"novelty_{cat}",
                    current_value=nov_score,
                    recommended_value=0.5,
                    rationale=f"Strategy stagnation in '{cat}' "
                              f"(novelty={nov_score:.2f}). "
                              f"Swarm is recycling the same approaches. "
                              f"Increase Rebel creativity weight.",
                    priority=0.5,
                ))

        # === META: Check if previous improvements worked ===
        if len(self._improvement_success) >= 3:
            recent = self._improvement_success[-3:]
            avg_success = sum(recent) / len(recent)
            if avg_success < 0.3:
                actions.append(ImprovementAction(
                    action_type="restructure",
                    target="self_improver",
                    parameter="meta_effectiveness",
                    current_value=avg_success,
                    recommended_value=0.7,
                    rationale=f"Self-improvement loop is ineffective "
                              f"(success rate={avg_success:.0%}). "
                              f"The improver needs to change its own strategy. "
                              f"Consider broader structural changes.",
                    priority=1.0,
                ))

        # Sort by priority
        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions

    def apply(self, action: ImprovementAction,
              mesh=None) -> bool:
        """
        Apply an improvement action to the swarm or mesh.
        Returns True if the action was successfully applied.
        """
        success = False

        if action.action_type == "reweight" and mesh is not None:
            # Adjust trust in the cognitive mesh
            if hasattr(mesh, 'trust_net') and action.target in mesh.trust_net.trust:
                # Reduce trust from all agents toward the target
                for other in mesh.trust_net.agents:
                    if other != action.target:
                        bt = mesh.trust_net.trust[other].get(action.target)
                        if bt:
                            bt.beta_param += 1.0  # increase failures → lower trust
                success = True

        elif action.action_type == "restructure" and mesh is not None:
            # Boost rebel/satirical influence
            if "entropy" in action.parameter or "echo" in action.parameter:
                for rebel_id in ["rebel", "satirical"]:
                    if hasattr(mesh, 'trust_net'):
                        for other in mesh.trust_net.agents:
                            bt = mesh.trust_net.trust.get(other, {}).get(rebel_id)
                            if bt:
                                bt.alpha += 0.5
                success = True

        elif action.action_type == "alert":
            # Alerts are informational — always succeed
            success = True

        elif action.action_type == "retrain":
            # Record for future adjustment
            success = True

        self._actions_taken.append({
            "iteration": self._iteration,
            "action": action.to_dict(),
            "applied": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return success

    def verify(self, pre_quality: float, post_quality: float):
        """
        Verify if the most recent improvement worked.
        """
        delta = post_quality - pre_quality
        self._improvement_success.append(
            1.0 if delta > 0.01 else (0.5 if abs(delta) < 0.01 else 0.0)
        )

    def improvement_report(self) -> Dict[str, Any]:
        """Full diagnostic report."""
        return {
            "iteration": self._iteration,
            "total_actions": len(self._actions_taken),
            "success_rate": (
                sum(self._improvement_success) / len(self._improvement_success)
                if self._improvement_success else 0.0
            ),
            "temporal_health": self.temporal.agent_health(),
            "cognitive_entropy": round(self.structural.cognitive_entropy(), 4),
            "echo_chamber_score": round(self.structural.echo_chamber_score(), 4),
            "contrarian_value": self.structural.contrarian_value(),
            "capability_map": self.semantic.capability_map(),
            "blind_spots": self.semantic.blind_spots(),
            "strategy_novelty": self.semantic.strategy_novelty(),
            "quality_forecast": self.temporal.quality_forecast(5),
            "recent_alerts": [a.to_dict() for a in self.temporal.recent_alerts(5)],
        }


# ════════════════════════════════════════════════════════════════════════════════
# UNIFIED INTROSPECTION ENGINE
# ════════════════════════════════════════════════════════════════════════════════

class IntrospectionEngine:
    """
    Unified entry point for the tridirectional introspection system.

    Composes temporal, structural, and semantic analyzers with
    the recursive self-improvement loop.

    Designed to be plugged into NCLLMSwarm.solve() as a post-round hook.
    """

    def __init__(self, agent_ids: List[str] = None):
        if agent_ids is None:
            agent_ids = [
                "orchestrator", "reasoner", "coder", "critic",
                "optimizer", "self_reflector", "rebel", "empath", "satirical"
            ]
        self.agent_ids = agent_ids

        self.temporal = TemporalIntrospector(agent_ids)
        self.structural = StructuralIntrospector(agent_ids)
        self.semantic = SemanticIntrospector()
        self.improver = RecursiveSelfImprover(
            self.temporal, self.structural, self.semantic
        )

        self._round_count = 0
        self._task_count = 0

    def observe_round(self, responses: List[Dict[str, Any]],
                      consensus: str, quality: float):
        """
        Feed swarm round data into all three axes simultaneously.
        """
        self._round_count += 1

        # Temporal: per-agent performance tracking
        self.temporal.observe_round(responses, consensus, quality)

        # Structural: voting patterns & entropy
        votes = {r["agent"]: r.get("vote", "abstain") for r in responses}
        self.structural.observe_round(votes, consensus, quality)

    def observe_task(self, task: str, final_output: str,
                     quality: float, success: bool = True):
        """
        Feed completed task into semantic analyzer.
        """
        self._task_count += 1
        self.semantic.observe_task(task, final_output, quality,
                                  success=(quality >= 0.6))

    def run_improvement_cycle(self, mesh=None) -> List[ImprovementAction]:
        """
        Run one cycle of diagnose → apply → (verify later).
        Returns the list of actions taken.
        """
        actions = self.improver.diagnose()
        for action in actions[:5]:  # apply top-5 priority actions
            self.improver.apply(action, mesh=mesh)
        return actions

    def full_report(self) -> Dict[str, Any]:
        """Complete introspection report across all three axes."""
        return {
            "rounds_observed": self._round_count,
            "tasks_observed": self._task_count,
            "improvement_report": self.improver.improvement_report(),
            "voting_patterns": self.structural.voting_pattern_matrix(),
        }

    def print_dashboard(self):
        """Pretty-print introspection dashboard."""
        report = self.improver.improvement_report()

        print("\n" + "═" * 72)
        print("  OSIRIS INTROSPECTION ENGINE — Tridirectional Self-Awareness")
        print("═" * 72)
        print(f"  Rounds: {self._round_count}  |  Tasks: {self._task_count}  |  "
              f"Improvement iterations: {report['iteration']}")

        # Temporal
        print("\n  ── Axis 1: Temporal Health ──")
        for agent, health in report["temporal_health"].items():
            if health["observations"] == 0:
                continue
            conf = health["avg_confidence"]
            stab = health["stability"]
            cons = health["consensus_agreement"]
            bar = "█" * int(stab * 20) + "░" * (20 - int(stab * 20))
            print(f"    {agent:18s} conf={conf:.2f} stab=[{bar}] "
                  f"agree={cons:.0%}")

        forecast = report["quality_forecast"]
        if forecast:
            trend = "↑" if forecast[-1] > forecast[0] else "↓" if forecast[-1] < forecast[0] else "→"
            print(f"  Quality forecast: {' → '.join(f'{f:.2f}' for f in forecast)} {trend}")

        # Structural
        print(f"\n  ── Axis 2: Structural Dynamics ──")
        entropy = report["cognitive_entropy"]
        max_e = math.log2(3) if math.log2(3) > 0 else 1.0
        print(f"    Cognitive entropy:  {entropy:.3f} / {max_e:.3f} "
              f"({'healthy' if entropy > 0.8 else 'low diversity' if entropy < 0.5 else 'moderate'})")
        print(f"    Echo chamber score: {report['echo_chamber_score']:.3f} "
              f"({'severe' if report['echo_chamber_score'] > 0.8 else 'mild' if report['echo_chamber_score'] > 0.6 else 'healthy'})")

        cv = report["contrarian_value"]
        if cv:
            print(f"    Contrarian value:")
            for agent, val in cv.items():
                sign = "+" if val >= 0 else ""
                print(f"      {agent:18s}  {sign}{val:.4f}")

        # Semantic
        print(f"\n  ── Axis 3: Semantic Learning ──")
        cm = report["capability_map"]
        if cm:
            for cat, info in cm.items():
                n = info["n_tasks"]
                avg = info["avg_quality"]
                rating = info["strength_rating"]
                trend = info["trend"]
                trend_arrow = "↑" if trend > 0.02 else "↓" if trend < -0.02 else "→"
                print(f"    {cat:18s} q={avg:.2f} ({rating:>10s}) "
                      f"n={n:3d} {trend_arrow}")

        spots = report["blind_spots"]
        if spots:
            print(f"\n  ⚠ Blind Spots:")
            for spot in spots[:3]:
                print(f"    • {spot['category']}: {spot['n_failures']} failures "
                      f"({spot['recommendation']})")

        novelty = report["strategy_novelty"]
        if novelty:
            stale = [
                (cat, n) for cat, n in novelty.items() if n < 0.4
            ]
            if stale:
                print(f"\n  ⚠ Strategy Stagnation:")
                for cat, n in stale:
                    print(f"    • {cat}: {n:.0%} novelty")

        # Alerts
        alerts = report["recent_alerts"]
        if alerts:
            print(f"\n  ── Recent Alerts ──")
            for alert in alerts[-5:]:
                sev = "🔴" if alert["severity"] > 0.7 else "🟡" if alert["severity"] > 0.4 else "🟢"
                print(f"    {sev} [{alert['agent_id']}] {alert['context']}")

        print("═" * 72)
