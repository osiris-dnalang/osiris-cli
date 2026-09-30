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
