"""Reasoner agent — deep analysis and problem decomposition.

Performs multi-step chain-of-thought reasoning, identifies
sub-problems, and produces structured analysis outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ReasoningTrace:
    """Structured chain-of-thought output."""
    task: str
    steps: List[str]
    sub_problems: List[str]
    assumptions: List[str]
    conclusion: str
    confidence: float
    depth: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "steps": self.steps,
            "sub_problems": self.sub_problems,
            "assumptions": self.assumptions,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "depth": self.depth,
        }


class Reasoner:
    """Deep analysis agent with chain-of-thought reasoning."""

    def run(self, task: str, context: str = "") -> ReasoningTrace:
        """Produce a structured reasoning trace for the given task."""
        steps = self._chain_of_thought(task, context)
        sub_problems = self._decompose(task)
        assumptions = self._identify_assumptions(task)
        conclusion = self._synthesize(task, steps, sub_problems)
        confidence = self._estimate_confidence(steps, sub_problems)

        return ReasoningTrace(
            task=task,
            steps=steps,
            sub_problems=sub_problems,
            assumptions=assumptions,
            conclusion=conclusion,
            confidence=confidence,
            depth=len(steps),
        )

    def _chain_of_thought(self, task: str, context: str) -> List[str]:
        """Generate chain-of-thought reasoning steps."""
        steps = []

        # Step 1: Parse intent
        steps.append(f"UNDERSTAND: The task requests '{self._extract_verb(task)}' "
                      f"in the domain of '{self._extract_domain(task)}'.")

        # Step 2: Identify core challenge
        steps.append(f"IDENTIFY: The core challenge is {self._identify_challenge(task)}.")

        # Step 3: Map requirements
        reqs = self._map_requirements(task)
        steps.append(f"REQUIRE: Key requirements — {', '.join(reqs)}.")

        # Step 4: Consider approaches
        approaches = self._generate_approaches(task)
        steps.append(f"APPROACHES: Possible strategies — "
                      f"{'; '.join(approaches[:3])}.")

        # Step 5: Select best approach
        best = approaches[0] if approaches else "direct execution"
        steps.append(f"SELECT: Best approach — {best} — "
                      f"because it minimises complexity while meeting requirements.")

        # Step 6: Plan execution
        steps.append(f"PLAN: Execute {best} with verification at each step.")

        if context:
            steps.append(f"CONTEXT: Incorporating prior context ({len(context)} chars).")

        return steps

    def _extract_verb(self, task: str) -> str:
        verbs = ["write", "implement", "explain", "solve", "debug", "fix",
                 "create", "build", "design", "optimize", "analyze", "compare",
                 "calculate", "prove", "generate", "find", "deploy"]
        lowered = task.lower()
        for v in verbs:
            if v in lowered:
                return v
        return "process"

    def _extract_domain(self, task: str) -> str:
        domains = {
            "code": ["function", "python", "script", "class", "algorithm", "code"],
            "math": ["equation", "calculate", "proof", "integral", "solve"],
            "reasoning": ["explain", "why", "how", "analyze", "compare"],
            "system": ["deploy", "configure", "architecture", "docker"],
        }
        lowered = task.lower()
        for domain, keywords in domains.items():
            if any(kw in lowered for kw in keywords):
                return domain
        return "general"

    def _identify_challenge(self, task: str) -> str:
        length = len(task.split())
        if length > 40:
            return "a multi-faceted problem requiring decomposition"
        if length > 20:
            return "a moderately complex task requiring structured analysis"
        return "a focused task requiring precise execution"

    def _map_requirements(self, task: str) -> List[str]:
        reqs = ["correctness"]
        lowered = task.lower()
        if any(w in lowered for w in ["fast", "efficient", "optimize"]):
            reqs.append("performance")
        if any(w in lowered for w in ["readable", "clean", "maintainable"]):
            reqs.append("code quality")
        if any(w in lowered for w in ["test", "verify", "validate"]):
            reqs.append("verifiability")
        if any(w in lowered for w in ["explain", "document", "describe"]):
            reqs.append("clarity")
        if any(w in lowered for w in ["secure", "safe"]):
            reqs.append("security")
        return reqs

    def _identify_assumptions(self, task: str) -> List[str]:
        """Identify implicit assumptions in the task."""
        assumptions = []
        lowered = task.lower()
        if "function" in lowered or "implement" in lowered:
            assumptions.append("Input is well-formed and type-correct")
        if "sort" in lowered or "search" in lowered:
            assumptions.append("Collection fits in memory")
        if "file" in lowered or "read" in lowered:
            assumptions.append("File exists and is accessible")
        if "api" in lowered or "request" in lowered:
            assumptions.append("Network is available and endpoint is reachable")
        if not assumptions:
            assumptions.append("Standard operating conditions")
        return assumptions

    def _generate_approaches(self, task: str) -> List[str]:
        domain = self._extract_domain(task)
        if domain == "code":
            return [
                "test-driven development with incremental implementation",
                "functional decomposition into helper functions",
                "iterative refinement with linting and type checking",
            ]
        if domain == "math":
            return [
                "algebraic manipulation with verification",
                "divide and conquer with sub-problem reduction",
                "proof by construction with counterexample checking",
            ]
        if domain == "reasoning":
            return [
                "structured argumentation with evidence mapping",
                "multi-perspective analysis with synthesis",
                "first-principles decomposition",
            ]
        return [
            "systematic analysis → implementation → verification",
            "iterative refinement with feedback loops",
            "divide-and-conquer with integration",
        ]

    def _synthesize(self, task: str, steps: List[str],
                    sub_problems: List[str]) -> str:
        verb = self._extract_verb(task)
        domain = self._extract_domain(task)
        return (f"After {len(steps)}-step analysis across {domain} domain, "
                f"the task ('{verb}') can be solved by addressing "
                f"{len(sub_problems)} sub-problems in sequence with "
                f"verification at each stage.")

    def _estimate_confidence(self, steps: List[str],
                             sub_problems: List[str]) -> float:
        base = 0.7
        base += min(0.15, len(steps) * 0.02)
        if len(sub_problems) <= 3:
            base += 0.1
        return min(0.99, base)

    def _decompose(self, task: str) -> List[str]:
        """Break task into sub-problems."""
        parts = re.split(r'\band\b|\bthen\b|,\s*(?:and|then)', task, flags=re.IGNORECASE)
        if len(parts) <= 1:
            return [task.strip()]
        return [p.strip() for p in parts if p.strip()]
