from osiris.runtime.report import capability_status


def test_capability_status_is_conservative_and_machine_readable():
    status = capability_status()

    # no recorded verification evidence exists for the contracts yet, so the
    # conservative label is the correct one (2026-09-29)
    assert status["runtime_contracts"] == "implemented-unverified"
    assert status["mcp"] == "disabled"
    assert status["external_adapters"] == "disabled"
    assert status["artifact_classifier"] == "implemented-unverified"
