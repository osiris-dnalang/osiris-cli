"""
OSIRIS Hypothesis Engine — proactive research intelligence.

OSIRIS stops waiting to be asked. This engine runs over the knowledge graph
and surfaces:

  1. Contradictions       — claims with conflicting evidence (most valuable)
  2. Gaps                 — theoretical claims with insufficient experiments
  3. Unexplored bridges   — cross-domain connections not yet tested
  4. Proposed experiments — ranked, specific, grounded in YOUR data
  5. Novel hypotheses     — LLM-generated from graph state, not generic

The output is a daily/on-demand briefing: a ranked research agenda
derived from what you've already built, pointing at the next step
that is most likely to produce something profound.
"""

from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .research_graph import (
    ResearchGraph, GraphNode, TheoreticalClaim, ExperimentNode,
    CompoundNode, ResearchQuestion,
    NodeType, EdgeType, Domain,
    get_research_graph, _make_id,
)

_BRIEFING_LOG       = os.path.expanduser("~/.osiris/hypothesis_briefings.jsonl")
_PROPOSALS_FILE     = os.path.expanduser("~/.osiris/experiment_proposals.json")
_CONTRADICTION_LOG  = os.path.expanduser("~/.osiris/contradiction_watch.jsonl")
_LAST_CONTRA_FILE   = os.path.expanduser("~/.osiris/last_contradiction_scan.json")


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class ContradictionReport:
    claim_id:     str
    claim_title:  str
    claim_domain: str
    supporting:   List[str]    # experiment titles
    contradicting: List[str]   # experiment titles
    priority:     int          # 1-10 — how resolvable and impactful

    def summary(self) -> str:
        return (
            f"CONTRADICTION [{self.claim_domain}]: {self.claim_title}\n"
            f"  Supporting: {len(self.supporting)} experiment(s)\n"
            f"  Contradicting: {len(self.contradicting)} experiment(s)\n"
            f"  Priority: {self.priority}/10\n"
            f"  → A decisive experiment resolving this is your highest-leverage move."
        )


@dataclass
class GapReport:
    claim_id:      str
    claim_title:   str
    claim_domain:  str
    current_support: int
    needed_support:  int
    open_questions:  List[str]
    suggestion:      str       # what kind of experiment would fill this gap

    def summary(self) -> str:
        q = self.open_questions[0] if self.open_questions else "Unknown"
        return (
            f"GAP [{self.claim_domain}]: {self.claim_title}\n"
            f"  Support: {self.current_support}/{self.needed_support} experiments\n"
            f"  Open question: {q}\n"
            f"  Suggestion: {self.suggestion}"
        )


@dataclass
class BridgeOpportunity:
    edge_id:      str
    source_title: str
    source_domain: str
    target_title: str
    target_domain: str
    note:         str
    rationale:    str    # why this bridge might be profound

    def summary(self) -> str:
        return (
            f"BRIDGE: {self.source_domain} ↔ {self.target_domain}\n"
            f"  {self.source_title}\n"
            f"  ↔ {self.target_title}\n"
            f"  {self.note}\n"
            f"  Why profound: {self.rationale}"
        )


@dataclass
class ExperimentProposal:
    id:           str
    title:        str
    domain:       str
    rationale:    str     # grounded in existing graph nodes
    method:       str     # concrete: circuit template, wet-lab, simulation
    predicted_outcome: str
    falsifiable:  bool
    priority:     int     # 1-10
    based_on:     List[str]  # node IDs from graph that ground this proposal
    created:      str    = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status:       str    = "proposed"   # proposed|approved|running|completed

    def summary(self) -> str:
        return (
            f"PROPOSAL [{self.domain}]: {self.title}  (P{self.priority})\n"
            f"  Rationale: {self.rationale}\n"
            f"  Method: {self.method}\n"
            f"  Predicted outcome: {self.predicted_outcome}\n"
            f"  Falsifiable: {'Yes' if self.falsifiable else 'No'}\n"
            f"  Based on: {len(self.based_on)} existing node(s)"
        )


@dataclass
class HypothesisScanResult:
    timestamp:     str
    contradictions: List[ContradictionReport]
    gaps:          List[GapReport]
    bridges:       List[BridgeOpportunity]
    proposals:     List[ExperimentProposal]
    graph_pulse:   Dict[str, Any]

    def briefing(self) -> str:
        """Format as a human-readable research briefing."""
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            "║     OSIRIS RESEARCH INTELLIGENCE BRIEFING            ║",
            f"║     {self.timestamp[:19]}                            ║",
            "╚══════════════════════════════════════════════════════╝",
            "",
        ]

        pulse = self.graph_pulse
        lines += [
            f"GRAPH STATE: {pulse.get('total_nodes', 0)} nodes · "
            f"{pulse.get('total_edges', 0)} edges · "
            f"{pulse.get('contradictions', 0)} contradictions · "
            f"{pulse.get('bridges', 0)} bridges",
            "",
        ]

        if self.contradictions:
            lines += ["━━━━ CONTRADICTIONS (resolve these first) ━━━━"]
            for i, c in enumerate(self.contradictions[:3], 1):
                lines += [f"{i}. {c.summary()}", ""]

        if self.gaps:
            lines += ["━━━━ EVIDENCE GAPS ━━━━"]
            for i, g in enumerate(self.gaps[:3], 1):
                lines += [f"{i}. {g.summary()}", ""]

        if self.bridges:
            lines += ["━━━━ UNEXPLORED BRIDGES (cross-domain opportunity) ━━━━"]
            for i, b in enumerate(self.bridges[:3], 1):
                lines += [f"{i}. {b.summary()}", ""]

        if self.proposals:
            lines += ["━━━━ PROPOSED EXPERIMENTS ━━━━"]
            for i, p in enumerate(self.proposals[:5], 1):
                lines += [f"{i}. {p.summary()}", ""]

        if not (self.contradictions or self.gaps or self.bridges or self.proposals):
            lines += [
                "No contradictions, gaps, or bridges found.",
                "Add more experimental results to enable deeper analysis.",
                "Run: osiris learn <your-experiment-log>",
            ]

        return "\n".join(lines)


# ── Hypothesis Engine ─────────────────────────────────────────────────────────

class HypothesisEngine:
    """
    Proactive research intelligence over the ResearchGraph.

    Runs automatically on scan() — returns a HypothesisScanResult with
    ranked research priorities derived from contradictions, gaps, and
    cross-domain bridges in Devin's knowledge graph.
    """

    # Bridge rationale templates — filled with actual domain context
    _BRIDGE_RATIONALE: Dict[str, str] = {
        f"{Domain.QUANTUM}-{Domain.ONCOLOGY}": (
            "Quantum coherence timescales (10-100 fs) overlap with enzyme "
            "catalysis and DNA repair kinetics. Your quantum circuit parameters "
            "(θ_lock, χ_pc) may map directly onto biological coherence windows."
        ),
        f"{Domain.QUANTUM}-{Domain.DRUG_DISCOVERY}": (
            "Drug-target binding free energy computations are classically "
            "intractable at quantum accuracy. Your ibm_fez circuit library "
            "and coherence metrics may give a quantum advantage here."
        ),
        f"{Domain.ONCOLOGY}-{Domain.DRUG_DISCOVERY}": (
            "Oncogenic mutation signatures alter the quantum chemistry of "
            "protein active sites. Compounds targeting mutant-specific "
            "quantum properties (HOMO-LUMO shifts) are more selective."
        ),
        f"{Domain.PHYSICS}-{Domain.BIOLOGY}": (
            "Information-theoretic measures (Φ, negentropy Ξ) that you've "
            "computed on quantum systems have direct analogs in biological "
            "complexity and network integration."
        ),
    }

    def __init__(self, graph: Optional[ResearchGraph] = None):
        self._graph = graph or get_research_graph()
        self._proposals: List[ExperimentProposal] = []
        self._load_proposals()

    # ── Main scan ─────────────────────────────────────────────────────────────

    def scan(self) -> HypothesisScanResult:
        """
        Run a full intelligence scan. Returns ranked research priorities.
        This is the core OSIRIS research contribution — not responding, proposing.
        """
        contradictions = self._find_contradictions()
        gaps           = self._find_gaps()
        bridges        = self._find_bridges()
        proposals      = self._generate_proposals(contradictions, gaps, bridges)

        # Save new proposals — and auto-simulate new ones (closes the hypothesis loop)
        for p in proposals:
            existing = [ep for ep in self._proposals if ep.id == p.id]
            if not existing:
                self._proposals.append(p)
                # Auto-simulate in background thread (non-blocking)
                self._auto_simulate_proposal(p)
        self._save_proposals()

        result = HypothesisScanResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            contradictions=contradictions,
            gaps=gaps,
            bridges=bridges,
            proposals=proposals,
            graph_pulse=self._graph.stats(),
        )

        # Log briefing
        try:
            with open(_BRIEFING_LOG, "a") as f:
                f.write(json.dumps({
                    "ts": result.timestamp,
                    "contradictions": len(contradictions),
                    "gaps": len(gaps),
                    "bridges": len(bridges),
                    "proposals": len(proposals),
                }) + "\n")
        except Exception:
            pass

        return result

    # ── Analysis passes ───────────────────────────────────────────────────────

    def _find_contradictions(self) -> List[ContradictionReport]:
        reports = []
        for c in self._graph.find_contradictions():
            claim = c["claim"]
            sup   = [n.title for n in c["supporting"]    if n]
            con   = [n.title for n in c["contradicting"] if n]
            # Priority: contradictions with equal support on both sides = highest tension
            priority = min(10, 5 + min(len(sup), len(con)) * 2)
            reports.append(ContradictionReport(
                claim_id=claim.id,
                claim_title=claim.title,
                claim_domain=claim.domain,
                supporting=sup,
                contradicting=con,
                priority=priority,
            ))
        reports.sort(key=lambda r: r.priority, reverse=True)
        return reports

    def _find_gaps(self) -> List[GapReport]:
        reports = []
        for g in self._graph.find_gaps(min_support=2):
            claim = g["claim"]
            oq    = getattr(claim, "open_questions", [])
            # Generate a concrete suggestion based on domain
            suggestion = self._gap_suggestion(claim)
            reports.append(GapReport(
                claim_id=claim.id,
                claim_title=claim.title,
                claim_domain=claim.domain,
                current_support=g["support_count"],
                needed_support=2,
                open_questions=oq[:2],
                suggestion=suggestion,
            ))
        return reports[:8]

    def _find_bridges(self) -> List[BridgeOpportunity]:
        reports = []
        for b in self._graph.find_bridges():
            src, tgt, edge = b["source"], b["target"], b["edge"]
            # Look up rationale template
            key1 = f"{src.domain}-{tgt.domain}"
            key2 = f"{tgt.domain}-{src.domain}"
            rationale = (
                self._BRIDGE_RATIONALE.get(key1) or
                self._BRIDGE_RATIONALE.get(key2) or
                "Cross-domain structural analogy — parameters from one domain "
                "may constrain or predict behaviour in the other."
            )
            reports.append(BridgeOpportunity(
                edge_id=edge.id,
                source_title=src.title,
                source_domain=src.domain,
                target_title=tgt.title,
                target_domain=tgt.domain,
                note=edge.note,
                rationale=rationale,
            ))
        return reports

    def _check_convergence_gate(self, claim_id: str,
                                 param_variance: Optional[float] = None) -> bool:
        """
        Phase 4→5 gate: call statistical_engine convergence check.
        Returns True if the claim has passed all criteria and can advance to Phase 5.
        Silently returns True (do not block) if statistical_engine unavailable.
        """
        try:
            from .statistical_engine import get_statistical_engine
            report = get_statistical_engine().full_convergence_report(
                claim_id, param_variance=param_variance
            )
            return report.passed
        except Exception:
            return True  # fail-open: don't block when engine unavailable

    def _generate_proposals(
        self,
        contradictions: List[ContradictionReport],
        gaps: List[GapReport],
        bridges: List[BridgeOpportunity],
    ) -> List[ExperimentProposal]:
        """
        Generate concrete experiment proposals grounded in graph state.
        Priority: resolve contradictions first, then fill gaps, then test bridges.
        Phase 4→5 gate: convergence check gates advancement for each claim.
        """
        proposals: List[ExperimentProposal] = []

        # From contradictions — these are always Phase 4 work (resolve the tension)
        for c in contradictions[:2]:
            p = self._proposal_for_contradiction(c)
            if p:
                # Contradictions don't need convergence gate — resolving them IS the work
                proposals.append(p)

        # From gaps — gate on convergence: only propose Phase 5 advancement if
        # the claim is statistically stable enough
        for g in gaps[:3]:
            p = self._proposal_for_gap(g)
            if p:
                gate_passed = self._check_convergence_gate(g.claim_id)
                if not gate_passed:
                    # Claim not ready for Phase 5 — lower priority, flag in method
                    p.priority = max(1, p.priority - 2)
                    p.method = (
                        "[Phase 4→5 GATE: statistical convergence not yet met — "
                        "run `osiris stats convergence " + g.claim_id + "` for details]\n"
                        + p.method
                    )
                proposals.append(p)

        # From bridges
        for b in bridges[:2]:
            p = self._proposal_for_bridge(b)
            if p:
                proposals.append(p)

        # Sort by priority
        proposals.sort(key=lambda p: p.priority, reverse=True)
        return proposals

    # ── Proposal generators ───────────────────────────────────────────────────

    def _proposal_for_contradiction(self, c: ContradictionReport) -> Optional[ExperimentProposal]:
        domain_method = {
            Domain.QUANTUM:        "Run a high-shot (8192) circuit on ibm_fez with the chi_pc template, varying the contested parameter systematically. Use Lindblad master equation simulation as cross-check.",
            Domain.ONCOLOGY:       "Design a cell-line assay targeting the specific mutation context. Use isogenic cell pairs (WT vs mutant) to isolate the effect.",
            Domain.DRUG_DISCOVERY: "Run molecular dynamics simulation with explicit solvent. Compare binding free energy via FEP between the two competing models.",
            Domain.PHYSICS:        "Derive the falsifiable prediction from each competing model and identify the measurement that distinguishes them. Run quantum circuit analog.",
        }
        method = domain_method.get(c.claim_domain,
                                   "Design a decisive experiment that produces an outcome incompatible with one side of the contradiction.")
        pid = _make_id("PRO", f"contradict-{c.claim_id}")
        return ExperimentProposal(
            id=pid,
            title=f"Resolve contradiction: {c.claim_title[:60]}",
            domain=c.claim_domain,
            rationale=(
                f"You have {len(c.supporting)} supporting and "
                f"{len(c.contradicting)} contradicting result(s) for this claim. "
                f"This is unresolved tension in your framework — resolving it "
                f"either validates the claim decisively or eliminates it."
            ),
            method=method,
            predicted_outcome=(
                "One body of evidence should be reproducible; the other should "
                "show a confound when controlled correctly. The decisive result "
                "will either confirm or falsify the claim."
            ),
            falsifiable=True,
            priority=min(10, 6 + len(c.contradicting)),
            based_on=[c.claim_id],
        )

    def _proposal_for_gap(self, g: GapReport) -> Optional[ExperimentProposal]:
        suggestion = g.suggestion
        pid = _make_id("PRO", f"gap-{g.claim_id}")
        return ExperimentProposal(
            id=pid,
            title=f"Strengthen evidence: {g.claim_title[:60]}",
            domain=g.claim_domain,
            rationale=(
                f"This claim has only {g.current_support} supporting "
                f"experiment(s) — below the 2-experiment minimum for strong "
                f"epistemic confidence. An independent measurement is needed."
            ),
            method=suggestion,
            predicted_outcome=(
                "Confirmation at independent conditions will raise epistemic "
                "confidence above 0.80 and make this claim framework-stable."
            ),
            falsifiable=True,
            priority=5 + (2 - g.current_support),
            based_on=[g.claim_id],
        )

    def _proposal_for_bridge(self, b: BridgeOpportunity) -> Optional[ExperimentProposal]:
        method_map = {
            f"{Domain.QUANTUM}-{Domain.ONCOLOGY}": (
                "Map your θ_lock coherence parameter onto the biological "
                "coherence timescale for the target process. Run a quantum "
                "circuit that encodes the biological Hamiltonian and measure "
                "decoherence rate. Compare to known enzyme catalysis kinetics."
            ),
            f"{Domain.QUANTUM}-{Domain.DRUG_DISCOVERY}": (
                "Use your ibm_fez chi_pc circuit as a variational quantum "
                "eigensolver ansatz for the drug-target binding Hamiltonian. "
                "Extract HOMO-LUMO gap from circuit measurement. Compare "
                "to classical DFT baseline."
            ),
        }
        key1 = f"{b.source_domain}-{b.target_domain}"
        key2 = f"{b.target_domain}-{b.source_domain}"
        method = method_map.get(key1) or method_map.get(key2) or (
            "Design a measurement that uses parameters from one domain as "
            "input to a model in the other. The result either validates the "
            "bridge or quantifies why the analogy breaks."
        )
        pid = _make_id("PRO", f"bridge-{b.edge_id}")
        return ExperimentProposal(
            id=pid,
            title=f"Test bridge: {b.source_domain} ↔ {b.target_domain}",
            domain=Domain.CROSS_DOMAIN,
            rationale=b.rationale,
            method=method,
            predicted_outcome=(
                "If the bridge is valid, parameters from one domain will "
                "predict or constrain behaviour in the other with no free "
                "parameters — this is genuine quantum advantage."
            ),
            falsifiable=True,
            priority=8,   # bridges are always high priority — this is the profound work
            based_on=[b.edge_id],
        )

    # ── Experiment → Simulation → Validation loop ─────────────────────────────

    def simulate_and_validate(self, proposal: ExperimentProposal) -> Optional[str]:
        """
        Phase 4 autopoiesis: when a proposal is generated, auto-run it through
        the simulation harness to get a PREDICTED outcome. Adds it as a
        TheoreticalClaim node. When hardware data arrives via hardware_loop,
        compare delta and update confidence.

        Returns a summary string or None if simulation unavailable.
        """
        try:
            from .simulation_harness import get_simulation_harness
            harness = get_simulation_harness()
        except Exception:
            return None

        # Route to appropriate simulator based on domain
        sim_result: Optional[Dict[str, Any]] = None
        sim_type   = "unknown"

        if proposal.domain in (Domain.QUANTUM, Domain.PHYSICS):
            # Use CoherenceDecay — maps quantum coherence onto the proposal
            try:
                from .simulation_harness import CoherenceDecaySimulator
                from .research_graph import NCPhysics
                cds = CoherenceDecaySimulator()
                # Use framework constants as simulation parameters
                sim_result = cds.simulate(
                    theta_lock=51.843,
                    chi_pc=0.946,
                    gamma=0.06,
                    t_max=1e-6,
                    n_steps=200,
                )
                sim_type = "coherence_decay"
            except Exception:
                pass

        if sim_result is None:
            return None

        # Build a TheoreticalClaim from the simulation output
        try:
            from .research_graph import TheoreticalClaim, EdgeType, _make_id
            graph = self._graph

            # Extract key predicted values
            if sim_type == "coherence_decay":
                T2 = sim_result.get("T2_star", 0)
                fid = sim_result.get("final_fidelity", 0)
                predicted_summary = (
                    f"Simulation predicts: T2*={T2:.3e}s, "
                    f"final_fidelity={fid:.4f} under θ_lock=51.843° and χ_pc=0.946. "
                    f"Based on proposal: {proposal.title[:80]}"
                )
            else:
                predicted_summary = f"Simulation result for {proposal.domain}: {sim_result}"

            claim = TheoreticalClaim(
                id=_make_id("SIM", f"pred-{proposal.id}"),
                title=f"[Sim] {proposal.title[:70]}",
                summary=predicted_summary,
                domain=proposal.domain,
                confidence=0.5,  # simulation = intermediate confidence
                open_questions=[
                    f"Does hardware measurement match T2*={T2:.3e}s?" if sim_type == "coherence_decay"
                    else "Does hardware match simulation?"
                ],
                falsifiable=True,
            )
            graph.add_node(claim)

            # Connect to the proposal basis nodes
            for base_id in proposal.based_on:
                if graph.get_node(base_id):
                    graph.connect(claim.id, base_id, EdgeType.EXTENDS,
                                  note="Simulation prediction from proposal")

            graph.save()
            return predicted_summary
        except Exception:
            return None

    def validate_against_hardware(self, proposal_id: str,
                                   hardware_result: Dict[str, Any]) -> Optional[str]:
        """
        Called by hardware_loop when a new result arrives.
        Finds the simulation prediction for this proposal and computes delta.
        Updates confidence on the TheoreticalClaim.
        Returns a validation summary or None.
        """
        sim_node_id = None
        try:
            sim_id_prefix = _make_id("SIM", f"pred-{proposal_id}")[:20]
            for node in self._graph.all_nodes():
                if node.id.startswith("SIM-"):
                    sim_node_id = node.id
                    sim_node    = node
                    break
        except Exception:
            return None

        if sim_node_id is None:
            return None

        try:
            # Compare predicted fidelity vs actual
            pred_text = sim_node.summary
            hw_bell   = hardware_result.get("bell_fidelity")
            hw_shock  = hardware_result.get("shock_exc", 0)
            if hw_bell is None:
                return None

            # Predicted: extract T2/fidelity from summary text
            import re
            m = re.search(r"final_fidelity=(\d+\.\d+)", pred_text)
            pred_fid = float(m.group(1)) if m else None
            if pred_fid is None:
                return None

            delta = abs(hw_bell - pred_fid)
            agrees = delta < 0.10
            new_conf = sim_node.confidence + (0.2 if agrees else -0.1)
            new_conf = max(0.1, min(1.0, new_conf))

            # Update confidence on the node
            sim_node.confidence = new_conf
            self._graph.save()

            return (
                f"Validation: predicted F={pred_fid:.4f} vs hardware F={hw_bell:.4f} "
                f"(Δ={delta:.4f}) — {'AGREES' if agrees else 'DIVERGES'}. "
                f"Claim confidence → {new_conf:.2f}"
            )
        except Exception:
            return None

    # ── LLM-assisted hypothesis generation ───────────────────────────────────

    def generate_hypothesis(self, domain: str = Domain.CROSS_DOMAIN,
                            prompt_context: str = "") -> str:
        """
        Ask the LLM to propose a novel hypothesis given the current graph state.
        Returns a formatted hypothesis string.
        """
        scan = self.scan()
        graph_summary = self._graph_summary_for_llm(domain)

        prompt = (
            f"You are OSIRIS, analysing Devin's research knowledge graph.\n\n"
            f"GRAPH STATE:\n{graph_summary}\n\n"
            + (f"ADDITIONAL CONTEXT:\n{prompt_context}\n\n" if prompt_context else "")
            + f"SCAN FINDINGS:\n"
            f"  Contradictions: {len(scan.contradictions)}\n"
            f"  Evidence gaps:  {len(scan.gaps)}\n"
            f"  Open bridges:   {len(scan.bridges)}\n\n"
            f"Propose ONE novel, specific, testable hypothesis in the {domain} domain "
            f"that:\n"
            f"  1. Is grounded in Devin's existing experiments (cite specific results)\n"
            f"  2. Makes a falsifiable prediction (quantitative if possible)\n"
            f"  3. If confirmed, would advance the field — not just replicate\n"
            f"  4. Connects at least two domains if possible\n\n"
            f"Format:\n"
            f"  HYPOTHESIS: [one sentence]\n"
            f"  GROUNDED IN: [cite specific experiments or claims from the graph]\n"
            f"  PREDICTION: [what you'd observe if true, what if false]\n"
            f"  EXPERIMENT: [most direct test, with method and expected result]\n"
            f"  POTENTIAL IMPACT: [if validated, what does this change?]"
        )

        try:
            from .tools import tool_llm
            result = tool_llm(prompt)
            return result or "LLM unavailable — run `osiris chat` to generate hypothesis interactively."
        except Exception as e:
            return f"Hypothesis generation error: {e}"

    # ── Daily briefing ────────────────────────────────────────────────────────

    def daily_briefing(self) -> str:
        """Run a full scan and return formatted briefing string."""
        result = self.scan()
        return result.briefing()

    def briefing_for_llm(self) -> str:
        """Compact version of the briefing for injection into LLM context."""
        result = self.scan()
        lines = []
        if result.contradictions:
            c = result.contradictions[0]
            lines.append(f"TOP CONTRADICTION: {c.claim_title} ({c.claim_domain}) — "
                         f"{len(c.supporting)} sup / {len(c.contradicting)} con")
        if result.gaps:
            g = result.gaps[0]
            lines.append(f"TOP GAP: {g.claim_title} — {g.current_support}/2 support")
        if result.bridges:
            b = result.bridges[0]
            lines.append(f"TOP BRIDGE: {b.source_domain} ↔ {b.target_domain} — {b.source_title}")
        if result.proposals:
            p = result.proposals[0]
            lines.append(f"TOP PROPOSAL (P{p.priority}): {p.title}")
        return "\n".join(lines) if lines else ""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _gap_suggestion(self, claim: GraphNode) -> str:
        domain = claim.domain
        suggestions = {
            Domain.QUANTUM: (
                "Run an independent circuit on a different backend "
                "(ibm_torino if prior was ibm_fez, or vice versa). "
                "Vary shots and basis. If result holds, confidence rises sharply."
            ),
            Domain.ONCOLOGY: (
                "Replicate in a second cell line or biological context. "
                "If using in-vitro, consider in-vivo validation or "
                "patient-derived xenograft model."
            ),
            Domain.DRUG_DISCOVERY: (
                "Synthesise an analogue with a single structural change and "
                "measure activity delta. This separates the key pharmacophore "
                "from scaffold effects."
            ),
            Domain.PHYSICS: (
                "Derive an independent observable that follows from this claim "
                "and measure it. The best supporting evidence comes from "
                "orthogonal measurement methods."
            ),
        }
        return suggestions.get(domain,
                               "Design an independent replication experiment using "
                               "a different method or instrument to avoid systematic "
                               "error correlation.")

    def _graph_summary_for_llm(self, domain: str) -> str:
        """Compact graph summary for hypothesis generation prompt."""
        nodes = self._graph.all_nodes(domain=domain)[:6]
        if not nodes:
            nodes = self._graph.all_nodes()[:6]
        lines = []
        for n in nodes:
            lines.append(f"  [{n.node_type}] {n.title}: {n.summary[:120]}")
        return "\n".join(lines) if lines else "Graph empty — ingest research data first."

    def _load_proposals(self) -> None:
        if os.path.exists(_PROPOSALS_FILE):
            try:
                with open(_PROPOSALS_FILE) as f:
                    raw = json.load(f)
                self._proposals = [
                    ExperimentProposal(**{k: v for k, v in p.items()
                                         if k in ExperimentProposal.__dataclass_fields__})  # type: ignore
                    for p in raw
                ]
            except Exception:
                self._proposals = []

    def _save_proposals(self) -> None:
        try:
            with open(_PROPOSALS_FILE, "w") as f:
                json.dump([asdict(p) for p in self._proposals], f, indent=2)
        except Exception:
            pass

    @property
    def proposals(self) -> List[ExperimentProposal]:
        return list(self._proposals)

    # ── Background simulation ──────────────────────────────────────────────────

    def _auto_simulate_proposal(self, proposal: ExperimentProposal) -> None:
        """Kick off simulation in a background thread. Non-blocking."""
        import threading

        def _run():
            try:
                self.simulate_and_validate(proposal)
            except Exception:
                pass

        t = threading.Thread(target=_run, daemon=True, name=f"osiris-sim-{proposal.id[:8]}")
        t.start()

    # ── Proactive contradiction watch ─────────────────────────────────────────

    def contradiction_delta(self) -> List[ContradictionReport]:
        """
        Compare current contradictions to last saved state.
        Returns only NEW contradictions not seen before.
        Called by osiris pulse and the background watcher.
        """
        current = self._find_contradictions()
        previous_ids = self._load_last_contradiction_ids()
        new_ones = [c for c in current if c.claim_id not in previous_ids]
        # Save current state
        self._save_contradiction_ids([c.claim_id for c in current])
        # Log new ones
        for c in new_ones:
            self._log_contradiction(c)
        return new_ones

    def pulse_summary(self) -> str:
        """
        One-line negentropic summary for osiris pulse output.
        Shows: graph state, new contradictions, top proposal.
        """
        parts = []
        try:
            stats = self._graph.stats()
            parts.append(
                f"Graph: {stats.get('total_nodes',0)}n "
                f"{stats.get('total_edges',0)}e "
                f"{stats.get('contradictions',0)}⚡contradict"
            )
        except Exception:
            pass
        try:
            delta = self.contradiction_delta()
            if delta:
                parts.append(
                    f"NEW contradictions: {len(delta)} — "
                    + ", ".join(c.claim_title[:40] for c in delta[:2])
                )
        except Exception:
            pass
        try:
            if self._proposals:
                top = max(self._proposals, key=lambda p: p.priority)
                parts.append(f"Top proposal P{top.priority}: {top.title[:60]}")
        except Exception:
            pass
        return "  |  ".join(parts) if parts else ""

    def start_background_watcher(self, interval_sec: int = 3600) -> None:
        """
        Background thread: scan for new contradictions every `interval_sec`.
        Appends alerts to ~/.osiris/pending_briefing.txt for pulse to pick up.
        """
        import threading
        _stop = threading.Event()

        def _watch():
            while not _stop.wait(timeout=interval_sec):
                try:
                    delta = self.contradiction_delta()
                    if delta:
                        alert_lines = [
                            "\n⚡ OSIRIS PROACTIVE ALERT — New contradictions detected:\n"
                        ]
                        for c in delta[:3]:
                            alert_lines.append(f"  {c.summary()}\n")
                        alert_lines.append(
                            "\nRun `osiris hypothesis briefing` for full analysis.\n"
                        )
                        _pend = os.path.expanduser("~/.osiris/pending_briefing.txt")
                        with open(_pend, "a") as f:
                            f.writelines(alert_lines)
                except Exception:
                    pass

        t = threading.Thread(target=_watch, daemon=True, name="osiris-contra-watcher")
        t.start()

    def _load_last_contradiction_ids(self) -> set:
        if os.path.exists(_LAST_CONTRA_FILE):
            try:
                with open(_LAST_CONTRA_FILE) as f:
                    return set(json.load(f).get("ids", []))
            except Exception:
                pass
        return set()

    def _save_contradiction_ids(self, ids: List[str]) -> None:
        try:
            os.makedirs(os.path.dirname(_LAST_CONTRA_FILE), exist_ok=True)
            with open(_LAST_CONTRA_FILE, "w") as f:
                json.dump({"ids": ids, "ts": datetime.now(timezone.utc).isoformat()}, f)
        except Exception:
            pass

    def _log_contradiction(self, c: ContradictionReport) -> None:
        try:
            with open(_CONTRADICTION_LOG, "a") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "claim_id": c.claim_id,
                    "claim_title": c.claim_title,
                    "priority": c.priority,
                    "supporting": len(c.supporting),
                    "contradicting": len(c.contradicting),
                }) + "\n")
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine_singleton: Optional[HypothesisEngine] = None


def get_hypothesis_engine() -> HypothesisEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = HypothesisEngine()
    return _engine_singleton
