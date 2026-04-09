"""Self-reflector agent — meta-learning and performance tracking.

Analyses the full pipeline output, identifies systemic patterns,
and generates recursive self-improvement directives that feed
back into the orchestrator for the next cycle.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .memory import AgentMemory, MemoryEntry


@dataclass
class ReflectionReport:
    """Output of the self-reflector."""
    task: str
    solved_correctly: bool
    quality_score: float
    reasoning_depth: int
    process_assessment: str
    improvement_directives: List[str]
    pattern_signals: List[str]
    meta_question: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "solved_correctly": self.solved_correctly,
            "quality_score": self.quality_score,
            "reasoning_depth": self.reasoning_depth,
            "process_assessment": self.process_assessment,
            "improvement_directives": self.improvement_directives,
            "pattern_signals": self.pattern_signals,
            "meta_question": self.meta_question,
        }


class SelfReflector:
    """Analyses pipeline results and generates self-improvement signals."""

    def __init__(self, memory: AgentMemory) -> None:
        self.memory = memory

    def reflect(self, task: str, results: Dict[str, Any]) -> ReflectionReport:
        """Produce a reflection report and store the learning in memory."""
        critique = results.get("critique", {})
        optimization = results.get("optimization", {})
        reasoning = results.get("reasoning", {})

        quality = critique.get("overall_score", 0.5)
        verdict = critique.get("verdict", "unknown")
        solved = verdict == "pass"
        depth = reasoning.get("depth", 0)

        # Assess the process
        assessment = self._assess_process(results, quality, solved)

        # Generate improvement directives
        directives = self._generate_directives(results, quality)

        # Detect patterns from memory
        patterns = self._detect_patterns(task, quality)

        # Generate meta-question for recursive improvement
        meta_q = self._meta_question(task, quality, directives)

        # Store in memory
        import hashlib
        sol_hash = hashlib.md5(
            str(results.get("solution", "")).encode()
        ).hexdigest()[:12]

        self.memory.store(MemoryEntry(
            task=task[:200],
            solution_hash=sol_hash,
            quality_score=quality,
            reasoning_depth=depth,
            critique="; ".join(critique.get("weaknesses", []))[:300],
            improvement="; ".join(directives[:3])[:300],
            domain=results.get("domain", "general"),
            tags=patterns[:5],
        ))

        return ReflectionReport(
            task=task,
            solved_correctly=solved,
            quality_score=quality,
            reasoning_depth=depth,
            process_assessment=assessment,
            improvement_directives=directives,
            pattern_signals=patterns,
            meta_question=meta_q,
        )

    def _assess_process(self, results: Dict[str, Any],
                        quality: float, solved: bool) -> str:
        if quality >= 0.9 and solved:
            return ("Excellent execution — all agents performed well. "
                    "Consider reducing iteration count to improve speed.")
        if quality >= 0.7:
            return ("Good execution with minor issues. "
                    "The critic identified actionable improvements "
                    "that the optimizer has planned.")
        if quality >= 0.5:
            return ("Moderate execution — several weaknesses detected. "
                    "The reasoning phase may need more depth, "
                    "or the coder needs stronger templates.")
        return ("Poor execution — fundamental issues detected. "
                "Consider decomposing the task further or "
                "switching to a different strategy.")

    def _generate_directives(self, results: Dict[str, Any],
                             quality: float) -> List[str]:
        directives = []
        critique = results.get("critique", {})
        optimization = results.get("optimization", {})

        # From critique weaknesses
        for w in critique.get("weaknesses", []):
            directives.append(f"Address: {w}")

        # From optimization meta-insights
        for m in optimization.get("meta_insights", []):
            directives.append(f"Apply: {m}")

        # Process-level improvements
        if quality < 0.5:
            directives.append(
                "CRITICAL: Increase reasoning depth before code generation")
        if not critique.get("strengths"):
            directives.append(
                "No strengths identified — review task decomposition strategy")

        # Learning from memory trends
        trend = self.memory.improvement_trend()
        if trend < -0.05:
            directives.append(
                "ALERT: Quality trending downward — review recent changes")
        elif trend > 0.05:
            directives.append(
                "POSITIVE: Quality improving — continue current approach")

        if not directives:
            directives.append("Maintain current quality — no critical issues")

        return directives

    def _detect_patterns(self, task: str, quality: float) -> List[str]:
        """Detect patterns from memory history."""
        patterns = []

        # Check domain performance
        lowered = task.lower()
        domain_map = {
            "code": ["code", "function", "implement", "python"],
            "math": ["calculate", "solve", "equation"],
            "reasoning": ["explain", "analyze", "compare"],
        }
        detected_domain = "general"
        for d, kws in domain_map.items():
            if any(kw in lowered for kw in kws):
                detected_domain = d
                break

        domain_history = self.memory.by_domain(detected_domain)
        if len(domain_history) >= 3:
            avg = sum(e.quality_score for e in domain_history) / len(domain_history)
            if avg < 0.6:
                patterns.append(f"weak-domain:{detected_domain}")
            elif avg > 0.85:
                patterns.append(f"strong-domain:{detected_domain}")

        # Check recent quality stability
        recent = self.memory.recent(5)
        if len(recent) >= 3:
            scores = [e.quality_score for e in recent]
            variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            if variance > 0.04:
                patterns.append("unstable-quality")
            else:
                patterns.append("stable-quality")

        # Check total experience
        total = len(self.memory)
        if total < 5:
            patterns.append("low-experience")
        elif total > 50:
            patterns.append("high-experience")

        return patterns

    def _meta_question(self, task: str, quality: float,
                       directives: List[str]) -> str:
        """Generate a recursive self-improvement question."""
        if quality >= 0.9:
            return ("How can the agent achieve this quality level "
                    "with fewer reasoning steps (speed optimisation)?")
        if quality >= 0.7:
            return ("What specific knowledge would push quality "
                    f"from {quality:.2f} to 0.90+ for this task type?")
        if quality >= 0.5:
            return ("Is the current strategy fundamentally correct, "
                    "or should the orchestrator try a different approach?")
        return ("Should this task be decomposed into simpler sub-tasks "
                "before attempting a solution?")
