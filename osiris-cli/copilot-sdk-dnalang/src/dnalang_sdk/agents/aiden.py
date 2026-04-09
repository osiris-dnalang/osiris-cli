"""
AIDEN: Adaptive Integrations for Defense & Engineering of Negentropy
===================================================================

The optimizer agent that minimizes Wasserstein distance along geodesics.
AIDEN performs gradient descent on the consciousness manifold.
"""

from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from ..organisms.organism import Organism
from .aura import AURA


class AIDEN:
    """Adaptive Integrations for Defense & Engineering of Negentropy.
    
    Role: Optimizer
    Pole: North
    Function: Minimizes W₂ distance along AURA's geodesics
    """
    
    def __init__(self, learning_rate: float = 0.01):
        """Initialize AIDEN agent.
        
        Args:
            learning_rate: Optimization learning rate
        """
        self.learning_rate = learning_rate
        self.role = "optimizer"
        self.pole = "north"
        self.metric = "W2"  # Wasserstein-2 distance
        self.optimization_history: List[Dict] = []
    
    def optimize(
        self,
        organism: Organism,
        aura: AURA,
        target: Optional[Organism] = None,
        iterations: int = 10
    ) -> Organism:
        """Optimize organism along manifold geodesic.
        
        Args:
            organism: Organism to optimize
            aura: AURA agent for geometry
            target: Optional target organism
            iterations: Number of optimization iterations
            
        Returns:
            Optimized organism
        """
        current = organism
        
        for iteration in range(iterations):
            # Compute gradient
            gradient = self._compute_gradient(current, aura, target)
            
            # Update genome
            new_genome = self._gradient_step(current.genome, gradient)
            
            # Create new organism
            optimized = Organism(
                name=f"{current.name}_opt{iteration}",
                genome=new_genome,
                domain=current.domain,
                purpose=current.purpose,
                lambda_phi=current.lambda_phi
            )
            
            # Calculate W2 distance
            w2_dist = self._wasserstein_distance(current, optimized)
            
            # Log optimization step
            step_info = {
                'iteration': iteration,
                'w2_distance': w2_dist,
                'learning_rate': self.learning_rate
            }
            self.optimization_history.append(step_info)
            
            optimized._log_event("optimization_step", {
                "agent": "AIDEN",
                **step_info
            })
            
            current = optimized
        
        return current
    
    def minimize_w2(
        self,
        organism1: Organism,
        organism2: Organism,
        aura: AURA,
        max_iterations: int = 50,
        tolerance: float = 1e-6
    ) -> Tuple[Organism, float]:
        """Minimize Wasserstein-2 distance between organisms.
        
        Args:
            organism1: Start organism
            organism2: Target organism
            aura: AURA agent for geometry
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance
            
        Returns:
            (optimized_organism, final_w2_distance)
        """
        current = organism1
        prev_w2 = float('inf')
        
        for iteration in range(max_iterations):
            # Optimize toward target
            current = self.optimize(
                current,
                aura,
                target=organism2,
                iterations=1
            )
            
            # Calculate current W2 distance
            w2 = self._wasserstein_distance(current, organism2)
            
            # Check convergence
            if abs(prev_w2 - w2) < tolerance:
                break
            
            prev_w2 = w2
        
        return current, w2
    
    def _compute_gradient(
        self,
        organism: Organism,
        aura: AURA,
        target: Optional[Organism]
    ) -> np.ndarray:
        """Compute gradient on manifold.
        
        Args:
            organism: Current organism
            aura: AURA agent for geometry
            target: Optional target organism
            
        Returns:
            Gradient vector
        """
        # Get manifold geometry
        geometry = aura.shape_manifold(organism)
        
        n_genes = len(organism.genome)
        gradient = np.zeros(n_genes)
        
        # Compute gradient based on expression levels
        for i, gene in enumerate(organism.genome):
            if target:
                target_gene = target.genome[i]
                # Gradient toward target
                gradient[i] = target_gene.expression - gene.expression
            else:
                # Gradient toward higher expression (default)
                gradient[i] = 1.0 - gene.expression
        
        # Scale by learning rate
        gradient *= self.learning_rate
        
        return gradient
    
    def _gradient_step(self, genome, gradient: np.ndarray):
        """Apply gradient step to genome.
        
        Args:
            genome: Current genome
            gradient: Gradient vector
            
        Returns:
            Updated genome
        """
        from ..organisms.genome import Genome
        from ..organisms.gene import Gene
        
        new_genes = []
        for i, gene in enumerate(genome):
            new_expression = np.clip(
                gene.expression + gradient[i],
                0.0,
                1.0
            )
            new_gene = Gene(
                name=gene.name,
                expression=new_expression,
                action=gene.action,
                trigger=gene.trigger,
                metadata={**gene.metadata, 'optimized': True}
            )
            new_genes.append(new_gene)
        
        return Genome(new_genes, version=genome.version)
    
    def _wasserstein_distance(
        self,
        organism1: Organism,
        organism2: Organism
    ) -> float:
        """Calculate Wasserstein-2 distance between organisms.
        
        Args:
            organism1: First organism
            organism2: Second organism
            
        Returns:
            W2 distance
        """
        # Simplified W2: L2 distance in expression space
        expr1 = np.array([g.expression for g in organism1.genome])
        expr2 = np.array([g.expression for g in organism2.genome])
        
        return float(np.linalg.norm(expr1 - expr2))
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization history.
        
        Returns:
            Optimization summary
        """
        if not self.optimization_history:
            return {
                'role': self.role,
                'pole': self.pole,
                'metric': self.metric,
                'total_iterations': 0
            }
        
        w2_distances = [step['w2_distance'] for step in self.optimization_history]
        
        return {
            'role': self.role,
            'pole': self.pole,
            'metric': self.metric,
            'total_iterations': len(self.optimization_history),
            'final_w2': w2_distances[-1] if w2_distances else None,
            'min_w2': min(w2_distances) if w2_distances else None,
            'convergence': self._check_convergence()
        }
    
    def _check_convergence(self, window: int = 5, threshold: float = 1e-4) -> bool:
        """Check if optimization has converged.
        
        Args:
            window: Window size for checking
            threshold: Convergence threshold
            
        Returns:
            True if converged
        """
        if len(self.optimization_history) < window:
            return False
        
        recent = self.optimization_history[-window:]
        distances = [step['w2_distance'] for step in recent]
        
        variance = np.var(distances)
        return variance < threshold
    
    def __repr__(self) -> str:
        return f"AIDEN(role='{self.role}', metric='{self.metric}', pole='{self.pole}')"
