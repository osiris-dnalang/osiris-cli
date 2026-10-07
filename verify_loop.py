#!/usr/bin/env python3
"""
verify_loop.py -- generate-and-verify: up to k candidates, keep the first
that passes, feeding each failure back into the next attempt.

Used by /sprint execute (verifier = the sandbox running the candidate's own
test) and by osiris_bench.py (same verifier, so the benchmark measures the
loop OSIRIS actually runs; the hidden acceptance test only scores the result).
"""

FEEDBACK_CHARS = 1500


def feedback_block(reason: str) -> str:
    """Appended to the prompt for attempts 2..k."""
    tail = (reason or "").strip()[-FEEDBACK_CHARS:]
    return (f"\n\nA previous candidate FAILED verification. The real output was:\n{tail}\n"
            "Return a corrected candidate in the same JSON format.")


def first_passing(generate, verify, k: int, on_attempt=None):
    """generate(feedback: str | None) -> (candidate | None, note) and
    verify(candidate) -> (ok: bool, reason: str). Returns (winner | None,
    attempts) where attempts is a list of {"n", "ok", "reason", "candidate"}.
    on_attempt(attempt) is called after each attempt, for progress output."""
    if k < 1:
        raise ValueError("k must be >= 1")
    attempts = []
    feedback = None
    for n in range(1, k + 1):
        candidate, note = generate(feedback)
        if candidate is None:
            ok, reason = False, note
        else:
            ok, reason = verify(candidate)
        attempt = {"n": n, "ok": ok, "reason": reason, "candidate": candidate}
        attempts.append(attempt)
        if on_attempt:
            on_attempt(attempt)
        if ok:
            return candidate, attempts
        feedback = reason
    return None, attempts


def verified_first_passing(
    generate,
    hermetic_verify,
    k: int,
    confinement_guard=None,
    on_attempt=None,
):
    """Adjudicated generate-and-verify: enforces that evaluation runs outside
    the candidate's scope, checks confinement, and uses hermetic reference tests.
    
    Prevents reward hacking and evaluator doctoring (DGM/METR/Devin failure 4).
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    attempts = []
    feedback = None
    for n in range(1, k + 1):
        candidate, note = generate(feedback)
        if candidate is None:
            ok, reason = False, note
        else:
            # 1. Pre-execution confinement check if guard provided
            if confinement_guard is not None:
                patch_str = candidate.get("patch") if isinstance(candidate, dict) else None
                source_str = candidate.get("source") if isinstance(candidate, dict) else str(candidate)
                if patch_str:
                    c_res = confinement_guard.audit_patch_paths(patch_str)
                    if not c_res.is_admissible:
                        ok, reason = False, f"[EVALUATOR_CONFINEMENT_BREACH] {c_res.message}"
                        attempts.append({"n": n, "ok": False, "reason": reason, "candidate": candidate})
                        if on_attempt:
                            on_attempt(attempts[-1])
                        feedback = reason
                        continue
                if source_str:
                    a_res = confinement_guard.audit_ast_safety(source_str)
                    if not a_res.is_admissible:
                        ok, reason = False, f"[FORBIDDEN_AST_PRIMITIVE] {a_res.message}"
                        attempts.append({"n": n, "ok": False, "reason": reason, "candidate": candidate})
                        if on_attempt:
                            on_attempt(attempts[-1])
                        feedback = reason
                        continue

            # 2. Run hermetic verifier (reference tests, not candidate's own tests)
            ok, reason = hermetic_verify(candidate)

        attempt = {"n": n, "ok": ok, "reason": reason, "candidate": candidate}
        attempts.append(attempt)
        if on_attempt:
            on_attempt(attempt)
        if ok:
            return candidate, attempts
        feedback = reason
    return None, attempts
