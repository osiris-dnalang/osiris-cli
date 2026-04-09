"""Mentor Swarm — expert-level agent ensemble that teaches the protégé.

The mentor wraps the existing AgentSwarm but focuses on:
  1. Generating *optimal* solutions as reference
  2. Producing detailed strategy decompositions
  3. Critiquing protégé solutions with actionable feedback
  4. Evolving its own teaching strategies over time
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..swarm import AgentSwarm
from ..critic import Critic, CritiqueReport
from ..reasoner import Reasoner, ReasoningTrace
from ..model_interface import ModelInterface, get_model_interface


@dataclass
class TeachingRecord:
    """A single mentoring interaction."""
    task: str
    strategy: str
    reference_solution: str
    critique_of_protege: Dict[str, Any]
    teaching_points: List[str]
    failure_modes: List[str]
    reusable_patterns: List[str]
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "strategy": self.strategy,
            "reference_solution": self.reference_solution,
            "critique_of_protege": self.critique_of_protege,
            "teaching_points": self.teaching_points,
            "failure_modes": self.failure_modes,
            "reusable_patterns": self.reusable_patterns,
            "latency_ms": round(self.latency_ms, 2),
        }


class MentorSwarm:
    """Expert swarm that solves tasks optimally and teaches the protégé.

    Uses the full AgentSwarm pipeline internally with higher quality
    thresholds and more refinement loops.
    """

    def __init__(
        self,
        model_interface: Optional[ModelInterface] = None,
        quality_threshold: float = 0.85,
        max_loops: int = 5,
    ) -> None:
        self.model = model_interface or get_model_interface()
        self._swarm = AgentSwarm(
            memory_path="artifacts/mentor_memory.jsonl",
            max_refinement_loops=max_loops,
            quality_threshold=quality_threshold,
            model_interface=self.model,
        )
        self._reasoner = Reasoner()
        self._critic = Critic()
        self._teaching_history: List[TeachingRecord] = []

    def generate_reference(self, task: str) -> Dict[str, Any]:
        """Produce the mentor's own optimal solution."""
        result = self._swarm.run(task)
        return result.to_dict()

    def generate_strategy(self, task: str) -> Dict[str, Any]:
        """Produce a strategy decomposition for the task."""
        trace = self._reasoner.run(task)
        return trace.to_dict()

    def critique(self, task: str, protege_solution: str) -> CritiqueReport:
        """Critique a protégé solution."""
        return self._critic.review(task, protege_solution)

    def teach(self, task: str, protege_solution: str) -> TeachingRecord:
        """Full teaching cycle: reference + critique + pedagogical output."""
        t0 = time.perf_counter()

        # 1. Generate mentor's own reference solution
        ref = self.generate_reference(task)

        # 2. Critique the protégé
        crit = self.critique(task, protege_solution)

        # 3. Generate strategy decomposition
        strategy = self.generate_strategy(task)

        # 4. Extract teaching points from critique
        teaching_points = self._extract_teaching_points(crit, ref)

        # 5. Identify failure modes
        failure_modes = self._identify_failure_modes(
            protege_solution, crit)

        # 6. Extract reusable patterns
        reusable = self._extract_reusable_patterns(
            task, ref.get("solution", ""))

        latency = (time.perf_counter() - t0) * 1000

        record = TeachingRecord(
            task=task,
            strategy=strategy.get("conclusion", ""),
            reference_solution=ref.get("solution", ""),
            critique_of_protege=crit.to_dict(),
            teaching_points=teaching_points,
            failure_modes=failure_modes,
            reusable_patterns=reusable,
            latency_ms=latency,
        )
        self._teaching_history.append(record)
        return record

    def evolve_strategy(self) -> Dict[str, Any]:
        """Analyse teaching history and refine mentoring approach.

        This is the mentor's own self-improvement: if the protégé
        isn't improving, the mentor must change how it teaches.
        """
        if not self._teaching_history:
            return {"status": "no_history", "adjustments": []}

        # Analyse recent critique scores
        recent = self._teaching_history[-10:]
        scores = [
            r.critique_of_protege.get("overall_score", 0.5)
            for r in recent
        ]
        avg = sum(scores) / len(scores) if scores else 0.5

        adjustments: List[str] = []
        if avg < 0.5:
            adjustments.append(
                "Protégé performance low — switch to step-by-step "
                "scaffolded teaching with explicit sub-problem solutions")
        elif avg < 0.7:
            adjustments.append(
                "Moderate performance — focus critique on highest-delta "
                "axes; provide worked examples for weak areas")
        else:
            adjustments.append(
                "Good performance — shift to adversarial challenges "
                "and edge-case teaching")

        # Check for stagnation
        if len(scores) >= 4:
            first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            if second_half <= first_half:
                adjustments.append(
                    "No improvement trend detected — fundamentally "
                    "change teaching method (e.g. switch from critique "
                    "to collaborative problem-solving)")

        return {
            "status": "evolved",
            "average_protege_score": round(avg, 3),
            "teaching_iterations": len(self._teaching_history),
            "adjustments": adjustments,
        }

    # ---- internal helpers ----

    def _extract_teaching_points(
        self, critique: CritiqueReport, reference: Dict[str, Any]
    ) -> List[str]:
        points = []
        for w in critique.weaknesses:
            points.append(f"Address weakness: {w}")
        for s in critique.suggestions[:3]:
            points.append(f"Apply improvement: {s}")
        if reference.get("solution"):
            points.append(
                "Study the reference solution for structural patterns")
        return points

    def _identify_failure_modes(
        self, solution: str, critique: CritiqueReport
    ) -> List[str]:
        modes = []
        if critique.axis_scores.get("correctness", 1) < 0.5:
            modes.append("Logical correctness failure")
        if critique.axis_scores.get("robustness", 1) < 0.5:
            modes.append("Missing edge-case handling")
        if critique.axis_scores.get("efficiency", 1) < 0.5:
            modes.append("Suboptimal algorithmic complexity")
        if not solution.strip():
            modes.append("Empty solution — fundamental comprehension gap")
        return modes or ["No critical failure modes detected"]

    def _extract_reusable_patterns(
        self, task: str, solution: str
    ) -> List[str]:
        patterns = []
        lowered = task.lower()
        if "sort" in lowered:
            patterns.append("divide-and-conquer")
        if "search" in lowered:
            patterns.append("binary-search")
        if "graph" in lowered or "path" in lowered:
            patterns.append("graph-traversal")
        if "dynamic" in lowered or "optimal" in lowered:
            patterns.append("dynamic-programming")
        if "return" in solution:
            patterns.append("function-decomposition")
        if "try" in solution and "except" in solution:
            patterns.append("defensive-programming")
        return patterns or ["general-problem-solving"]
