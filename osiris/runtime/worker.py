"""Fail-closed worker runner and isolation backend contract."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence

from .contracts import RuntimeCapability


class WorkerError(RuntimeError):
    """Base class for worker validation and execution failures."""


class IsolationUnavailable(WorkerError):
    """Raised when no OS-level isolation backend has been configured."""


class WorkerProtocolError(WorkerError):
    """Raised when a backend returns an invalid result."""


@dataclass(frozen=True)
class WorkerRequest:
    request_id: str
    command: str
    arguments: Sequence[str] = ()
    environment: Mapping[str, str] = ()


@dataclass(frozen=True)
class WorkerResult:
    request_id: str
    status: str
    output: str = ""
    output_sha256: str = ""
    artifact_refs: Sequence[str] = ()

    def validate(self, max_output_bytes: int) -> None:
        if not self.request_id:
            raise WorkerProtocolError("worker result has no request id")
        if self.status not in {"completed", "failed", "cancelled"}:
            raise WorkerProtocolError("worker result has invalid status")
        encoded = self.output.encode("utf-8")
        if len(encoded) > max_output_bytes:
            raise WorkerProtocolError("worker output exceeds the capability limit")
        expected = hashlib.sha256(encoded).hexdigest()
        if self.output_sha256 and self.output_sha256 != expected:
            raise WorkerProtocolError("worker output hash mismatch")
        if self.artifact_refs and any(not ref.startswith("artifact://") for ref in self.artifact_refs):
            raise WorkerProtocolError("worker returned an unapproved artifact reference")


IsolationBackend = Callable[[WorkerRequest, RuntimeCapability], WorkerResult]


class WorkerRunner:
    """Host-side capability gate around an OS-level isolation backend.

    No backend is installed by default. A caller must supply an independently
    reviewed container, microVM, or VM adapter.
    """

    def __init__(self, backend: Optional[IsolationBackend] = None):
        self.backend = backend

    def run(self, request: WorkerRequest, capability: RuntimeCapability) -> WorkerResult:
        capability.validate(time.time())
        if self.backend is None:
            raise IsolationUnavailable("no OS-level isolation backend is configured")
        if request.command not in capability.allowed_commands:
            raise PermissionError("command is not allowed by the capability")
        if any(key not in capability.allowed_environment for key in request.environment):
            raise PermissionError("environment key is not allowed by the capability")
        result = self.backend(request, capability)
        result.validate(capability.max_output_bytes)
        if result.request_id != request.request_id:
            raise WorkerProtocolError("worker request id mismatch")
        return result
