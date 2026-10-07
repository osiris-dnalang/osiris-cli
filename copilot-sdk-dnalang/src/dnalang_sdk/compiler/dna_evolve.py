#!/usr/bin/env python3
"""
dna_evolve.py - DNA-Lang Evolutionary Optimization Engine
Implements DARWINIAN-LOOP and EOTS (Evolutionary Optimization Triage System)
"""

import random
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from copy import deepcopy
import json

from .dna_ir import (
    QuantumCircuitIR, IROperation, IROpType,
    QuantumRegister, ClassicalRegister
)

# ==========================================
# EVOLUTIONARY CONSTANTS
# ==========================================

# Universal Memory Constant
LAMBDA_PHI = 2.176435e-8  # s^-1

# Evolution parameters
DEFAULT_POPULATION_SIZE = 8
DEFAULT_MUTATION_RATE = 0.15
DEFAULT_CROSSOVER_RATE = 0.7
DEFAULT_ELITE_SIZE = 2
DEFAULT_MAX_GENERATIONS = 50

# Fitness weights
ALPHA_GATE_ERROR = 0.4
BETA_DECOHERENCE = 0.3
GAMMA_FIDELITY = 0.3

# ==========================================
# FITNESS FUNCTIONS
# ==========================================

@dataclass
class FitnessMetrics:
    """Comprehensive fitness metrics for quantum organism"""
    
    # Primary metrics
    lambda_coherence: float = 0.0      # Λ - Coherence measure
    gamma_decoherence: float = 1.0     # Γ - Decoherence rate
    phi_integrated_info: float = 0.0   # Φ - Integrated information
    w2_distance: float = 0.0           # W₂ - Wasserstein distance
    
    # Circuit metrics
    gate_count: int = 0
    circuit_depth: int = 0
    qubit_count: int = 0
    
    # Hardware metrics
    expected_fidelity: float = 0.0
    gate_error_rate: float = 0.0
    
    # Composite fitness
    fitness: float = 0.0
    
    def compute_fitness(self) -> float:
        """
        Compute composite fitness score
        
        Fitness = Λ - αΓ - β(gate_error) + γ(Φ)
        """
        # Normalize gate count (penalty for complexity)
        gate_penalty = min(self.gate_count / 100.0, 1.0)
        
        # Normalize depth (penalty for deep circuits)
        depth_penalty = min(self.circuit_depth / 50.0, 1.0)
        
        # Compute fitness
        self.fitness = (
            self.lambda_coherence
            - ALPHA_GATE_ERROR * self.gamma_decoherence
            - BETA_DECOHERENCE * (gate_penalty + depth_penalty)
            + GAMMA_FIDELITY * self.phi_integrated_info
        )
        
        # Ensure non-negative
        self.fitness = max(0.0, self.fitness)
        
        return self.fitness

class FitnessEvaluator:
    """Evaluates fitness of quantum circuits"""
    
    @staticmethod
    def evaluate_circuit(circuit: QuantumCircuitIR, 
                        backend_calibration: Optional[Dict] = None) -> FitnessMetrics:
        """
        Evaluate circuit fitness
        
        Args:
            circuit: Circuit to evaluate
            backend_calibration: Hardware calibration data
            
        Returns:
            Fitness metrics
        """
        metrics = FitnessMetrics()
        
        # Basic circuit metrics
        metrics.gate_count = circuit.gate_count
        metrics.circuit_depth = circuit.depth
        metrics.qubit_count = circuit.qubit_count
        
        # Estimate lambda coherence (higher is better)
        # λ ∝ 1/depth * entanglement_ops
        entanglement_ops = sum(1 for op in circuit.operations 
                              if op.op_type in [IROpType.CX, IROpType.CY, IROpType.CZ])
        
        if circuit.depth > 0:
            metrics.lambda_coherence = (entanglement_ops / circuit.depth) * LAMBDA_PHI * 1e8
        else:
            metrics.lambda_coherence = 0.0
        
        # Estimate gamma decoherence (lower is better)
        # Γ ∝ depth * gate_count
        metrics.gamma_decoherence = (circuit.depth * circuit.gate_count) / 1000.0
        
        # Estimate integrated information Φ
        # Φ ∝ entanglement_density
        if circuit.gate_count > 0:
            metrics.phi_integrated_info = entanglement_ops / circuit.gate_count
        else:
            metrics.phi_integrated_info = 0.0
        
        # Estimate fidelity from backend calibration
        if backend_calibration:
            metrics.expected_fidelity = FitnessEvaluator._estimate_fidelity(
                circuit, backend_calibration
            )
            metrics.gate_error_rate = backend_calibration.get('avg_gate_error', 0.01)
        else:
            # Default estimates
            metrics.expected_fidelity = 0.85
            metrics.gate_error_rate = 0.01
        
        # Compute composite fitness
        metrics.compute_fitness()
        
        # Update circuit metrics
        circuit.lambda_coherence = metrics.lambda_coherence
        circuit.gamma_decoherence = metrics.gamma_decoherence
        circuit.phi_integrated_info = metrics.phi_integrated_info
        
        return metrics
    
    @staticmethod
    def _estimate_fidelity(circuit: QuantumCircuitIR, 
                          calibration: Dict) -> float:
        """Estimate circuit fidelity from hardware calibration"""
        # Simplified fidelity model: F = ∏(1 - error_i)
        fidelity = 1.0
        
        avg_single_gate_error = calibration.get('avg_single_gate_error', 0.001)
        avg_two_gate_error = calibration.get('avg_two_gate_error', 0.01)
        
        for op in circuit.operations:
            if len(op.qubits) == 1:
                fidelity *= (1.0 - avg_single_gate_error)
            elif len(op.qubits) == 2:
                fidelity *= (1.0 - avg_two_gate_error)
        
        return fidelity

# ==========================================
# MUTATION OPERATORS
# ==========================================

class MutationOperator:
    """Genetic mutation operators for quantum circuits"""
    
    @staticmethod
    def mutate_gate_replacement(circuit: QuantumCircuitIR, 
                                rate: float = 0.1) -> QuantumCircuitIR:
        """Replace random gates with equivalent alternatives"""
        mutated = deepcopy(circuit)
        
        for i, op in enumerate(mutated.operations):
            if random.random() < rate and op.op_type != IROpType.MEASURE:
                # Single-qubit gate alternatives
                if len(op.qubits) == 1:
                    alternatives = [IROpType.X, IROpType.Y, IROpType.Z, IROpType.H]
                    mutated.operations[i].op_type = random.choice(alternatives)
                
                # Two-qubit gate alternatives
                elif len(op.qubits) == 2:
                    alternatives = [IROpType.CX, IROpType.CY, IROpType.CZ]
                    mutated.operations[i].op_type = random.choice(alternatives)
        
        mutated.compute_metrics()
        return mutated
    
    @staticmethod
    def mutate_gate_insertion(circuit: QuantumCircuitIR,
                             rate: float = 0.05) -> QuantumCircuitIR:
        """Insert random gates at random positions"""
        mutated = deepcopy(circuit)
        
        if random.random() < rate:
            # Choose random position
            pos = random.randint(0, len(mutated.operations))
            
            # Choose random qubit
            qubit = random.randint(0, circuit.qubit_count - 1)
            
            # Choose random gate
            gate_type = random.choice([IROpType.H, IROpType.X, IROpType.Y, IROpType.Z])
            
            # Insert gate
            new_op = IROperation(op_type=gate_type, qubits=[qubit])
            mutated.operations.insert(pos, new_op)
        
        mutated.compute_metrics()
        return mutated
    
    @staticmethod
    def mutate_gate_deletion(circuit: QuantumCircuitIR,
                            rate: float = 0.05) -> QuantumCircuitIR:
        """Delete random gates"""
        mutated = deepcopy(circuit)
        
        if random.random() < rate and len(mutated.operations) > 2:
            # Find non-measurement operations
            non_measure_indices = [i for i, op in enumerate(mutated.operations)
                                  if op.op_type != IROpType.MEASURE]
            
            if non_measure_indices:
                # Delete random operation
                del_idx = random.choice(non_measure_indices)
                del mutated.operations[del_idx]
        
        mutated.compute_metrics()
        return mutated
    
    @staticmethod
    def mutate_parameter_perturbation(circuit: QuantumCircuitIR,
                                     rate: float = 0.1,
                                     scale: float = 0.1) -> QuantumCircuitIR:
        """Perturb rotation gate parameters"""
        mutated = deepcopy(circuit)
        
        for op in mutated.operations:
            if op.params and random.random() < rate:
                # Perturb each parameter
                op.params = [
                    p + np.random.normal(0, scale * np.pi)
                    for p in op.params
                ]
        
        mutated.compute_metrics()
        return mutated
    
    @staticmethod
    def apply_mutations(circuit: QuantumCircuitIR,
                       mutation_rate: float = 0.15) -> QuantumCircuitIR:
        """Apply all mutation operators with given probability"""
        mutated = deepcopy(circuit)
        
        # Apply each mutation type probabilistically
        if random.random() < mutation_rate:
            mutated = MutationOperator.mutate_gate_replacement(mutated, rate=0.1)
        
        if random.random() < mutation_rate * 0.5:
            mutated = MutationOperator.mutate_gate_insertion(mutated, rate=0.05)
        
        if random.random() < mutation_rate * 0.5:
            mutated = MutationOperator.mutate_gate_deletion(mutated, rate=0.05)
        
        if random.random() < mutation_rate:
            mutated = MutationOperator.mutate_parameter_perturbation(mutated, rate=0.1)
        
        # Update lineage
        parent_hash = circuit.lineage_hash
        mutated.parent_hash = parent_hash
        mutated.generation = circuit.generation + 1
        mutated.lineage_hash = MutationOperator._compute_lineage_hash(mutated)
        
        return mutated
    
    @staticmethod
    def _compute_lineage_hash(circuit: QuantumCircuitIR) -> str:
        """Compute new lineage hash"""
        data = f"{circuit.name}:{circuit.parent_hash}:{circuit.generation}:"
        for op in circuit.operations:
            data += f"{op.op_type.value}-{op.qubits};"
        
        return hashlib.sha256(data.encode()).hexdigest()[:16]

# ==========================================
# CROSSOVER OPERATORS
# ==========================================

class CrossoverOperator:
    """Genetic crossover operators for quantum circuits"""
    
    @staticmethod
    def single_point_crossover(parent1: QuantumCircuitIR,
                              parent2: QuantumCircuitIR) -> Tuple[QuantumCircuitIR, QuantumCircuitIR]:
        """Single-point crossover between two circuits"""
        child1 = deepcopy(parent1)
        child2 = deepcopy(parent2)
        
        # Find crossover point
        min_len = min(len(parent1.operations), len(parent2.operations))
        if min_len > 2:
            crossover_point = random.randint(1, min_len - 1)
            
            # Swap tails
            child1.operations = (parent1.operations[:crossover_point] + 
                               parent2.operations[crossover_point:])
            child2.operations = (parent2.operations[:crossover_point] + 
                               parent1.operations[crossover_point:])
            
            # Update metrics and lineage
            child1.compute_metrics()
            child2.compute_metrics()
            
            child1.parent_hash = f"{parent1.lineage_hash}+{parent2.lineage_hash}"
            child2.parent_hash = f"{parent2.lineage_hash}+{parent1.lineage_hash}"
            
            child1.generation = max(parent1.generation, parent2.generation) + 1
            child2.generation = max(parent1.generation, parent2.generation) + 1
            
            child1.lineage_hash = MutationOperator._compute_lineage_hash(child1)
            child2.lineage_hash = MutationOperator._compute_lineage_hash(child2)
        
        return child1, child2

# ==========================================
# EVOLUTIONARY ALGORITHM
# ==========================================

@dataclass
class EvolutionResult:
    """Result of evolutionary optimization"""
    best_circuit: QuantumCircuitIR
    best_fitness: float
    generation: int
    fitness_history: List[float]
    population_history: List[List[QuantumCircuitIR]]
    convergence_generation: Optional[int] = None

class EvolutionaryOptimizer:
    """EOTS - Evolutionary Optimization Triage System"""
    
    def __init__(self,
                 population_size: int = DEFAULT_POPULATION_SIZE,
                 mutation_rate: float = DEFAULT_MUTATION_RATE,
                 crossover_rate: float = DEFAULT_CROSSOVER_RATE,
                 elite_size: int = DEFAULT_ELITE_SIZE,
                 max_generations: int = DEFAULT_MAX_GENERATIONS):
        
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        self.max_generations = max_generations
        
        self.evaluator = FitnessEvaluator()
    
    def evolve(self, 
              initial_circuit: QuantumCircuitIR,
              backend_calibration: Optional[Dict] = None,
              convergence_threshold: float = 1e-4) -> EvolutionResult:
        """
        Evolve quantum circuit using DARWINIAN-LOOP
        
        Args:
            initial_circuit: Starting circuit
            backend_calibration: Hardware calibration data
            convergence_threshold: Stop when fitness improvement < threshold
            
        Returns:
            Evolution result with best circuit
        """
        # Initialize population
        population = [deepcopy(initial_circuit) for _ in range(self.population_size)]
        
        # Mutate initial population for diversity
        for i in range(1, len(population)):
            population[i] = MutationOperator.apply_mutations(
                population[i], 
                mutation_rate=self.mutation_rate
            )
        
        # Track evolution
        fitness_history = []
        population_history = []
        best_circuit = None
        best_fitness = 0.0
        convergence_gen = None
        
        # Evolution loop
        for generation in range(self.max_generations):
            # Evaluate fitness
            fitness_scores = []
            for circuit in population:
                metrics = self.evaluator.evaluate_circuit(circuit, backend_calibration)
                fitness_scores.append(metrics.fitness)
            
            # Track best
            gen_best_idx = np.argmax(fitness_scores)
            gen_best_fitness = fitness_scores[gen_best_idx]
            
            if gen_best_fitness > best_fitness:
                best_fitness = gen_best_fitness
                best_circuit = deepcopy(population[gen_best_idx])
            
            fitness_history.append(best_fitness)
            population_history.append(deepcopy(population))
            
            # Check convergence
            if len(fitness_history) > 5:
                recent_improvement = fitness_history[-1] - fitness_history[-5]
                if recent_improvement < convergence_threshold:
                    convergence_gen = generation
                    break
            
            # Selection
            sorted_indices = np.argsort(fitness_scores)[::-1]
            elite = [population[i] for i in sorted_indices[:self.elite_size]]
            
            # Generate new population
            new_population = elite.copy()
            
            while len(new_population) < self.population_size:
                # Tournament selection
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                
                # Crossover
                if random.random() < self.crossover_rate:
                    child1, child2 = CrossoverOperator.single_point_crossover(
                        parent1, parent2
                    )
                else:
                    child1, child2 = deepcopy(parent1), deepcopy(parent2)
                
                # Mutation
                child1 = MutationOperator.apply_mutations(child1, self.mutation_rate)
                child2 = MutationOperator.apply_mutations(child2, self.mutation_rate)
                
                new_population.extend([child1, child2])
            
            # Trim to population size
            population = new_population[:self.population_size]
        
        return EvolutionResult(
            best_circuit=best_circuit or initial_circuit,
            best_fitness=best_fitness,
            generation=generation,
            fitness_history=fitness_history,
            population_history=population_history,
            convergence_generation=convergence_gen
        )
    
    def _tournament_selection(self, 
                             population: List[QuantumCircuitIR],
                             fitness_scores: List[float],
                             tournament_size: int = 3) -> QuantumCircuitIR:
        """Tournament selection"""
        tournament_indices = random.sample(range(len(population)), tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx]

# ==========================================
# MAIN INTERFACE
# ==========================================

def evolve_organism(circuit: QuantumCircuitIR,
                   generations: int = DEFAULT_MAX_GENERATIONS,
                   population_size: int = DEFAULT_POPULATION_SIZE,
                   backend_calibration: Optional[Dict] = None) -> EvolutionResult:
    """
    Evolve quantum organism using DARWINIAN-LOOP
    
    Args:
        circuit: Initial circuit
        generations: Maximum generations
        population_size: Population size
        backend_calibration: Hardware calibration data
        
    Returns:
        Evolution result with best circuit
    """
    optimizer = EvolutionaryOptimizer(
        population_size=population_size,
        max_generations=generations
    )
    
    return optimizer.evolve(circuit, backend_calibration)

if __name__ == "__main__":
    from dna_parser import parse_dna_lang
    from dna_ir import compile_to_ir
    
    # Test evolution
    test_source = """
organism test_evolution {
    quantum_state {
        helix(q[0]);
        bond(q[0], q[1]);
        helix(q[1]);
        measure(q[0]);
        measure(q[1]);
    }
    
    fitness = lambda;
}
"""
    
    print("=== Evolutionary Optimizer Test ===")
    organisms = parse_dna_lang(test_source)
    
    for organism in organisms:
        print(f"\nEvolving organism: {organism.name}")
        circuit = compile_to_ir(organism)
        
        print(f"Initial fitness: {FitnessEvaluator.evaluate_circuit(circuit).fitness:.4f}")
        
        # Evolve
        result = evolve_organism(circuit, generations=20, population_size=8)
        
        print(f"\nEvolution complete:")
        print(f"  Generations: {result.generation}")
        print(f"  Best fitness: {result.best_fitness:.4f}")
        print(f"  Fitness improvement: {result.best_fitness - result.fitness_history[0]:.4f}")
        print(f"  Convergence generation: {result.convergence_generation}")
        
        print(f"\n  Optimized circuit:")
        print(f"    Gate count: {result.best_circuit.gate_count}")
        print(f"    Circuit depth: {result.best_circuit.depth}")
        print(f"    λ-coherence: {result.best_circuit.lambda_coherence:.6f}")
        print(f"    Γ-decoherence: {result.best_circuit.gamma_decoherence:.6f}")
        print(f"    Φ-integrated info: {result.best_circuit.phi_integrated_info:.6f}")
