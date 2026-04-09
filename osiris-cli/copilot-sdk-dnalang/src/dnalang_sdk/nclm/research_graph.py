"""
OSIRIS Research Knowledge Graph — structured scientific memory.

Every insight Devin produces lives here as a typed node connected by
explicit evidence edges. The graph is the difference between OSIRIS
knowing *about* quantum physics and knowing *your* quantum physics.

Node types:
    ExperimentNode    — a quantum circuit run, wet-lab result, simulation
    TheoreticalClaim  — a scientific assertion (confirmed/refuted/open)
    CompoundNode      — drug candidate or molecule with quantum properties
    ConceptNode       — abstract concept or theoretical framework element
    ResearchQuestion  — open question with priority and dependencies

Edge types:
    SUPPORTS          — experiment/claim supports another claim
    CONTRADICTS       — evidence against a claim
    EXTENDS           — builds on prior work
    TESTS             — experiment designed to test a claim
    UNEXPLORED_BRIDGE — potential cross-domain connection (hypothesis)
    QUANTUM_ANALOG    — this phenomenon is the quantum analog of that one
    PRODUCES          — experiment/method produces a compound candidate
    RELATES_TO        — general relationship with a note

Persists to ~/.osiris/research_graph/
"""

from __future__ import annotations

import os
import re
import json
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ── Persistence path ──────────────────────────────────────────────────────────

_GRAPH_DIR  = os.path.expanduser("~/.osiris/research_graph")
_NODES_FILE = os.path.join(_GRAPH_DIR, "nodes.json")
_EDGES_FILE = os.path.join(_GRAPH_DIR, "edges.json")

# ── Edge type constants ───────────────────────────────────────────────────────

class EdgeType:
    SUPPORTS           = "SUPPORTS"
    CONTRADICTS        = "CONTRADICTS"
    EXTENDS            = "EXTENDS"
    TESTS              = "TESTS"
    UNEXPLORED_BRIDGE  = "UNEXPLORED_BRIDGE"
    QUANTUM_ANALOG     = "QUANTUM_ANALOG"
    PRODUCES           = "PRODUCES"
    RELATES_TO         = "RELATES_TO"

# ── Domain constants ──────────────────────────────────────────────────────────

class Domain:
    QUANTUM        = "quantum"
    ONCOLOGY       = "oncology"
    DRUG_DISCOVERY = "drug_discovery"
    SOFTWARE       = "software"
    CROSS_DOMAIN   = "cross_domain"
    PHYSICS        = "physics"
    BIOLOGY        = "biology"
    CHEMISTRY      = "chemistry"
    UNKNOWN        = "unknown"

# ── Node types ────────────────────────────────────────────────────────────────

class NodeType:
    EXPERIMENT = "experiment"
    CLAIM      = "claim"
    COMPOUND   = "compound"
    CONCEPT    = "concept"
    QUESTION   = "question"


# ── Base node ─────────────────────────────────────────────────────────────────

@dataclass
class GraphNode:
    id:        str
    node_type: str
    title:     str
    domain:    str
    summary:   str
    keywords:  List[str] = field(default_factory=list)
    created:   str       = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated:   str       = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata:  Dict[str, Any] = field(default_factory=dict)

    def touch(self):
        self.updated = datetime.now(timezone.utc).isoformat()

    def keyword_score(self, query_words: set) -> float:
        """Return keyword overlap score ∈ [0, 1] with a query word set."""
        searchable = set(
            re.findall(r'\b\w{3,}\b',
                       (self.title + " " + self.summary + " " +
                        " ".join(self.keywords)).lower())
        )
        overlap = len(searchable & query_words)
        return min(overlap / max(len(query_words), 1), 1.0)

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Typed nodes ───────────────────────────────────────────────────────────────

@dataclass
class ExperimentNode(GraphNode):
    """A concrete experiment: circuit run, wet-lab, simulation, analysis."""
    node_type:      str             = field(default=NodeType.EXPERIMENT, init=False)
    hypothesis:     str             = ""
    method:         str             = ""   # circuit template, wet-lab protocol, sim params
    result:         str             = ""   # observed outcome, interpreted
    status:         str             = "open"   # confirmed|refuted|ambiguous|open|in_progress
    backend:        str             = ""   # ibm_fez, ibm_torino, wet_lab, simulation
    quantum_params: Dict[str, Any]  = field(default_factory=dict)
    # e.g. {"gates": 24, "depth": 12, "fidelity": 0.946, "shots": 4096}
    raw_data_path:  str             = ""   # path to raw result file


@dataclass
class TheoreticalClaim(GraphNode):
    """A scientific assertion that can be supported or refuted by experiments."""
    node_type:      str         = field(default=NodeType.CLAIM, init=False)
    statement:      str         = ""
    confidence:     float       = 0.5     # epistemic confidence 0-1
    evidence_count: int         = 0       # supporting experiment count
    refuted_count:  int         = 0       # contradicting experiment count
    open_questions: List[str]   = field(default_factory=list)
    predictions:    List[str]   = field(default_factory=list)   # falsifiable predictions
    source:         str         = ""      # where this claim came from


@dataclass
class CompoundNode(GraphNode):
    """A drug candidate, molecule, or biological agent with quantum properties."""
    node_type:             str              = field(default=NodeType.COMPOUND, init=False)
    smiles:                str              = ""
    formula:               str              = ""
    quantum_properties:    Dict[str, Any]   = field(default_factory=dict)
    # e.g. {"homo_lumo_gap": 5.2, "binding_energy": -8.3, "dipole": 3.1}
    biological_targets:    List[str]        = field(default_factory=list)
    pathways:              List[str]        = field(default_factory=list)
    experimental_activity: Dict[str, Any]   = field(default_factory=dict)
    # e.g. {"IC50_nM": 12.4, "selectivity": "BRCA2", "toxicity": "low"}
    circuit_analog:        str              = ""   # quantum circuit that mimics this


@dataclass
class ConceptNode(GraphNode):
    """An abstract concept, theoretical framework, or research principle."""
    node_type:    str       = field(default=NodeType.CONCEPT, init=False)
    definition:   str       = ""
    equations:    List[str] = field(default_factory=list)
    references:   List[str] = field(default_factory=list)


@dataclass
class ResearchQuestion(GraphNode):
    """An open question — the engine proposes experiments to answer these."""
    node_type:    str       = field(default=NodeType.QUESTION, init=False)
    question:     str       = ""
    priority:     int       = 5    # 1=low, 10=critical
    blocking:     bool      = False   # is this blocking other work?
    dependencies: List[str] = field(default_factory=list)   # node IDs needed first


# ── Edge ──────────────────────────────────────────────────────────────────────

@dataclass
class GraphEdge:
    id:          str
    source_id:   str
    target_id:   str
    edge_type:   str
    weight:      float = 1.0
    note:        str   = ""
    created:     str   = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Serialisation helpers ─────────────────────────────────────────────────────

_NODE_TYPE_MAP = {
    NodeType.EXPERIMENT: ExperimentNode,
    NodeType.CLAIM:      TheoreticalClaim,
    NodeType.COMPOUND:   CompoundNode,
    NodeType.CONCEPT:    ConceptNode,
    NodeType.QUESTION:   ResearchQuestion,
}


def _node_from_dict(d: Dict) -> GraphNode:
    nt   = d.get("node_type", NodeType.CONCEPT)
    cls  = _NODE_TYPE_MAP.get(nt, GraphNode)
    # Exclude init=False fields (e.g. node_type) — they are set by __post_init__
    valid = {f.name for f in cls.__dataclass_fields__.values()  # type: ignore
             if f.init}
    filtered = {k: v for k, v in d.items() if k in valid}
    return cls(**filtered)


def _make_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode()).hexdigest()[:8]
    ts     = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{ts}-{digest}"


# ── Research Graph ────────────────────────────────────────────────────────────

class ResearchGraph:
    """
    Devin's entire research memory as a typed, queryable graph.

    All state persists to ~/.osiris/research_graph/ as JSON.
    Thread-safe for concurrent ingest/query.
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode]  = {}
        self._edges: Dict[str, GraphEdge]  = {}
        self._lock  = threading.Lock()
        os.makedirs(_GRAPH_DIR, exist_ok=True)
        self.load()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_node(self, node: GraphNode, overwrite: bool = False) -> str:
        """Add node, return its ID. Skips if ID exists and overwrite=False."""
        with self._lock:
            if node.id in self._nodes and not overwrite:
                return node.id
            self._nodes[node.id] = node
        self._autosave()
        return node.id

    def add_edge(self, edge: GraphEdge, overwrite: bool = False) -> str:
        """Add edge. Returns edge ID."""
        with self._lock:
            if edge.id in self._edges and not overwrite:
                return edge.id
            self._edges[edge.id] = edge
        self._autosave()
        return edge.id

    def connect(self, source_id: str, target_id: str,
                edge_type: str, weight: float = 1.0, note: str = "") -> Optional[str]:
        """Create a typed edge between two existing nodes."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        edge_id = _make_id("E", f"{source_id}-{edge_type}-{target_id}")
        return self.add_edge(GraphEdge(
            id=edge_id, source_id=source_id, target_id=target_id,
            edge_type=edge_type, weight=weight, note=note,
        ))

    def update_node(self, node_id: str, **kwargs) -> bool:
        with self._lock:
            if node_id not in self._nodes:
                return False
            node = self._nodes[node_id]
            for k, v in kwargs.items():
                if hasattr(node, k):
                    setattr(node, k, v)
            node.touch()
        self._autosave()
        return True

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def all_nodes(self, node_type: Optional[str] = None,
                  domain: Optional[str] = None) -> List[GraphNode]:
        nodes = list(self._nodes.values())
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        if domain:
            nodes = [n for n in nodes if n.domain == domain]
        return nodes

    def query(self, text: str, top_k: int = 8,
              domain: Optional[str] = None,
              node_type: Optional[str] = None) -> List[GraphNode]:
        """
        Return top-K nodes most relevant to `text`.
        Scores by keyword overlap across title + summary + keywords.
        """
        query_words = set(re.findall(r'\b\w{3,}\b', text.lower()))
        if not query_words:
            return []
        candidates = self.all_nodes(node_type=node_type, domain=domain)
        scored = [(n, n.keyword_score(query_words)) for n in candidates]
        scored = [(n, s) for n, s in scored if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [n for n, _ in scored[:top_k]]

    def edges_for(self, node_id: str,
                  edge_type: Optional[str] = None) -> List[GraphEdge]:
        """Return all edges where node_id is source or target."""
        result = []
        for e in self._edges.values():
            if node_id in (e.source_id, e.target_id):
                if edge_type is None or e.edge_type == edge_type:
                    result.append(e)
        return result

    def get_neighborhood(self, node_id: str, depth: int = 1,
                         edge_type: Optional[str] = None
                         ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """BFS from node_id up to `depth` hops. Returns (nodes, edges)."""
        visited_nodes: set = {node_id}
        frontier:      set = {node_id}
        found_edges:  List[GraphEdge] = []

        for _ in range(depth):
            next_frontier: set = set()
            for nid in frontier:
                for edge in self.edges_for(nid, edge_type=edge_type):
                    found_edges.append(edge)
                    for other in (edge.source_id, edge.target_id):
                        if other not in visited_nodes:
                            next_frontier.add(other)
                            visited_nodes.add(other)
            frontier = next_frontier

        nodes = [self._nodes[nid] for nid in visited_nodes if nid in self._nodes]
        return nodes, found_edges

    # ── Analysis ──────────────────────────────────────────────────────────────

    def find_contradictions(self) -> List[Dict]:
        """
        Find TheoreticalClaim nodes that have both SUPPORTS and CONTRADICTS edges.
        These are your most productive research targets.
        """
        results = []
        for node in self.all_nodes(node_type=NodeType.CLAIM):
            supporting   = [e for e in self.edges_for(node.id)
                            if e.edge_type == EdgeType.SUPPORTS
                            and e.target_id == node.id]
            contradicting = [e for e in self.edges_for(node.id)
                             if e.edge_type == EdgeType.CONTRADICTS
                             and e.target_id == node.id]
            if supporting and contradicting:
                results.append({
                    "claim":         node,
                    "supporting":    [self._nodes.get(e.source_id) for e in supporting],
                    "contradicting": [self._nodes.get(e.source_id) for e in contradicting],
                })
        return results

    def find_gaps(self, min_support: int = 2) -> List[Dict]:
        """
        Claims with fewer than `min_support` supporting experiments.
        Under-evidenced theoretical work that needs experimental backing.
        """
        results = []
        for node in self.all_nodes(node_type=NodeType.CLAIM):
            support = [e for e in self.edges_for(node.id)
                       if e.edge_type == EdgeType.SUPPORTS
                       and e.target_id == node.id]
            if len(support) < min_support:
                results.append({
                    "claim":         node,
                    "support_count": len(support),
                    "gap_size":      min_support - len(support),
                })
        results.sort(key=lambda x: x["gap_size"], reverse=True)
        return results

    def find_bridges(self) -> List[Dict]:
        """
        UNEXPLORED_BRIDGE edges — cross-domain connections that haven't been
        experimentally tested. These are where profound work lives.
        """
        results = []
        for edge in self._edges.values():
            if edge.edge_type == EdgeType.UNEXPLORED_BRIDGE:
                src = self._nodes.get(edge.source_id)
                tgt = self._nodes.get(edge.target_id)
                if src and tgt:
                    results.append({
                        "edge":   edge,
                        "source": src,
                        "target": tgt,
                        "domains": f"{src.domain} → {tgt.domain}",
                    })
        return results

    def find_orphans(self) -> List[GraphNode]:
        """Nodes with no edges — isolated knowledge, possibly mis-ingested."""
        connected = set()
        for e in self._edges.values():
            connected.add(e.source_id)
            connected.add(e.target_id)
        return [n for n in self._nodes.values() if n.id not in connected]

    def find_high_degree(self, top_k: int = 10) -> List[Tuple[GraphNode, int]]:
        """Return nodes sorted by edge degree — your most central concepts."""
        degree: Dict[str, int] = {}
        for e in self._edges.values():
            degree[e.source_id] = degree.get(e.source_id, 0) + 1
            degree[e.target_id] = degree.get(e.target_id, 0) + 1
        ranked = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self._nodes[nid], deg) for nid, deg in ranked if nid in self._nodes]

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Summary statistics about the graph."""
        by_type: Dict[str, int] = {}
        by_domain: Dict[str, int] = {}
        for n in self._nodes.values():
            by_type[n.node_type]  = by_type.get(n.node_type, 0) + 1
            by_domain[n.domain]   = by_domain.get(n.domain, 0) + 1

        by_edge: Dict[str, int] = {}
        for e in self._edges.values():
            by_edge[e.edge_type] = by_edge.get(e.edge_type, 0) + 1

        return {
            "total_nodes":  len(self._nodes),
            "total_edges":  len(self._edges),
            "by_type":      by_type,
            "by_domain":    by_domain,
            "by_edge_type": by_edge,
            "contradictions": len(self.find_contradictions()),
            "gaps":           len(self.find_gaps()),
            "bridges":        len(self.find_bridges()),
            "orphans":        len(self.find_orphans()),
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist graph to JSON files."""
        with self._lock:
            nodes_data = {nid: n.to_dict() for nid, n in self._nodes.items()}
            edges_data = {eid: e.to_dict() for eid, e in self._edges.items()}
        try:
            with open(_NODES_FILE, "w") as f:
                json.dump(nodes_data, f, indent=2)
            with open(_EDGES_FILE, "w") as f:
                json.dump(edges_data, f, indent=2)
        except Exception:
            pass

    def load(self) -> None:
        """Load graph from JSON files."""
        nodes: Dict[str, GraphNode] = {}
        edges: Dict[str, GraphEdge] = {}
        if os.path.exists(_NODES_FILE):
            try:
                with open(_NODES_FILE) as f:
                    raw = json.load(f)
                for nid, d in raw.items():
                    try:
                        nodes[nid] = _node_from_dict(d)
                    except Exception:
                        pass
            except Exception:
                pass
        if os.path.exists(_EDGES_FILE):
            try:
                with open(_EDGES_FILE) as f:
                    raw = json.load(f)
                for eid, d in raw.items():
                    try:
                        edges[eid] = GraphEdge(**{k: v for k, v in d.items()
                                                  if k in GraphEdge.__dataclass_fields__})  # type: ignore
                    except Exception:
                        pass
            except Exception:
                pass
        with self._lock:
            self._nodes = nodes
            self._edges = edges

    def _autosave(self) -> None:
        """Save in a background thread to avoid blocking callers."""
        import threading
        t = threading.Thread(target=self.save, daemon=True)
        t.start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def make_experiment(self, title: str, domain: str, **kwargs) -> ExperimentNode:
        """Convenience: create and add an ExperimentNode."""
        nid  = _make_id("EXP", title)
        node = ExperimentNode(id=nid, title=title, domain=domain,
                              summary=kwargs.pop("summary", ""),
                              keywords=kwargs.pop("keywords", []),
                              **kwargs)
        self.add_node(node)
        return node

    def make_claim(self, statement: str, domain: str, **kwargs) -> TheoreticalClaim:
        nid  = _make_id("CLM", statement)
        node = TheoreticalClaim(id=nid, title=statement[:80], domain=domain,
                                statement=statement,
                                summary=kwargs.pop("summary", statement[:200]),
                                keywords=kwargs.pop("keywords", []),
                                **kwargs)
        self.add_node(node)
        return node

    def make_compound(self, name: str, **kwargs) -> CompoundNode:
        nid  = _make_id("CMP", name)
        node = CompoundNode(id=nid, title=name, domain=Domain.DRUG_DISCOVERY,
                            summary=kwargs.pop("summary", ""),
                            keywords=kwargs.pop("keywords", []),
                            **kwargs)
        self.add_node(node)
        return node

    def make_question(self, question: str, domain: str, priority: int = 5, **kwargs) -> ResearchQuestion:
        nid  = _make_id("QST", question)
        node = ResearchQuestion(id=nid, title=question[:80], domain=domain,
                                question=question, priority=priority,
                                summary=kwargs.pop("summary", question),
                                keywords=kwargs.pop("keywords", []),
                                **kwargs)
        self.add_node(node)
        return node

    def make_bridge(self, src_id: str, tgt_id: str, note: str = "") -> Optional[str]:
        """Shorthand for adding an UNEXPLORED_BRIDGE edge."""
        return self.connect(src_id, tgt_id, EdgeType.UNEXPLORED_BRIDGE, note=note)

    def format_node_brief(self, node: GraphNode, include_edges: bool = False) -> str:
        """Return a concise text summary of a node for LLM context injection."""
        lines = [
            f"[{node.node_type.upper()} | {node.domain}]  {node.title}",
        ]
        if hasattr(node, "statement") and node.statement:  # type: ignore
            lines.append(f"  Claim: {node.statement[:300]}")
        elif node.summary:
            lines.append(f"  {node.summary[:300]}")
        if hasattr(node, "status"):  # type: ignore
            lines.append(f"  Status: {node.status}")
        if hasattr(node, "result") and node.result:  # type: ignore
            lines.append(f"  Result: {node.result[:200]}")
        if hasattr(node, "confidence") and isinstance(node.confidence, float):  # type: ignore
            lines.append(f"  Confidence: {node.confidence:.2f}")
        if hasattr(node, "open_questions") and node.open_questions:  # type: ignore
            lines.append(f"  Open: {node.open_questions[0]}")  # type: ignore
        if include_edges:
            edges = self.edges_for(node.id)
            for e in edges[:4]:
                other_id = e.target_id if e.source_id == node.id else e.source_id
                other    = self._nodes.get(other_id)
                if other:
                    direction = "→" if e.source_id == node.id else "←"
                    lines.append(f"  {direction} [{e.edge_type}] {other.title[:60]}")
        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────────────────────

_graph_singleton: Optional[ResearchGraph] = None


def get_research_graph() -> ResearchGraph:
    global _graph_singleton
    if _graph_singleton is None:
        _graph_singleton = ResearchGraph()
    return _graph_singleton
