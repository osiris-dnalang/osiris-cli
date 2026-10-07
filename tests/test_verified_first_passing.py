"""Tests for verified_first_passing in verify_loop.py."""

import pytest
from verify_loop import first_passing, verified_first_passing
from osiris_governance.candidate_router import EvaluatorConfinementGuard


def test_verified_first_passing_blocks_confinement_breach():
    guard = EvaluatorConfinementGuard()

    # Generator proposes a malicious patch attempting to touch tests
    def generate(feedback):
        return {"patch": "--- tests/test_core.py\n+++ tests/test_core.py\n@@ -1 +1 @@\n-assert False\n+assert True\n"}, "malicious patch"

    def hermetic_verify(candidate):
        return True, "should not be reached"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=2, confinement_guard=guard)
    assert winner is None
    assert len(attempts) == 2
    assert "EVALUATOR_CONFINEMENT_BREACH" in attempts[0]["reason"]


def test_verified_first_passing_blocks_forbidden_ast():
    guard = EvaluatorConfinementGuard()

    def generate(feedback):
        return {"source": "def foo(): eval('1+1')"}, "eval call"

    def hermetic_verify(candidate):
        return True, "should not be reached"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=1, confinement_guard=guard)
    assert winner is None
    assert "FORBIDDEN_AST_PRIMITIVE" in attempts[0]["reason"]


def test_verified_first_passing_success():
    guard = EvaluatorConfinementGuard()

    def generate(feedback):
        return {"source": "def foo(): return 42"}, "clean code"

    def hermetic_verify(candidate):
        return True, "all reference tests passed"

    winner, attempts = verified_first_passing(generate, hermetic_verify, k=2, confinement_guard=guard)
    assert winner is not None
    assert attempts[0]["ok"] is True
