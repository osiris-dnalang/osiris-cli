"""Redacted runtime traces, budgets, and capability evidence registry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .contracts import CapabilityClaim, CapabilityStatus
from .policy import redact


@dataclass(frozen=True)
class ResourceBudget:
    max_tasks: int = 9
    max_concurrent_workers: int = 3
    max_tool_calls: int = 10
    max_runtime_seconds: int = 900


@dataclass(frozen=True)
class TraceReceipt:
    run_id: str
    event_type: str
    message: str
    timestamp_utc: float = field(default_factory=time.time)

    def redacted(self) -> "TraceReceipt":
        return TraceReceipt(self.run_id, self.event_type, redact(self.message), self.timestamp_utc)


class Observability:
    def __init__(self, budget: ResourceBudget = ResourceBudget()):
        self.budget = budget
        self.receipts: List[TraceReceipt] = []
        self._task_count = 0
        self._tool_calls = 0
        self._started_at = time.time()

    def record(self, run_id: str, event_type: str, message: str) -> TraceReceipt:
        receipt = TraceReceipt(run_id, event_type, message).redacted()
        self.receipts.append(receipt)
        return receipt

    def consume_task(self) -> None:
        self._task_count += 1
        self._assert_budget()

    def consume_tool_call(self) -> None:
        self._tool_calls += 1
        self._assert_budget()

    def _assert_budget(self) -> None:
        if self._task_count > self.budget.max_tasks:
            raise RuntimeError("task budget exceeded")
        if self._tool_calls > self.budget.max_tool_calls * max(self._task_count, 1):
            raise RuntimeError("tool-call budget exceeded")
        if time.time() - self._started_at > self.budget.max_runtime_seconds:
            raise RuntimeError("runtime budget exceeded")


class CapabilityRegistry:
    def __init__(self, claims: Optional[List[CapabilityClaim]] = None):
        self.claims: Dict[str, CapabilityClaim] = {claim.name: claim for claim in claims or []}

    def register(self, claim: CapabilityClaim) -> None:
        claim.validate()
        self.claims[claim.name] = claim

    def status(self, name: str) -> CapabilityStatus:
        return self.claims[name].status

    def as_dict(self) -> Dict[str, str]:
        return {name: claim.status.value for name, claim in sorted(self.claims.items())}
