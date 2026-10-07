"""
Tesseract Decoder Organism — A* / beam-search decoding in 4D lattice space.
"""

import heapq
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class DecoderNode:
    syndrome: Tuple[int, ...]
    correction: Tuple[int, ...]
    cost: float = 0.0
    heuristic: float = 0.0
    parent: Optional["DecoderNode"] = None

    @property
    def f(self) -> float:
        return self.cost + self.heuristic

    def __lt__(self, other):
        return self.f < other.f


class TesseractDecoderOrganism:
    """A* decoder with beam-search pruning for quantum error correction."""

    D: int = 3

    def __init__(self, distance: int = 3, beam_width: int = 32,
                 max_iterations: int = 10_000):
        self.distance = distance
        self.D = distance
        self.beam_width = beam_width
        self.max_iterations = max_iterations

    @staticmethod
    def residual_syndrome(syndrome: Tuple[int, ...],
                          correction: Tuple[int, ...]) -> Tuple[int, ...]:
        return tuple((s ^ c) for s, c in zip(syndrome, correction))

    @staticmethod
    def errors_touching(correction: Tuple[int, ...]) -> int:
        return sum(1 for c in correction if c != 0)

    @staticmethod
    def precedence_forbidden(correction: Tuple[int, ...],
                             visited: Set[Tuple[int, ...]]) -> bool:
        return correction in visited

    @staticmethod
    def prune_edges(correction: Tuple[int, ...], distance: int) -> bool:
        return sum(c for c in correction) > distance * 2

    def heuristic(self, syndrome: Tuple[int, ...]) -> float:
        return sum(abs(s) for s in syndrome) * 0.5

    def g_cost(self, correction: Tuple[int, ...]) -> float:
        return float(self.errors_touching(correction))

    def beam_prune(self, frontier: list) -> list:
        if len(frontier) <= self.beam_width:
            return frontier
        frontier.sort()
        return frontier[:self.beam_width]

    def _neighbors(self, node: DecoderNode) -> List[DecoderNode]:
        neighbors = []
        for i in range(len(node.correction)):
            for flip in (-1, 1):
                new_corr = list(node.correction)
                new_corr[i] = (new_corr[i] + flip) % 2
                new_corr_t = tuple(new_corr)
                residual = self.residual_syndrome(node.syndrome, new_corr_t)
                neighbors.append(DecoderNode(
                    syndrome=residual,
                    correction=new_corr_t,
                    cost=self.g_cost(new_corr_t),
                    heuristic=self.heuristic(residual),
                    parent=node,
                ))
        return neighbors

    def decode(self, syndrome: Tuple[int, ...]) -> Tuple[int, ...]:
        if all(s == 0 for s in syndrome):
            return (0,) * len(syndrome)
        n = len(syndrome)
        start = DecoderNode(
            syndrome=syndrome,
            correction=(0,) * n,
            cost=0.0,
            heuristic=self.heuristic(syndrome),
        )
        frontier: list = [start]
        visited: Set[Tuple[int, ...]] = set()
        for _ in range(self.max_iterations):
            if not frontier:
                break
            frontier = self.beam_prune(frontier)
            node = heapq.heappop(frontier)
            if all(s == 0 for s in node.syndrome):
                return node.correction
            if node.correction in visited:
                continue
            visited.add(node.correction)
            for nb in self._neighbors(node):
                if not self.precedence_forbidden(nb.correction, visited):
                    if not self.prune_edges(nb.correction, self.distance):
                        heapq.heappush(frontier, nb)
        return (0,) * n


class TesseractResonatorOrganism:
    """4D resonance mapping for tesseract lattice visualization."""

    def __init__(self, distance: int = 3, dimensions: int = 4):
        self.distance = distance
        self.dimensions = dimensions

    def resonance_4d_mapping(self, syndromes: List[Tuple[int, ...]]) -> Dict[str, Any]:
        mapping: Dict[str, Any] = {
            "distance": self.distance,
            "dimensions": self.dimensions,
            "syndrome_count": len(syndromes),
            "weight_distribution": {},
            "resonance_peaks": [],
        }
        for s in syndromes:
            w = sum(abs(x) for x in s)
            mapping["weight_distribution"][w] = mapping["weight_distribution"].get(w, 0) + 1
        if syndromes:
            max_w = max(mapping["weight_distribution"].values())
            mapping["resonance_peaks"] = [
                k for k, v in mapping["weight_distribution"].items() if v == max_w
            ]
        return mapping

    def deploy(self) -> Dict[str, Any]:
        return {
            "distance": self.distance,
            "dimensions": self.dimensions,
            "status": "deployed",
        }
