import time

import pytest

from osiris.runtime.contracts import RuntimeCapability
from osiris.runtime.worker import (
    IsolationUnavailable,
    WorkerRequest,
    WorkerResult,
    WorkerRunner,
)


def capability(**kwargs):
    values = {
        "run_id": "run-1",
        "task_id": "task-1",
        "expires_at_utc": time.time() + 60,
        "allowed_commands": ("echo",),
        "allowed_environment": ("LANG",),
        "allowed_read_roots": ("/workspace",),
    }
    values.update(kwargs)
    return RuntimeCapability(**values)


def test_worker_fails_closed_without_isolation_backend():
    runner = WorkerRunner()

    with pytest.raises(IsolationUnavailable):
        runner.run(WorkerRequest("request-1", "echo"), capability())


def test_worker_rejects_unallowed_command():
    runner = WorkerRunner(lambda request, cap: WorkerResult(request.request_id, "completed"))

    with pytest.raises(PermissionError):
        runner.run(WorkerRequest("request-1", "sh"), capability())


def test_worker_validates_result_identity_and_hash():
    def backend(request, cap):
        output = "ok"
        return WorkerResult(
            request.request_id,
            "completed",
            output,
            output_sha256=__import__("hashlib").sha256(output.encode()).hexdigest(),
        )

    result = WorkerRunner(backend).run(WorkerRequest("request-1", "echo"), capability())

    assert result.output == "ok"
