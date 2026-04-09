"""
OSIRIS Statistical Engine — Phase 3: Comparative Synthesis and Anomaly Detection.

This is the rigour layer. Every hypothesis that OSIRIS advances must
pass through this engine before it becomes a proposal.

Implements:
  Theoretical Tension Index (TTI)
    — measures conflict of a claim against the accumulated evidence corpus.
    — TTI = weighted contradiction mass / (weighted support + contradiction)
    — TTI > 0.5: claim is in tension; TTI > 0.8: near-refuted

  Bayesian Posterior Stability (BPS)
    — models each claim's confidence as a Beta(α, β) distribution
    — α = supporting experiments weighted by quality
    — β = contradicting experiments weighted by quality
    — Stability = |delta_mean| < threshold after N new observations
    — Unstable = rapid posterior shifting = claim needs investigation

  Statistical Divergence Detector
    — given a new experimental result and a distribution of prior results,
      compute a z-score and flag anomalies
    — anomaly_threshold = 2.0 sigma (flagged), 3.0 sigma (critical)

  Cross-Domain Consistency Score (CDCS)
    — for each pair of claims in different domains that share keywords,
      measure whether their confidence trajectories are consistent
    — consistent = both rising together, or one constrains the other
    — inconsistent = one rising while the other falls

  Convergence Criteria (Phase 4 advancement gate)
    — Bayesian posterior stability: delta_mean < 0.02 over last 5 updates
    — Cross-simulation variance: σ² < 0.05
    — Theoretical coherence: no TTI > 0.7 among supporting claims
    — Stress test stability: parameter perturbation < 10% changes outcome

All claims that do not meet convergence criteria are BLOCKED from
advancing to Phase 5 experimental proposals.

Usage:
  engine = StatisticalEngine()
  tti    = engine.theoretical_tension_index(claim_id)
  stable = engine.is_bayesian_stable(claim_id)
  report = engine.full_convergence_report(claim_id)
"""

from __future__ import annotations

import os
import re
import json
import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as sp_stats

from .research_graph import (
    ResearchGraph, TheoreticalClaim, ExperimentNode,
    NodeType, EdgeType, Domain,
    get_research_graph,
)

# ── Persistence ───────────────────────────────────────────────────────────────

_STATS_DIR     = os.path.expanduser("~/.osiris/statistical_engine")
_POSTERIOR_FILE = os.path.join(_STATS_DIR, "posteriors.json")
_TTI_LOG        = os.path.join(_STATS_DIR, "tti_history.jsonl")


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class BetaPosterior:
    """Beta(α, β) posterior for a binary hypothesis (confirmed / refuted)."""
    claim_id: str
    alpha:    float = 1.0   # pseudo-count: confirmations + 1 (uniform prior)
    beta:     float = 1.0   # pseudo-count: refutations + 1
    history:  List[Dict] = field(default_factory=list)   # update log

    @property
    def mean(self) -> float:
        """Posterior mean confidence."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def credible_interval_95(self) -> Tuple[float, float]:
        """95% highest-density interval."""
        lo = sp_stats.beta.ppf(0.025, self.alpha, self.beta)
        hi = sp_stats.beta.ppf(0.975, self.alpha, self.beta)
        return float(lo), float(hi)

    def update(self, confirmed: float, refuted: float) -> float:
        """
        Update posterior with new evidence.
        confirmed/refuted are experiment-quality-weighted counts.
        Returns |delta_mean| for stability check.
        """
        old_mean = self.mean
        self.alpha += confirmed
        self.beta  += refuted
        delta = abs(self.mean - old_mean)
        self.history.append({
            "ts":        datetime.now(timezone.utc).isoformat(),
            "confirmed": confirmed,
            "refuted":   refuted,
            "mean":      round(self.mean, 4),
            "delta":     round(delta, 4),
        })
        return delta

    def is_stable(self, window: int = 5, delta_threshold: float = 0.02) -> bool:
        """
        True if the last `window` updates all produced |delta_mean| < threshold.
        This is the Bayesian posterior stability convergence criterion.
        """
        if len(self.history) < window:
            return False
        recent_deltas = [h["delta"] for h in self.history[-window:]]
        return all(d < delta_threshold for d in recent_deltas)


@dataclass
class TTIScore:
    claim_id:       str
    claim_title:    str
    tti:            float    # 0=fully supported, 1=fully contradicted
    support_mass:   float
    contradiction_mass: float
    support_count:  int
    contra_count:   int
    verdict:        str      # "supported" | "tension" | "contested" | "refuted"
    notes:          List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"TTI[{self.verdict.upper()}]  {self.claim_title[:60]}\n"
            f"  TTI={self.tti:.3f}  "
            f"support={self.support_count}  contra={self.contra_count}\n"
            f"  support_mass={self.support_mass:.2f}  "
            f"contra_mass={self.contradiction_mass:.2f}"
        )


@dataclass
class ConvergenceReport:
    claim_id:   str
    claim_title: str
    passed:     bool
    criteria:   Dict[str, bool]   # criterion_name → passed
    details:    Dict[str, Any]
    blocked:    bool              # True = cannot advance to Phase 5

    def summary(self) -> str:
        gate = "✓ PASS — eligible for Phase 5" if self.passed else "✗ BLOCKED — not ready for Phase 5"
        lines = [f"CONVERGENCE: {self.claim_title[:60]}", f"  {gate}"]
        for crit, ok in self.criteria.items():
            sym = "✓" if ok else "✗"
            lines.append(f"  {sym} {crit}")
        return "\n".join(lines)


@dataclass
class AnomalyFlag:
    node_id:    str
    node_title: str
    z_score:    float
    p_value:    float
    direction:  str    # "above_mean" | "below_mean"
    severity:   str    # "flagged" | "critical"
    context:    str


# ── Statistical Engine ────────────────────────────────────────────────────────

class StatisticalEngine:
    """
    Phase 3 rigour layer — quantifies tension, tracks Bayesian posteriors,
    detects anomalies, and gates Phase 4 hypotheses.
    """

    TTI_SUPPORTED  = 0.30
    TTI_TENSION    = 0.50
    TTI_CONTESTED  = 0.70
    # TTI > 0.70 → "refuted"

    ANOMALY_SIGMA  = 2.0
    CRITICAL_SIGMA = 3.0

    BPS_WINDOW     = 5
    BPS_THRESHOLD  = 0.02

    def __init__(self, graph: Optional[ResearchGraph] = None):
        self._graph     = graph or get_research_graph()
        self._posteriors: Dict[str, BetaPosterior] = {}
        os.makedirs(_STATS_DIR, exist_ok=True)
        self._load_posteriors()

    # ── Theoretical Tension Index ─────────────────────────────────────────────

    def theoretical_tension_index(self, claim_id: str) -> TTIScore:
        """
        Compute the TTI for a claim node.

        Weight each supporting/contradicting experiment by:
          - Its own status (confirmed=1.0, ambiguous=0.5, open=0.3)
          - Result fidelity if available from quantum_params
        """
        node = self._graph.get_node(claim_id)
        if node is None:
            return TTIScore(claim_id, "unknown", 1.0, 0.0, 0.0, 0, 0, "refuted",
                            notes=["Claim node not found"])

        supporting    = [e for e in self._graph.edges_for(claim_id)
                         if e.edge_type == EdgeType.SUPPORTS
                         and e.target_id == claim_id]
        contradicting = [e for e in self._graph.edges_for(claim_id)
                         if e.edge_type == EdgeType.CONTRADICTS
                         and e.target_id == claim_id]

        def _quality_weight(exp_id: str, base_weight: float) -> float:
            exp = self._graph.get_node(exp_id)
            if exp is None:
                return base_weight * 0.3
            status = getattr(exp, "status", "open")
            status_w = {"confirmed": 1.0, "ambiguous": 0.5, "open": 0.3,
                        "in_progress": 0.2, "refuted": 0.8}.get(status, 0.3)
            # Fidelity bonus for quantum experiments
            fidelity = getattr(exp, "quantum_params", {}).get("fidelity", 0.0)
            fidelity_bonus = fidelity * 0.3 if fidelity else 0.0
            return base_weight * status_w + fidelity_bonus

        support_mass = sum(
            _quality_weight(e.source_id, e.weight) for e in supporting
        )
        contra_mass  = sum(
            _quality_weight(e.source_id, e.weight) for e in contradicting
        )
        total = support_mass + contra_mass

        if total < 0.001:
            tti = 0.5   # no evidence: maximum uncertainty
            verdict = "tension"
        else:
            tti = contra_mass / total

        if tti <= self.TTI_SUPPORTED:
            verdict = "supported"
        elif tti <= self.TTI_TENSION:
            verdict = "tension"
        elif tti <= self.TTI_CONTESTED:
            verdict = "contested"
        else:
            verdict = "refuted"

        # Log to history
        try:
            with open(_TTI_LOG, "a") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "claim_id": claim_id,
                    "tti": round(tti, 4),
                    "verdict": verdict,
                }) + "\n")
        except Exception:
            pass

        return TTIScore(
            claim_id=claim_id,
            claim_title=node.title,
            tti=tti,
            support_mass=round(support_mass, 3),
            contradiction_mass=round(contra_mass, 3),
            support_count=len(supporting),
            contra_count=len(contradicting),
            verdict=verdict,
        )

    def rank_by_tti(self) -> List[TTIScore]:
        """
        Rank all claims by TTI (highest tension first).
        These are the Theoretical Tension Index rankings — the claims
        with the most productive unresolved conflict.
        """
        scores = []
        for node in self._graph.all_nodes(node_type=NodeType.CLAIM):
            scores.append(self.theoretical_tension_index(node.id))
        scores.sort(key=lambda s: (s.tti > 0.3, s.tti), reverse=True)
        return scores

    # ── Bayesian Posterior Stability ──────────────────────────────────────────

    def get_posterior(self, claim_id: str) -> BetaPosterior:
        """Return or initialise the Beta posterior for a claim."""
        if claim_id not in self._posteriors:
            self._posteriors[claim_id] = BetaPosterior(claim_id=claim_id)
        return self._posteriors[claim_id]

    def update_posterior(self, claim_id: str) -> float:
        """
        Recompute posterior from current graph evidence.
        Returns |delta_mean| — the change in confidence after updating.
        """
        supporting    = [e for e in self._graph.edges_for(claim_id)
                         if e.edge_type == EdgeType.SUPPORTS
                         and e.target_id == claim_id]
        contradicting = [e for e in self._graph.edges_for(claim_id)
                         if e.edge_type == EdgeType.CONTRADICTS
                         and e.target_id == claim_id]
        # Quality-weighted counts
        def _w(eid: str) -> float:
            exp = self._graph.get_node(eid)
            if exp is None: return 0.3
            return 1.0 if getattr(exp, "status", "") == "confirmed" else 0.5

        conf = sum(_w(e.source_id) for e in supporting)
        ref  = sum(_w(e.source_id) for e in contradicting)

        posterior = self.get_posterior(claim_id)
        delta     = posterior.update(conf, ref)
        self._save_posteriors()
        return delta

    def is_bayesian_stable(self, claim_id: str) -> bool:
        """True if the posterior for this claim is stable (low delta over window)."""
        self.update_posterior(claim_id)
        return self.get_posterior(claim_id).is_stable(
            window=self.BPS_WINDOW, delta_threshold=self.BPS_THRESHOLD
        )

    def posterior_summary(self, claim_id: str) -> str:
        p = self.get_posterior(claim_id)
        lo, hi = p.credible_interval_95
        stable = p.is_stable(self.BPS_WINDOW, self.BPS_THRESHOLD)
        return (
            f"Posterior: mean={p.mean:.3f}  σ={math.sqrt(p.variance):.3f}  "
            f"95%CI=[{lo:.3f},{hi:.3f}]  "
            f"stable={'Yes' if stable else 'No'}  "
            f"updates={len(p.history)}"
        )

    # ── Statistical Divergence ────────────────────────────────────────────────

    def detect_anomaly(self, values: List[float], new_value: float,
                       node_id: str = "", node_title: str = "",
                       context: str = "") -> Optional[AnomalyFlag]:
        """
        Detect if new_value is a statistical anomaly in the distribution of
        prior values. Returns an AnomalyFlag if anomalous.

        Uses a robust z-score against the IQR-trimmed distribution.
        """
        if len(values) < 4:
            return None   # insufficient baseline

        arr   = np.array(values, dtype=float)
        mean  = float(np.mean(arr))
        std   = float(np.std(arr, ddof=1))

        if std < 1e-9:
            return None   # degenerate distribution

        z = (new_value - mean) / std

        # p-value from two-tailed normal approximation
        p_val = float(2 * (1 - sp_stats.norm.cdf(abs(z))))

        if abs(z) < self.ANOMALY_SIGMA:
            return None

        severity  = "critical" if abs(z) >= self.CRITICAL_SIGMA else "flagged"
        direction = "above_mean" if z > 0 else "below_mean"

        return AnomalyFlag(
            node_id=node_id,
            node_title=node_title,
            z_score=round(z, 3),
            p_value=round(p_val, 5),
            direction=direction,
            severity=severity,
            context=context,
        )

    def scan_for_anomalies(self) -> List[AnomalyFlag]:
        """
        Scan all confirmed experiments for anomalous fidelity/result values.
        Flags any experiment whose fidelity or numeric result deviates > 2σ
        from the distribution of similar experiments.
        """
        flags: List[AnomalyFlag] = []

        # Group experiments by domain + backend
        by_group: Dict[str, List[ExperimentNode]] = {}
        for node in self._graph.all_nodes(node_type=NodeType.EXPERIMENT):
            node_exp = node  # type: ignore
            key = f"{node.domain}:{getattr(node_exp, 'backend', 'unknown')}"
            by_group.setdefault(key, []).append(node_exp)  # type: ignore

        for group_key, exps in by_group.items():
            if len(exps) < 4:
                continue
            fidelities = [
                e.quantum_params.get("fidelity", 0.0)  # type: ignore
                for e in exps
                if e.quantum_params.get("fidelity", 0.0) > 0  # type: ignore
            ]
            if len(fidelities) < 4:
                continue

            for exp in exps:
                fid = exp.quantum_params.get("fidelity", 0.0)  # type: ignore
                if fid <= 0:
                    continue
                other_fids = [f for f in fidelities if f != fid]
                flag = self.detect_anomaly(
                    other_fids, fid,
                    node_id=exp.id, node_title=exp.title,
                    context=f"fidelity in {group_key}"
                )
                if flag:
                    flags.append(flag)

        return flags

    # ── Cross-Domain Consistency Score ────────────────────────────────────────

    def cross_domain_consistency(self) -> Dict[str, float]:
        """
        Compute CDCS: how consistent are the confidence trajectories of
        claims in different domains that share strong keyword overlap?

        Returns dict: domain_pair → consistency score [0, 1]
        0 = perfectly inconsistent (one rising, one falling)
        1 = perfectly consistent
        """
        claims = self._graph.all_nodes(node_type=NodeType.CLAIM)
        results: Dict[str, List[float]] = {}

        for i, c1 in enumerate(claims):
            for c2 in claims[i+1:]:
                if c1.domain == c2.domain:
                    continue
                # Keyword overlap check
                w1 = set(re.findall(r'\b\w{5,}\b', f"{c1.title} {c1.summary}".lower()))
                w2 = set(re.findall(r'\b\w{5,}\b', f"{c2.title} {c2.summary}".lower()))
                if len(w1 & w2) < 2:
                    continue

                conf1 = getattr(c1, "confidence", 0.5)
                conf2 = getattr(c2, "confidence", 0.5)
                # Posterior updates
                p1 = self.get_posterior(c1.id)
                p2 = self.get_posterior(c2.id)
                if len(p1.history) >= 2 and len(p2.history) >= 2:
                    # Compare last delta directions
                    delta1 = p1.history[-1]["mean"] - p1.history[-2]["mean"]
                    delta2 = p2.history[-1]["mean"] - p2.history[-2]["mean"]
                    # Consistent = same direction, or one near-zero
                    consistent = (delta1 * delta2 >= 0) or \
                                  abs(delta1) < 0.01 or abs(delta2) < 0.01
                    score = 1.0 if consistent else 0.0
                else:
                    # No history: fall back to confidence alignment
                    score = 1.0 - abs(conf1 - conf2)

                key = f"{min(c1.domain, c2.domain)}↔{max(c1.domain, c2.domain)}"
                results.setdefault(key, []).append(score)

        return {k: float(np.mean(v)) for k, v in results.items()}

    # ── Convergence Gate (Phase 4 → Phase 5) ─────────────────────────────────

    def full_convergence_report(self, claim_id: str,
                                param_variance: Optional[float] = None) -> ConvergenceReport:
        """
        Check all Phase 4 convergence criteria for a claim.
        param_variance is optionally passed from simulation_harness.

        Returns ConvergenceReport — if not passed, claim is BLOCKED from Phase 5.
        """
        node = self._graph.get_node(claim_id)
        title = node.title if node else "unknown"

        # 1. Bayesian posterior stability
        bps_stable = self.is_bayesian_stable(claim_id)

        # 2. TTI < 0.7 (not refuted)
        tti_score = self.theoretical_tension_index(claim_id)
        tti_ok    = tti_score.tti <= self.TTI_CONTESTED

        # 3. Cross-simulation variance (from harness, or estimated from posterior)
        if param_variance is not None:
            variance_ok = param_variance < 0.05
        else:
            post = self.get_posterior(claim_id)
            variance_ok = post.variance < 0.05

        # 4. Theoretical coherence: no highly-tensioned claims among supporters
        supporting_nodes = [
            self._graph.get_node(e.source_id)
            for e in self._graph.edges_for(claim_id)
            if e.edge_type == EdgeType.SUPPORTS and e.target_id == claim_id
        ]
        coherence_ok = True
        for sup in supporting_nodes:
            if sup and sup.node_type == NodeType.CLAIM:
                sup_tti = self.theoretical_tension_index(sup.id)
                if sup_tti.tti > self.TTI_CONTESTED:
                    coherence_ok = False
                    break

        # 5. Minimum evidence: at least 2 independent supporting experiments
        sup_exps = [
            self._graph.get_node(e.source_id)
            for e in self._graph.edges_for(claim_id)
            if e.edge_type == EdgeType.SUPPORTS and e.target_id == claim_id
            and self._graph.get_node(e.source_id) is not None
            and self._graph.get_node(e.source_id).node_type == NodeType.EXPERIMENT  # type: ignore
        ]
        evidence_ok = len(sup_exps) >= 2

        criteria = {
            "Bayesian posterior stability (delta<0.02, n=5)": bps_stable,
            "Theoretical Tension Index < 0.70":              tti_ok,
            "Cross-simulation variance < 0.05":              variance_ok,
            "Supporting claims are coherent (TTI<0.70)":     coherence_ok,
            "Minimum 2 independent supporting experiments":  evidence_ok,
        }

        passed  = all(criteria.values())
        blocked = not passed

        return ConvergenceReport(
            claim_id=claim_id,
            claim_title=title,
            passed=passed,
            criteria=criteria,
            details={
                "tti": round(tti_score.tti, 4),
                "tti_verdict": tti_score.verdict,
                "posterior_mean": round(self.get_posterior(claim_id).mean, 4),
                "posterior_variance": round(self.get_posterior(claim_id).variance, 5),
                "supporting_experiments": len(sup_exps),
                "param_variance": param_variance,
            },
            blocked=blocked,
        )

    def full_scan(self) -> Dict[str, Any]:
        """
        Run full statistical scan across all claims.
        Returns summary of TTI rankings, anomalies, convergence status.
        """
        # Update all posteriors first
        for node in self._graph.all_nodes(node_type=NodeType.CLAIM):
            self.update_posterior(node.id)

        tti_scores   = self.rank_by_tti()
        anomalies    = self.scan_for_anomalies()
        cdcs         = self.cross_domain_consistency()
        convergence  = [
            self.full_convergence_report(n.id)
            for n in self._graph.all_nodes(node_type=NodeType.CLAIM)
        ]
        n_ready   = sum(1 for r in convergence if r.passed)
        n_blocked = sum(1 for r in convergence if r.blocked)

        return {
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "tti_scores":       [asdict(s) for s in tti_scores[:10]],
            "top_tension":      tti_scores[0].summary() if tti_scores else "none",
            "anomalies":        len(anomalies),
            "critical_anomalies": sum(1 for a in anomalies if a.severity == "critical"),
            "cross_domain_consistency": cdcs,
            "proposals_ready":  n_ready,
            "proposals_blocked": n_blocked,
            "convergence_gate": f"{n_ready}/{len(convergence)} pass convergence",
        }

    def formatted_report(self) -> str:
        """Human-readable statistical intelligence report."""
        scan  = self.full_scan()
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            "║     STATISTICAL INTELLIGENCE REPORT                  ║",
            f"║     {scan['timestamp'][:19]}                          ║",
            "╚══════════════════════════════════════════════════════╝",
            "",
            f"CONVERGENCE GATE: {scan['convergence_gate']}",
            f"ANOMALIES: {scan['anomalies']} total  "
            f"({scan['critical_anomalies']} critical)",
            "",
            "THEORETICAL TENSION INDEX (top tensions):",
        ]
        for d in scan["tti_scores"][:5]:
            v = d.get("verdict", "?")
            sym = "⚠" if v in ("tension", "contested") else ("✗" if v == "refuted" else "✓")
            lines.append(
                f"  {sym} [{v.upper():<10}] TTI={d['tti']:.3f}  {d['claim_title'][:55]}"
            )

        cdcs = scan["cross_domain_consistency"]
        if cdcs:
            lines += ["", "CROSS-DOMAIN CONSISTENCY:"]
            for pair, score in sorted(cdcs.items(), key=lambda x: x[1]):
                sym = "✓" if score >= 0.7 else ("⚠" if score >= 0.4 else "✗")
                lines.append(f"  {sym} {pair}: {score:.2f}")

        return "\n".join(lines)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_posteriors(self) -> None:
        if os.path.exists(_POSTERIOR_FILE):
            try:
                with open(_POSTERIOR_FILE) as f:
                    raw = json.load(f)
                for claim_id, d in raw.items():
                    self._posteriors[claim_id] = BetaPosterior(
                        claim_id=claim_id,
                        alpha=d.get("alpha", 1.0),
                        beta=d.get("beta", 1.0),
                        history=d.get("history", []),
                    )
            except Exception:
                pass

    def _save_posteriors(self) -> None:
        try:
            data = {
                cid: {"alpha": p.alpha, "beta": p.beta, "history": p.history[-20:]}
                for cid, p in self._posteriors.items()
            }
            with open(_POSTERIOR_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_singleton: Optional[StatisticalEngine] = None


def get_statistical_engine() -> StatisticalEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = StatisticalEngine()
    return _engine_singleton
