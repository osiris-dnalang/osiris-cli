"""Host-enforced policy and pre/post tool hooks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from .contracts import ActionClass, ExecutionMode, TaskRequest


@dataclass(frozen=True)
class PolicyDecision:
    action: ActionClass
    decision: str
    reason: str
    approval_required: bool = False


class RuntimePolicy:
    """Deterministic policy; metrics and model output are intentionally ignored."""

    _external = {
        ActionClass.AI_INFER,
        ActionClass.NETWORK_REQUEST,
        ActionClass.CLOUD_DEPLOY,
        ActionClass.QUANTUM_SUBMIT,
    }

    def decide(self, task: TaskRequest) -> PolicyDecision:
        task.validate()
        if task.action in self._external:
            return PolicyDecision(
                task.action,
                "deny" if not task.approval_id else "needs_approval",
                "external effects are disabled by default",
                approval_required=True,
            )
        if task.action is ActionClass.WRITE_WORKSPACE and not task.allowed_write_root:
            return PolicyDecision(task.action, "deny", "write root is not declared")
        if task.execution_mode is ExecutionMode.REMOTE:
            return PolicyDecision(task.action, "deny", "remote mode is disabled")
        return PolicyDecision(task.action, "allow", "bounded local action")


_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret)(\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)-----BEGIN [^-]+ PRIVATE KEY-----.*?-----END [^-]+ PRIVATE KEY-----", re.DOTALL),
)


def redact(value: str) -> str:
    result = value
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(
            lambda match: (
                (match.group(1) + "=<REDACTED>")
                if match.lastindex
                else "<REDACTED>"
            ),
            result,
        )
    return result


class PolicyHooks:
    def __init__(self, policy: Optional[RuntimePolicy] = None):
        self.policy = policy or RuntimePolicy()

    def before(self, task: TaskRequest) -> PolicyDecision:
        return self.policy.decide(task)

    def after(self, result: Mapping[str, Any]) -> Dict[str, Any]:
        return {str(key): redact(str(value)) for key, value in result.items()}
