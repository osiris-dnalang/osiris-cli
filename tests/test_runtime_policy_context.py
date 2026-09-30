import pytest

from osiris.runtime.context import ContextBroker, ContextBudget, ContextItem, ContextLimitExceeded
from osiris.runtime.contracts import ActionClass, ExecutionMode, TaskRequest
from osiris.runtime.policy import PolicyHooks, RuntimePolicy, redact


def test_policy_denies_external_action_by_default():
    task = TaskRequest(ActionClass.NETWORK_REQUEST, ExecutionMode.LOCAL_SANDBOX)

    decision = RuntimePolicy().decide(task)

    assert decision.decision == "deny"
    assert decision.approval_required


def test_policy_denial_does_not_depend_on_agent_metadata():
    policy = RuntimePolicy()
    plain = TaskRequest(ActionClass.NETWORK_REQUEST, ExecutionMode.LOCAL_SANDBOX)
    annotated = TaskRequest(
        ActionClass.NETWORK_REQUEST,
        ExecutionMode.LOCAL_SANDBOX,
        input_ref=None,
    )

    assert policy.decide(plain).decision == "deny"
    assert policy.decide(annotated).decision == "deny"


def test_policy_requires_declared_write_root():
    task = TaskRequest(ActionClass.WRITE_WORKSPACE, ExecutionMode.LOCAL_SANDBOX)

    assert RuntimePolicy().decide(task).decision == "deny"


def test_redaction_removes_secret_values():
    assert "super-secret" not in redact("api_key=super-secret")
    assert "<REDACTED>" in redact("api_key=super-secret")


def test_policy_hook_redacts_result():
    result = PolicyHooks().after({"output": "token=secret-value"})

    assert "secret-value" not in result["output"]


def test_context_compacts_and_stops_after_budget():
    broker = ContextBroker(ContextBudget(max_context_chars=40, max_compactions=1))
    items = [ContextItem("tool", "x" * 100, "artifact://one")]

    compacted = broker.assemble(items)
    assert "artifact://one" in compacted
    with pytest.raises(ContextLimitExceeded):
        broker.assemble(items)
