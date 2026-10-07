#!/usr/bin/env python3
"""
verify_loop.py -- generate-and-verify: up to k candidates, keep the first
that passes, feeding each failure back into the next attempt.

Used by /sprint execute (verifier = the sandbox running the candidate's own
test) and by osiris_bench.py (same verifier, so the benchmark measures the
loop OSIRIS actually runs; the hidden acceptance test only scores the result).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Callable, Dict, List, Literal, Mapping, Optional, Sequence, Tuple, Union

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


@dataclass(frozen=True)
class CandidateArtifact:
    """Strict schema for generated candidates."""
    candidate_id: str
    artifact_type: Literal["patch", "source", "module"]
    payload: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_digest(self) -> str:
        data = {
            "candidate_id": self.candidate_id,
            "artifact_type": self.artifact_type,
            "payload": self.payload,
        }
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def verified_first_passing(
    generate: Callable[[Optional[str]], Tuple[Optional[CandidateArtifact], str]],
    hermetic_verify: Callable[[CandidateArtifact], Union[Tuple[bool, str], Tuple[bool, str, Dict[str, Any]]]],
    k: int,
    confinement_guard: Any,
    evaluator_id: str = "reference_evaluator",
    policy_version: str = "OSIRIS-SPEC-VERIF-015",
    on_attempt: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[Optional[CandidateArtifact], List[Dict[str, Any]]]:
    """Adjudicated generate-and-verify: enforces that evaluation runs outside
    the candidate's scope, checks confinement, and uses hermetic reference tests.
    
    Prevents reward hacking and evaluator doctoring (DGM/METR/Devin failure 4).
    Enforces fail-closed contracts:
      1. Rejects missing confinement_guard before generating any candidate.
      2. Requires CandidateArtifact schema rather than arbitrary objects.
      3. Requires non-empty payload and audits patch/source/module paths and AST.
      4. Catches auditor exceptions fail-closed.
      5. Cryptographically verifies receipts bound to candidate_digest.
    """
    if confinement_guard is None:
        raise ValueError("CONFINEMENT_GUARD_REQUIRED: Confinement guard must be provided and cannot be None.")
    if k < 1:
        raise ValueError("k must be >= 1")

    attempts = []
    feedback = None

    for n in range(1, k + 1):
        candidate, note = generate(feedback)
        if candidate is None:
            ok, reason = False, note
        else:
            # 1. Enforce strict candidate schema
            if not isinstance(candidate, CandidateArtifact):
                ok, reason = False, f"[SCHEMA_VIOLATION] Candidate must be CandidateArtifact instance, got {type(candidate).__name__}"
                attempts.append({"n": n, "ok": False, "reason": reason, "candidate": None})
                if on_attempt:
                    on_attempt(attempts[-1])
                feedback = reason[:FEEDBACK_CHARS]
                continue

            # 2. Confinement Guard Screening (fail-closed)
            c_res = None
            try:
                if candidate.artifact_type == "patch":
                    if not candidate.payload.strip():
                        ok, reason = False, "[MALFORMED_ARTIFACT] Patch candidate contains empty payload"
                        attempts.append({"n": n, "ok": False, "reason": reason, "candidate": candidate})
                        if on_attempt:
                            on_attempt(attempts[-1])
                        feedback = reason[:FEEDBACK_CHARS]
                        continue
                    c_res = confinement_guard.audit_patch_paths(candidate.payload, candidate_id=candidate.candidate_id)
                elif candidate.artifact_type in ("source", "module"):
                    if not candidate.payload.strip():
                        ok, reason = False, "[MALFORMED_ARTIFACT] Source candidate contains empty payload"
                        attempts.append({"n": n, "ok": False, "reason": reason, "candidate": candidate})
                        if on_attempt:
                            on_attempt(attempts[-1])
                        feedback = reason[:FEEDBACK_CHARS]
                        continue
                    c_res = confinement_guard.audit_ast_safety(candidate.payload, candidate_id=candidate.candidate_id)
                else:
                    ok, reason = False, f"[UNSUPPORTED_ARTIFACT_TYPE] Artifact type '{candidate.artifact_type}' is unsupported"
                    attempts.append({"n": n, "ok": False, "reason": reason, "candidate": candidate})
                    if on_attempt:
                        on_attempt(attempts[-1])
                    feedback = reason[:FEEDBACK_CHARS]
                    continue
            except Exception as exc:
                ok, reason = False, f"[AUDITOR_EXCEPTION] Confinement auditor encountered error: {exc}"
                attempts.append({"n": n, "ok": False, "reason": reason, "candidate": candidate})
                if on_attempt:
                    on_attempt(attempts[-1])
                feedback = reason[:FEEDBACK_CHARS]
                continue

            if c_res is not None and not c_res.is_admissible:
                reason_tag = "EVALUATOR_CONFINEMENT_BREACH" if candidate.artifact_type == "patch" else "FORBIDDEN_AST_PRIMITIVE"
                ok, reason = False, f"[{reason_tag}] {c_res.message}"
                attempts.append({"n": n, "ok": False, "reason": reason, "candidate": candidate})
                if on_attempt:
                    on_attempt(attempts[-1])
                feedback = reason[:FEEDBACK_CHARS]
                continue

            # 3. Hermetic Verifier Execution
            verify_out = hermetic_verify(candidate)
            if isinstance(verify_out, tuple):
                ok = verify_out[0]
                reason = verify_out[1] if len(verify_out) > 1 else ""
                receipt = verify_out[2] if len(verify_out) > 2 else {}
            else:
                ok, reason, receipt = False, "[INVALID_VERIFIER_OUTPUT] Verifier must return a tuple", {}

            # 4. Receipt Binding Check
            if ok and isinstance(receipt, dict) and "candidate_digest" in receipt:
                cand_digest = candidate.compute_digest()
                if receipt["candidate_digest"] != cand_digest:
                    ok, reason = False, f"[RECEIPT_BINDING_MISMATCH] Receipt digest '{receipt['candidate_digest']}' != candidate '{cand_digest}'"

        attempt = {"n": n, "ok": ok, "reason": reason, "candidate": candidate}
        attempts.append(attempt)
        if on_attempt:
            on_attempt(attempt)
        if ok:
            return candidate, attempts
        feedback = (reason or "").strip()[:FEEDBACK_CHARS]

    return None, attempts
