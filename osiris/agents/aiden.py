"""
AIDEN: Adaptive Integrations for Defense & Engineering of Negentropy
===================================================================

The optimizer agent that minimizes Wasserstein distance along geodesics.
Pole: North
"""

from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from osiris.organisms.organism import Organism
from osiris.organisms.genome import Genome
from osiris.organisms.gene import Gene
from .aura import AURA


class AIDEN:
    """Adaptive Integrations for Defense & Engineering of Negentropy.

    Role: Optimizer
    Pole: North
    Function: Minimizes W2 distance along AURA's geodesics
    """

    def __init__(self, learning_rate: float = 0.01):
        self.learning_rate = learning_rate
        self.role = "optimizer"
        self.pole = "north"
        self.metric = "W2"
        self.optimization_history: List[Dict] = []

    def optimize(
        self, organism: Organism, aura: AURA,
        target: Optional[Organism] = None, iterations: int = 10
    ) -> Organism:
        current = organism
        for iteration in range(iterations):
            gradient = self._compute_gradient(current, aura, target)
            new_genome = self._gradient_step(current.genome, gradient)
            optimized = Organism(
                name=f"{current.name}_opt{iteration}",
                genome=new_genome,
                domain=current.domain,
                purpose=current.purpose,
                lambda_phi=current.lambda_phi
            )
            w2_dist = self._wasserstein_distance(current, optimized)
            step_info = {
                'iteration': iteration,
                'w2_distance': w2_dist,
                'learning_rate': self.learning_rate
            }
            self.optimization_history.append(step_info)
            optimized._log_event("optimization_step", {"agent": "AIDEN", **step_info})
            current = optimized
        return current

    def minimize_w2(
        self, organism1: Organism, organism2: Organism, aura: AURA,
        max_iterations: int = 50, tolerance: float = 1e-6
    ) -> Tuple[Organism, float]:
        current = organism1
        prev_w2 = float('inf')
        w2 = prev_w2
        for iteration in range(max_iterations):
            current = self.optimize(current, aura, target=organism2, iterations=1)
            w2 = self._wasserstein_distance(current, organism2)
            if abs(prev_w2 - w2) < tolerance:
                break
            prev_w2 = w2
        return current, w2

    def _compute_gradient(self, organism: Organism, aura: AURA, target: Optional[Organism]) -> np.ndarray:
        aura.shape_manifold(organism)
        n_genes = len(organism.genome)
        gradient = np.zeros(n_genes)
        for i, gene in enumerate(organism.genome):
            if target:
                target_gene = target.genome.genes[i]
                gradient[i] = target_gene.expression - gene.expression
            else:
                gradient[i] = 1.0 - gene.expression
        gradient *= self.learning_rate
        return gradient

    def _gradient_step(self, genome, gradient: np.ndarray):
        new_genes = []
        for i, gene in enumerate(genome):
            new_expression = np.clip(gene.expression + gradient[i], 0.0, 1.0)
            new_gene = Gene(
                name=gene.name,
                expression=float(new_expression),
                action=gene.action,
                trigger=gene.trigger,
                metadata={**gene.metadata, 'optimized': True}
            )
            new_genes.append(new_gene)
        return Genome(new_genes, version=genome.version)

    def _wasserstein_distance(self, organism1: Organism, organism2: Organism) -> float:
        expr1 = np.array([g.expression for g in organism1.genome])
        expr2 = np.array([g.expression for g in organism2.genome])
        return float(np.linalg.norm(expr1 - expr2))

    def get_optimization_summary(self) -> Dict[str, Any]:
        if not self.optimization_history:
            return {'role': self.role, 'pole': self.pole, 'metric': self.metric, 'total_iterations': 0}
        w2_distances = [step['w2_distance'] for step in self.optimization_history]
        return {
            'role': self.role, 'pole': self.pole, 'metric': self.metric,
            'total_iterations': len(self.optimization_history),
            'final_w2': w2_distances[-1] if w2_distances else None,
            'min_w2': min(w2_distances) if w2_distances else None,
            'convergence': self._check_convergence()
        }

    def _check_convergence(self, window: int = 5, threshold: float = 1e-4) -> bool:
        if len(self.optimization_history) < window:
            return False
        recent = self.optimization_history[-window:]
        distances = [step['w2_distance'] for step in recent]
        return float(np.var(distances)) < threshold

    def __repr__(self) -> str:
        return f"AIDEN(role='{self.role}', metric='{self.metric}', pole='{self.pole}')"
