"""Mentor–Protégé dual-swarm architecture for self-improving AI.

Modules:
    mentor_swarm   — Expert swarm that critiques and teaches
    protege_swarm  — Learning swarm that improves from feedback
    evaluator      — Measures improvement with honest accounting
    distillation   — Runs the mentor→protégé knowledge transfer loop
"""

from .mentor_swarm import MentorSwarm
from .protege_swarm import ProtegeSwarm
from .evaluator import ImprovementEvaluator
from .distillation import DistillationEngine, DistillationRecord

__all__ = [
    "MentorSwarm",
    "ProtegeSwarm",
    "ImprovementEvaluator",
    "DistillationEngine",
    "DistillationRecord",
]
