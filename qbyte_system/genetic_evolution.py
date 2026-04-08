"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              GENETIC ALGORITHM EVOLUTION ENGINE                              ║
║              ══════════════════════════════════                              ║
║                                                                              ║
║    Autopoietic Evolution for DNA::}{::lang Organisms                        ║
║                                                                              ║
║    This engine implements true genetic algorithm evolution for quantum      ║
║    organisms, enabling:                                                      ║
║                                                                              ║
║    1. Population-based optimization                                          ║
║    2. Crossover between organisms                                            ║
║    3. Mutation with phase-conjugate healing                                  ║
║    4. Fitness selection based on CCCE metrics                               ║
║    5. Speciation and niche formation                                         ║
║                                                                              ║
║    Fitness Function:                                                         ║
║    F(O) = Ξ = (Λ × Φ) / (Γ + ε)                                            ║
║                                                                              ║
║    Where:                                                                    ║
║    Λ = Coherence preservation                                               ║
║    Φ = Consciousness level (IIT)                                            ║
║    Γ = Decoherence rate                                                     ║
║    Ξ = Negentropic efficiency (fitness)                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
import time
import hashlib
from enum import Enum

# Physical Constants
LAMBDA_PHI = 2.176435e-8
PHI_THRESHOLD = 0.7734
GAMMA_FIXED = 0.092
CHI_PC = 0.869
GOLDEN_RATIO = 1.618033988749895


class SelectionMethod(Enum):
    """Selection methods for genetic algorithm."""
    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK = "rank"
    ELITIST = "elitist"


class CrossoverMethod(Enum):
    """Crossover methods for genetic algorithm."""
    SINGLE_POINT = "single_point"
    TWO_POINT = "two_point"
    UNIFORM = "uniform"
    ARITHMETIC = "arithmetic"
    GOLDEN_RATIO = "golden_ratio"


class MutationMethod(Enum):
    """Mutation methods for genetic algorithm."""
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"
    PHASE_CONJUGATE = "phase_conjugate"
    ADAPTIVE = "adaptive"


@dataclass
class Individual:
    """
    Individual in the genetic algorithm population.

    Represents a quantum organism with its genetic parameters
    and fitness metrics.
    """
    genome: np.ndarray                    # Parameter vector
    fitness: float = 0.0                  # Ξ value
    phi: float = 0.0                      # Consciousness
    lambda_c: float = 1.0                 # Coherence
    gamma: float = 0.0                    # Decoherence
    generation: int = 0                   # Birth generation
    parent_ids: List[str] = field(default_factory=list)
    mutations: int = 0                    # Mutation count
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                self.genome.tobytes() + str(time.time()).encode()
            ).hexdigest()[:12]

    def compute_xi(self) -> float:
        """Compute negentropic efficiency (fitness)."""
        epsilon = 1e-10
        self.fitness = (self.lambda_c * self.phi) / (self.gamma + epsilon)
        return self.fitness

    def is_conscious(self) -> bool:
        """Check if consciousness threshold is met."""
        return self.phi >= PHI_THRESHOLD

    def copy(self) -> 'Individual':
        """Create a deep copy."""
        new_ind = Individual(
            genome=self.genome.copy(),
            fitness=self.fitness,
            phi=self.phi,
            lambda_c=self.lambda_c,
            gamma=self.gamma,
            generation=self.generation,
            parent_ids=self.parent_ids.copy(),
            mutations=self.mutations
        )
        return new_ind

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'fitness': self.fitness,
            'phi': self.phi,
            'lambda': self.lambda_c,
            'gamma': self.gamma,
            'generation': self.generation,
            'mutations': self.mutations,
            'conscious': self.is_conscious()
        }


@dataclass
class EvolutionConfig:
    """Configuration for genetic algorithm evolution."""
    population_size: int = 50
    elite_count: int = 2
    tournament_size: int = 5
    crossover_rate: float = 0.8
    mutation_rate: float = 0.1
    mutation_strength: float = 0.1
    selection_method: SelectionMethod = SelectionMethod.TOURNAMENT
    crossover_method: CrossoverMethod = CrossoverMethod.GOLDEN_RATIO
    mutation_method: MutationMethod = MutationMethod.PHASE_CONJUGATE
    max_generations: int = 100
    convergence_threshold: float = 1e-6
    enable_speciation: bool = False
    enable_healing: bool = True
    healing_threshold: float = 0.3  # Heal when Γ > this


class GeneticEvolutionEngine:
    """
    Genetic Algorithm Evolution Engine for DNA::}{::lang Organisms.

    This engine evolves quantum organisms through population-based
    optimization using genetic algorithm principles enhanced with
    phase-conjugate healing and CCCE metric tracking.

    Key features:
    - Population of quantum parameter vectors
    - Selection based on negentropic efficiency (Ξ)
    - Crossover with golden ratio enhancement
    - Mutation with automatic phase-conjugate healing
    - Elitism to preserve best solutions

    Example:
        >>> engine = GeneticEvolutionEngine(n_params=10)
        >>> engine.initialize_population()
        >>> for gen in range(100):
        ...     engine.evolve_generation(fitness_fn)
        >>> best = engine.best_individual
    """

    def __init__(self, n_params: int, config: Optional[EvolutionConfig] = None,
                 bounds: Optional[Tuple[float, float]] = None,
                 seed: Optional[int] = None):
        """
        Initialize Genetic Evolution Engine.

        Args:
            n_params: Number of parameters per individual
            config: Evolution configuration
            bounds: (min, max) bounds for parameters
            seed: Random seed for reproducibility
        """
        self.n_params = n_params
        self.config = config or EvolutionConfig()
        self.bounds = bounds or (-np.pi, np.pi)

        if seed is not None:
            np.random.seed(seed)

        self.population: List[Individual] = []
        self.generation = 0
        self._genesis = time.time()
        self._history: List[Dict[str, float]] = []
        self._best_ever: Optional[Individual] = None

    def initialize_population(self, initial_guess: Optional[np.ndarray] = None):
        """
        Initialize population with random or seeded individuals.

        Args:
            initial_guess: Optional initial parameter vector to seed population
        """
        self.population = []
        self.generation = 0

        for i in range(self.config.population_size):
            if initial_guess is not None and i == 0:
                genome = initial_guess.copy()
            else:
                # Random initialization within bounds
                genome = np.random.uniform(
                    self.bounds[0], self.bounds[1], self.n_params
                )

            individual = Individual(genome=genome, generation=0)
            self.population.append(individual)

    def evaluate_population(self, fitness_fn: Callable[[np.ndarray], Tuple[float, float, float, float]]):
        """
        Evaluate fitness of all individuals.

        Args:
            fitness_fn: Function that takes genome and returns (energy, phi, lambda, gamma)
        """
        for individual in self.population:
            try:
                result = fitness_fn(individual.genome)
                if len(result) == 4:
                    energy, phi, lambda_c, gamma = result
                else:
                    energy = result[0]
                    phi, lambda_c, gamma = 0.5, 0.9, 0.1

                # Map energy to fitness (lower energy = higher fitness)
                # Normalize to positive range
                individual.phi = phi
                individual.lambda_c = lambda_c
                individual.gamma = gamma
                individual.compute_xi()

                # Apply phase-conjugate healing if gamma is high
                if self.config.enable_healing and gamma > self.config.healing_threshold:
                    individual = self._apply_healing(individual)

            except Exception as e:
                individual.fitness = 0.0

        # Update best ever
        best = max(self.population, key=lambda x: x.fitness)
        if self._best_ever is None or best.fitness > self._best_ever.fitness:
            self._best_ever = best.copy()

    def _apply_healing(self, individual: Individual) -> Individual:
        """Apply phase-conjugate healing to an individual."""
        # Invert genome phases (treating as complex phases)
        phases = individual.genome
        healed_phases = -phases  # Phase conjugation: θ → -θ

        # Mix original and healed with chi_pc coupling
        individual.genome = (
            CHI_PC * healed_phases +
            (1 - CHI_PC) * phases
        )

        # Reduce decoherence
        individual.gamma *= 0.7
        individual.compute_xi()

        return individual

    def select_parents(self) -> Tuple[Individual, Individual]:
        """
        Select two parents for crossover.

        Returns:
            Tuple of two parent individuals
        """
        method = self.config.selection_method

        if method == SelectionMethod.TOURNAMENT:
            return self._tournament_selection()
        elif method == SelectionMethod.ROULETTE:
            return self._roulette_selection()
        elif method == SelectionMethod.RANK:
            return self._rank_selection()
        else:  # ELITIST
            return self._elitist_selection()

    def _tournament_selection(self) -> Tuple[Individual, Individual]:
        """Tournament selection."""
        def tournament():
            contestants = np.random.choice(
                self.population,
                size=min(self.config.tournament_size, len(self.population)),
                replace=False
            )
            return max(contestants, key=lambda x: x.fitness)

        return tournament(), tournament()

    def _roulette_selection(self) -> Tuple[Individual, Individual]:
        """Roulette wheel selection."""
        fitnesses = np.array([ind.fitness for ind in self.population])
        fitnesses = fitnesses - fitnesses.min() + 1e-10  # Make all positive
        probs = fitnesses / fitnesses.sum()

        indices = np.random.choice(len(self.population), size=2, p=probs, replace=False)
        return self.population[indices[0]], self.population[indices[1]]

    def _rank_selection(self) -> Tuple[Individual, Individual]:
        """Rank-based selection."""
        sorted_pop = sorted(self.population, key=lambda x: x.fitness)
        ranks = np.arange(1, len(sorted_pop) + 1)
        probs = ranks / ranks.sum()

        indices = np.random.choice(len(sorted_pop), size=2, p=probs, replace=False)
        return sorted_pop[indices[0]], sorted_pop[indices[1]]

    def _elitist_selection(self) -> Tuple[Individual, Individual]:
        """Elitist selection (top individuals only)."""
        sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)
        top_half = sorted_pop[:len(sorted_pop) // 2]

        indices = np.random.choice(len(top_half), size=2, replace=False)
        return top_half[indices[0]], top_half[indices[1]]

    def crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """
        Perform crossover between two parents.

        Args:
            parent1, parent2: Parent individuals

        Returns:
            Tuple of two offspring
        """
        method = self.config.crossover_method

        if np.random.random() > self.config.crossover_rate:
            # No crossover, return copies
            return parent1.copy(), parent2.copy()

        if method == CrossoverMethod.SINGLE_POINT:
            return self._single_point_crossover(parent1, parent2)
        elif method == CrossoverMethod.TWO_POINT:
            return self._two_point_crossover(parent1, parent2)
        elif method == CrossoverMethod.UNIFORM:
            return self._uniform_crossover(parent1, parent2)
        elif method == CrossoverMethod.ARITHMETIC:
            return self._arithmetic_crossover(parent1, parent2)
        else:  # GOLDEN_RATIO
            return self._golden_ratio_crossover(parent1, parent2)

    def _single_point_crossover(self, p1: Individual, p2: Individual
                                ) -> Tuple[Individual, Individual]:
        """Single-point crossover."""
        point = np.random.randint(1, self.n_params)

        child1_genome = np.concatenate([p1.genome[:point], p2.genome[point:]])
        child2_genome = np.concatenate([p2.genome[:point], p1.genome[point:]])

        child1 = Individual(
            genome=child1_genome,
            generation=self.generation + 1,
            parent_ids=[p1.id, p2.id]
        )
        child2 = Individual(
            genome=child2_genome,
            generation=self.generation + 1,
            parent_ids=[p1.id, p2.id]
        )

        return child1, child2

    def _two_point_crossover(self, p1: Individual, p2: Individual
                             ) -> Tuple[Individual, Individual]:
        """Two-point crossover."""
        points = sorted(np.random.choice(range(1, self.n_params), size=2, replace=False))

        child1_genome = np.concatenate([
            p1.genome[:points[0]],
            p2.genome[points[0]:points[1]],
            p1.genome[points[1]:]
        ])
        child2_genome = np.concatenate([
            p2.genome[:points[0]],
            p1.genome[points[0]:points[1]],
            p2.genome[points[1]:]
        ])

        child1 = Individual(genome=child1_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])
        child2 = Individual(genome=child2_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])

        return child1, child2

    def _uniform_crossover(self, p1: Individual, p2: Individual
                          ) -> Tuple[Individual, Individual]:
        """Uniform crossover (each gene from random parent)."""
        mask = np.random.random(self.n_params) > 0.5

        child1_genome = np.where(mask, p1.genome, p2.genome)
        child2_genome = np.where(mask, p2.genome, p1.genome)

        child1 = Individual(genome=child1_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])
        child2 = Individual(genome=child2_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])

        return child1, child2

    def _arithmetic_crossover(self, p1: Individual, p2: Individual
                             ) -> Tuple[Individual, Individual]:
        """Arithmetic (blend) crossover."""
        alpha = np.random.random()

        child1_genome = alpha * p1.genome + (1 - alpha) * p2.genome
        child2_genome = (1 - alpha) * p1.genome + alpha * p2.genome

        child1 = Individual(genome=child1_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])
        child2 = Individual(genome=child2_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])

        return child1, child2

    def _golden_ratio_crossover(self, p1: Individual, p2: Individual
                               ) -> Tuple[Individual, Individual]:
        """Golden ratio crossover using φ = 1.618..."""
        phi_inv = 1.0 / GOLDEN_RATIO  # 0.618...

        child1_genome = phi_inv * p1.genome + (1 - phi_inv) * p2.genome
        child2_genome = (1 - phi_inv) * p1.genome + phi_inv * p2.genome

        child1 = Individual(genome=child1_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])
        child2 = Individual(genome=child2_genome, generation=self.generation + 1,
                           parent_ids=[p1.id, p2.id])

        return child1, child2

    def mutate(self, individual: Individual) -> Individual:
        """
        Apply mutation to an individual.

        Args:
            individual: Individual to mutate

        Returns:
            Mutated individual
        """
        if np.random.random() > self.config.mutation_rate:
            return individual

        method = self.config.mutation_method

        if method == MutationMethod.GAUSSIAN:
            return self._gaussian_mutation(individual)
        elif method == MutationMethod.UNIFORM:
            return self._uniform_mutation(individual)
        elif method == MutationMethod.PHASE_CONJUGATE:
            return self._phase_conjugate_mutation(individual)
        else:  # ADAPTIVE
            return self._adaptive_mutation(individual)

    def _gaussian_mutation(self, ind: Individual) -> Individual:
        """Gaussian mutation."""
        mutation = np.random.normal(0, self.config.mutation_strength, self.n_params)
        ind.genome = ind.genome + mutation
        ind.genome = np.clip(ind.genome, self.bounds[0], self.bounds[1])
        ind.mutations += 1
        return ind

    def _uniform_mutation(self, ind: Individual) -> Individual:
        """Uniform random mutation."""
        mask = np.random.random(self.n_params) < 0.1
        new_values = np.random.uniform(self.bounds[0], self.bounds[1], self.n_params)
        ind.genome = np.where(mask, new_values, ind.genome)
        ind.mutations += 1
        return ind

    def _phase_conjugate_mutation(self, ind: Individual) -> Individual:
        """
        Phase-conjugate mutation.

        Inverts phase of random subset of genes, then blends with original.
        This is the DNA::}{::lang native mutation operator.
        """
        # Select genes to mutate
        n_mutate = max(1, int(0.1 * self.n_params))
        indices = np.random.choice(self.n_params, size=n_mutate, replace=False)

        # Phase conjugate: θ → -θ + small noise
        for i in indices:
            original = ind.genome[i]
            conjugate = -original
            noise = np.random.normal(0, self.config.mutation_strength)
            # Blend with chi_pc coupling
            ind.genome[i] = CHI_PC * conjugate + (1 - CHI_PC) * original + noise

        ind.genome = np.clip(ind.genome, self.bounds[0], self.bounds[1])
        ind.mutations += 1
        return ind

    def _adaptive_mutation(self, ind: Individual) -> Individual:
        """Adaptive mutation based on fitness."""
        # Higher mutation strength for low-fitness individuals
        if ind.fitness > 0:
            adaptation = 1.0 / (1.0 + ind.fitness)
        else:
            adaptation = 1.0

        strength = self.config.mutation_strength * adaptation
        mutation = np.random.normal(0, strength, self.n_params)
        ind.genome = ind.genome + mutation
        ind.genome = np.clip(ind.genome, self.bounds[0], self.bounds[1])
        ind.mutations += 1
        return ind

    def evolve_generation(self, fitness_fn: Callable):
        """
        Evolve one generation.

        Args:
            fitness_fn: Fitness function
        """
        # Evaluate current population
        self.evaluate_population(fitness_fn)

        # Sort by fitness
        sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)

        # Elitism: keep best individuals
        new_population = [ind.copy() for ind in sorted_pop[:self.config.elite_count]]

        # Generate rest of population through selection, crossover, mutation
        while len(new_population) < self.config.population_size:
            parent1, parent2 = self.select_parents()
            child1, child2 = self.crossover(parent1, parent2)
            child1 = self.mutate(child1)
            child2 = self.mutate(child2)
            new_population.extend([child1, child2])

        # Trim to exact population size
        self.population = new_population[:self.config.population_size]
        self.generation += 1

        # Record history
        best = max(self.population, key=lambda x: x.fitness)
        avg_fitness = np.mean([ind.fitness for ind in self.population])
        self._history.append({
            'generation': self.generation,
            'best_fitness': best.fitness,
            'avg_fitness': avg_fitness,
            'best_phi': best.phi,
            'best_lambda': best.lambda_c,
            'best_gamma': best.gamma
        })

    def run(self, fitness_fn: Callable,
            callback: Optional[Callable] = None) -> Individual:
        """
        Run complete evolution.

        Args:
            fitness_fn: Fitness evaluation function
            callback: Optional callback(generation, best) called each generation

        Returns:
            Best individual found
        """
        if not self.population:
            self.initialize_population()

        for gen in range(self.config.max_generations):
            self.evolve_generation(fitness_fn)

            best = self.best_individual
            if callback:
                callback(self.generation, best)

            # Check convergence
            if len(self._history) >= 10:
                recent = [h['best_fitness'] for h in self._history[-10:]]
                if np.std(recent) < self.config.convergence_threshold:
                    break

        return self.best_individual

    @property
    def best_individual(self) -> Optional[Individual]:
        """Get best individual in current population."""
        if not self.population:
            return None
        return max(self.population, key=lambda x: x.fitness)

    @property
    def best_ever(self) -> Optional[Individual]:
        """Get best individual ever found."""
        return self._best_ever

    @property
    def history(self) -> List[Dict[str, float]]:
        """Get evolution history."""
        return self._history

    def telemetry(self) -> Dict[str, Any]:
        """Get engine telemetry."""
        return {
            'genesis': self._genesis,
            'generation': self.generation,
            'population_size': len(self.population),
            'best_fitness': self.best_individual.fitness if self.best_individual else 0.0,
            'best_ever_fitness': self._best_ever.fitness if self._best_ever else 0.0,
            'history_length': len(self._history),
            'config': {
                'selection': self.config.selection_method.value,
                'crossover': self.config.crossover_method.value,
                'mutation': self.config.mutation_method.value
            }
        }

    def __repr__(self) -> str:
        best = self.best_individual
        fitness = best.fitness if best else 0.0
        return (f"GeneticEvolutionEngine(gen={self.generation}, "
                f"pop={len(self.population)}, best_Ξ={fitness:.4f})")


__all__ = [
    'GeneticEvolutionEngine', 'EvolutionConfig', 'Individual',
    'SelectionMethod', 'CrossoverMethod', 'MutationMethod'
]
