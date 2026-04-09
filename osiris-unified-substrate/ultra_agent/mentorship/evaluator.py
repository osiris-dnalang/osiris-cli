"""Evaluator — measures improvement honestly with full accounting.

Computes quality deltas between initial and improved solutions,
tracks whether improvement is real or noise, and flags when the
system is in simulation mode so results cannot be over-claimed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..critic import Critic, CritiqueReport


@dataclass
class EvaluationResult:
    """Honest evaluation of a single improvement step."""
    task: str
    initial_score: float
    improved_score: float
    improvement: float
    is_real_improvement: bool      # delta > threshold
    evaluation_mode: str           # "simulation" | "model"
    axis_deltas: Dict[str, float]
    verdict: str                   # "improved" | "stagnant" | "regressed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "initial_score": round(self.initial_score, 4),
            "improved_score": round(self.improved_score, 4),
            "improvement": round(self.improvement, 4),
            "is_real_improvement": self.is_real_improvement,
            "evaluation_mode": self.evaluation_mode,
            "axis_deltas": {
                k: round(v, 4) for k, v in self.axis_deltas.items()
            },
            "verdict": self.verdict,
        }


class ImprovementEvaluator:
    """Measures quality deltas between solution versions.

    Uses a configurable significance threshold to distinguish
    genuine improvement from noise.  All results are tagged
    with evaluation_mode.
    """

    def __init__(
        self,
        significance_threshold: float = 0.02,
        simulation_mode: bool = True,
    ) -> None:
        self._critic = Critic()
        self._threshold = significance_threshold
        self._simulation_mode = simulation_mode
        self._history: List[EvaluationResult] = []

    def evaluate(
        self,
        task: str,
        initial_solution: str,
        improved_solution: str,
    ) -> EvaluationResult:
        """Compare two solutions and produce an honest evaluation."""
        crit_initial = self._critic.review(task, initial_solution)
        crit_improved = self._critic.review(task, improved_solution)

        delta = crit_improved.overall_score - crit_initial.overall_score

        # Per-axis deltas
        axis_deltas: Dict[str, float] = {}
        all_axes = set(crit_initial.axis_scores) | set(crit_improved.axis_scores)
        for axis in all_axes:
            old = crit_initial.axis_scores.get(axis, 0.0)
            new = crit_improved.axis_scores.get(axis, 0.0)
            axis_deltas[axis] = new - old

        is_real = delta > self._threshold

        if delta > self._threshold:
            verdict = "improved"
        elif delta < -self._threshold:
            verdict = "regressed"
        else:
            verdict = "stagnant"

        result = EvaluationResult(
            task=task,
            initial_score=crit_initial.overall_score,
            improved_score=crit_improved.overall_score,
            improvement=delta,
            is_real_improvement=is_real,
            evaluation_mode="simulation" if self._simulation_mode else "model",
            axis_deltas=axis_deltas,
            verdict=verdict,
        )
        self._history.append(result)
        return result

    def aggregate(self, window: int = 0) -> Dict[str, Any]:
        """Aggregate evaluation results.

        Parameters
        ----------
        window : int
            Number of recent evaluations. 0 = all.
        """
        entries = self._history[-window:] if window else self._history
        if not entries:
            return {"status": "no_data"}

        improvements = [e.improvement for e in entries]
        real_count = sum(1 for e in entries if e.is_real_improvement)
        regressed = sum(1 for e in entries if e.verdict == "regressed")

        return {
            "total_evaluations": len(entries),
            "real_improvements": real_count,
            "real_improvement_rate": round(real_count / len(entries), 3),
            "regressions": regressed,
            "avg_improvement": round(sum(improvements) / len(improvements), 4),
            "max_improvement": round(max(improvements), 4),
            "min_improvement": round(min(improvements), 4),
            "evaluation_mode": "simulation" if self._simulation_mode else "model",
        }
