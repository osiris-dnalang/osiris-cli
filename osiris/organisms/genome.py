"""
osiris.organisms.genome — Genome container
==========================================

A Genome is an ordered collection of Genes that can be mutated,
crossed over, and expressed as a unit.
"""

from typing import Any, Dict, Iterator, List, Optional
import random

from .gene import Gene


class Genome:
    """Ordered collection of genes forming an organism's blueprint."""

    def __init__(self, genes: Optional[List[Gene]] = None, version: int = 1):
        self.genes: List[Gene] = genes or []
        self.version = version

    def add_gene(self, gene: Gene):
        self.genes.append(gene)

    def mutate(self, rate: float = 0.1) -> 'Genome':
        mutated_genes = [g.mutate(rate) for g in self.genes]
        return Genome(mutated_genes, version=self.version + 1)

    def crossover(self, other: 'Genome') -> 'Genome':
        min_len = min(len(self.genes), len(other.genes))
        point = random.randint(1, max(min_len - 1, 1))
        child_genes = []
        for i in range(min_len):
            if i < point:
                child_genes.append(self.genes[i].crossover(other.genes[i]))
            else:
                child_genes.append(other.genes[i].crossover(self.genes[i]))
        if len(self.genes) > min_len:
            child_genes.extend(self.genes[min_len:])
        elif len(other.genes) > min_len:
            child_genes.extend(other.genes[min_len:])
        return Genome(child_genes, version=max(self.version, other.version) + 1)

    def express(self, context: Optional[Dict[str, Any]] = None) -> List[Any]:
        return [g.express(context) for g in self.genes]

    def fitness(self) -> float:
        if not self.genes:
            return 0.0
        return sum(g.expression for g in self.genes) / len(self.genes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'genes': [g.to_dict() for g in self.genes],
            'fitness': self.fitness(),
        }

    def __len__(self) -> int:
        return len(self.genes)

    def __iter__(self) -> Iterator[Gene]:
        return iter(self.genes)

    def __getitem__(self, idx: int) -> Gene:
        return self.genes[idx]

    def __repr__(self) -> str:
        return f"Genome(genes={len(self.genes)}, v={self.version}, fitness={self.fitness():.3f})"
