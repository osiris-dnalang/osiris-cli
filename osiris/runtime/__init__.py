"""Opt-in, evidence-based OSIRIS Agent Runtime primitives.

Importing this package does not register tools, start workers, load providers, or
enable network access.
"""

from .contracts import (
    ActionClass,
    ArtifactRef,
    CapabilityClaim,
    CapabilityStatus,
    EvidenceRecord,
    ExecutionMode,
    RuntimeCapability,
    TaskRequest,
)
from .persistence import SessionStore
from .context import ContextBroker, ContextBudget, ContextItem, ContextLimitExceeded
from .policy import PolicyDecision, PolicyHooks, RuntimePolicy, redact
from .observability import (
    CapabilityRegistry,
    Observability,
    ResourceBudget,
    TraceReceipt,
)
from .scheduler import ScheduledTask, TaskGraph
from .extensions import (
    CapabilityPack,
    ExtensionRegistry,
    MCPServerRegistration,
    PluginManifest,
)
from .adapters import ExternalAdapter, AdapterState, default_adapters
from .report import capability_status
from .evidence import EvidenceCapsule, EvidenceStore, EvidenceStoreError
from .artifacts import ArtifactClassification, ArtifactRejected, classify_artifact
from .workspace import Workspace, WorkspaceError
from .worker import (
    IsolationUnavailable,
    WorkerError,
    WorkerProtocolError,
    WorkerRequest,
    WorkerResult,
    WorkerRunner,
)

__all__ = [
    "ActionClass",
    "ArtifactRef",
    "CapabilityClaim",
    "CapabilityStatus",
    "ContextBroker",
    "ContextBudget",
    "ContextItem",
    "ContextLimitExceeded",
    "EvidenceRecord",
    "ExecutionMode",
    "RuntimeCapability",
    "PolicyDecision",
    "PolicyHooks",
    "RuntimePolicy",
    "redact",
    "CapabilityRegistry",
    "Observability",
    "ResourceBudget",
    "TraceReceipt",
    "ScheduledTask",
    "TaskGraph",
    "CapabilityPack",
    "ExtensionRegistry",
    "MCPServerRegistration",
    "PluginManifest",
    "ExternalAdapter",
    "AdapterState",
    "default_adapters",
    "capability_status",
    "EvidenceCapsule",
    "EvidenceStore",
    "EvidenceStoreError",
    "ArtifactClassification",
    "ArtifactRejected",
    "classify_artifact",
    "SessionStore",
    "TaskRequest",
    "Workspace",
    "WorkspaceError",
    "IsolationUnavailable",
    "WorkerError",
    "WorkerProtocolError",
    "WorkerRequest",
    "WorkerResult",
    "WorkerRunner",
]
