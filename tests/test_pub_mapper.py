"""
Unit and integration tests for OSIRIS IBM Circuit-to-Publication Mapper (IBMPubMapper).
Verifies epistemic 1-to-1 spec-PUB mapping, statistical accuracy against Heron r2 ground truth,
tamper rejection, fidelity metrics (F_state, F_gate), and Merkle ledger anchoring.
"""

import json
from pathlib import Path
import numpy as np
import pytest

from osiris_cli.quantum.pub_mapper import (
    CircuitSpec,
    ConditionSummary,
    ExperimentMappingReceipt,
    IBMPubMapper,
    OperationalMerkleLedger,
    PubResult,
)

EXPERIMENT_DIR = Path(__file__).resolve().parents[1] / "experiments" / "osiris_advantage_marrakesh"
META_PATH = EXPERIMENT_DIR / "dau0q3qhcrkc73durtgg.meta.json"
COUNTS_PATH = EXPERIMENT_DIR / "dau0q3qhcrkc73durtgg.counts.json"
ANALYSIS_PATH = EXPERIMENT_DIR / "dau0q3qhcrkc73durtgg.analysis.json"


def test_real_heron_mapping_and_statistical_replication():
    """Verify that IBMPubMapper accurately replicates the Marrakesh hardware analysis."""
    assert META_PATH.exists()
    assert COUNTS_PATH.exists()
    assert ANALYSIS_PATH.exists()

    receipt = IBMPubMapper.map_payload(META_PATH, COUNTS_PATH)

    assert receipt.job_id == "dau0q3qhcrkc73durtgg"
    assert receipt.backend == "ibm_marrakesh"
    assert receipt.total_circuits == 20
    assert receipt.total_shots == 20 * 512
    assert len(receipt.summaries) == 10

    # Load ground truth analysis
    with open(ANALYSIS_PATH, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    # Map by (name, T_us)
    gt_map = {(row["name"], row["T_us"]): row for row in ground_truth}

    for summary in receipt.summaries:
        key = (summary["name"], summary["t_us"])
        assert key in gt_map, f"Condition {key} not found in ground truth"
        gt = gt_map[key]

        np.testing.assert_allclose(
            summary["mean_survival"],
            gt["mean_survival"],
            atol=1e-7,
            err_msg=f"Mismatch in mean_survival for {key}",
        )
        np.testing.assert_allclose(
            summary["sem"],
            gt["sem"],
            atol=1e-7,
            err_msg=f"Mismatch in sem for {key}",
        )
        np.testing.assert_allclose(
            summary["ci_95_lo"],
            gt["ci_95_lo"],
            atol=1e-7,
            err_msg=f"Mismatch in ci_95_lo for {key}",
        )
        np.testing.assert_allclose(
            summary["ci_95_hi"],
            gt["ci_95_hi"],
            atol=1e-7,
            err_msg=f"Mismatch in ci_95_hi for {key}",
        )
        np.testing.assert_allclose(
            summary["gamma_us_inv"],
            gt["gamma_us_inv"],
            atol=1e-6,
            err_msg=f"Mismatch in gamma_us_inv for {key}",
        )
        np.testing.assert_allclose(
            summary["qubit_means"],
            gt["qubit_means"],
            atol=1e-7,
            err_msg=f"Mismatch in qubit_means for {key}",
        )
        assert 0.0 <= summary["f_state"] <= 1.0
        assert 0.0 <= summary["f_gate"] <= 1.0


def test_hypothesis_adjudication_h1_confirmed():
    """Verify H1 advantage confirmation on real IBM Heron dataset."""
    receipt = IBMPubMapper.map_payload(META_PATH, COUNTS_PATH)
    verdict = receipt.hypothesis_verdict

    assert verdict["verdict"] == "H1_CONFIRMED"
    assert verdict["best_staggered_condition"] in ("xy4x2_stag", "xy8_stag")
    assert verdict["best_staggered_condition"] == "xy8_stag"
    assert verdict["criteria"]["criterion_1_idle_ge_0_15"]["passed"] is True
    assert verdict["criteria"]["criterion_2_simul_ge_0_02"]["passed"] is True
    assert verdict["criteria"]["criterion_3_ci_non_overlapping"]["passed"] is True

    # Delta vs idle should exceed 0.30 (threshold is 0.15)
    assert verdict["metrics"]["delta_vs_bare_idle"] > 0.30
    # Delta vs textbook simultaneous should exceed 0.06 (threshold is 0.02)
    assert verdict["metrics"]["delta_vs_textbook_simultaneous"] > 0.06
    # Best staggered gate fidelity should exceed simultaneous
    assert verdict["metrics"]["best_staggered_f_gate"] > verdict["metrics"]["textbook_simultaneous_f_gate"]


def test_tamper_rejection_length_mismatch():
    """Verify fail-closed rejection when PUB results count does not match pre-registered specs."""
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    with open(COUNTS_PATH, "r", encoding="utf-8") as f:
        counts = json.load(f)

    # Truncate one PUB result
    with pytest.raises(ValueError, match="Spec/PUB length mismatch"):
        IBMPubMapper.map_payload(meta, counts[:-1])


def test_tamper_rejection_invalid_hashes():
    """Verify rejection when manifest_sha256 or calibration_hash is invalid."""
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    with open(COUNTS_PATH, "r", encoding="utf-8") as f:
        counts = json.load(f)

    # Bad manifest hash
    bad_meta = dict(meta)
    bad_meta["manifest_sha256"] = "invalid_hash"
    with pytest.raises(ValueError, match="Invalid or missing manifest_sha256"):
        IBMPubMapper.map_payload(bad_meta, counts)

    # Bad calibration hash
    bad_meta2 = dict(meta)
    bad_meta2["calibration_hash"] = "short"
    with pytest.raises(ValueError, match="Invalid or missing calibration_hash"):
        IBMPubMapper.map_payload(bad_meta2, counts)


def test_receipt_digest_determinism_and_sensitivity():
    """Verify that RFC 8785 receipt digest is deterministic and sensitive to any modification."""
    receipt1 = IBMPubMapper.map_payload(META_PATH, COUNTS_PATH)
    receipt2 = IBMPubMapper.map_payload(META_PATH, COUNTS_PATH)

    assert receipt1.receipt_digest == receipt2.receipt_digest
    assert len(receipt1.receipt_digest) == 64

    # Tampering with a summary must change digest
    tampered_summaries = list(receipt1.summaries)
    tampered_summaries[0] = dict(tampered_summaries[0], mean_survival=0.5)
    receipt_tampered = ExperimentMappingReceipt(
        job_id=receipt1.job_id,
        backend=receipt1.backend,
        manifest_sha256=receipt1.manifest_sha256,
        calibration_hash=receipt1.calibration_hash,
        chain=receipt1.chain,
        total_circuits=receipt1.total_circuits,
        total_shots=receipt1.total_shots,
        conditions=receipt1.conditions,
        t_list_us=receipt1.t_list_us,
        summaries=tampered_summaries,
        hypothesis_verdict=receipt1.hypothesis_verdict,
    )
    assert receipt_tampered.receipt_digest != receipt1.receipt_digest


def test_hypothesis_adjudication_null_cases():
    """Verify H0_SUPPORTED adjudication when advantage criteria are not met."""
    summaries_h0 = [
        {
            "name": "none",
            "t_us": 32.0,
            "mean_survival": 0.80,
            "ci_95_lo": 0.79,
            "ci_95_hi": 0.81,
            "f_gate": 0.94,
        },
        {
            "name": "xy4x2",
            "t_us": 32.0,
            "mean_survival": 0.85,
            "ci_95_lo": 0.84,
            "ci_95_hi": 0.86,
            "f_gate": 0.96,
        },
        {
            "name": "xy4x2_stag",
            "t_us": 32.0,
            "mean_survival": 0.855,  # Only +0.005 advantage over xy4x2 (< 0.02)
            "ci_95_lo": 0.845,
            "ci_95_hi": 0.865,
            "f_gate": 0.961,
        },
    ]
    verdict = IBMPubMapper.evaluate_hypotheses(summaries_h0)
    assert verdict["verdict"] == "H0_SUPPORTED"
    assert verdict["criteria"]["criterion_1_idle_ge_0_15"]["passed"] is False
    assert verdict["criteria"]["criterion_2_simul_ge_0_02"]["passed"] is False


def test_merkle_operational_journal_locking(tmp_path):
    """Verify that mapped receipts can be locked to an append-only Merkle journal with unbroken verification."""
    receipt = IBMPubMapper.map_payload(META_PATH, COUNTS_PATH)
    test_journal = tmp_path / "test_operational_journal.jsonl"

    entry1 = IBMPubMapper.lock_to_journal(receipt, journal_path=test_journal, grant_id="GRANT-IBM-MAPPER-001")
    assert entry1["prev"] == "0" * 64
    assert entry1["grant_id"] == "GRANT-IBM-MAPPER-001"
    assert entry1["receipt_digest"] == receipt.receipt_digest

    ledger = OperationalMerkleLedger(test_journal)
    assert ledger.verify() is None

    # Append second entry
    entry2 = ledger.append("verification_check", {"checker": "osiris_harness", "status": "CONFIRMED"})
    assert entry2["prev"] == entry1["hash"]
    assert ledger.verify() is None
