"""Bounded task graph scheduler with cancellation and idempotent task claims."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Set

from .observability import Observability


@dataclass(frozen=True)
class ScheduledTask:
    task_id: str
    dependencies: Set[str]


class TaskGraph:
    def __init__(self, observability: Optional[Observability] = None):
        self.observability = observability or Observability()
        self.tasks: Dict[str, ScheduledTask] = {}
        self.completed: Set[str] = set()
        self.claimed: Set[str] = set()
        self.cancelled = False

    def add(self, task_id: str, dependencies: Iterable[str] = ()) -> None:
        if self.cancelled:
            raise RuntimeError("task graph is cancelled")
        if task_id in self.tasks:
            raise ValueError("duplicate task id")
        if len(self.tasks) >= self.observability.budget.max_tasks:
            raise RuntimeError("task budget exceeded")
        self.tasks[task_id] = ScheduledTask(task_id, set(dependencies))

    def ready(self) -> Set[str]:
        if self.cancelled:
            return set()
        return {
            task_id
            for task_id, task in self.tasks.items()
            if task_id not in self.completed
            and task_id not in self.claimed
            and task.dependencies.issubset(self.completed)
        }

    def run_one(self, task_id: str, handler: Callable[[str], None]) -> None:
        if task_id not in self.ready():
            raise RuntimeError("task is not ready")
        self.claimed.add(task_id)
        self.observability.consume_task()
        try:
            handler(task_id)
        except Exception:
            self.claimed.remove(task_id)
            raise
        self.completed.add(task_id)

    def cancel(self) -> None:
        self.cancelled = True
