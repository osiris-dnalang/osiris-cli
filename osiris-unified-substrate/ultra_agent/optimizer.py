"""Optimizer agent — transforms critique into concrete improvements.

Analyses feedback patterns, applies known optimisation strategies,
and produces actionable improvement directives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class OptimizationResult:
    """Output of the optimizer agent."""
    original_score: float
    target_score: float
    actions_taken: List[str]
    efficiency_gains: List[str]
    quality_improvements: List[str]
    meta_insights: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_score": self.original_score,
            "target_score": self.target_score,
            "actions_taken": self.actions_taken,
            "efficiency_gains": self.efficiency_gains,
            "quality_improvements": self.quality_improvements,
            "meta_insights": self.meta_insights,
        }


# Optimisation strategy catalogue
_STRATEGIES: Dict[str, List[str]] = {
    "correctness": [
        "Apply formal verification techniques",
        "Add invariant assertions at loop boundaries",
        "Cross-check with mathematical proof or known results",
    ],
    "completeness": [
        "Map each task requirement to a specific output",
        "Add output validation for all subtasks",
        "Enumerate and cover all input edge cases",
    ],
    "efficiency": [
        "Replace O(n²) operations with hash-based O(n) alternatives",
        "Use generator expressions instead of list comprehensions for large data",
        "Apply memoisation to recursive calls",
        "Eliminate redundant computations with caching",
    ],
    "readability": [
        "Extract magic numbers into named constants",
        "Group related logic into well-named helper functions",
        "Add type annotations to all public interfaces",
    ],
    "robustness": [
        "Wrap external calls in try/except with specific exceptions",
        "Add input validation at function entry points",
        "Implement graceful degradation for partial failures",
    ],
}


class Optimizer:
    """Converts critique feedback into actionable improvement plans."""

    def optimize(self, critique: Dict[str, Any],
                 iteration: int = 1) -> OptimizationResult:
        """Produce an optimisation result from a critique report."""
        axis_scores = critique.get("axis_scores", {})
        weaknesses = critique.get("weaknesses", [])
        overall = critique.get("overall_score", 0.5)

        actions: List[str] = []
        efficiency_gains: List[str] = []
        quality_improvements: List[str] = []
        meta_insights: List[str] = []

        # Target weak axes
        for axis, score in axis_scores.items():
            if score < 0.6:
                strategies = _STRATEGIES.get(axis, [])
                for s in strategies[:2]:
                    actions.append(f"[{axis}] {s}")

                if axis == "efficiency":
                    efficiency_gains.append(
                        f"Improve {axis} from {score:.2f} → target 0.80+")
                else:
                    quality_improvements.append(
                        f"Improve {axis} from {score:.2f} → target 0.80+")

        # Meta-level insights
        if iteration > 1:
            meta_insights.append(
                f"Iteration {iteration}: Focus on highest-delta improvements first")
        if overall < 0.5:
            meta_insights.append(
                "Overall quality is low — consider fundamental redesign")
        elif overall < 0.7:
            meta_insights.append(
                "Quality is moderate — targeted fixes can reach production readiness")
        else:
            meta_insights.append(
                "Quality is high — diminishing returns on further optimisation")

        # Cross-axis synergies
        if axis_scores.get("correctness", 1) < 0.6 and axis_scores.get("robustness", 1) < 0.6:
            meta_insights.append(
                "Correctness AND robustness are both weak — add comprehensive "
                "input validation which improves both simultaneously")

        if axis_scores.get("readability", 1) < 0.6 and axis_scores.get("completeness", 1) < 0.6:
            meta_insights.append(
                "Poor readability may be masking incomplete logic — "
                "refactor first, then re-evaluate completeness")

        # Compute target
        target = min(0.98, overall + 0.15 * (1.0 - overall))

        if not actions:
            actions.append("No critical weaknesses — maintain current quality")

        return OptimizationResult(
            original_score=overall,
            target_score=round(target, 3),
            actions_taken=actions,
            efficiency_gains=efficiency_gains,
            quality_improvements=quality_improvements,
            meta_insights=meta_insights,
        )
