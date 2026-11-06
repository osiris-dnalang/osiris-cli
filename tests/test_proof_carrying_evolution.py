"""
Unit and Integration Tests for Sprint 1: Proof-Carrying Evolution
================================================================
Verifies:
  1. Typed evaluation receipts with canonical RFC 8785 digest binding
  2. Hardened promotion policy (strict improvement, tie rejection, NaN/inf rejection)
  3. Hash-chained evidence and lineage ledger
  4. Parent-derived candidate mutation across successive generations
  5. Governed engine execution application upon valid authorization
"""

import math
import os
import tempfile
import pytest

from osiris_cli.dnalang import (
    CandidateEvolutionLoop,
    GenomeCandidate,
    EvaluationReceipt,
    PromotionPolicy,
)
from osiris_cli.orchestration.engine import GovernedAgentEngine
from osiris_cli.orchestration.schemas import ExecutionGrant
from osiris.compiler.dna_ir import QuantumCircuitIR

FIXTURE_LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "dnalang_ledger_v0_2_0.py")


def test_typed_evaluation_receipt_canonical_digest():
    """Verify EvaluationReceipt computes deterministic RFC 8785 SHA-256 digest."""
    receipt1 = EvaluationReceipt(
        candidate_id="cand_1",
        candidate_digest="a" * 64,
        parent_id=None,
        evaluator_id="eval_xeb",
        evaluator_version="1.0.0",
        metric_name="fidelity",
        fitness_score=0.885,
        uncertainty=0.012,
        passed=True,
        input_artifacts_hash="input_123",
        timestamp=1792112718.0,
    )
    receipt2 = EvaluationReceipt(
        candidate_id="cand_1",
        candidate_digest="a" * 64,
        parent_id=None,
        evaluator_id="eval_xeb",
        evaluator_version="1.0.0",
        metric_name="fidelity",
        fitness_score=0.885,
        uncertainty=0.012,
        passed=True,
        input_artifacts_hash="input_123",
        timestamp=1792112718.0,
    )

    assert len(receipt1.receipt_digest) == 64
    assert receipt1.receipt_digest == receipt2.receipt_digest


def test_promotion_policy_rejects_nan_and_inf():
    """Promotion must strictly reject NaN and Infinity values."""
    policy = PromotionPolicy(allow_ties=False)

    cand_nan = EvaluationReceipt(
        candidate_id="c_nan",
        candidate_digest="hash1",
        parent_id=None,
        evaluator_id="test",
        evaluator_version="1.0",
        metric_name="score",
        fitness_score=float("nan"),
    )
    ok, reason = policy.evaluate_promotion(cand_nan, None, expected_candidate_digest="hash1")
    assert ok is False
    assert "NaN" in reason

    cand_inf = EvaluationReceipt(
        candidate_id="c_inf",
        candidate_digest="hash1",
        parent_id=None,
        evaluator_id="test",
        evaluator_version="1.0",
        metric_name="score",
        fitness_score=float("inf"),
    )
    ok, reason = policy.evaluate_promotion(cand_inf, None, expected_candidate_digest="hash1")
    assert ok is False
    assert "Infinite" in reason


def test_promotion_policy_strictly_rejects_ties():
    """Equal fitness must not silently replace the champion."""
    policy = PromotionPolicy(min_improvement=0.001, allow_ties=False)

    champion = EvaluationReceipt(
        candidate_id="champ",
        candidate_digest="hash_champ",
        parent_id=None,
        evaluator_id="test",
        evaluator_version="1.0",
        metric_name="score",
        fitness_score=0.8500,
    )

    # Identical candidate score
    cand_tie = EvaluationReceipt(
        candidate_id="c_tie",
        candidate_digest="hash_cand",
        parent_id="champ",
        evaluator_id="test",
        evaluator_version="1.0",
        metric_name="score",
        fitness_score=0.8500,
    )
    ok, reason = policy.evaluate_promotion(cand_tie, champion, expected_candidate_digest="hash_cand")
    assert ok is False
    assert "tie" in reason.lower()

    # Sub-threshold candidate score (+0.0001 < 0.001 min_improvement)
    cand_sub = EvaluationReceipt(
        candidate_id="c_sub",
        candidate_digest="hash_cand",
        parent_id="champ",
        evaluator_id="test",
        evaluator_version="1.0",
        metric_name="score",
        fitness_score=0.8502,
    )
    ok, reason = policy.evaluate_promotion(cand_sub, champion, expected_candidate_digest="hash_cand")
    assert ok is False
    assert "below minimum threshold" in reason.lower()

    # Valid improvement
    cand_better = EvaluationReceipt(
        candidate_id="c_better",
        candidate_digest="hash_cand",
        parent_id="champ",
        evaluator_id="test",
        evaluator_version="1.0",
        metric_name="score",
        fitness_score=0.8900,
    )
    ok, reason = policy.evaluate_promotion(cand_better, champion, expected_candidate_digest="hash_cand")
    assert ok is True
    assert "improved" in reason.lower()


def test_promotion_policy_rejects_tampered_payload_digest():
    """SYS-021: Receipts bound to a different candidate hash must be rejected."""
    policy = PromotionPolicy(require_receipt_match=True)

    cand_tampered = EvaluationReceipt(
        candidate_id="c1",
        candidate_digest="legitimate_hash_a" + "0" * 47,
        parent_id=None,
        evaluator_id="test",
        evaluator_version="1.0",
        metric_name="score",
        fitness_score=0.90,
    )
    ok, reason = policy.evaluate_promotion(
        cand_tampered,
        None,
        expected_candidate_digest="modified_payload_b" + "0" * 46,
    )
    assert ok is False
    assert "SYS-021" in reason
    assert "mismatch" in reason.lower()


def test_parent_derived_mutation_and_hash_chained_ledger(tmp_path):
    """Verify successive generations derive from parents and commit to hash chain."""
    ledger_path = str(tmp_path / "chained_lineage.jsonl")
    loop = CandidateEvolutionLoop(lineage_ledger_path=ledger_path)

    # Generation 1 (Genesis)
    res1 = loop.run_cycle("Create Bell state", lambda ir: (True, 0.70))
    assert res1["promoted"] is True
    assert res1["generation"] == 1
    assert "organism Gen_1" in res1["candidate"].genome_source
    assert "h 0" in res1["candidate"].genome_source
    assert "cx 0, 1" in res1["candidate"].genome_source

    # Generation 2 (Parent-derived mutation: adds rz phase)
    res2 = loop.run_cycle("Add rz phase rotation to second qubit", lambda ir: (True, 0.85))
    assert res2["promoted"] is True
    assert res2["generation"] == 2
    assert "organism Gen_2" in res2["candidate"].genome_source
    assert "h 0" in res2["candidate"].genome_source
    assert "cx 0, 1" in res2["candidate"].genome_source
    assert "rz 1" in res2["candidate"].genome_source  # Derived from parent!

    # Generation 3 (Attempt tie - must reject)
    res3 = loop.run_cycle("Another tweak", lambda ir: (True, 0.85))
    assert res3["promoted"] is False
    assert res3["generation"] == 2  # Not incremented

    # Verify Ledger Hash-Chaining
    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 3
    import json
    b0 = json.loads(lines[0])
    b1 = json.loads(lines[1])
    b2 = json.loads(lines[2])

    assert b0["prev_ledger_hash"] == "GENESIS_ROOT"
    assert b1["prev_ledger_hash"] == b0["block_hash"]
    assert b2["prev_ledger_hash"] == b1["block_hash"]


def test_governed_engine_application_on_authorization(tmp_path, monkeypatch):
    """
    Verify GovernedAgentEngine applies changes to disk IF AND ONLY IF authorized.
    When unauthorized, application is skipped.
    """
    import genome_ledger as gl

    if not os.path.exists(gl.LEDGER_SRC):  # no dnalang-core: use the pinned ledger.py
        monkeypatch.setattr(gl, "LEDGER_SRC", FIXTURE_LEDGER)
        monkeypatch.setattr(gl, "_ledger_mod", None)
    # A ledger of its own: the default is the canonical ~/.osiris/genome_ledger.jsonl.
    engine = GovernedAgentEngine(ledger_file=str(tmp_path / "genome_ledger.jsonl"), allowed_paths=[str(tmp_path)])
    target = str(tmp_path / "sample_module.py")

    # 1. Run step without grant -> authorized=False, applied=False, file does not exist
    res_unauth = engine.run_sprint_step(
        goal="Implement add_values function",
        target_file=target,
        grant=None,
    )
    assert res_unauth["authorized"] is False
    assert res_unauth["applied"] is False
    assert not os.path.exists(target)

    # 2. Mint valid grant matching synthesized proposal
    proposal = res_unauth["proposal"]
    import time
    now = time.time()
    valid_grant = ExecutionGrant(
        grant_id="grant_test_001",
        payload_digest=proposal.payload_digest(),
        authorized_by="Devin Phillip Davis",
        authorized_at=now,
        expires_at=now + 300.0,
    )

    # 3. Run step with valid grant -> authorized=True, applied=True, file exists on disk
    res_auth = engine.run_sprint_step(
        goal="Implement add_values function",
        target_file=target,
        grant=valid_grant,
    )
    assert res_auth["authorized"] is True
    assert res_auth["applied"] is True
    assert os.path.exists(target)

    with open(target, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == proposal.module_code
