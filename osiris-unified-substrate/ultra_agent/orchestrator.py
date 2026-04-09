"""Orchestrator agent — plans, delegates, supervises.

Uses the OSIRIS stack planner (LLMStackRefiner) for strategic
decomposition and the meta-loop for iterative improvement planning.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TaskPlan:
    """Execution plan produced by the orchestrator."""
    task: str
    domain: str
    steps: List[Dict[str, str]]
    strategy: str
    constraints: List[str] = field(default_factory=list)
    estimated_depth: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "domain": self.domain,
            "steps": self.steps,
            "strategy": self.strategy,
            "constraints": self.constraints,
            "estimated_depth": self.estimated_depth,
        }


# Domain detection keywords
_DOMAIN_SIGNALS = {
    "code": ["write", "function", "implement", "debug", "fix", "refactor",
             "python", "class", "algorithm", "program", "script", "code",
             "api", "test", "bug", "error", "compile", "import"],
    "math": ["calculate", "solve", "equation", "proof", "integral",
             "derivative", "probability", "algebra", "geometry", "math"],
    "reasoning": ["explain", "why", "how", "compare", "contrast",
                  "implications", "analyze", "reason", "logic", "argument",
                  "cause", "effect", "deduce", "infer"],
    "research": ["survey", "literature", "paper", "hypothesis", "experiment",
                 "methodology", "findings", "conclusion", "citation"],
    "system": ["deploy", "configure", "install", "setup", "architecture",
               "infrastructure", "docker", "kubernetes", "database"],
}


def _detect_domain(task: str) -> str:
    """Detect the primary domain of a task."""
    lowered = task.lower()
    scores: Dict[str, int] = {}
    for domain, keywords in _DOMAIN_SIGNALS.items():
        scores[domain] = sum(1 for kw in keywords if kw in lowered)
    if not any(scores.values()):
        return "general"
    return max(scores, key=lambda d: scores[d])


def _detect_complexity(task: str) -> int:
    """Estimate task complexity on a 1-5 scale."""
    length = len(task.split())
    connectors = sum(1 for w in task.lower().split()
                     if w in ("and", "then", "also", "but", "after", "while", "including"))
    if length > 60 or connectors > 3:
        return 5
    if length > 30 or connectors > 1:
        return 3
    return 1


class Orchestrator:
    """Plans tasks into executable step sequences for the agent swarm."""

    def __init__(self) -> None:
        self.plan_history: List[TaskPlan] = []

    def plan(self, task: str) -> TaskPlan:
        """Decompose a task into an execution plan."""
        domain = _detect_domain(task)
        complexity = _detect_complexity(task)
        strategy = self._select_strategy(domain, complexity)
        steps = self._build_steps(task, domain, strategy, complexity)
        constraints = self._identify_constraints(task, domain)

        plan = TaskPlan(
            task=task,
            domain=domain,
            steps=steps,
            strategy=strategy,
            constraints=constraints,
            estimated_depth=complexity,
        )
        self.plan_history.append(plan)
        return plan

    def _select_strategy(self, domain: str, complexity: int) -> str:
        if complexity >= 4:
            return "decompose-conquer-synthesize"
        if domain == "code":
            return "spec-implement-test-refine"
        if domain == "math":
            return "formalize-solve-verify"
        if domain == "reasoning":
            return "analyze-argue-conclude"
        if domain == "research":
            return "survey-hypothesize-validate"
        return "reason-execute-critique"

    def _build_steps(self, task: str, domain: str, strategy: str,
                     complexity: int) -> List[Dict[str, str]]:
        """Build concrete execution steps."""
        base_steps = [
            {"agent": "reasoner", "action": "analyze", "input": task},
        ]

        if domain == "code":
            base_steps.extend([
                {"agent": "coder", "action": "implement", "input": "reasoner.output"},
                {"agent": "critic", "action": "review", "input": "coder.output"},
                {"agent": "coder", "action": "refine", "input": "critic.feedback"},
            ])
        elif domain == "math":
            base_steps.extend([
                {"agent": "reasoner", "action": "solve", "input": "reasoner.analysis"},
                {"agent": "critic", "action": "verify", "input": "reasoner.solution"},
            ])
        elif domain == "research":
            base_steps.extend([
                {"agent": "reasoner", "action": "hypothesize", "input": "reasoner.analysis"},
                {"agent": "coder", "action": "experiment", "input": "reasoner.hypothesis"},
                {"agent": "critic", "action": "evaluate", "input": "coder.results"},
            ])
        else:
            base_steps.extend([
                {"agent": "coder", "action": "execute", "input": "reasoner.output"},
                {"agent": "critic", "action": "evaluate", "input": "coder.output"},
            ])

        # Always end with optimization and reflection
        base_steps.extend([
            {"agent": "optimizer", "action": "optimize", "input": "critic.feedback"},
            {"agent": "self_reflector", "action": "reflect", "input": "all.results"},
        ])

        # For high complexity, add decomposition step at the beginning
        if complexity >= 4:
            base_steps.insert(0, {"agent": "orchestrator", "action": "decompose",
                                  "input": task})

        return base_steps

    def _identify_constraints(self, task: str, domain: str) -> List[str]:
        constraints = []
        lowered = task.lower()
        if "fast" in lowered or "quick" in lowered:
            constraints.append("latency-sensitive")
        if "accurate" in lowered or "correct" in lowered:
            constraints.append("accuracy-critical")
        if "secure" in lowered or "safe" in lowered:
            constraints.append("security-hardened")
        if domain == "code":
            constraints.append("must-be-runnable")
        if not constraints:
            constraints.append("standard")
        return constraints
