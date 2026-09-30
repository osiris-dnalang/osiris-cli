"""Versioned contracts for the local OSIRIS runtime.

These contracts describe authority; they do not grant authority by themselves.
The host policy and worker boundary must validate and enforce them.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "1.0"
MAX_TASK_BYTES = 32 * 1024


class ActionClass(str, Enum):
    READ_WORKSPACE = "workspace.read"
    SEARCH_WORKSPACE = "workspace.search"
    WRITE_WORKSPACE = "workspace.write"
    RUN_LOCAL = "worker.local"
    AI_INFER = "provider.ai_infer"
    NETWORK_REQUEST = "network.request"
    CLOUD_DEPLOY = "cloud.deploy"
    QUANTUM_SUBMIT = "quantum.remote_submit"


class ExecutionMode(str, Enum):
    DRY_RUN = "dry_run"
    LOCAL_SANDBOX = "local_sandbox"
    REMOTE = "remote"


class CapabilityStatus(str, Enum):
    PLANNED = "planned"
    PARTIAL = "partial"
    IMPLEMENTED_UNVERIFIED = "implemented-unverified"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    DISABLED = "disabled"


def _identifier(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex)


def _bounded_text(value: str, name: str, limit: int) -> None:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError("{} must be a non-empty bounded string".format(name))


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to immutable content stored outside an event envelope."""

    uri: str
    sha256: str
    content_type: str = "application/octet-stream"
    classification: str = "internal"

    def validate(self) -> None:
        _bounded_text(self.uri, "uri", 512)
        _bounded_text(self.content_type, "content_type", 128)
        _bounded_text(self.classification, "classification", 64)
        if len(self.sha256) != 64 or any(char not in "0123456789abcdef" for char in self.sha256):
            raise ValueError("sha256 must be a lowercase 64-character hex digest")


@dataclass(frozen=True)
class TaskRequest:
    """Host-submitted work request; model output cannot create one implicitly."""

    action: ActionClass
    execution_mode: ExecutionMode
    run_id: str = field(default_factory=lambda: _identifier("run"))
    task_id: str = field(default_factory=lambda: _identifier("task"))
    input_ref: Optional[ArtifactRef] = None
    allowed_read_roots: Tuple[str, ...] = ()
    allowed_write_root: Optional[str] = None
    max_output_bytes: int = 12_000
    timeout_seconds: int = 60
    approval_id: Optional[str] = None
    schema_version: str = SCHEMA_VERSION

    def validate(self) -> None:
        _bounded_text(self.run_id, "run_id", 128)
        _bounded_text(self.task_id, "task_id", 128)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported task schema version")
        if self.input_ref is not None:
            self.input_ref.validate()
        if len(self.allowed_read_roots) > 16:
            raise ValueError("too many read roots")
        if any(not isinstance(root, str) or not root for root in self.allowed_read_roots):
            raise ValueError("read roots must be non-empty strings")
        if self.allowed_write_root is not None:
            _bounded_text(self.allowed_write_root, "allowed_write_root", 512)
        if not 1 <= self.max_output_bytes <= 1_000_000:
            raise ValueError("max_output_bytes is out of bounds")
        if not 1 <= self.timeout_seconds <= 900:
            raise ValueError("timeout_seconds is out of bounds")
        if self.execution_mode is ExecutionMode.REMOTE and not self.approval_id:
            raise ValueError("remote execution requires an approval_id")
        if len(json.dumps(asdict(self), default=str)) > MAX_TASK_BYTES:
            raise ValueError("task request exceeds the size limit")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class RuntimeCapability:
    """Immutable host-issued worker capability."""

    run_id: str
    task_id: str
    capability_id: str = field(default_factory=lambda: _identifier("cap"))
    expires_at_utc: float = 0.0
    allowed_read_roots: Tuple[str, ...] = ()
    allowed_write_root: Optional[str] = None
    allowed_commands: Tuple[str, ...] = ()
    allowed_environment: Tuple[str, ...] = ()
    allow_network: bool = False
    allowed_network_destinations: Tuple[str, ...] = ()
    max_cpu_seconds: int = 30
    max_memory_mb: int = 256
    max_disk_mb: int = 256
    max_output_bytes: int = 12_000
    max_processes: int = 1
    execution_mode: ExecutionMode = ExecutionMode.LOCAL_SANDBOX
    approval_id: Optional[str] = None

    def validate(self, now: Optional[float] = None) -> None:
        _bounded_text(self.run_id, "run_id", 128)
        _bounded_text(self.task_id, "task_id", 128)
        _bounded_text(self.capability_id, "capability_id", 128)
        if self.expires_at_utc <= 0 or (now is not None and self.expires_at_utc <= now):
            raise ValueError("capability is expired or has no expiry")
        if self.execution_mode is ExecutionMode.REMOTE:
            raise ValueError("worker capabilities cannot authorize remote execution")
        if not 1 <= self.max_cpu_seconds <= 900:
            raise ValueError("max_cpu_seconds is out of bounds")
        if not 16 <= self.max_memory_mb <= 4096:
            raise ValueError("max_memory_mb is out of bounds")
        if not 1 <= self.max_disk_mb <= 4096:
            raise ValueError("max_disk_mb is out of bounds")
        if not 1 <= self.max_output_bytes <= 1_000_000:
            raise ValueError("max_output_bytes is out of bounds")
        if not 1 <= self.max_processes <= 16:
            raise ValueError("max_processes is out of bounds")
        if self.allow_network and not self.allowed_network_destinations:
            raise ValueError("network capability requires explicit destinations")
        if self.allowed_write_root and not self.allowed_read_roots:
            raise ValueError("write capability requires declared read scope")


@dataclass(frozen=True)
class CapabilityClaim:
    """Evidence-backed status for one user-visible runtime capability."""

    name: str
    status: CapabilityStatus
    implementation_ref: Optional[str] = None
    test_ref: Optional[str] = None
    evidence_ref: Optional[str] = None
    boundary: str = ""
    notes: str = ""

    def validate(self) -> None:
        _bounded_text(self.name, "name", 128)
        _bounded_text(self.boundary, "boundary", 2_000)
        if self.status is CapabilityStatus.VERIFIED:
            for field_name, value in (
                ("implementation_ref", self.implementation_ref),
                ("test_ref", self.test_ref),
                ("evidence_ref", self.evidence_ref),
            ):
                if not value:
                    raise ValueError("verified capability requires {}".format(field_name))


@dataclass(frozen=True)
class EvidenceRecord:
    """Reproducible record of a verification command and its limitations."""

    capability_name: str
    command: str
    result: str
    environment: Mapping[str, str] = field(default_factory=dict)
    commit: Optional[str] = None
    limitations: Sequence[str] = ()
    evidence_id: str = field(default_factory=lambda: _identifier("evidence"))
    recorded_at_utc: float = field(default_factory=time.time)

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
