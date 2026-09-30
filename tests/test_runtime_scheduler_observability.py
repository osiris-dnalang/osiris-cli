import pytest

from osiris.runtime.observability import CapabilityRegistry, Observability, ResourceBudget
from osiris.runtime.scheduler import TaskGraph
from osiris.runtime.contracts import CapabilityClaim, CapabilityStatus


def test_observability_redacts_receipts_and_enforces_task_budget():
    observability = Observability(ResourceBudget(max_tasks=1))
    receipt = observability.record("run-1", "tool", "api_key=secret")

    assert "secret" not in receipt.message
    observability.consume_task()
    with pytest.raises(RuntimeError, match="task budget"):
        observability.consume_task()


def test_task_graph_runs_dependencies_once_and_cancels():
    graph = TaskGraph(Observability(ResourceBudget(max_tasks=2)))
    graph.add("a")
    graph.add("b", ("a",))
    seen = []

    graph.run_one("a", seen.append)
    assert graph.ready() == {"b"}
    graph.run_one("b", seen.append)
    assert seen == ["a", "b"]
    graph.cancel()
    assert graph.ready() == set()


def test_capability_registry_reports_evidence_status():
    registry = CapabilityRegistry()
    registry.register(
        CapabilityClaim(
            "worker",
            CapabilityStatus.IMPLEMENTED_UNVERIFIED,
            boundary="backend required",
        )
    )

    assert registry.as_dict() == {"worker": "implemented-unverified"}
