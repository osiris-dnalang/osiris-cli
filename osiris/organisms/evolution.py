"""
osiris.organisms.evolution — Evolution Engine
=============================================

Drives evolutionary cycles over populations of Organisms using
tournament, roulette, and rank selection strategies.
"""

from typing import Callable, Dict, Any, List, Optional
import random

from .organism import Organism
from .genome import Genome


class EvolutionEngine:
    """Drives evolutionary cycles over organisms."""

    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        selection: str = "tournament",
        elitism: int = 2,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.selection_method = selection
        self.elitism = elitism
        self.generation = 0
        self.history: List[Dict[str, Any]] = []

    def evolve_population(
        self, population: List[Organism],
        fitness_fn: Optional[Callable[[Organism], float]] = None,
        generations: int = 1,
    ) -> List[Organism]:
        current = list(population)
        for _ in range(generations):
            scores = [(org, (fitness_fn(org) if fitness_fn else org.genome.fitness()))
                      for org in current]
            scores.sort(key=lambda x: x[1], reverse=True)
            elite = [org for org, _ in scores[:self.elitism]]
            new_pop = list(elite)
            while len(new_pop) < self.population_size:
                p1, p2 = self._select(scores), self._select(scores)
                if random.random() < self.crossover_rate:
                    child_genome = p1.genome.crossover(p2.genome)
                else:
                    child_genome = p1.genome
                if random.random() < self.mutation_rate:
                    child_genome = child_genome.mutate(self.mutation_rate)
                child = Organism(
                    name=f"gen{self.generation}_{len(new_pop)}",
                    genome=child_genome,
                    domain=p1.domain,
                    purpose=p1.purpose,
                )
                new_pop.append(child)
            self.generation += 1
            best_fitness = scores[0][1]
            avg_fitness = sum(s for _, s in scores) / len(scores)
            self.history.append({
                "generation": self.generation,
                "best_fitness": best_fitness,
                "avg_fitness": avg_fitness,
                "population_size": len(new_pop),
            })
            current = new_pop
        return current

    def _select(self, scored: List[tuple]) -> Organism:
        if self.selection_method == "tournament":
            return self._tournament(scored)
        elif self.selection_method == "roulette":
            return self._roulette(scored)
        else:
            return self._rank(scored)

    def _tournament(self, scored: List[tuple], k: int = 3) -> Organism:
        contenders = random.sample(scored, min(k, len(scored)))
        return max(contenders, key=lambda x: x[1])[0]

    def _roulette(self, scored: List[tuple]) -> Organism:
        total = sum(max(s, 0.001) for _, s in scored)
        pick = random.uniform(0, total)
        current = 0
        for org, score in scored:
            current += max(score, 0.001)
            if current >= pick:
                return org
        return scored[-1][0]

    def _rank(self, scored: List[tuple]) -> Organism:
        n = len(scored)
        weights = list(range(n, 0, -1))
        total = sum(weights)
        pick = random.uniform(0, total)
        current = 0
        for i, (org, _) in enumerate(scored):
            current += weights[i]
            if current >= pick:
                return org
        return scored[-1][0]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population_size": self.population_size,
            "mutation_rate": self.mutation_rate,
            "crossover_rate": self.crossover_rate,
            "selection": self.selection_method,
            "history_length": len(self.history),
        }
