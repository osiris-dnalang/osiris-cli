"""Protégé Swarm — the learning agent ensemble.

The protégé is a lighter-weight swarm that:
  1. Attempts tasks independently
  2. Receives structured feedback from the mentor
  3. Improves its solutions iteratively
  4. Stores learnings in memory for future retrieval
  5. Tracks its own improvement over time
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..swarm import AgentSwarm, SwarmResult
from ..memory import AgentMemory
from ..model_interface import ModelInterface, get_model_interface


@dataclass
class LearningRecord:
    """Tracks a single learning iteration."""
    task: str
    initial_quality: float
    improved_quality: float
    improvement_delta: float
    feedback_applied: str
    iteration: int
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "initial_quality": round(self.initial_quality, 4),
            "improved_quality": round(self.improved_quality, 4),
            "improvement_delta": round(self.improvement_delta, 4),
            "feedback_applied": self.feedback_applied,
            "iteration": self.iteration,
            "latency_ms": round(self.latency_ms, 2),
        }


class ProtegeSwarm:
    """Learning swarm that improves via mentor feedback.

    Lower quality threshold and fewer loops than the mentor —
    the protégé is meant to struggle, receive feedback, and grow.
    """

    def __init__(
        self,
        model_interface: Optional[ModelInterface] = None,
        quality_threshold: float = 0.60,
        max_loops: int = 2,
    ) -> None:
        self.model = model_interface or get_model_interface()
        self._swarm = AgentSwarm(
            memory_path="artifacts/protege_memory.jsonl",
            max_refinement_loops=max_loops,
            quality_threshold=quality_threshold,
            model_interface=self.model,
        )
        self._learning_history: List[LearningRecord] = []
        self._feedback_memory: List[Dict[str, Any]] = []

    def attempt(self, task: str) -> SwarmResult:
        """Make an independent attempt at solving a task."""
        return self._swarm.run(task)

    def improve(self, task: str, feedback: str) -> SwarmResult:
        """Re-attempt a task incorporating mentor feedback."""
        augmented = f"{task}\n\n[Mentor Feedback] Improve based on:\n{feedback}"
        return self._swarm.run(augmented)

    def learn(self, feedback: Dict[str, Any]) -> None:
        """Store structured feedback in learning memory."""
        self._feedback_memory.append(feedback)

    def learn_from_teaching(
        self,
        task: str,
        initial: SwarmResult,
        improved: SwarmResult,
        feedback: str,
        iteration: int,
    ) -> LearningRecord:
        """Record a full learning cycle."""
        initial_q = initial.performance.get("quality_score", 0)
        improved_q = improved.performance.get("quality_score", 0)
        delta = improved_q - initial_q

        record = LearningRecord(
            task=task,
            initial_quality=initial_q,
            improved_quality=improved_q,
            improvement_delta=delta,
            feedback_applied=feedback[:300],
            iteration=iteration,
            latency_ms=initial.elapsed_ms + improved.elapsed_ms,
        )
        self._learning_history.append(record)
        return record

    def improvement_trend(self, window: int = 10) -> Dict[str, Any]:
        """Compute learning trajectory over recent iterations."""
        if not self._learning_history:
            return {"status": "no_data", "trend": 0.0}

        recent = self._learning_history[-window:]
        deltas = [r.improvement_delta for r in recent]
        avg_delta = sum(deltas) / len(deltas)
        positive = sum(1 for d in deltas if d > 0)

        # Quality trajectory
        qualities = [r.improved_quality for r in recent]
        q_start = qualities[0] if qualities else 0
        q_end = qualities[-1] if qualities else 0

        return {
            "status": "tracking",
            "iterations": len(self._learning_history),
            "recent_window": len(recent),
            "avg_improvement_delta": round(avg_delta, 4),
            "positive_improvements": positive,
            "positive_rate": round(positive / len(recent), 3),
            "quality_start": round(q_start, 4),
            "quality_end": round(q_end, 4),
            "quality_trajectory": round(q_end - q_start, 4),
        }

    def stats(self) -> Dict[str, Any]:
        """Return protégé learning statistics."""
        trend = self.improvement_trend()
        return {
            "total_learning_iterations": len(self._learning_history),
            "feedback_entries": len(self._feedback_memory),
            "swarm_memory": self._swarm.memory.stats(),
            "improvement_trend": trend,
            "inference_mode": (
                "simulation" if self.model.simulation_mode else "model"
            ),
        }
