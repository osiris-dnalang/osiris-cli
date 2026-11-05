"""Fail-closed evaluation primitives for the A-Field research organism.

Evaluates declared evidence only. Never runs experiments, signs grants, changes claim
standing, or promotes a research organism.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


class GateVerdict(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class GateEvaluation:
    verdict: GateVerdict
    reasons: tuple[str, ...]
    passed_gate_ids: tuple[str, ...]
    blocked_gate_ids: tuple[str, ...]


_ALLOWED_CLAIM_STANDINGS = {
    "ARTIFACT", "SUPPORTED", "HYPOTHESIS", "NOT_MEASURED", "REFUTED", "OVERCLAIM"
}


def evaluate_research_gates(
    genome: Mapping[str, Any],
    evidence_receipt: Mapping[str, Any],
    *,
    required_gate_ids: Sequence[str] = ("GATE-01", "GATE-02", "GATE-03", "GATE-04"),
    promotion_requested: bool = False,
    human_approval: Mapping[str, Any] | None = None,
) -> GateEvaluation:
    """Evaluate metadata only; PASS does not authorize execution or promotion."""
    reasons: list[str] = []
    passed: list[str] = []
    blocked: list[str] = []

    if genome.get("organism_type") != "research_genome":
        return GateEvaluation(GateVerdict.INVALID, ("organism_type must be research_genome",), (), ())
    if not genome.get("organism_id") or not genome.get("version"):
        return GateEvaluation(GateVerdict.INVALID, ("organism_id and version are required",), (), ())
    claims = genome.get("claims")
    if not isinstance(claims, list) or not claims:
        return GateEvaluation(GateVerdict.INVALID, ("claims must be a non-empty list",), (), ())

    claim_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            reasons.append("every claim must be an object")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id or claim_id in claim_ids:
            reasons.append("claim ids must be non-empty and unique")
        else:
            claim_ids.add(claim_id)
        if claim.get("standing") not in _ALLOWED_CLAIM_STANDINGS:
            reasons.append(f"{claim_id or '<unknown>'}: invalid or missing standing")
        if claim.get("quarantined") is True and claim.get("firewall_status") not in {
            "QUARANTINED", "MODEL_PROPOSED", "BLOCKED"
        }:
            reasons.append(f"{claim_id}: quarantined claim has permissive firewall status")

    gate_rows = genome.get("gates")
    if not isinstance(gate_rows, list):
        return GateEvaluation(GateVerdict.INVALID, tuple(reasons + ["gates must be a list"]), (), ())
    by_id: dict[str, Mapping[str, Any]] = {}
    for gate in gate_rows:
        if not isinstance(gate, dict) or not isinstance(gate.get("gate_id"), str):
            reasons.append("each gate must be an object with gate_id")
            continue
        if gate["gate_id"] in by_id:
            reasons.append(f"duplicate gate id: {gate['gate_id']}")
        by_id[gate["gate_id"]] = gate

    for gate_id in required_gate_ids:
        gate = by_id.get(gate_id)
        if gate is None:
            blocked.append(gate_id)
            reasons.append(f"{gate_id}: missing required gate")
        elif gate.get("status") == "PASS" and gate.get("blocking") is False:
            passed.append(gate_id)
        else:
            blocked.append(gate_id)
            reasons.append(f"{gate_id}: status is not an explicit non-blocking PASS")

    if evidence_receipt.get("organism_id") != genome.get("organism_id"):
        reasons.append("evidence receipt organism_id does not match genome")
    invariant = genome.get("governance", {}).get("epistemic_invariant")
    if evidence_receipt.get("epistemic_invariant") != invariant:
        reasons.append("evidence receipt epistemic invariant does not match genome")
    if evidence_receipt.get("governance_status", {}).get("SYS_023_evidence_recorded") is not True:
        reasons.append("SYS-023 evidence recording is not affirmatively attested")

    # This evaluator cannot authorize promotion; SYS-021 verification is separate.
    if promotion_requested:
        reasons.append("promotion denied: this evaluator cannot authorize promotion")
        if not isinstance(human_approval, dict) or not human_approval.get("grant_id") or not human_approval.get("payload_digest"):
            reasons.append("promotion requires an independently verified SYS-021 grant bound to the exact payload")

    if reasons or blocked:
        verdict = GateVerdict.BLOCKED
    else:
        verdict = GateVerdict.PASS
        reasons.append("metadata contract satisfied; no execution or promotion authority granted")
    return GateEvaluation(verdict, tuple(reasons), tuple(passed), tuple(blocked))
