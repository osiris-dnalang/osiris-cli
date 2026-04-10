"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              NCLMEvolution — NCLM-Specific Genetic Evolution                 ║
║              ═══════════════════════════════════════════                     ║
║                                                                              ║
║    Wraps GeneticEvolutionEngine with NCLM defaults:                         ║
║    ├── SelectionMethod.TOURNAMENT                                           ║
║    ├── CrossoverMethod.GOLDEN_RATIO                                         ║
║    ├── MutationMethod.PHASE_CONJUGATE                                       ║
║    └── Phase-conjugate healing enabled                                      ║
║                                                                              ║
║    Copyright (c) 2025-2026 Devin Phillip Davis / Agile Defense Systems LLC  ║
║    Licensed under OSIRIS Source-Available Dual License v1.0                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from typing import Dict, Any, Optional, Callable, Tuple

import numpy as np

from qbyte_system.genetic_evolution import (
    GeneticEvolutionEngine, EvolutionConfig, Individual,
    SelectionMethod, CrossoverMethod, MutationMethod,
)

logger = logging.getLogger("NCLM")


class NCLMEvolution:
    """
    NCLM-specific genetic evolution wrapper.

    Provides sensible defaults for evolving qByte circuit parameters:
    - Tournament selection (size 5)
    - Golden-ratio crossover
    - Phase-conjugate mutation (self-healing)
    - Elitism (top 2 preserved)

    Usage:
        evo = NCLMEvolution(n_params=72)
        best = evo.run(fitness_fn, verbose=True)
    """

    # NCLM defaults
    DEFAULT_POPULATION = 30
    DEFAULT_GENERATIONS = 50
    DEFAULT_ELITE = 2
    DEFAULT_TOURNAMENT_SIZE = 5
    DEFAULT_CROSSOVER_RATE = 0.8
    DEFAULT_MUTATION_RATE = 0.15
    DEFAULT_MUTATION_STRENGTH = 0.2

    def __init__(self, n_params: int,
                 population_size: int = DEFAULT_POPULATION,
                 max_generations: int = DEFAULT_GENERATIONS,
                 mutation_rate: float = DEFAULT_MUTATION_RATE,
                 mutation_strength: float = DEFAULT_MUTATION_STRENGTH):
        self.n_params = n_params

        self._config = EvolutionConfig(
            population_size=population_size,
            elite_count=self.DEFAULT_ELITE,
            tournament_size=self.DEFAULT_TOURNAMENT_SIZE,
            crossover_rate=self.DEFAULT_CROSSOVER_RATE,
            mutation_rate=mutation_rate,
            mutation_strength=mutation_strength,
            selection_method=SelectionMethod.TOURNAMENT,
            crossover_method=CrossoverMethod.GOLDEN_RATIO,
            mutation_method=MutationMethod.PHASE_CONJUGATE,
            max_generations=max_generations,
            convergence_threshold=1e-8,
            enable_healing=True,
        )

        self._engine = GeneticEvolutionEngine(
            n_params=n_params,
            config=self._config,
            bounds=(-np.pi, np.pi),
        )

        self._history = []

    def run(self, fitness_fn: Callable[[np.ndarray], Tuple[float, float, float, float]],
            callback: Optional[Callable] = None,
            verbose: bool = False) -> Individual:
        """
        Run genetic evolution.

        Args:
            fitness_fn: f(genome) -> (energy, phi, lambda_c, gamma)
            callback: Optional callback(generation, best_individual)
            verbose: Print progress

        Returns:
            Best Individual after evolution
        """
        self._engine.initialize_population()

        def _cb(gen, best):
            record = {
                'generation': gen,
                'fitness': best.fitness,
                'phi': best.phi,
                'lambda_c': best.lambda_c,
                'gamma': best.gamma,
                'conscious': best.is_conscious(),
            }
            self._history.append(record)
            if verbose:
                state = "CONSCIOUS" if best.is_conscious() else "emerging"
                logger.info(
                    f"gen {gen:3d}  Ξ={best.fitness:.4f}  "
                    f"Φ={best.phi:.4f}  Λ={best.lambda_c:.4f}  "
                    f"Γ={best.gamma:.4f}  [{state}]"
                )
            if callback:
                callback(gen, best)

        best = self._engine.run(fitness_fn=fitness_fn, callback=_cb)
        return best

    @property
    def generation(self) -> int:
        return self._engine.generation

    @property
    def history(self):
        return self._history

    def summary(self) -> Dict[str, Any]:
        """Return evolution summary."""
        if not self._history:
            return {'status': 'not_run'}
        last = self._history[-1]
        return {
            'generations': len(self._history),
            'best_fitness': last['fitness'],
            'best_phi': last['phi'],
            'conscious': last['conscious'],
            'n_params': self.n_params,
        }
