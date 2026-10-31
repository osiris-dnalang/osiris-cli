#!/usr/bin/env python3
"""
OSIRIS Operational Journal, Promotion Gate & Substrate Context
==============================================================
Provides evidence-governed journaling, SHA-256 hash-chained entries,
hardware substrate probing, and the formal Promotion Gate:
Promote(c) = (Delta_Q > tau_Q) ^ (Delta_S >= 0) ^ (Delta_R >= -tau_R) ^ Reproducible(c)
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SubstrateContext:
    node_id: str
    architecture: str
    simd_profile: str
    cores: int
    timeout_s: float
    is_mobile: bool
    workspace_root: str


def probe_substrate_context(workspace_dir: Optional[Path] = None) -> SubstrateContext:
    """Probes local hardware capabilities and assigns sovereign node identity."""
    arch = platform.machine().lower()
    system = platform.system().lower()
    uname_release = platform.uname().release.lower()
    cores = os.cpu_count() or 1
    env_home = Path(os.environ.get("HOME", os.path.expanduser("~")))

    is_mobile = (
        "aarch64" in arch or "arm" in arch or
        "android" in uname_release or "android" in system or
        bool(os.environ.get("TERMUX_VERSION")) or
        os.path.exists("/data/data/com.termux")
    )

    if is_mobile:
        node_id = "NODE_ALPHA_MOBILE"
        simd_profile = "ARM_NEON"
        timeout_s = 300.0
    elif "x86_64" in arch or "amd64" in arch:
        node_id = "NODE_BETA_COMPUTE"
        simd_profile = "AVX2_AVX_VNNI"
        timeout_s = 1800.0
    else:
        node_id = "NODE_GENERIC_EDGE"
        simd_profile = "GENERIC_SCALAR"
        timeout_s = 300.0

    ws = str(workspace_dir.resolve()) if workspace_dir else str((env_home / "osiris-cli").resolve())

    return SubstrateContext(
        node_id=node_id,
        architecture=arch,
        simd_profile=simd_profile,
        cores=cores,
        timeout_s=timeout_s,
        is_mobile=is_mobile,
        workspace_root=ws,
    )


@dataclass
class CandidatePatchProposal:
    proposal_id: str
    target_component: str
    causal_hypothesis: str
    diff_summary: str
    expected_metric_delta: float
    quality_delta: float
    safety_delta: float
    resource_delta: float
    reproducible: bool
    p_value: float
    cohens_d: float
    wasserstein_w2: float
    shannon_entropy: float
    evidence_state: str
    rollback_token: str


@dataclass
class PromotionDecision:
    proposal_id: str
    status: str  # "PROMOTED" | "REJECTED_SUB_THRESHOLD" | "REJECTED_SAFETY" | "AWAITING_HUMAN_GATE"
    rationale: str
    evaluated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromotionGate:
    """
    Formal Evidence-Governed Promotion Gate:
    Promote(c) = (Delta_Q > tau_Q) ^ (Delta_S >= 0) ^ (Delta_R >= -tau_R) ^ Reproducible(c) ^ (p < alpha)
    """

    def __init__(
        self,
        tau_quality: float = 0.015,
        tau_resource: float = 0.10,
        alpha_significance: float = 0.05,
        require_human_gate: bool = True,
    ) -> None:
        self.tau_quality = tau_quality
        self.tau_resource = tau_resource
        self.alpha_significance = alpha_significance
        self.require_human_gate = require_human_gate

    def evaluate(self, proposal: CandidatePatchProposal) -> PromotionDecision:
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Safety check
        if proposal.safety_delta < 0:
            return PromotionDecision(
                proposal_id=proposal.proposal_id,
                status="REJECTED_SAFETY",
                rationale=f"Safety regression detected: Delta_S = {proposal.safety_delta:.4f} < 0. Immediate rejection.",
                evaluated_at_utc=now_iso,
            )

        # 2. Quality threshold
        if proposal.quality_delta <= self.tau_quality:
            return PromotionDecision(
                proposal_id=proposal.proposal_id,
                status="REJECTED_SUB_THRESHOLD",
                rationale=(
                    f"Quality delta {proposal.quality_delta:.4f} did not exceed threshold tau_Q = {self.tau_quality:.4f}. "
                    "Preserving as negative knowledge."
                ),
                evaluated_at_utc=now_iso,
            )

        # 3. Resource budget check
        if proposal.resource_delta < -self.tau_resource:
            return PromotionDecision(
                proposal_id=proposal.proposal_id,
                status="REJECTED_RESOURCE",
                rationale=f"Resource overhead {proposal.resource_delta:.4f} exceeded budget -tau_R = {-self.tau_resource:.4f}.",
                evaluated_at_utc=now_iso,
            )

        # 4. Statistical significance and reproducibility
        if proposal.p_value >= self.alpha_significance or not proposal.reproducible:
            return PromotionDecision(
                proposal_id=proposal.proposal_id,
                status="REJECTED_SIGNIFICANCE",
                rationale=f"Candidate failed significance gate: p = {proposal.p_value:.4f} >= {self.alpha_significance} or reproducible=False.",
                evaluated_at_utc=now_iso,
            )

        # 5. Human Promotion Gate for hybrid/manual modes
        if self.require_human_gate:
            return PromotionDecision(
                proposal_id=proposal.proposal_id,
                status="PROMOTED_PENDING_HUMAN_SIGN_OFF",
                rationale=(
                    f"Candidate verified statistically (Delta_Q = +{proposal.quality_delta:.4f}, p = {proposal.p_value:.4f}, "
                    f"d = {proposal.cohens_d:.2f}). Awaiting final operator signature."
                ),
                evaluated_at_utc=now_iso,
            )

        return PromotionDecision(
            proposal_id=proposal.proposal_id,
            status="PROMOTED",
            rationale=f"Autonomous criteria satisfied: Delta_Q = +{proposal.quality_delta:.4f}, p = {proposal.p_value:.4f}, zero safety regression.",
            evaluated_at_utc=now_iso,
        )


class OperationalJournal:
    """
    Hash-chained append-only operational journal for evidence recording and rollback tracking.
    """

    def __init__(self, workspace_dir: Path) -> None:
        p = Path(workspace_dir)
        if p.suffix or (p.exists() and p.is_file()):
            self.workspace_dir = p.parent
            self.journal_path = p
        else:
            self.workspace_dir = p
            self.journal_path = self.workspace_dir / "osiris_operational_journal.jsonl"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.substrate = probe_substrate_context(self.workspace_dir)
        self.last_hash = self._get_tail_hash()

    def record(self, entry_type: str, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Convenience alias for record_entry."""
        return self.record_entry(event_type=entry_type, payload=payload, **kwargs)

    def _get_tail_hash(self) -> str:
        if not self.journal_path.exists():
            return "0" * 64
        tail = "0" * 64
        try:
            with self.journal_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        entry = json.loads(line)
                        tail = entry.get("entry_hash", tail)
        except Exception:
            pass
        return tail

    def record_entry(
        self,
        event_type: str,
        payload: Dict[str, Any],
        evidence_state: str = "CONFIRMED",
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        body_to_hash = json.dumps({
            "prev_hash": self.last_hash,
            "event_type": event_type,
            "payload": payload,
            "timestamp": now_iso,
        }, sort_keys=True)
        entry_hash = hashlib.sha256(body_to_hash.encode("utf-8")).hexdigest()

        entry = {
            "entry_hash": entry_hash,
            "prev_hash": self.last_hash,
            "timestamp_utc": now_iso,
            "event_type": event_type,
            "evidence_state": evidence_state,
            "confidence": confidence,
            "substrate": self.substrate.node_id,
            "payload": payload,
        }

        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self.last_hash = entry_hash
        return entry

    def log_promotion_evaluation(
        self,
        proposal: CandidatePatchProposal,
        decision: PromotionDecision,
    ) -> None:
        self.record_entry(
            event_type="PROMOTION_GATE_EVALUATION",
            payload={
                "proposal": asdict(proposal),
                "decision": asdict(decision),
            },
            evidence_state=proposal.evidence_state,
            confidence=max(0.5, 1.0 - proposal.p_value),
        )

    def read_explicit_paste(self, prompt_text: str) -> str:
        return prompt_text.strip()

    def read_terminal_input(self) -> str:
        return ""
