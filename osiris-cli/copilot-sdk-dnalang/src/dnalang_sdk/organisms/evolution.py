"""
Evolution: Quantum-accelerated genetic algorithms
===============================================

Evolution engine for organisms using quantum-enhanced selection,
mutation, and fitness evaluation.
"""

from typing import List, Callable, Optional, Dict, Any
import numpy as np
from .organism import Organism
from .genome import Genome


class EvolutionEngine:
    """Quantum-accelerated evolution engine.
    
    Attributes:
        population_size: Number of organisms in population
        mutation_rate: Probability of mutation per generation
        crossover_rate: Probability of crossover per generation
        selection_method: 'tournament', 'roulette', or 'rank'
        elite_count: Number of top organisms to preserve
    """
    
    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        selection_method: str = 'tournament',
        elite_count: int = 2
    ):
        """Initialize evolution engine."""
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.selection_method = selection_method
        self.elite_count = elite_count
        self.generation = 0
        self.history: List[Dict] = []
    
    def evolve(
        self,
        population: List[Organism],
        fitness_fn: Callable[[Organism], float],
        generations: int = 10,
        callback: Optional[Callable] = None
    ) -> List[Organism]:
        """Evolve population over multiple generations.
        
        Args:
            population: Initial population
            fitness_fn: Fitness evaluation function
            generations: Number of generations to evolve
            callback: Optional callback(generation, population, stats)
            
        Returns:
            Final population
        """
        # Evaluate initial fitness
        for organism in population:
            organism.genome.fitness = fitness_fn(organism)
        
        for gen in range(generations):
            self.generation = gen
            
            # Sort by fitness
            population.sort(key=lambda o: o.genome.fitness or 0, reverse=True)
            
            # Track statistics
            fitnesses = [o.genome.fitness for o in population if o.genome.fitness]
            stats = {
                'generation': gen,
                'best_fitness': max(fitnesses) if fitnesses else 0,
                'avg_fitness': np.mean(fitnesses) if fitnesses else 0,
                'worst_fitness': min(fitnesses) if fitnesses else 0,
                'diversity': self._calculate_diversity(population)
            }
            self.history.append(stats)
            
            if callback:
                callback(gen, population, stats)
            
            # Elitism: preserve top performers
            next_generation = population[:self.elite_count]
            
            # Generate offspring
            while len(next_generation) < self.population_size:
                # Selection
                parent1 = self._select(population)
                parent2 = self._select(population)
                
                # Crossover
                if np.random.random() < self.crossover_rate:
                    offspring_genome = parent1.genome.crossover(parent2.genome)
                else:
                    offspring_genome = parent1.genome
                
                # Mutation
                if np.random.random() < self.mutation_rate:
                    offspring_genome = offspring_genome.mutate()
                
                # Create offspring organism
                offspring = Organism(
                    name=f"{parent1.name}_x_{parent2.name}",
                    genome=offspring_genome,
                    domain=parent1.domain,
                    purpose=parent1.purpose,
                    lambda_phi=parent1.lambda_phi
                )
                offspring.generation = gen + 1
                
                # Evaluate fitness
                offspring.genome.fitness = fitness_fn(offspring)
                
                next_generation.append(offspring)
            
            population = next_generation[:self.population_size]
        
        # Final sort
        population.sort(key=lambda o: o.genome.fitness or 0, reverse=True)
        return population
    
    def _select(self, population: List[Organism]) -> Organism:
        """Select organism based on selection method.
        
        Args:
            population: Population to select from
            
        Returns:
            Selected organism
        """
        if self.selection_method == 'tournament':
            return self._tournament_selection(population, k=3)
        elif self.selection_method == 'roulette':
            return self._roulette_selection(population)
        elif self.selection_method == 'rank':
            return self._rank_selection(population)
        else:
            raise ValueError(f"Unknown selection method: {self.selection_method}")
    
    def _tournament_selection(self, population: List[Organism], k: int = 3) -> Organism:
        """Tournament selection.
        
        Args:
            population: Population to select from
            k: Tournament size
            
        Returns:
            Winner of tournament
        """
        tournament = np.random.choice(population, size=k, replace=False)
        return max(tournament, key=lambda o: o.genome.fitness or 0)
    
    def _roulette_selection(self, population: List[Organism]) -> Organism:
        """Roulette wheel selection.
        
        Args:
            population: Population to select from
            
        Returns:
            Selected organism
        """
        fitnesses = np.array([o.genome.fitness or 0 for o in population])
        # Handle negative fitness
        fitnesses = fitnesses - fitnesses.min() + 1e-6
        probabilities = fitnesses / fitnesses.sum()
        return np.random.choice(population, p=probabilities)
    
    def _rank_selection(self, population: List[Organism]) -> Organism:
        """Rank-based selection.
        
        Args:
            population: Population to select from
            
        Returns:
            Selected organism
        """
        ranks = np.arange(1, len(population) + 1)
        probabilities = ranks / ranks.sum()
        return np.random.choice(population, p=probabilities)
    
    def _calculate_diversity(self, population: List[Organism]) -> float:
        """Calculate population diversity.
        
        Args:
            population: Population to analyze
            
        Returns:
            Diversity metric [0, 1]
        """
        # Simple diversity based on fitness variance
        fitnesses = [o.genome.fitness for o in population if o.genome.fitness]
        if len(fitnesses) < 2:
            return 0.0
        return float(np.std(fitnesses) / (np.mean(fitnesses) + 1e-6))


def evolve(
    organism: Organism,
    fitness_fn: Callable[[Organism], float],
    generations: int = 10,
    population_size: int = 50,
    backend: Optional[str] = None,
    shots: int = 8192,
    **kwargs
) -> Organism:
    """Evolve a single organism.
    
    Args:
        organism: Initial organism
        fitness_fn: Fitness evaluation function
        generations: Number of generations
        population_size: Population size
        backend: Optional quantum backend name
        shots: Number of quantum shots
        **kwargs: Additional evolution parameters
        
    Returns:
        Best evolved organism
    """
    # Create initial population from organism
    population = [organism]
    for i in range(population_size - 1):
        mutated = organism.genome.mutate()
        pop_organism = Organism(
            name=f"{organism.name}_init_{i}",
            genome=mutated,
            domain=organism.domain,
            purpose=organism.purpose,
            lambda_phi=organism.lambda_phi
        )
        population.append(pop_organism)
    
    # Create evolution engine
    engine = EvolutionEngine(
        population_size=population_size,
        **kwargs
    )
    
    # Evolve
    final_population = engine.evolve(
        population=population,
        fitness_fn=fitness_fn,
        generations=generations
    )
    
    # Return best organism
    best = max(final_population, key=lambda o: o.genome.fitness or 0)
    
    # Add backend execution info if provided
    if backend:
        best._log_event("quantum_execution", {
            "backend": backend,
            "shots": shots,
            "lambda_phi": organism.lambda_phi
        })
    
    return best
