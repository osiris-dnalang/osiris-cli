#!/usr/bin/env python3
"""
OSIRIS Deterministic Capability-Gap Analysis Component
======================================================
Deterministic decision component between plan generation and action scheduling.
Answers: "What prevents the next step from being valid, permitted, and verifiable—
and what registered response can resolve that blocker?"

Output is an immutable, typed GapReport.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Tuple


class GapKind(str, Enum):
    INTENT_AMBIGUITY = "intent_ambiguity"
    MISSING_INPUT = "missing_input"
    MISSING_CONTEXT = "missing_context"
    STALE_CONTEXT = "stale_context"
    SNAPSHOT_MISMATCH = "snapshot_mismatch"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    EXECUTION_UNAVAILABLE = "execution_unavailable"
    POLICY_UNEVALUATED = "policy_unevaluated"
    APPROVAL_REQUIRED = "approval_required"
    POLICY_DENIED = "policy_denied"
    VERIFICATION_UNAVAILABLE = "verification_unavailable"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"


class Disposition(str, Enum):
    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_CONTEXT = "needs_context"
    NEEDS_POLICY = "needs_policy"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"


class PolicyState(str, Enum):
    UNEVALUATED = "unevaluated"
    APPROVAL_REQUIRED = "approval_required"
    DENIED = "denied"
    ALLOWED = "allowed"


@dataclass(frozen=True)
class ContextRequirement:
    key: str
    max_age_seconds: Optional[float] = None
    must_match_snapshot: bool = True


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    required_inputs: FrozenSet[str]
    context_requirements: Tuple[ContextRequirement, ...] = ()
    required_verifiers: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class ContextFact:
    fact_id: str
    observed_at: datetime
    snapshot_id: Optional[str]
    artifact_refs: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Ambiguity:
    ambiguity_id: str
    question: str
    affects_step_ids: FrozenSet[str]


@dataclass(frozen=True)
class Contradiction:
    contradiction_id: str
    summary: str
    fact_ids: Tuple[str, ...]
    affects_step_ids: FrozenSet[str]


@dataclass(frozen=True)
class PolicyAssessment:
    state: PolicyState
    action_fingerprint: str
    expires_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class ProposedStep:
    step_id: str
    capability_id: str
    execution_target: str
    snapshot_id: str
    arguments: Mapping[str, Any]
    required_verifiers: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class AnalysisInput:
    step: ProposedStep
    now: datetime
    registry_revision: str
    capabilities: Mapping[str, CapabilitySpec]
    context: Mapping[str, ContextFact]
    available_targets: FrozenSet[str]
    available_verifiers: FrozenSet[str]
    policy: Optional[PolicyAssessment] = None
    ambiguities: Tuple[Ambiguity, ...] = ()
    contradictions: Tuple[Contradiction, ...] = ()


@dataclass(frozen=True)
class Gap:
    gap_id: str
    kind: GapKind
    subject: str
    message: str
    resolution_ids: Tuple[str, ...]
    evidence_refs: Tuple[str, ...] = ()
    blocking: bool = True


@dataclass(frozen=True)
class GapReport:
    step_id: str
    action_fingerprint: str
    registry_revision: str
    evaluated_at: datetime
    disposition: Disposition
    gaps: Tuple[Gap, ...]
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "step_id": self.step_id,
            "action_fingerprint": self.action_fingerprint,
            "registry_revision": self.registry_revision,
            "evaluated_at": self.evaluated_at.isoformat(),
            "disposition": self.disposition.value,
            "gaps": [
                {
                    "gap_id": g.gap_id,
                    "kind": g.kind.value,
                    "subject": g.subject,
                    "message": g.message,
                    "resolution_ids": list(g.resolution_ids),
                    "evidence_refs": list(g.evidence_refs),
                    "blocking": g.blocking,
                }
                for g in self.gaps
            ],
        }


def action_fingerprint(step: ProposedStep) -> str:
    """Computes a deterministic SHA-256 fingerprint of the proposed step document."""
    document = {
        "arguments": dict(step.arguments),
        "capability_id": step.capability_id,
        "execution_target": step.execution_target,
        "required_verifiers": sorted(step.required_verifiers),
        "snapshot_id": step.snapshot_id,
        "step_id": step.step_id,
    }
    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def make_gap(
    step_id: str,
    kind: GapKind,
    subject: str,
    message: str,
    resolutions: Tuple[str, ...],
    evidence_refs: Tuple[str, ...] = (),
) -> Gap:
    identity = f"{step_id}\0{kind.value}\0{subject}"
    gap_id = "gap_" + sha256(identity.encode("utf-8")).hexdigest()[:24]
    return Gap(
        gap_id=gap_id,
        kind=kind,
        subject=subject,
        message=message,
        resolution_ids=resolutions,
        evidence_refs=evidence_refs,
    )


def choose_disposition(gaps: Tuple[Gap, ...]) -> Disposition:
    kinds = {gap.kind for gap in gaps if gap.blocking}

    if not kinds:
        return Disposition.READY

    hard_blockers = {
        GapKind.CAPABILITY_UNAVAILABLE,
        GapKind.EXECUTION_UNAVAILABLE,
        GapKind.POLICY_DENIED,
        GapKind.VERIFICATION_UNAVAILABLE,
    }
    if kinds & hard_blockers:
        return Disposition.BLOCKED

    if kinds & {GapKind.INTENT_AMBIGUITY, GapKind.MISSING_INPUT}:
        return Disposition.NEEDS_CLARIFICATION

    context_blockers = {
        GapKind.MISSING_CONTEXT,
        GapKind.STALE_CONTEXT,
        GapKind.SNAPSHOT_MISMATCH,
        GapKind.CONTRADICTORY_EVIDENCE,
    }
    if kinds & context_blockers:
        return Disposition.NEEDS_CONTEXT

    if GapKind.POLICY_UNEVALUATED in kinds:
        return Disposition.NEEDS_POLICY

    return Disposition.WAITING_APPROVAL


class CapabilityGapAnalyzer:
    """
    Deterministic Capability-Gap Analyzer:
    Validates preconditions, freshness, policy disposition, and verification coverage
    against immutable input snapshots. Never grants execution authority or auto-generates tools.
    """

    def analyze(self, data: AnalysisInput) -> GapReport:
        self._validate_times(data)

        step = data.step
        fingerprint = action_fingerprint(step)
        gaps: List[Gap] = []

        def add(
            kind: GapKind,
            subject: str,
            message: str,
            resolutions: Tuple[str, ...],
            evidence_refs: Tuple[str, ...] = (),
        ) -> None:
            gaps.append(
                make_gap(
                    step.step_id,
                    kind,
                    subject,
                    message,
                    resolutions,
                    evidence_refs,
                )
            )

        # 1. Ambiguity Checks
        for ambiguity in sorted(data.ambiguities, key=lambda item: item.ambiguity_id):
            if step.step_id in ambiguity.affects_step_ids:
                add(
                    GapKind.INTENT_AMBIGUITY,
                    ambiguity.ambiguity_id,
                    ambiguity.question,
                    ("ask-operator",),
                )

        # 2. Contradiction Checks
        for conflict in sorted(data.contradictions, key=lambda item: item.contradiction_id):
            if step.step_id in conflict.affects_step_ids:
                add(
                    GapKind.CONTRADICTORY_EVIDENCE,
                    conflict.contradiction_id,
                    conflict.summary,
                    ("propose-evidence-reconciliation",),
                    conflict.fact_ids,
                )

        # 3. Capability Resolution & Input Preconditions
        spec = data.capabilities.get(step.capability_id)
        if spec is None:
            add(
                GapKind.CAPABILITY_UNAVAILABLE,
                step.capability_id,
                "The proposed capability has no registered specification.",
                ("report-capability-gap", "draft-capability-criteria"),
            )
        else:
            for key in sorted(spec.required_inputs):
                if key not in step.arguments or step.arguments[key] is None:
                    add(
                        GapKind.MISSING_INPUT,
                        key,
                        f"Required input is missing: {key}.",
                        ("resolve-input", "ask-operator"),
                    )

            for requirement in sorted(spec.context_requirements, key=lambda item: item.key):
                fact = data.context.get(requirement.key)
                if fact is None:
                    add(
                        GapKind.MISSING_CONTEXT,
                        requirement.key,
                        f"Required context is unavailable: {requirement.key}.",
                        ("propose-context-read",),
                    )
                    continue

                refs = (fact.fact_id,) + fact.artifact_refs
                age = (data.now - fact.observed_at).total_seconds()

                if age < 0:
                    add(
                        GapKind.CONTRADICTORY_EVIDENCE,
                        requirement.key,
                        "Observation timestamp is later than analysis time.",
                        ("reconcile-observation-time",),
                        refs,
                    )
                elif requirement.max_age_seconds is not None and age > requirement.max_age_seconds:
                    add(
                        GapKind.STALE_CONTEXT,
                        requirement.key,
                        "Context age exceeds its allowed freshness window.",
                        ("propose-context-refresh",),
                        refs,
                    )

                if requirement.must_match_snapshot and fact.snapshot_id != step.snapshot_id:
                    add(
                        GapKind.SNAPSHOT_MISMATCH,
                        requirement.key,
                        "Context does not match the proposed step snapshot.",
                        ("propose-context-refresh", "revise-plan"),
                        refs,
                    )

        # 4. Target Execution Availability
        if step.execution_target not in data.available_targets:
            add(
                GapKind.EXECUTION_UNAVAILABLE,
                step.execution_target,
                "The selected execution target is not currently available.",
                ("inspect-target-health", "propose-alternate-target"),
            )

        # 5. Verification Coverage
        required_verifiers = set(step.required_verifiers)
        if spec is not None:
            required_verifiers.update(spec.required_verifiers)

        for verifier in sorted(required_verifiers - set(data.available_verifiers)):
            add(
                GapKind.VERIFICATION_UNAVAILABLE,
                verifier,
                f"Required verifier is unavailable: {verifier}.",
                ("report-verification-gap", "draft-verifier-criteria"),
            )

        # 6. Policy Disposition
        policy = data.policy
        if (
            policy is None
            or policy.action_fingerprint != fingerprint
            or policy.expires_at <= data.now
            or policy.state == PolicyState.UNEVALUATED
        ):
            add(
                GapKind.POLICY_UNEVALUATED,
                fingerprint,
                "A current policy assessment for this exact action is required.",
                ("request-policy-evaluation",),
            )
        elif policy.state == PolicyState.DENIED:
            add(
                GapKind.POLICY_DENIED,
                fingerprint,
                policy.reason or "Policy denies the proposed action.",
                ("report-policy-block", "propose-permitted-alternative"),
            )
        elif policy.state == PolicyState.APPROVAL_REQUIRED:
            add(
                GapKind.APPROVAL_REQUIRED,
                fingerprint,
                "The exact proposed action requires operator approval.",
                ("request-exact-action-approval",),
            )

        ordered = tuple(sorted(gaps, key=lambda gap: (gap.kind.value, gap.subject)))

        return GapReport(
            step_id=step.step_id,
            action_fingerprint=fingerprint,
            registry_revision=data.registry_revision,
            evaluated_at=data.now,
            disposition=choose_disposition(ordered),
            gaps=ordered,
        )

    @staticmethod
    def _validate_times(data: AnalysisInput) -> None:
        timestamps = [data.now]
        timestamps.extend(fact.observed_at for fact in data.context.values())

        if data.policy is not None:
            timestamps.append(data.policy.expires_at)

        if any(value.tzinfo is None or value.utcoffset() is None for value in timestamps):
            raise ValueError("All timestamps must be timezone-aware.")

        for spec in data.capabilities.values():
            for requirement in spec.context_requirements:
                if requirement.max_age_seconds is not None and requirement.max_age_seconds < 0:
                    raise ValueError("Context freshness limits must be nonnegative.")
