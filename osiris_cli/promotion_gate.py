"""Evidence-governed promotion gate (SYS-023 / SYS-026).

A candidate is eligible for promotion only when all four predicates hold:

1. QUALITY    its quality delta is positive and significant: delta_q > 0 and p_value < alpha.
2. STABILITY  the NCLM neither drifted nor collapsed: w2_drift <= w2_max and
              entropy_bits >= entropy_floor_bits.
3. INTEGRITY  no SYS-025 AST firewall violations, and the operational journal verifies end to end.
4. SPEAKING   the SYS-026 speaking gate is open as Osiris.gate() reports it: at least GATE_WINDOW
              held-out exchanges under the current SCORER, mean core bits/byte <= SPEAK_BPB and
              below the unigram baseline. Those numbers are living.py's; this module adds none.

The gate decides eligibility and nothing else: it promotes nothing and writes nothing, and the
operator promotes. alpha, w2_max and entropy_floor_bits have no defaults. Under GEMINI.md the
operator registers thresholds, so QUALITY and STABILITY fail until PromotionCriteria supplies them
together with where they were registered. Any non-finite number fails its predicate.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, fields
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple

from osiris_cli.journal import OperationalMerkleLedger
from osiris_cli.living import GATE_WINDOW, SPEAK_BPB


class Predicate(str, Enum):
    QUALITY = "QUALITY"
    STABILITY = "STABILITY"
    INTEGRITY = "INTEGRITY"
    SPEAKING = "SPEAKING"


@dataclass(frozen=True)
class PromotionCriteria:
    """Operator-registered thresholds and the place they were committed before the run."""
    alpha: float
    w2_max: float
    entropy_floor_bits: float
    registration_ref: str


@dataclass(frozen=True)
class PromotionEvidence:
    """What was measured on the candidate. speaking_gate is Osiris.gate() as returned."""
    candidate_id: str
    candidate_digest: str
    delta_q: float
    p_value: float
    w2_drift: float
    entropy_bits: float
    ast_violations: int
    speaking_gate: Mapping[str, Any]


@dataclass(frozen=True)
class PredicateResult:
    predicate: Predicate
    passed: bool
    detail: str


@dataclass(frozen=True)
class PromotionVerdict:
    candidate_id: str
    candidate_digest: str
    eligible: bool
    results: Tuple[PredicateResult, ...]
    evidence_sha256: str
    registration_ref: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_digest": self.candidate_digest,
            "eligible": self.eligible,
            "results": [
                {"predicate": r.predicate.value, "passed": r.passed, "detail": r.detail} for r in self.results
            ],
            "evidence_sha256": self.evidence_sha256,
            "registration_ref": self.registration_ref,
        }


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _criteria_problem(c: Optional[PromotionCriteria]) -> Optional[str]:
    if c is None:
        return "no PromotionCriteria: the operator has not registered alpha, w2_max and entropy_floor_bits"
    if not isinstance(c.registration_ref, str) or not c.registration_ref.strip():
        return "PromotionCriteria has no registration_ref"
    if not (_finite(c.alpha) and 0 < c.alpha < 1):
        return f"alpha {c.alpha!r} is not in (0, 1)"
    if not (_finite(c.w2_max) and c.w2_max >= 0):
        return f"w2_max {c.w2_max!r} is not a non-negative number"
    if not (_finite(c.entropy_floor_bits) and c.entropy_floor_bits >= 0):
        return f"entropy_floor_bits {c.entropy_floor_bits!r} is not a non-negative number"
    return None


def _quality(e: PromotionEvidence, c: Optional[PromotionCriteria], problem: Optional[str]) -> PredicateResult:
    def fail(detail: str) -> PredicateResult:
        return PredicateResult(Predicate.QUALITY, False, detail)

    if problem:
        return fail(problem)
    if not (_finite(e.delta_q) and e.delta_q > 0):
        return fail(f"delta_q {e.delta_q!r} is not a positive number")
    if not (_finite(e.p_value) and 0 <= e.p_value <= 1):
        return fail(f"p_value {e.p_value!r} is not a probability")
    if not e.p_value < c.alpha:
        return fail(f"p = {e.p_value:.4g} is not below alpha = {c.alpha:.4g}")
    return PredicateResult(
        Predicate.QUALITY, True, f"delta_q = {e.delta_q:.4g} > 0 at p = {e.p_value:.4g} < alpha = {c.alpha:.4g}"
    )


def _stability(e: PromotionEvidence, c: Optional[PromotionCriteria], problem: Optional[str]) -> PredicateResult:
    def fail(detail: str) -> PredicateResult:
        return PredicateResult(Predicate.STABILITY, False, detail)

    if problem:
        return fail(problem)
    if not (_finite(e.w2_drift) and e.w2_drift >= 0):
        return fail(f"w2_drift {e.w2_drift!r} is not a non-negative number")
    if e.w2_drift > c.w2_max:
        return fail(f"W2 drift {e.w2_drift:.4g} exceeds w2_max = {c.w2_max:.4g}")
    if not _finite(e.entropy_bits):
        return fail(f"entropy_bits {e.entropy_bits!r} is not a number")
    if e.entropy_bits < c.entropy_floor_bits:
        return fail(f"entropy {e.entropy_bits:.4g} bits is below the floor of {c.entropy_floor_bits:.4g}")
    return PredicateResult(
        Predicate.STABILITY, True,
        f"W2 drift {e.w2_drift:.4g} <= {c.w2_max:.4g}; entropy {e.entropy_bits:.4g} >= {c.entropy_floor_bits:.4g} bits",
    )


def _integrity(e: PromotionEvidence, journal: OperationalMerkleLedger) -> PredicateResult:
    def fail(detail: str) -> PredicateResult:
        return PredicateResult(Predicate.INTEGRITY, False, detail)

    if type(e.ast_violations) is not int or e.ast_violations != 0:
        return fail(f"{e.ast_violations!r} SYS-025 AST firewall violations")
    try:
        fault = journal.verify()
    except (OSError, ValueError) as exc:
        fault = f"journal could not be read ({exc})"
    if fault:
        return fail(f"operational journal does not verify: {fault}")
    return PredicateResult(Predicate.INTEGRITY, True, "0 AST firewall violations; operational journal verifies")


def _speaking(e: PromotionEvidence) -> PredicateResult:
    def fail(detail: str) -> PredicateResult:
        return PredicateResult(Predicate.SPEAKING, False, detail)

    gate = e.speaking_gate or {}
    n, core, uni = gate.get("n"), gate.get("core_bpb"), gate.get("unigram_bpb")
    if gate.get("open") is not True:
        return fail("speaking gate is closed")
    if type(n) is not int or n < GATE_WINDOW:
        return fail(f"{n!r} held-out exchanges scored; the gate needs {GATE_WINDOW}")
    if not (_finite(core) and core <= SPEAK_BPB):
        return fail(f"core {core!r} bits/byte is not <= {SPEAK_BPB}")
    if not (_finite(uni) and core < uni):
        return fail(f"core {core:.2f} bits/byte is not below the unigram baseline {uni!r}")
    return PredicateResult(
        Predicate.SPEAKING, True,
        f"open: {core:.2f} bits/byte over {n} held-out exchanges (<= {SPEAK_BPB}; unigram {uni:.2f})",
    )


def evidence_digest(evidence: PromotionEvidence, criteria: Optional[PromotionCriteria]) -> str:
    """SHA-256 over the canonical evidence and criteria, binding a verdict to exactly what it judged."""
    body = {
        "evidence": {
            **{f.name: getattr(evidence, f.name) for f in fields(evidence)},
            "speaking_gate": dict(evidence.speaking_gate or {}),
        },
        "criteria": asdict(criteria) if criteria is not None else None,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_promotion(
    evidence: PromotionEvidence,
    criteria: Optional[PromotionCriteria],
    journal: OperationalMerkleLedger,
) -> PromotionVerdict:
    """Judge one candidate. Every predicate is reported, eligible only when all four pass."""
    problem = _criteria_problem(criteria)
    results = (
        _quality(evidence, criteria, problem),
        _stability(evidence, criteria, problem),
        _integrity(evidence, journal),
        _speaking(evidence),
    )
    return PromotionVerdict(
        candidate_id=evidence.candidate_id,
        candidate_digest=evidence.candidate_digest,
        eligible=all(r.passed for r in results),
        results=results,
        evidence_sha256=evidence_digest(evidence, criteria),
        registration_ref=criteria.registration_ref if criteria is not None else None,
    )
