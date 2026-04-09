"""
Genome: Collection of genes defining organism behavior
=====================================================

The genome is the complete set of genetic instructions that determine
an organism's structure, function, and behavior.
"""

from typing import List, Optional, Iterator
import numpy as np
from .gene import Gene


class Genome:
    """Collection of genes that define organism behavior.
    
    Attributes:
        genes: List of genes
        version: Genome version identifier
        fitness: Fitness score from last evaluation
    """
    
    def __init__(self, genes: List[Gene], version: str = "1.0.0"):
        """Initialize genome.
        
        Args:
            genes: List of Gene objects
            version: Version identifier
        """
        self.genes = genes
        self.version = version
        self.fitness: Optional[float] = None
        self._gene_map = {g.name: g for g in genes}
    
    def __getitem__(self, key: str) -> Gene:
        """Access gene by name."""
        return self._gene_map[key]
    
    def __iter__(self) -> Iterator[Gene]:
        """Iterate over genes."""
        return iter(self.genes)
    
    def __len__(self) -> int:
        """Number of genes."""
        return len(self.genes)
    
    def mutate(self, mutation_rate: float = 0.1, delta: float = 0.05) -> 'Genome':
        """Apply mutations to genome.
        
        Args:
            mutation_rate: Probability each gene mutates
            delta: Magnitude of mutations
            
        Returns:
            Mutated genome
        """
        mutated_genes = []
        for gene in self.genes:
            if np.random.random() < mutation_rate:
                mutated_genes.append(gene.mutate(delta))
            else:
                mutated_genes.append(gene)
        
        return Genome(mutated_genes, version=self.version)
    
    def crossover(self, other: 'Genome', strategy: str = 'uniform') -> 'Genome':
        """Perform crossover with another genome.
        
        Args:
            other: Genome to crossover with
            strategy: 'uniform', 'single_point', or 'two_point'
            
        Returns:
            Offspring genome
        """
        if len(self.genes) != len(other.genes):
            raise ValueError("Cannot crossover genomes of different lengths")
        
        if strategy == 'uniform':
            # Randomly select genes from each parent
            offspring_genes = []
            for g1, g2 in zip(self.genes, other.genes):
                if np.random.random() < 0.5:
                    offspring_genes.append(g1)
                else:
                    offspring_genes.append(g2)
        
        elif strategy == 'single_point':
            # Single crossover point
            point = np.random.randint(1, len(self.genes))
            offspring_genes = self.genes[:point] + other.genes[point:]
        
        elif strategy == 'two_point':
            # Two crossover points
            p1, p2 = sorted(np.random.choice(len(self.genes), 2, replace=False))
            offspring_genes = self.genes[:p1] + other.genes[p1:p2] + self.genes[p2:]
        
        else:
            raise ValueError(f"Unknown crossover strategy: {strategy}")
        
        return Genome(offspring_genes, version=self.version)
    
    def express(self) -> dict:
        """Express all genes and collect results.
        
        Returns:
            Dictionary mapping gene names to expression results
        """
        return {gene.name: gene.express() for gene in self.genes}
    
    def get_gene(self, name: str) -> Optional[Gene]:
        """Get gene by name."""
        return self._gene_map.get(name)
    
    def add_gene(self, gene: Gene):
        """Add a new gene to genome."""
        if gene.name in self._gene_map:
            raise ValueError(f"Gene {gene.name} already exists")
        self.genes.append(gene)
        self._gene_map[gene.name] = gene
    
    def remove_gene(self, name: str):
        """Remove gene by name."""
        if name not in self._gene_map:
            raise ValueError(f"Gene {name} not found")
        gene = self._gene_map.pop(name)
        self.genes.remove(gene)
    
    def to_dict(self) -> dict:
        """Serialize genome to dictionary."""
        return {
            'version': self.version,
            'genes': [g.to_dict() for g in self.genes],
            'fitness': self.fitness
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Genome':
        """Deserialize genome from dictionary."""
        genes = [Gene.from_dict(g) for g in data['genes']]
        genome = cls(genes, version=data['version'])
        genome.fitness = data.get('fitness')
        return genome
    
    def __repr__(self) -> str:
        fitness_str = f", fitness={self.fitness:.3f}" if self.fitness else ""
        return f"Genome(genes={len(self.genes)}, version='{self.version}'{fitness_str})"
