"""Machine-readable runtime capability status."""

from __future__ import annotations

from typing import Dict

from .contracts import CapabilityStatus


def capability_status() -> Dict[str, str]:
    """Return conservative status labels; no probing or side effects occur."""
    return {
        "runtime_contracts": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "workspace_tools": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "session_evidence_store": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "pcrb_evidence_store": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "runtime_policy_hooks": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "artifact_classifier": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "context_broker": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "worker_isolation": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "agent_scheduler": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "observability": CapabilityStatus.IMPLEMENTED_UNVERIFIED.value,
        "plugins": CapabilityStatus.PLANNED.value,
        "mcp": CapabilityStatus.DISABLED.value,
        "external_adapters": CapabilityStatus.DISABLED.value,
    }
