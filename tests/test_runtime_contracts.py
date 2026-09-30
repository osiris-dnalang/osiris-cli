import time

import pytest

from osiris.runtime import (
    ActionClass,
    ArtifactRef,
    CapabilityClaim,
    CapabilityStatus,
    ExecutionMode,
    EvidenceRecord,
    RuntimeCapability,
    TaskRequest,
)


def test_task_request_rejects_remote_execution_without_approval():
    task = TaskRequest(ActionClass.RUN_LOCAL, ExecutionMode.REMOTE)

    with pytest.raises(ValueError, match="approval_id"):
        task.validate()


def test_runtime_capability_is_local_and_expiring():
    capability = RuntimeCapability(
        run_id="run-1",
        task_id="task-1",
        expires_at_utc=time.time() + 60,
        allowed_read_roots=("/workspace",),
    )

    capability.validate()

    with pytest.raises(ValueError, match="expired"):
        capability.validate(time.time() + 61)


def test_runtime_capability_rejects_remote_mode():
    capability = RuntimeCapability(
        run_id="run-1",
        task_id="task-1",
        expires_at_utc=time.time() + 60,
        execution_mode=ExecutionMode.REMOTE,
    )

    with pytest.raises(ValueError, match="remote"):
        capability.validate()


def test_artifact_reference_validates_hash():
    artifact = ArtifactRef("artifact://run-1/input", "0" * 64)
    artifact.validate()

    with pytest.raises(ValueError, match="sha256"):
        ArtifactRef(artifact.uri, "not-a-hash").validate()


def test_verified_claim_requires_all_evidence_references():
    claim = CapabilityClaim("worker", CapabilityStatus.VERIFIED, boundary="sandbox")

    with pytest.raises(ValueError, match="implementation_ref"):
        claim.validate()


def test_evidence_digest_is_stable():
    record = EvidenceRecord(
        capability_name="contracts",
        command="python -m pytest tests/test_runtime_contracts.py",
        result="passed",
        environment={"python": "3.12"},
    )

    assert record.digest() == record.digest()
