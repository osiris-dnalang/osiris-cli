"""
OSIRIS Research Context Assembler — saturate every LLM call with your research.

Before each call to tool_llm(), this assembler queries the ResearchGraph for
nodes relevant to the user's query and formats them into a structured briefing
that gets injected into the system prompt.

The difference: instead of "you work on quantum physics and oncology",
the LLM gets:

  Relevant prior work:
  [EXPERIMENT | quantum]  chi_pc coherence at 3.2kT — ibm_fez
    Result: θ_lock preserved at 51.843°, fidelity 0.946
    Status: confirmed
    ← [CONTRADICTS] Claim: decoherence dominates above 1.8kT

  [CLAIM | oncology]  BRCA2 quantum tunnelling hypothesis
    Claim: Proton transfer across the BRCA2 binding cleft involves
           coherent quantum tunnelling at physiological temperature
    Confidence: 0.62
    Open: No direct measurement of tunnelling rate in BRCA2 context

  UNEXPLORED BRIDGE:
  chi_pc coherence (quantum) ↔ BRCA2 proton transfer (oncology)
    Note: Same Lindblad noise parameters; coherence window overlaps
          physiological timescale of BRCA2 catalytic step

That's what enables contribution rather than calculation.
"""

from __future__ import annotations

import re
from typing import List, Optional, Dict, Any

from .research_graph import (
    ResearchGraph, GraphNode, TheoreticalClaim, ExperimentNode,
    CompoundNode, ResearchQuestion, NodeType, EdgeType, Domain,
    get_research_graph,
)


# ── Token budget ──────────────────────────────────────────────────────────────
# Approximate chars-per-token ≈ 4; keep injected context < 3500 chars to leave
# room for the base system prompt and the user's actual query.
DEFAULT_BUDGET = 3200


class ResearchContextAssembler:
    """
    Builds a structured research context block from the knowledge graph,
    tuned to the current query.
    """

    def __init__(self, graph: Optional[ResearchGraph] = None,
                 budget: int = DEFAULT_BUDGET):
        self._graph  = graph or get_research_graph()
        self._budget = budget

    # ── Public API ────────────────────────────────────────────────────────────

    def assemble(self, query: str) -> str:
        """
        Return a context string to inject into the LLM system prompt.
        Returns "" if the graph is empty or nothing is relevant.
        """
        if not self._graph._nodes:
            return ""

        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))

        # 1. Find relevant nodes
        relevant = self._graph.query(query, top_k=6)

        # 2. Pull immediate neighborhoods for each top node
        #    to surface connected evidence/claims
        neighbourhood_nodes: List[GraphNode] = []
        neighbourhood_edges = []
        seen: set = {n.id for n in relevant}
        for node in relevant[:3]:
            nbrs, edges = self._graph.get_neighborhood(node.id, depth=1)
            for n in nbrs:
                if n.id not in seen:
                    neighbourhood_nodes.append(n)
                    seen.add(n.id)
            neighbourhood_edges.extend(edges)

        # 3. Pull active contradictions and bridges for this query
        contradictions = [
            c for c in self._graph.find_contradictions()
            if c["claim"].keyword_score(query_words) > 0
        ][:2]

        bridges = [
            b for b in self._graph.find_bridges()
            if (b["source"].keyword_score(query_words) > 0 or
                b["target"].keyword_score(query_words) > 0)
        ][:3]

        # 4. High-priority open questions that overlap this query
        questions = [
            n for n in self._graph.all_nodes(node_type=NodeType.QUESTION)
            if n.keyword_score(query_words) > 0 and
               getattr(n, "priority", 0) >= 7
        ][:2]

        # 5. Assemble sections
        sections: List[str] = []

        if relevant:
            sections.append(self._section_relevant(relevant))

        if neighbourhood_nodes:
            sections.append(self._section_connected(neighbourhood_nodes,
                                                     neighbourhood_edges))

        if contradictions:
            sections.append(self._section_contradictions(contradictions))

        if bridges:
            sections.append(self._section_bridges(bridges))

        if questions:
            sections.append(self._section_questions(questions))

        # 6. Graph pulse — brief statistics
        sections.append(self._section_pulse())

        if not any(s.strip() for s in sections):
            return ""

        header = (
            "━━━━ RESEARCH KNOWLEDGE GRAPH CONTEXT ━━━━\n"
            "The following is drawn from your personal research graph — "
            "prior experiments, theoretical claims, compounds, and open "
            "questions that are relevant to this query.\n"
        )
        body = "\n\n".join(s for s in sections if s.strip())
        footer = "━━━━ END RESEARCH CONTEXT ━━━━"

        full = f"{header}\n{body}\n\n{footer}"

        # Trim to budget
        if len(full) > self._budget:
            full = full[:self._budget - 3] + "..."

        return full

    # ── Section formatters ────────────────────────────────────────────────────

    def _section_relevant(self, nodes: List[GraphNode]) -> str:
        lines = ["RELEVANT PRIOR WORK:"]
        for node in nodes:
            lines.append(self._graph.format_node_brief(node, include_edges=True))
            lines.append("")
        return "\n".join(lines).strip()

    def _section_connected(self, nodes: List[GraphNode],
                           edges: List) -> str:
        lines = ["CONNECTED NODES (1-hop neighbourhood):"]
        for node in nodes[:4]:
            lines.append(f"  [{node.node_type.upper()} | {node.domain}]  {node.title}")
            if node.summary:
                lines.append(f"    {node.summary[:160]}")
        return "\n".join(lines)

    def _section_contradictions(self, contradictions: List[Dict]) -> str:
        lines = ["⚠  ACTIVE CONTRADICTIONS (unresolved — highest priority targets):"]
        for c in contradictions:
            claim    = c["claim"]
            sup_n    = len([x for x in c["supporting"]    if x])
            con_n    = len([x for x in c["contradicting"] if x])
            lines.append(
                f"  CLAIM: {claim.title}\n"
                f"    Supporting experiments: {sup_n}  |  Contradicting: {con_n}\n"
                f"    → This contradiction needs a decisive experiment."
            )
        return "\n".join(lines)

    def _section_bridges(self, bridges: List[Dict]) -> str:
        lines = ["✦  UNEXPLORED BRIDGES (cross-domain — potentially profound):"]
        for b in bridges:
            src, tgt, edge = b["source"], b["target"], b["edge"]
            lines.append(
                f"  {src.title} ({src.domain})\n"
                f"    ↔ {tgt.title} ({tgt.domain})\n"
                + (f"    Note: {edge.note}" if edge.note else "")
            )
        return "\n".join(lines)

    def _section_questions(self, questions: List[GraphNode]) -> str:
        lines = ["OPEN HIGH-PRIORITY QUESTIONS:"]
        for q in questions:
            prio = getattr(q, "priority", 5)
            lines.append(
                f"  [P{prio}] {getattr(q, 'question', q.title)}"
            )
        return "\n".join(lines)

    def _section_pulse(self) -> str:
        s = self._graph.stats()
        return (
            f"GRAPH PULSE: {s['total_nodes']} nodes · "
            f"{s['total_edges']} edges · "
            f"{s.get('contradictions', 0)} contradictions · "
            f"{s.get('bridges', 0)} unexplored bridges"
        )


# ── Module-level helpers ──────────────────────────────────────────────────────

_assembler_singleton: Optional[ResearchContextAssembler] = None


def get_assembler() -> ResearchContextAssembler:
    global _assembler_singleton
    if _assembler_singleton is None:
        _assembler_singleton = ResearchContextAssembler()
    return _assembler_singleton


def assemble_research_context(query: str) -> str:
    """
    Convenience function: assemble research context for a query.
    Returns "" if graph is empty or no relevant context found.
    """
    try:
        return get_assembler().assemble(query)
    except Exception:
        return ""
