"""record_outcome only accepts evidence of the kind the hypothesis declares."""

import pytest

import research


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "ROOT", str(tmp_path))
    monkeypatch.setattr(research, "INDEX", str(tmp_path / "research.json"))
    data = research._load()
    data["hypotheses"].append({"id": "hyp-1", "question": "Does the app improve between sessions?",
                               "variable": "session usage log", "metric": "user experience",
                               "status": "draft", "outcome": None})
    research._save(data)
    return research


def ok(evidence_id):
    return True, f"verified {evidence_id}", "ab" * 32


def test_outcome_refused_until_kind_declared(lab):
    with pytest.raises(ValueError, match="does not say what kind of experiment"):
        lab.record_outcome("hyp-1", "refuted", "evo-20261007T055730Z-d38afd", ok)


def test_hyp1_mismatch_rejected(lab):
    lab.set_evidence_kind("hyp-1", "run")
    with pytest.raises(ValueError, match="HYPOTHESIS_EXPERIMENT_MISMATCH"):
        lab.record_outcome("hyp-1", "refuted", "evo-20261007T055730Z-d38afd", ok)
    assert lab.hypotheses()[0]["outcome"] is None


def test_matching_kind_recorded(lab):
    lab.set_evidence_kind("hyp-1", "evo")
    h = lab.record_outcome("hyp-1", "refuted", "evo-20261007T055730Z-d38afd", ok)
    assert h["status"] == "refuted"


def test_kind_fixed_once_decided(lab):
    lab.set_evidence_kind("hyp-1", "evo")
    lab.record_outcome("hyp-1", "refuted", "evo-1", ok)
    with pytest.raises(ValueError, match="already decided"):
        lab.set_evidence_kind("hyp-1", "run")


def test_evidence_kind_prefixes():
    assert research.evidence_kind("trial-bench-20261001") == "trial-bench"
    assert research.evidence_kind("bench-20261001") == "bench"
    assert research.evidence_kind("run-7") == "run"
    assert research.evidence_kind("nonsense") is None


def test_hints_only_offer_matching_hypotheses(lab):
    assert lab.open_hypotheses_for("evo-1") == []
    lab.set_evidence_kind("hyp-1", "evo")
    assert [h["id"] for h in lab.open_hypotheses_for("evo-1")] == ["hyp-1"]
    assert lab.open_hypotheses_for("run-1") == []
