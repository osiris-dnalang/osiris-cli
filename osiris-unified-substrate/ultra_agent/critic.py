"""Critic agent — evaluates output quality and produces actionable feedback.

Scores solutions on multiple axes, identifies specific weaknesses,
and generates concrete improvement directives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CritiqueReport:
    """Structured critique of a solution."""
    overall_score: float  # 0.0–1.0
    axis_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    verdict: str  # "pass", "needs-work", "reject"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "axis_scores": self.axis_scores,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
            "verdict": self.verdict,
        }


# Quality axes and their checkers
_QUALITY_AXES = [
    "correctness",
    "completeness",
    "efficiency",
    "readability",
    "robustness",
]


class Critic:
    """Evaluates solutions and produces actionable critiques."""

    def review(self, task: str, solution: str,
               reasoning: Optional[Dict[str, Any]] = None) -> CritiqueReport:
        """Produce a critique report for the given solution."""
        axis_scores = {}
        strengths: List[str] = []
        weaknesses: List[str] = []
        suggestions: List[str] = []

        # Score each axis
        axis_scores["correctness"] = self._check_correctness(task, solution)
        axis_scores["completeness"] = self._check_completeness(task, solution)
        axis_scores["efficiency"] = self._check_efficiency(solution)
        axis_scores["readability"] = self._check_readability(solution)
        axis_scores["robustness"] = self._check_robustness(solution)

        # Identify strengths and weaknesses
        for axis, score in axis_scores.items():
            if score >= 0.8:
                strengths.append(f"Strong {axis} ({score:.2f})")
            elif score < 0.5:
                weaknesses.append(f"Weak {axis} ({score:.2f})")
                suggestions.extend(self._suggest_fix(axis, solution))

        # Check reasoning quality if available
        if reasoning:
            r_score = self._check_reasoning(reasoning)
            axis_scores["reasoning_quality"] = r_score
            if r_score >= 0.8:
                strengths.append(f"Well-reasoned approach ({r_score:.2f})")
            elif r_score < 0.5:
                weaknesses.append("Reasoning lacks depth or structure")
                suggestions.append("Add explicit chain-of-thought steps")

        # Compute overall
        overall = sum(axis_scores.values()) / len(axis_scores)

        # Verdict
        if overall >= 0.8:
            verdict = "pass"
        elif overall >= 0.5:
            verdict = "needs-work"
        else:
            verdict = "reject"

        return CritiqueReport(
            overall_score=round(overall, 3),
            axis_scores={k: round(v, 3) for k, v in axis_scores.items()},
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            verdict=verdict,
        )

    # -- axis checkers --

    def _check_correctness(self, task: str, solution: str) -> float:
        """Heuristic correctness check."""
        score = 0.5  # base
        # Penalise empty / stub solutions
        if not solution.strip():
            return 0.0
        if "raise NotImplementedError" in solution:
            return 0.2
        if "TODO" in solution:
            score -= 0.1

        # Reward actual implementation signals
        if "return " in solution:
            score += 0.2
        if "def " in solution:
            score += 0.1
        if "assert " in solution:
            score += 0.1

        # Check alignment between task keywords and solution
        task_words = set(task.lower().split())
        sol_words = set(solution.lower().split())
        overlap = len(task_words & sol_words)
        score += min(0.15, overlap * 0.02)

        return min(1.0, max(0.0, score))

    def _check_completeness(self, task: str, solution: str) -> float:
        """Check if solution addresses the full task."""
        score = 0.5
        # Count sub-tasks (clauses with 'and'/'then')
        subtasks = re.split(r'\band\b|\bthen\b', task, flags=re.IGNORECASE)
        addressed = 0
        for st in subtasks:
            key_words = [w for w in st.lower().split() if len(w) > 3]
            if any(kw in solution.lower() for kw in key_words[:3]):
                addressed += 1
        if subtasks:
            score = 0.3 + 0.7 * (addressed / len(subtasks))
        return min(1.0, score)

    def _check_efficiency(self, solution: str) -> float:
        """Heuristic efficiency check for code solutions."""
        score = 0.7
        # Nested loops = potential inefficiency
        indent_levels = [len(line) - len(line.lstrip())
                         for line in solution.split("\n") if line.strip()]
        max_indent = max(indent_levels) if indent_levels else 0
        if max_indent > 16:  # deeply nested
            score -= 0.2
        # Very long solutions may be over-engineered
        if len(solution.split("\n")) > 100:
            score -= 0.1
        return max(0.0, score)

    def _check_readability(self, solution: str) -> float:
        """Assess code readability."""
        score = 0.6
        lines = solution.split("\n")
        # Has comments?
        comments = sum(1 for l in lines if l.strip().startswith("#"))
        if comments >= 2:
            score += 0.15
        # Has docstrings?
        if '"""' in solution or "'''" in solution:
            score += 0.1
        # Reasonable line lengths?
        long_lines = sum(1 for l in lines if len(l) > 100)
        if long_lines == 0:
            score += 0.1
        elif long_lines > 5:
            score -= 0.1
        # Descriptive names (average identifier length > 3)?
        idents = re.findall(r'\b[a-z_]\w*\b', solution)
        if idents:
            avg_len = sum(len(i) for i in idents) / len(idents)
            if avg_len > 4:
                score += 0.1
        return min(1.0, max(0.0, score))

    def _check_robustness(self, solution: str) -> float:
        """Check for error handling and edge case coverage."""
        score = 0.5
        # Has try/except?
        if "try:" in solution and "except" in solution:
            score += 0.2
        # Has input validation?
        if re.search(r'if\s+(not\s+)?[\w]+\s*(is|==|!=|<|>|<=|>=)', solution):
            score += 0.15
        # Has type checking?
        if "isinstance(" in solution:
            score += 0.1
        # Has None checks?
        if "is None" in solution or "is not None" in solution:
            score += 0.05
        return min(1.0, score)

    def _check_reasoning(self, reasoning: Dict[str, Any]) -> float:
        """Evaluate the quality of reasoning trace."""
        score = 0.5
        steps = reasoning.get("steps", [])
        if len(steps) >= 3:
            score += 0.2
        if len(steps) >= 5:
            score += 0.1
        if reasoning.get("assumptions"):
            score += 0.1
        if reasoning.get("confidence", 0) > 0.7:
            score += 0.1
        return min(1.0, score)

    def _suggest_fix(self, axis: str, solution: str) -> List[str]:
        """Generate improvement suggestions for a weak axis."""
        suggestions: Dict[str, List[str]] = {
            "correctness": [
                "Verify output against expected results",
                "Add assertion checks for correctness",
                "Review algorithm logic for off-by-one errors",
            ],
            "completeness": [
                "Address all sub-tasks in the original request",
                "Add missing return/output handling",
                "Handle all specified input formats",
            ],
            "efficiency": [
                "Consider reducing nested loop depth",
                "Use more efficient data structures (set, dict)",
                "Explore divide-and-conquer alternatives",
            ],
            "readability": [
                "Add docstrings to public functions",
                "Use descriptive variable names",
                "Break long functions into smaller helpers",
            ],
            "robustness": [
                "Add error handling with try/except",
                "Validate inputs before processing",
                "Handle edge cases (empty input, None, etc.)",
            ],
        }
        return suggestions.get(axis, ["Review and improve"])
