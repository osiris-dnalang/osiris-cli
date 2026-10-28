"""The promotion gate: eligible only when QUALITY, STABILITY, INTEGRITY and SPEAKING all pass, it fails
closed without operator-registered criteria or on any non-finite number, and it writes nothing."""

import json
import math
from dataclasses import replace
from types import MappingProxyType

import pytest

from osiris_cli.journal import OperationalMerkleLedger
from osiris_cli.living import GATE_WINDOW, SPEAK_BPB
from osiris_cli.promotion_gate import (
    Predicate,
    PromotionCriteria,
    PromotionEvidence,
    evaluate_promotion,
)

# Test fixtures only. These are not registered thresholds; the operator registers the real ones.
CRITERIA = PromotionCriteria(alpha=0.05, w2_max=0.10, entropy_floor_bits=3.0, registration_ref="tests/fixture")

OPEN_GATE = {"open": True, "n": GATE_WINDOW, "core_bpb": 1.80, "unigram_bpb": 4.40, "stale": 0}
# The live core's state on 2026-10-27 (living.py, scorer 2 notes): 2.90 bits/byte on 30 held-out replies.
CLOSED_GATE = {"open": False, "n": GATE_WINDOW, "core_bpb": 2.90, "unigram_bpb": 4.40, "stale": 0}


def _evidence(**changes):
    base = PromotionEvidence(
        candidate_id="cand-001",
        candidate_digest="d" * 64,
        delta_q=0.012,
        p_value=0.003,
        w2_drift=0.04,
        entropy_bits=4.1,
        ast_violations=0,
        speaking_gate=dict(OPEN_GATE),
    )
    return replace(base, **changes)


@pytest.fixture
def journal(tmp_path):
    ledger = OperationalMerkleLedger(tmp_path / "journal.jsonl")
    ledger.append_event("evaluation.recorded", "NODE_BETA_WORKSTATION", {"candidate_id": "cand-001"})
    return ledger


def _result(verdict, predicate):
    return next(r for r in verdict.results if r.predicate == predicate)


def test_all_four_predicates_make_a_candidate_eligible(journal):
    verdict = evaluate_promotion(_evidence(), CRITERIA, journal)
    assert verdict.eligible
    assert [r.predicate for r in verdict.results] == list(Predicate)
    assert all(r.passed for r in verdict.results)
    assert verdict.registration_ref == "tests/fixture"


def test_the_gate_writes_nothing(journal):
    before = journal.path.read_bytes()
    evaluate_promotion(_evidence(), CRITERIA, journal)
    evaluate_promotion(_evidence(delta_q=-1.0), None, journal)
    assert journal.path.read_bytes() == before


def test_without_registered_criteria_quality_and_stability_fail(journal):
    verdict = evaluate_promotion(_evidence(), None, journal)
    assert not verdict.eligible
    for predicate in (Predicate.QUALITY, Predicate.STABILITY):
        result = _result(verdict, predicate)
        assert not result.passed and "not registered" in result.detail
    assert _result(verdict, Predicate.INTEGRITY).passed
    assert _result(verdict, Predicate.SPEAKING).passed
    assert verdict.registration_ref is None


@pytest.mark.parametrize("changes", [
    {"registration_ref": ""},
    {"alpha": 0.0},
    {"alpha": 1.0},
    {"alpha": math.nan},
    {"w2_max": -0.1},
    {"w2_max": math.inf},
    {"entropy_floor_bits": math.nan},
])
def test_malformed_criteria_fail_closed(journal, changes):
    verdict = evaluate_promotion(_evidence(), replace(CRITERIA, **changes), journal)
    assert not verdict.eligible
    assert not _result(verdict, Predicate.QUALITY).passed
    assert not _result(verdict, Predicate.STABILITY).passed


@pytest.mark.parametrize("changes", [
    {"delta_q": 0.0},
    {"delta_q": -0.01},
    {"delta_q": math.nan},
    {"p_value": 0.05},          # p must be strictly below alpha
    {"p_value": 0.2},
    {"p_value": math.nan},
    {"p_value": 1.5},
])
def test_quality_needs_a_positive_significant_delta(journal, changes):
    verdict = evaluate_promotion(_evidence(**changes), CRITERIA, journal)
    assert not verdict.eligible
    assert not _result(verdict, Predicate.QUALITY).passed
    assert _result(verdict, Predicate.STABILITY).passed


@pytest.mark.parametrize("changes, passed", [
    ({"w2_drift": 0.10}, True),          # at the bound
    ({"w2_drift": 0.11}, False),
    ({"w2_drift": -0.01}, False),
    ({"w2_drift": math.nan}, False),
    ({"entropy_bits": 3.0}, True),       # at the floor
    ({"entropy_bits": 2.9}, False),
    ({"entropy_bits": math.inf}, False),
])
def test_stability_bounds_drift_and_entropy(journal, changes, passed):
    verdict = evaluate_promotion(_evidence(**changes), CRITERIA, journal)
    assert _result(verdict, Predicate.STABILITY).passed is passed
    assert verdict.eligible is passed


@pytest.mark.parametrize("violations", [1, -1, True, None])
def test_integrity_needs_zero_ast_violations(journal, violations):
    verdict = evaluate_promotion(_evidence(ast_violations=violations), CRITERIA, journal)
    assert not verdict.eligible
    assert "AST firewall" in _result(verdict, Predicate.INTEGRITY).detail


def test_integrity_needs_an_intact_journal(journal):
    entries = [json.loads(line) for line in journal.path.read_text(encoding="utf-8").splitlines()]
    entries[0]["payload"]["candidate_id"] = "cand-999"
    journal.path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")

    verdict = evaluate_promotion(_evidence(), CRITERIA, journal)
    assert not verdict.eligible
    assert "hash mismatch" in _result(verdict, Predicate.INTEGRITY).detail


@pytest.mark.parametrize("gate", [
    CLOSED_GATE,
    {},
    {**OPEN_GATE, "n": GATE_WINDOW - 1},
    {**OPEN_GATE, "core_bpb": SPEAK_BPB + 0.01},
    {**OPEN_GATE, "core_bpb": math.nan},
    {**OPEN_GATE, "core_bpb": 1.8, "unigram_bpb": 1.8},
    {**OPEN_GATE, "unigram_bpb": None},
])
def test_speaking_gate_must_be_open_on_its_own_numbers(journal, gate):
    verdict = evaluate_promotion(_evidence(speaking_gate=gate), CRITERIA, journal)
    assert not verdict.eligible
    assert not _result(verdict, Predicate.SPEAKING).passed


def test_speaking_gate_opens_at_speak_bpb(journal):
    gate = {**OPEN_GATE, "core_bpb": SPEAK_BPB}
    assert evaluate_promotion(_evidence(speaking_gate=gate), CRITERIA, journal).eligible


def test_verdict_is_bound_to_exactly_what_it_judged(journal):
    verdict = evaluate_promotion(_evidence(), CRITERIA, journal)
    again = evaluate_promotion(_evidence(speaking_gate=MappingProxyType(dict(OPEN_GATE))), CRITERIA, journal)
    assert again.evidence_sha256 == verdict.evidence_sha256

    for evidence, criteria in (
        (_evidence(p_value=0.004), CRITERIA),
        (_evidence(candidate_digest="e" * 64), CRITERIA),
        (_evidence(speaking_gate={**OPEN_GATE, "n": GATE_WINDOW + 1}), CRITERIA),
        (_evidence(), replace(CRITERIA, registration_ref="docs/PRE_REGISTRATION.md@abc123")),
    ):
        assert evaluate_promotion(evidence, criteria, journal).evidence_sha256 != verdict.evidence_sha256


def test_a_verdict_can_be_recorded_in_the_journal(journal):
    verdict = evaluate_promotion(_evidence(), CRITERIA, journal)
    entry = journal.append_event("promotion.evaluated", "NODE_BETA_WORKSTATION", verdict.to_dict())
    assert entry["payload"]["eligible"] is True
    assert entry["payload"]["evidence_sha256"] == verdict.evidence_sha256
    assert journal.verify() is None
