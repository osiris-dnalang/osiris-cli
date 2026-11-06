"""
Unit and integration tests for OSIRIS Automated Adversarial Falsification Engine.
Verifies SYS-024 claims firewall enforcement, null-hypothesis testing batteries,
fail-closed quarantine, and RFC 8785 canonical receipt generation.
"""

import math
from pathlib import Path
import pytest

from osiris_cli.dnalang.falsification import (
    AdversarialFalsificationEngine,
    FalsificationReceipt,
    NullControlResult,
)

JOURNAL_PATH = Path(__file__).resolve().parents[1] / "provenance" / "osiris_operational_journal.jsonl"


def test_adversarial_falsification_passes_valid_candidate():
    """Verify that a candidate demonstrating genuine advantage passes all null controls."""
    engine = AdversarialFalsificationEngine(journal_path=JOURNAL_PATH)

    candidate_source = """
    organism OsirisBipartiteStaggered {
        sublattice_a { rz(0.785) 0; delay(16.0); rz(-0.785) 0; }
        sublattice_b { delay(8.0); rz(0.785) 1; delay(8.0); rz(-0.785) 1; }
    }
    """

    # Candidate with high survival exceeding textbook DD (0.8342) and bare idle (0.5945)
    candidate_metric = 0.8998

    receipt = engine.evaluate_candidate(
        candidate_id="cand_advantage_001",
        candidate_source=candidate_source,
        candidate_metric=candidate_metric,
    )

    assert receipt.all_controls_passed is True
    assert receipt.status == "READY_FOR_HUMAN_AUTH"
    assert receipt.quarantine_notice is None
    assert len(receipt.receipt_digest) == 64
    assert len(receipt.controls_executed) == 4

    # Verify each control passed
    controls_by_kind = {c["kind"]: c for c in receipt.controls_executed}
    assert controls_by_kind["SIGN_FLIPPED_PHASE_NULL"]["passed"] is True
    assert controls_by_kind["TIMING_SHUFFLE_CROSSTALK_NULL"]["passed"] is True
    assert controls_by_kind["NOISELESS_UNITARY_SANITY_CHECK"]["passed"] is True
    assert controls_by_kind["HARDWARE_BASELINE_CONTRAST"]["passed"] is True


def test_adversarial_falsification_quarantines_sign_flip_artifact():
    """Verify that candidate whose advantage persists under sign-flipped control is quarantined under SYS-024."""
    engine = AdversarialFalsificationEngine(journal_path=JOURNAL_PATH)

    candidate_source = """
    organism SpuriousAsymmetry {
        gate { rz(1.57) 0; }
    }
    """
    candidate_metric = 0.88

    # Custom evaluation where sign-flipped mutant yields IDENTICAL score (uncalibrated hardware bias)
    def biased_eval_fn(source: str) -> float:
        return 0.88

    receipt = engine.evaluate_candidate(
        candidate_id="cand_spurious_002",
        candidate_source=candidate_source,
        candidate_metric=candidate_metric,
        eval_fn=biased_eval_fn,
        min_advantage_over_null=0.02,
    )

    assert receipt.all_controls_passed is False
    assert receipt.status == "QUARANTINED_MODEL_PROPOSED"
    assert receipt.quarantine_notice is not None
    assert "SYS-024 EPISTEMIC QUARANTINE NOTICE" in receipt.quarantine_notice
    assert "SIGN_FLIPPED_PHASE_NULL" in receipt.quarantine_notice


def test_adversarial_falsification_quarantines_timing_shuffle_artifact():
    """Verify that candidate whose advantage persists under timing shuffle is quarantined."""
    engine = AdversarialFalsificationEngine(journal_path=JOURNAL_PATH)

    candidate_source = """
    organism ShuffledIdleDrift {
        gate { h 0; cx 0, 1; delay 10; rz(0.5) 0; }
    }
    """
    candidate_metric = 0.87

    # Sign flip passes, but timing shuffle matches candidate
    def shuffle_neutral_eval_fn(source: str) -> float:
        if "SIGN_FLIPPED" in source or "-0.5" in source:
            return 0.70  # Degrades under sign flip
        return 0.87  # Does not degrade under timing shuffle (idle drift artifact)

    receipt = engine.evaluate_candidate(
        candidate_id="cand_idle_drift_003",
        candidate_source=candidate_source,
        candidate_metric=candidate_metric,
        eval_fn=shuffle_neutral_eval_fn,
        min_advantage_over_null=0.02,
    )

    assert receipt.all_controls_passed is False
    assert receipt.status == "QUARANTINED_MODEL_PROPOSED"
    assert "TIMING_SHUFFLE_CROSSTALK_NULL" in receipt.quarantine_notice


def test_adversarial_falsification_quarantines_sub_hardware_baseline():
    """Verify that candidate trailing textbook hardware baseline is quarantined."""
    engine = AdversarialFalsificationEngine(journal_path=JOURNAL_PATH)

    candidate_source = "organism SubBaseline { quantum_state { h 0; } }"
    # Trails textbook simultaneous DD (0.8342)
    candidate_metric = 0.7500

    receipt = engine.evaluate_candidate(
        candidate_id="cand_sub_baseline_004",
        candidate_source=candidate_source,
        candidate_metric=candidate_metric,
    )

    assert receipt.all_controls_passed is False
    assert receipt.status == "QUARANTINED_MODEL_PROPOSED"
    assert "HARDWARE_BASELINE_CONTRAST" in receipt.quarantine_notice


def test_adversarial_falsification_quarantines_nan_and_inf():
    """Verify that NaN or infinite metrics fail noiseless unitary sanity check and get quarantined."""
    engine = AdversarialFalsificationEngine(journal_path=JOURNAL_PATH)

    candidate_source = "organism Divergent { state { } }"

    for bad_metric in (math.nan, math.inf, -1.0, 1.5):
        receipt = engine.evaluate_candidate(
            candidate_id="cand_divergent",
            candidate_source=candidate_source,
            candidate_metric=bad_metric,
        )
        assert receipt.all_controls_passed is False
        assert receipt.status == "QUARANTINED_MODEL_PROPOSED"


def test_falsification_receipt_canonical_digest_determinism():
    """Verify RFC 8785 canonical digest integrity on FalsificationReceipt."""
    engine = AdversarialFalsificationEngine(journal_path=JOURNAL_PATH)

    candidate_source = "organism CanonicalCheck { h 0; cx 0, 1; }"
    receipt1 = engine.evaluate_candidate("cand_canon_1", candidate_source, 0.8998)
    receipt2 = engine.evaluate_candidate("cand_canon_1", candidate_source, 0.8998)

    assert receipt1.receipt_digest == receipt2.receipt_digest

    # Tampering with status changes digest
    tampered = FalsificationReceipt(
        candidate_id=receipt1.candidate_id,
        candidate_digest=receipt1.candidate_digest,
        baseline_journal_hash=receipt1.baseline_journal_hash,
        controls_executed=receipt1.controls_executed,
        all_controls_passed=receipt1.all_controls_passed,
        status="QUARANTINED_MODEL_PROPOSED",  # modified
        quarantine_notice=receipt1.quarantine_notice,
    )
    assert tampered.receipt_digest != receipt1.receipt_digest
