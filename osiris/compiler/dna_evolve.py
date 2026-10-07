"""
DNA-Lang Evolutionary Optimization Engine — DARWINIAN-LOOP.
"""

import random
import hashlib
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from copy import deepcopy

from .dna_ir import QuantumCircuitIR, IROperation, IROpType, QuantumRegister, ClassicalRegister

LAMBDA_PHI = 2.176435e-8
DEFAULT_POPULATION_SIZE = 8
DEFAULT_MUTATION_RATE = 0.15
DEFAULT_CROSSOVER_RATE = 0.7
DEFAULT_ELITE_SIZE = 2
DEFAULT_MAX_GENERATIONS = 50


@dataclass
class FitnessMetrics:
    lambda_coherence: float = 0.0
    gamma_decoherence: float = 1.0
    phi_integrated_info: float = 0.0
    w2_distance: float = 0.0
    gate_count: int = 0
    circuit_depth: int = 0
    qubit_count: int = 0
    expected_fidelity: float = 0.0
    gate_error_rate: float = 0.0
    fitness: float = 0.0

    def compute_fitness(self) -> float:
        gate_penalty = min(self.gate_count / 100.0, 1.0)
        depth_penalty = min(self.circuit_depth / 50.0, 1.0)
        self.fitness = max(0.0,
            self.lambda_coherence
            - 0.4 * self.gamma_decoherence
            - 0.3 * (gate_penalty + depth_penalty)
            + 0.3 * self.phi_integrated_info
        )
        return self.fitness


class FitnessEvaluator:
    @staticmethod
    def evaluate_circuit(circuit: QuantumCircuitIR,
                         backend_calibration: Optional[Dict] = None) -> FitnessMetrics:
        metrics = FitnessMetrics()
        metrics.gate_count = circuit.gate_count
        metrics.circuit_depth = circuit.depth
        metrics.qubit_count = circuit.qubit_count
        entanglement_ops = sum(
            1 for op in circuit.operations
            if op.op_type in (IROpType.CX, IROpType.CY, IROpType.CZ)
        )
        if circuit.depth > 0:
            metrics.lambda_coherence = (entanglement_ops / circuit.depth) * LAMBDA_PHI * 1e8
        metrics.gamma_decoherence = (circuit.depth * circuit.gate_count) / 1000.0
        if circuit.gate_count > 0:
            metrics.phi_integrated_info = entanglement_ops / circuit.gate_count
        metrics.expected_fidelity = 0.85
        metrics.compute_fitness()
        circuit.lambda_coherence = metrics.lambda_coherence
        circuit.gamma_decoherence = metrics.gamma_decoherence
        circuit.phi_integrated_info = metrics.phi_integrated_info
        return metrics


@dataclass
class EvolutionResult:
    best_circuit: QuantumCircuitIR
    best_fitness: float
    generations: int
    population_size: int
    fitness_history: List[float] = field(default_factory=list)
    gene_pool_diversity: float = 0.0


class EvolutionaryOptimizer:
    """Evolutionary optimizer for quantum circuits via DARWINIAN-LOOP."""

    def __init__(self, population_size: int = DEFAULT_POPULATION_SIZE,
                 mutation_rate: float = DEFAULT_MUTATION_RATE,
                 crossover_rate: float = DEFAULT_CROSSOVER_RATE,
                 elite_size: int = DEFAULT_ELITE_SIZE):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size

    def evolve(self, circuit: QuantumCircuitIR,
               generations: int = DEFAULT_MAX_GENERATIONS) -> EvolutionResult:
        population = [deepcopy(circuit) for _ in range(self.population_size)]
        for c in population[1:]:
            self._mutate(c)

        fitness_history = []
        for gen in range(generations):
            scored = [(c, FitnessEvaluator.evaluate_circuit(c).fitness) for c in population]
            scored.sort(key=lambda x: x[1], reverse=True)
            fitness_history.append(scored[0][1])

            new_pop = [deepcopy(scored[i][0]) for i in range(min(self.elite_size, len(scored)))]
            while len(new_pop) < self.population_size:
                parent = scored[random.randint(0, len(scored) // 2)][0]
                child = deepcopy(parent)
                if random.random() < self.mutation_rate:
                    self._mutate(child)
                new_pop.append(child)
            population = new_pop

        scored = [(c, FitnessEvaluator.evaluate_circuit(c).fitness) for c in population]
        scored.sort(key=lambda x: x[1], reverse=True)
        best = scored[0][0]
        return EvolutionResult(
            best_circuit=best,
            best_fitness=scored[0][1],
            generations=generations,
            population_size=self.population_size,
            fitness_history=fitness_history,
        )

    @staticmethod
    def _mutate(circuit: QuantumCircuitIR):
        for i, op in enumerate(circuit.operations):
            if random.random() < 0.1 and op.op_type != IROpType.MEASURE:
                if len(op.qubits) == 1:
                    circuit.operations[i].op_type = random.choice(
                        [IROpType.X, IROpType.Y, IROpType.Z, IROpType.H])
                elif len(op.qubits) == 2:
                    circuit.operations[i].op_type = random.choice(
                        [IROpType.CX, IROpType.CY, IROpType.CZ])
        circuit.compute_metrics()
