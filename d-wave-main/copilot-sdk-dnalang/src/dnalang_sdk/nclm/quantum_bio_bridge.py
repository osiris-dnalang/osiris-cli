"""OSIRIS Gen 6.9 — Quantum-Biology Bridge
==========================================
Cross-domain bridge: quantum_physics ↔ drug_discovery
Hypothesis P8: TPSM SPT chain spectral gap as metabolic network rigidity proxy.

Key insight from P8 experiment (2026-03-02):
  - Cancer (Warburg) metabolic networks have HIGHER Fiedler connectivity (0.313 vs 0.268)
  - SSH chain with t₂/t₁=φ_golden is topological (1 in-gap state)
  - Simple model does NOT confirm gap-ratio bridge to 1/φ
  - Interpretation: cancer creates network ROBUSTNESS, not fragility — the Warburg metabolic
    remodeling strengthens specific flux axes while suppressing others
  - Bridge requires: higher-dimensional metabolic model or real TCGA pathway data

Usage:
    from dnalang_sdk.nclm.quantum_bio_bridge import get_quantum_bio_bridge, QuantumBioBridge
    bridge = get_quantum_bio_bridge()
    result = bridge.run_analysis()
    print(bridge.summary())
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import numpy as np
from scipy import linalg

# ── Constants ──────────────────────────────────────────────────────────────
PHI_GOLDEN      = (1 + math.sqrt(5)) / 2   # 1.618034
THETA_LOCK      = 51.843
SPT_HARDWARE_GAP = 0.482                    # IBM 120q SPT boundary_fraction - 0.5


@dataclass
class MetabolicNetwork:
    """Graph Laplacian spectral analysis of a metabolic network."""
    label:            str
    nodes:            List[str]
    adjacency:        np.ndarray
    eigenvalues:      List[float]    = field(default_factory=list)
    fiedler_gap:      float          = 0.0   # λ₂ - λ₁ (algebraic connectivity)
    second_gap:       float          = 0.0
    spectral_radius:  float          = 0.0
    gap_ratio:        float          = 0.0   # fiedler / second gap (golden ratio test)
    gap_normalized:   float          = 0.0

    def compute(self) -> "MetabolicNetwork":
        A = self.adjacency
        D = np.diag(A.sum(axis=1))
        Dinv = np.diag(1.0 / np.sqrt(np.maximum(A.sum(axis=1), 1e-12)))
        L = np.eye(len(self.nodes)) - Dinv @ A @ Dinv
        ev = np.sort(np.real(linalg.eigvalsh(L)))
        self.eigenvalues     = ev.tolist()
        self.fiedler_gap     = float(ev[1] - ev[0])
        self.second_gap      = float(ev[2] - ev[1]) if len(ev) > 2 else 0.0
        self.spectral_radius = float(ev[-1] - ev[0])
        self.gap_ratio       = self.fiedler_gap / self.second_gap if self.second_gap > 1e-10 else 0.0
        self.gap_normalized  = self.fiedler_gap / self.spectral_radius if self.spectral_radius > 0 else 0.0
        return self


@dataclass
class SPTChain:
    """SSH chain spectral analysis — quantum SPT topological gap."""
    sites:          int   = 20
    t1:             float = 1.0
    t2:             float = PHI_GOLDEN
    bulk_gap:       float = 0.0
    in_gap_states:  int   = 0
    gap_normalized: float = 0.0
    topological:    bool  = False

    def compute(self) -> "SPTChain":
        L = self.sites
        H = np.zeros((L, L))
        for i in range(L - 1):
            t = self.t2 if i % 2 == 0 else self.t1
            H[i, i + 1] = t
            H[i + 1, i] = t
        ev = np.sort(np.real(linalg.eigvalsh(H)))
        neg = ev[ev < -1e-6]; pos = ev[ev > 1e-6]
        self.bulk_gap      = float(pos[0] - neg[-1]) if len(neg) and len(pos) else 0.0
        self.in_gap_states = int(np.sum(np.abs(ev) < self.bulk_gap / 2))
        self.gap_normalized = self.bulk_gap / float(np.abs(ev).max() or 1.0)
        self.topological   = self.in_gap_states > 0
        return self


@dataclass
class BridgeResult:
    """Result of quantum↔biology spectral gap bridge test."""
    cancer_fiedler:    float = 0.0
    normal_fiedler:    float = 0.0
    gap_ratio:         float = 0.0
    quantum_gap:       float = 0.0
    scale_ratio:       float = 0.0     # Δmetabolic / quantum_gap
    gap_suppression:   float = 0.0
    cancer_gr_ratio:   float = 0.0     # cancer gap/gap₂ vs φ
    bridge_confirmed:  bool  = False
    reasons:           List[str] = field(default_factory=list)
    verdict:           str  = ""


def _warburg_adjacency(n: int = 8) -> tuple[List[str], np.ndarray]:
    nodes = ["Glucose", "G6P", "Pyruvate", "Lactate",
             "Acetyl-CoA", "TCA", "OXPHOS", "Biomass"]
    A = np.zeros((n, n))
    idx = {nd: i for i, nd in enumerate(nodes)}
    def e(a, b, w): A[idx[a], idx[b]] = w; A[idx[b], idx[a]] = w
    e("Glucose","G6P",2.8); e("G6P","Pyruvate",2.5)
    e("Pyruvate","Lactate",3.2); e("Pyruvate","Acetyl-CoA",0.4)
    e("Acetyl-CoA","TCA",0.5); e("TCA","OXPHOS",0.4)
    e("G6P","Biomass",1.8); e("TCA","Biomass",0.6); e("OXPHOS","Biomass",0.3)
    return nodes, A

def _normal_adjacency(n: int = 8) -> tuple[List[str], np.ndarray]:
    nodes = ["Glucose", "G6P", "Pyruvate", "Lactate",
             "Acetyl-CoA", "TCA", "OXPHOS", "Biomass"]
    A = np.zeros((n, n))
    idx = {nd: i for i, nd in enumerate(nodes)}
    def e(a, b, w): A[idx[a], idx[b]] = w; A[idx[b], idx[a]] = w
    e("Glucose","G6P",1.0); e("G6P","Pyruvate",1.0)
    e("Pyruvate","Lactate",0.3); e("Pyruvate","Acetyl-CoA",1.2)
    e("Acetyl-CoA","TCA",1.2); e("TCA","OXPHOS",1.4)
    e("G6P","Biomass",0.4); e("TCA","Biomass",0.4); e("OXPHOS","Biomass",0.8)
    return nodes, A


class QuantumBioBridge:
    """Gen 6.9 — Quantum-Biology Bridge analysis engine."""

    def __init__(self) -> None:
        self._cancer:  Optional[MetabolicNetwork] = None
        self._normal:  Optional[MetabolicNetwork] = None
        self._spt:     Optional[SPTChain]         = None
        self._bridge:  Optional[BridgeResult]     = None
        self._run      = False

    def run_analysis(self, spt_sites: int = 20, spt_t2: float = PHI_GOLDEN) -> BridgeResult:
        nodes_c, A_c = _warburg_adjacency()
        nodes_n, A_n = _normal_adjacency()
        self._cancer = MetabolicNetwork("Cancer (Warburg)", nodes_c, A_c).compute()
        self._normal = MetabolicNetwork("Normal cell",     nodes_n, A_n).compute()
        self._spt    = SPTChain(sites=spt_sites, t2=spt_t2).compute()
        self._bridge = self._compute_bridge()
        self._run    = True
        return self._bridge

    def _compute_bridge(self) -> BridgeResult:
        c, n, s = self._cancer, self._normal, self._spt
        gap_ratio   = c.fiedler_gap / n.fiedler_gap if n.fiedler_gap > 1e-10 else 0
        delta_m     = abs(c.fiedler_gap - n.fiedler_gap)
        scale_ratio = delta_m / SPT_HARDWARE_GAP if SPT_HARDWARE_GAP > 0 else 0
        suppression = 1.0 - c.gap_normalized / n.gap_normalized if n.gap_normalized > 0 else 0
        reasons: List[str] = []
        confirmed = False
        if abs(gap_ratio - 1 / PHI_GOLDEN) < 0.15:
            confirmed = True
            reasons.append(f"gap_ratio ≈ 1/φ ({gap_ratio:.3f})")
        if abs(gap_ratio - PHI_GOLDEN) < 0.15:
            confirmed = True
            reasons.append(f"gap_ratio ≈ φ ({gap_ratio:.3f})")
        if abs(scale_ratio - PHI_GOLDEN) < 0.5:
            confirmed = True
            reasons.append(f"scale_ratio ≈ φ ({scale_ratio:.3f})")
        if abs(c.gap_ratio - PHI_GOLDEN) < 0.3 and s.topological:
            confirmed = True
            reasons.append(f"cancer gap/gap₂={c.gap_ratio:.3f} ≈ φ + topological SPT")
        verdict = "PARTIAL" if confirmed else "NOT CONFIRMED (simple 8-node model)"
        return BridgeResult(
            cancer_fiedler=c.fiedler_gap, normal_fiedler=n.fiedler_gap,
            gap_ratio=gap_ratio, quantum_gap=s.gap_normalized,
            scale_ratio=scale_ratio, gap_suppression=suppression,
            cancer_gr_ratio=c.gap_ratio, bridge_confirmed=confirmed,
            reasons=reasons, verdict=verdict
        )

    def summary(self) -> str:
        if not self._run:
            self.run_analysis()
        b = self._bridge
        c, n, s = self._cancer, self._normal, self._spt
        lines = [
            "═" * 55,
            "OSIRIS QUANTUM-BIO BRIDGE (P8)",
            "═" * 55,
            f"Cancer Fiedler gap:  {c.fiedler_gap:.4f}",
            f"Normal Fiedler gap:  {n.fiedler_gap:.4f}",
            f"Gap ratio (C/N):     {b.gap_ratio:.4f}  (1/φ={1/PHI_GOLDEN:.4f})",
            f"Quantum SPT gap:     {s.bulk_gap:.4f}  (topological={s.topological})",
            f"Scale ratio Δm/q:    {b.scale_ratio:.4f}  (φ={PHI_GOLDEN:.4f})",
            f"Bridge:              {b.verdict}",
        ]
        if b.reasons:
            lines += ["Reasons: " + "; ".join(b.reasons)]
        return "\n".join(lines)

    def ingest_to_graph(self) -> int:
        """Add P8 experiment node to research graph. Returns edges added."""
        if not self._run:
            self.run_analysis()
        try:
            from dnalang_sdk.nclm.research_graph import (
                get_research_graph, ExperimentNode, EdgeType
            )
            b = self._bridge; c = self._cancer; s = self._spt
            g = get_research_graph()
            exp = ExperimentNode(
                id="EXP-QUANTUM-BIO-BRIDGE-P8",
                title="P8: SPT spectral gap vs Warburg metabolic network topology",
                domain="drug_discovery",
                summary=(
                    f"Cancer Fiedler={c.fiedler_gap:.4f}, Normal={self._normal.fiedler_gap:.4f}, "
                    f"ratio={b.gap_ratio:.4f}. SSH t₂/t₁=φ: bulk_gap={s.bulk_gap:.4f}, "
                    f"topological={s.topological}. Bridge: {b.verdict}."
                ),
                hypothesis="P8: SPT spectral gap → metabolic network rigidity proxy",
                method="8-node Warburg graph Laplacian + SSH chain diagonalization",
                result=b.verdict,
                status="completed",
                backend="simulation_scipy_linalg",
                keywords=["quantum_biology", "warburg", "spt", "spectral_gap", "p8", "bridge"]
            )
            g.add_node(exp)
            etype = EdgeType.SUPPORTS if b.bridge_confirmed else EdgeType.RELATES_TO
            note = f"Bridge {b.verdict}: ratio={b.gap_ratio:.3f}, reasons={b.reasons}"
            added = 0
            for target in ["CLM-TPSM-SPECTRAL-GAP", "CLM-ONCOLOGY-GAP-PROXY"]:
                e = g.connect("EXP-QUANTUM-BIO-BRIDGE-P8", target, etype, note=note)
                if e: added += 1
            g.save()
            return added
        except Exception:
            return 0

    @property
    def cancer(self) -> Optional[MetabolicNetwork]: return self._cancer
    @property
    def normal(self) -> Optional[MetabolicNetwork]: return self._normal
    @property
    def spt(self) -> Optional[SPTChain]:            return self._spt
    @property
    def bridge(self) -> Optional[BridgeResult]:     return self._bridge


_INSTANCE: Optional[QuantumBioBridge] = None

def get_quantum_bio_bridge() -> QuantumBioBridge:
    """Singleton accessor."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = QuantumBioBridge()
    return _INSTANCE
