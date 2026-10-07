"""Tests for verified_first_passing in verify_loop.py."""

import pytest
from verify_loop import first_passing, verified_first_passing, CandidateArtifact
from osiris_governance.candidate_router import EvaluatorConfinementGuard


def test_missing_confinement_guard_raises_before_generation():
    """Confinement guard cannot be omitted or None."""
    def generate(fb):
        raise AssertionError("Generator should not be reached when guard is None")

    def hermetic_verify(c):
        return True, "ok"

    with pytest.raises(ValueError, match="CONFINEMENT_GUARD_REQUIRED"):
        verified_first_passing(generate, hermetic_verify, k=1, confinement_guard=None)


def test_candidate_schema_violation_rejected_fail_closed():
    """Non-CandidateArtifact candidates are rejected fail-closed."""
    guard = EvaluatorConfinementGuard()

    # Generator returns legacy raw dict instead of CandidateArtifact
    def generate(fb):
        return {"code": "def foo(): pass"}, "raw dict"

    def hermetic_verify(c):
        return True, "should not be reached"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=1, confinement_guard=guard)
    assert winner is None
    assert len(attempts) == 1
    assert "SCHEMA_VIOLATION" in attempts[0]["reason"]


def test_empty_or_malformed_artifact_fails_closed():
    """Empty payload in artifact is rejected as malformed."""
    guard = EvaluatorConfinementGuard()

    def generate(fb):
        return CandidateArtifact("c1", "source", "   "), "empty"

    def hermetic_verify(c):
        return True, "should not be reached"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=1, confinement_guard=guard)
    assert winner is None
    assert "MALFORMED_ARTIFACT" in attempts[0]["reason"]


def test_auditor_exception_fails_closed():
    """Exceptions raised by the confinement auditor fail closed."""
    class BrokenGuard:
        def audit_patch_paths(self, patch, candidate_id=None):
            raise RuntimeError("Auditor segmentation fault")
        def audit_ast_safety(self, src, candidate_id=None):
            raise RuntimeError("AST parser bug")

    def generate(fb):
        return CandidateArtifact("c1", "patch", "--- a/foo\n+++ b/foo\n"), "patch"

    def hermetic_verify(c):
        return True, "should not be reached"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=1, confinement_guard=BrokenGuard())
    assert winner is None
    assert "AUDITOR_EXCEPTION" in attempts[0]["reason"]


def test_receipt_candidate_digest_mismatch_rejected():
    """Verifier receipt bound to a different candidate digest is rejected."""
    guard = EvaluatorConfinementGuard()

    candidate = CandidateArtifact("c1", "source", "def foo(): return 1")

    def generate(fb):
        return candidate, "cand"

    # Verifier returns a receipt with a mismatched candidate digest (replay attack)
    def hermetic_verify(c):
        receipt = {
            "evaluator_id": "ref_eval",
            "candidate_digest": "sha256:different_candidate_digest_0000000000000000",
            "status": "PASS",
        }
        return True, "tests passed", receipt

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=1, confinement_guard=guard)
    assert winner is None
    assert "RECEIPT_BINDING_MISMATCH" in attempts[0]["reason"]


def test_verified_first_passing_blocks_confinement_breach():
    guard = EvaluatorConfinementGuard()

    def generate(feedback):
        patch = "--- tests/test_core.py\n+++ tests/test_core.py\n@@ -1 +1 @@\n-assert False\n+assert True\n"
        return CandidateArtifact("c_bad", "patch", patch), "malicious patch"

    def hermetic_verify(candidate):
        return True, "should not be reached"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=2, confinement_guard=guard)
    assert winner is None
    assert len(attempts) == 2
    assert "EVALUATOR_CONFINEMENT_BREACH" in attempts[0]["reason"]


def test_verified_first_passing_blocks_forbidden_ast():
    guard = EvaluatorConfinementGuard()

    def generate(feedback):
        return CandidateArtifact("c_ast", "source", "def foo(): eval('1+1')"), "eval call"

    def hermetic_verify(candidate):
        return True, "should not be reached"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=1, confinement_guard=guard)
    assert winner is None
    assert "FORBIDDEN_AST_PRIMITIVE" in attempts[0]["reason"]


def test_verified_first_passing_success_with_receipt():
    guard = EvaluatorConfinementGuard()

    candidate = CandidateArtifact("c_ok", "source", "def foo(): return 42")

    def generate(feedback):
        return candidate, "clean code"

    def hermetic_verify(c):
        receipt = {
            "evaluator_id": "reference_evaluator",
            "candidate_digest": c.compute_digest(),
            "status": "PASS",
        }
        return True, "all reference tests passed", receipt

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=2, confinement_guard=guard)
    assert winner is not None
    assert attempts[0]["ok"] is True
    assert winner.candidate_id == "c_ok"
    assert winner.compute_digest() == candidate.compute_digest()


def test_pass_without_receipt_rejected():
    guard = EvaluatorConfinementGuard()
    cand = CandidateArtifact("c-nr", "source", "def f():\n    return 1\n")
    for out in [(True, "ok"), (True, "ok", {}), (True, "ok", {"evaluator": "x"}), (True, "ok", "not-a-dict")]:
        winner, attempts = verified_first_passing(lambda fb: (cand, ""), lambda c, out=out: out, k=1, confinement_guard=guard)
        assert winner is None
        assert attempts[-1]["reason"].startswith("[RECEIPT_MISSING]")
