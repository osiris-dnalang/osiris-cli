"""Distillation Engine — the core mentor→protégé knowledge transfer loop.

Runs the full cycle:
  1. Protégé attempts task
  2. Mentor critiques
  3. Protégé improves
  4. Evaluator measures improvement
  5. Training record is stored
  6. If no improvement → mentor evolves its teaching strategy

This is the beating heart of the self-improving system.
Every record is tagged with mode (simulation/model) and includes
full token/latency accounting for scientific defensibility.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..model_interface import ModelInterface, get_model_interface
from .mentor_swarm import MentorSwarm
from .protege_swarm import ProtegeSwarm
from .evaluator import ImprovementEvaluator


@dataclass
class DistillationRecord:
    """Single distillation step — the training signal."""
    task: str
    initial_solution: str
    initial_quality: float
    critique: Dict[str, Any]
    improved_solution: str
    improved_quality: float
    improvement_score: float
    strategy: str
    failure_modes: List[str]
    teaching_points: List[str]
    reusable_patterns: List[str]
    iteration: int
    mode: str                   # "simulation" | "model"
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "initial_solution": self.initial_solution,
            "initial_quality": round(self.initial_quality, 4),
            "critique": self.critique,
            "improved_solution": self.improved_solution,
            "improved_quality": round(self.improved_quality, 4),
            "improvement_score": round(self.improvement_score, 4),
            "strategy": self.strategy,
            "failure_modes": self.failure_modes,
            "teaching_points": self.teaching_points,
            "reusable_patterns": self.reusable_patterns,
            "iteration": self.iteration,
            "mode": self.mode,
            "latency_ms": round(self.latency_ms, 2),
        }


# ---- Curriculum: task generators ----

_CURRICULUM: Dict[str, List[str]] = {
    "code": [
        "Write a function to reverse a linked list in Python",
        "Implement a LRU cache with O(1) get and put",
        "Write a function to detect cycles in a directed graph",
        "Implement merge sort with O(n log n) guarantee",
        "Write a thread-safe producer-consumer queue",
    ],
    "math": [
        "Solve: find all x where x^3 - 6x^2 + 11x - 6 = 0",
        "Prove that the sum of first n odd numbers equals n^2",
        "Calculate the eigenvalues of [[4,1],[2,3]]",
        "Find the integral of e^(-x^2) from 0 to infinity",
        "Derive the formula for the nth Fibonacci number",
    ],
    "reasoning": [
        "Explain why gradient descent converges for convex functions",
        "Compare depth-first and breadth-first search trade-offs",
        "Analyse the time-space trade-off in hash tables vs trees",
        "Explain the CAP theorem and its practical implications",
        "Why does dropout prevent overfitting in neural networks?",
    ],
    "adversarial": [
        "Write a function that appears correct but has a subtle off-by-one error, then fix it",
        "Implement binary search, deliberately introduce a bug, identify and correct it",
        "Write code that handles the empty-input edge case that most implementations miss",
        "Solve FizzBuzz in a way that is both efficient and extensible to arbitrary rules",
        "Implement a function with 3 different approaches and argue which is best",
    ],
}


def _generate_tasks(
    domains: Optional[List[str]] = None,
    count: int = 5,
    difficulty_level: int = 1,
) -> List[str]:
    """Generate curriculum tasks at the given difficulty level."""
    domains = domains or list(_CURRICULUM.keys())
    tasks: List[str] = []
    for domain in domains:
        pool = _CURRICULUM.get(domain, _CURRICULUM["code"])
        # Rotate based on difficulty
        start = min(difficulty_level - 1, len(pool) - 1)
        for task in pool[start : start + count]:
            tasks.append(task)
    return tasks[:count] if count else tasks


def _generate_self_play_tasks(
    protege_swarm: "ProtegeSwarm",
    count: int = 3,
) -> List[str]:
    """Generate adversarial self-play tasks.

    The protégé generates problems designed to challenge itself,
    mirroring the AlphaZero self-play paradigm.
    """
    meta_prompts = [
        "Create a coding problem that would expose off-by-one errors",
        "Design a math problem that requires careful edge-case analysis",
        "Write a reasoning question that exposes confirmation bias",
        "Create a problem that seems simple but has a subtle correctness trap",
        "Design a task where the naive O(n^2) solution is tempting but O(n) exists",
    ]
    tasks: List[str] = []
    for prompt in meta_prompts[:count]:
        result = protege_swarm.attempt(prompt)
        # Use the protégé's output as the new task
        generated_task = result.solution.strip()
        if generated_task and len(generated_task) > 20:
            tasks.append(generated_task[:500])
        else:
            tasks.append(prompt)
    return tasks


class DistillationEngine:
    """Orchestrates the full mentor→protégé distillation loop.

    Parameters
    ----------
    output_path : str
        JSONL file for distillation records (training data).
    model_interface : ModelInterface, optional
        Shared model interface. Defaults to global singleton.
    """

    def __init__(
        self,
        output_path: str = "artifacts/distillation_records.jsonl",
        model_interface: Optional[ModelInterface] = None,
    ) -> None:
        self.model = model_interface or get_model_interface()
        self.mentor = MentorSwarm(model_interface=self.model)
        self.protege = ProtegeSwarm(model_interface=self.model)
        self.evaluator = ImprovementEvaluator(
            simulation_mode=self.model.simulation_mode,
        )
        self._output = Path(output_path)
        self._output.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[DistillationRecord] = []

    def distill_step(self, task: str, iteration: int = 1) -> DistillationRecord:
        """Single distillation step for one task."""
        t0 = time.perf_counter()

        # 1. Protégé attempts independently
        initial = self.protege.attempt(task)

        # 2. Mentor critiques + teaches
        teaching = self.mentor.teach(task, initial.solution)

        # 3. Build feedback string from teaching
        feedback_parts = teaching.teaching_points[:3]
        if teaching.failure_modes and teaching.failure_modes[0] != "No critical failure modes detected":
            feedback_parts.extend(teaching.failure_modes[:2])
        feedback = " | ".join(feedback_parts)

        # 4. Protégé improves
        improved = self.protege.improve(task, feedback)

        # 5. Record learning
        self.protege.learn_from_teaching(
            task, initial, improved, feedback, iteration)

        # 6. Evaluate improvement
        eval_result = self.evaluator.evaluate(
            task, initial.solution, improved.solution)

        latency = (time.perf_counter() - t0) * 1000

        record = DistillationRecord(
            task=task,
            initial_solution=initial.solution,
            initial_quality=eval_result.initial_score,
            critique=teaching.critique_of_protege,
            improved_solution=improved.solution,
            improved_quality=eval_result.improved_score,
            improvement_score=eval_result.improvement,
            strategy=teaching.strategy,
            failure_modes=teaching.failure_modes,
            teaching_points=teaching.teaching_points,
            reusable_patterns=teaching.reusable_patterns,
            iteration=iteration,
            mode="simulation" if self.model.simulation_mode else "model",
            latency_ms=latency,
        )
        self._records.append(record)
        self._persist(record)
        return record

    def run(
        self,
        iterations: int = 10,
        domains: Optional[List[str]] = None,
        tasks_per_iteration: int = 3,
    ) -> Dict[str, Any]:
        """Full distillation loop with curriculum and mentor evolution.

        Parameters
        ----------
        iterations : int
            Number of distillation epochs.
        domains : list of str, optional
            Domains to train on. Defaults to all.
        tasks_per_iteration : int
            Tasks per epoch.
        """
        t0 = time.perf_counter()
        all_records: List[DistillationRecord] = []
        stagnation_count = 0

        for epoch in range(1, iterations + 1):
            # Generate curriculum tasks (difficulty increases with epoch)
            tasks = _generate_tasks(
                domains=domains,
                count=tasks_per_iteration,
                difficulty_level=min(epoch, 5),
            )

            # Every 3rd epoch, add self-play adversarial tasks
            if epoch % 3 == 0:
                try:
                    self_play = _generate_self_play_tasks(
                        self.protege, count=max(1, tasks_per_iteration // 2))
                    tasks.extend(self_play)
                except Exception:
                    pass  # self-play is best-effort

            epoch_improvements: List[float] = []

            for task in tasks:
                record = self.distill_step(task, iteration=epoch)
                all_records.append(record)
                epoch_improvements.append(record.improvement_score)

            # Check if protégé is improving
            avg_improvement = (
                sum(epoch_improvements) / len(epoch_improvements)
                if epoch_improvements else 0
            )

            if avg_improvement <= 0:
                stagnation_count += 1
            else:
                stagnation_count = 0

            # If stagnating, mentor evolves its teaching strategy
            if stagnation_count >= 2:
                evolution = self.mentor.evolve_strategy()
                stagnation_count = 0  # reset after adaptation

        total_latency = (time.perf_counter() - t0) * 1000

        # Compute RLHF-compatible reward signal
        rewards = self._compute_rewards(all_records)

        # Auto-generate preference pairs for PPO
        pref_stats: Dict[str, Any] = {}
        try:
            from .preference_pipeline import distillation_to_preferences
            pref_stats = distillation_to_preferences(
                records_path=str(self._output),
                output_path=str(self._output.parent / "preference_pairs.jsonl"),
            )
        except Exception:
            pref_stats = {"status": "skipped"}

        return {
            "epochs": iterations,
            "total_records": len(all_records),
            "output_path": str(self._output),
            "mode": "simulation" if self.model.simulation_mode else "model",
            "protege_stats": self.protege.stats(),
            "evaluator_stats": self.evaluator.aggregate(),
            "mentor_evolution": self.mentor.evolve_strategy(),
            "rewards_summary": rewards,
            "preference_pairs": pref_stats,
            "total_latency_ms": round(total_latency, 2),
        }

    def _compute_rewards(
        self, records: List[DistillationRecord]
    ) -> Dict[str, Any]:
        """Compute RLHF-compatible rewards from distillation records.

        reward = quality(improved) - quality(initial)

        These can be fed into PPO as:
          - positive reward → reinforce improved solution
          - negative reward → reduce weight of initial approach
          - zero reward → filter out (no training signal)
        """
        if not records:
            return {"status": "no_data"}

        rewards = [r.improvement_score for r in records]
        positive = [r for r in rewards if r > 0]
        negative = [r for r in rewards if r < 0]

        return {
            "total_samples": len(rewards),
            "positive_rewards": len(positive),
            "negative_rewards": len(negative),
            "zero_rewards": len(rewards) - len(positive) - len(negative),
            "avg_reward": round(sum(rewards) / len(rewards), 4),
            "max_reward": round(max(rewards), 4),
            "min_reward": round(min(rewards), 4),
            "usable_for_ppo": len(positive),
            "usable_for_filtering": len([r for r in rewards if abs(r) > 0.02]),
        }

    def _persist(self, record: DistillationRecord) -> None:
        """Append a record to the JSONL output file."""
        with self._output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
