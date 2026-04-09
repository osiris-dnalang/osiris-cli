#!/usr/bin/env python3
"""
MEMORY GRAPH — Persistent Intent and Context Memory
===================================================

Captures evolving user preferences, goals, and relationships between concepts.
Used to bias future intent deduction, detect drift, and store latent knowledge.
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MemoryNode:
    node_id: str
    label: str
    category: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "category": self.category,
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass
class MemoryEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
        }


class MemoryGraph:
    """
    Lightweight persistent graph of memory nodes and relationships.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = Path(state_dir) if state_dir else Path.home() / ".osiris" / "memory_graph"
        self.state_dir.mkdir(exist_ok=True, parents=True)
        self.nodes: Dict[str, MemoryNode] = {}
        self.edges: List[MemoryEdge] = []
        self._load_state()

    def add_node(self, label: str, category: str, weight: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> MemoryNode:
        node_id = f"{category}:{label}".lower()
        metadata = metadata or {}
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.weight = min(5.0, node.weight + weight * 0.2)
            node.metadata.update(metadata)
        else:
            node = MemoryNode(node_id=node_id, label=label, category=category, weight=weight, metadata=metadata)
            self.nodes[node_id] = node
        return node

    def add_edge(self, source: str, target: str, relation: str, weight: float = 1.0) -> None:
        edge = next((e for e in self.edges if e.source == source and e.target == target and e.relation == relation), None)
        if edge:
            edge.weight = min(5.0, edge.weight + weight * 0.2)
        else:
            self.edges.append(MemoryEdge(source=source, target=target, relation=relation, weight=weight))

    def get_related(self, node_id: str, relation: Optional[str] = None) -> List[MemoryNode]:
        related = []
        for edge in self.edges:
            if edge.source == node_id and (relation is None or edge.relation == relation):
                related_node = self.nodes.get(edge.target)
                if related_node:
                    related.append(related_node)
        return sorted(related, key=lambda n: (-n.weight, n.label))

    def query(self, label: str, category: Optional[str] = None) -> Optional[MemoryNode]:
        node_id = f"{category}:{label}".lower() if category else None
        if node_id and node_id in self.nodes:
            return self.nodes[node_id]
        for node in self.nodes.values():
            if node.label == label and (category is None or node.category == category):
                return node
        return None

    def save_state(self) -> None:
        state_file = self.state_dir / "memory_graph.json"
        try:
            with open(state_file, "w") as f:
                json.dump({
                    "nodes": [n.to_dict() for n in self.nodes.values()],
                    "edges": [e.to_dict() for e in self.edges],
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save memory graph: {e}")

    def _load_state(self) -> None:
        state_file = self.state_dir / "memory_graph.json"
        if not state_file.exists():
            return
        try:
            with open(state_file) as f:
                state = json.load(f)
                for node_data in state.get("nodes", []):
                    self.nodes[node_data["node_id"]] = MemoryNode(**node_data)
                for edge_data in state.get("edges", []):
                    self.edges.append(MemoryEdge(**edge_data))
        except Exception as e:
            logger.warning(f"Could not load memory graph: {e}")

    def snapshot(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }


# Factory

def create_memory_graph(state_dir: Optional[Path] = None) -> MemoryGraph:
    return MemoryGraph(state_dir=state_dir)
