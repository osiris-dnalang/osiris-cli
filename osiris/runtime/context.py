"""Bounded context assembly and compaction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class ContextBudget:
    max_context_chars: int = 120_000
    max_file_bytes: int = 100_000
    max_file_count_per_task: int = 40
    max_tool_output_chars: int = 12_000
    max_agent_result_chars: int = 16_000
    max_session_turns_before_compaction: int = 20
    max_compactions: int = 2


@dataclass(frozen=True)
class ContextItem:
    kind: str
    content: str
    artifact_ref: str = ""


class ContextLimitExceeded(RuntimeError):
    """Raised when context cannot be safely reduced within the configured budget."""


class ContextBroker:
    def __init__(self, budget: ContextBudget = ContextBudget()):
        self.budget = budget
        self._compactions = 0

    def assemble(self, items: Sequence[ContextItem]) -> str:
        if len(items) > self.budget.max_file_count_per_task * 4:
            raise ContextLimitExceeded("too many context items")
        bounded = []
        for item in items:
            if len(item.content) > self.budget.max_tool_output_chars:
                content = item.content[: self.budget.max_tool_output_chars]
            else:
                content = item.content
            bounded.append("[{}] {}".format(item.kind, content))
        result = "\n".join(bounded)
        if len(result) > self.budget.max_context_chars:
            return self.compact(items)
        return result

    def compact(self, items: Sequence[ContextItem]) -> str:
        if self._compactions >= self.budget.max_compactions:
            raise ContextLimitExceeded("maximum context compactions reached")
        self._compactions += 1
        handoff = []
        for item in items[-8:]:
            excerpt = item.content[: self.budget.max_agent_result_chars]
            reference = " ref={}".format(item.artifact_ref) if item.artifact_ref else ""
            handoff.append("[{}]{} {}".format(item.kind, reference, excerpt))
        result = "\n".join(handoff)
        if len(result) > self.budget.max_context_chars:
            result = result[: self.budget.max_context_chars]
        return result

    @property
    def compactions(self) -> int:
        return self._compactions
