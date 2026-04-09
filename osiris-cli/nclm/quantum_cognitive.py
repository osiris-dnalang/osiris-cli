# nclm/quantum_cognitive.py
import numpy as np
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class QuantumCognitiveState(Enum):
    """Quantum cognitive processing states"""
    COHERENT = 1
    DECOHERED = 2
    ENTANGLED = 3
    SUPERPOSITION = 4
    COLLAPSED = 5

@dataclass
class QuantumConcept:
    """Represents a concept in quantum cognitive space"""
    label: str
    amplitude: complex
    phase: float
    entangled_with: List[str]

    def probability(self) -> float:
        """Calculate probability of this concept state"""
        return abs(self.amplitude) ** 2

    def interfere_with(self, other: 'QuantumConcept') -> float:
        """Calculate interference between two concepts"""
        phase_diff = (self.phase - other.phase) % (2 * math.pi)
        return abs(self.amplitude) * abs(other.amplitude) * math.cos(phase_diff)

class QuantumCognitiveProcessor:
    """Advanced quantum-inspired cognitive processor"""

    def __init__(self, dimensions: int = 8):
        self.dimensions = dimensions
        self.state_vector = np.ones(dimensions, dtype=complex) / math.sqrt(dimensions)
        self.concept_space = {}
        self.entanglement_map = {}
        self.cognitive_operators = {
            'hadamard': self._apply_hadamard,
            'cnot': self._apply_cnot,
            'phase': self._apply_phase,
            'rotation': self._apply_rotation,
            'measure': self._measure
        }
        self.decay_rate = 0.01
        self.entanglement_strength = 0.5

    def initialize_concepts(self, concepts: List[str]):
        """Initialize quantum concept space"""
        self.concept_space = {
            concept: QuantumConcept(
                label=concept,
                amplitude=1/math.sqrt(len(concepts)),
                phase=0,
                entangled_with=[]
            )
            for concept in concepts
        }

    def entangle_concepts(self, concept1: str, concept2: str, strength: float = 0.7):
        """Create entanglement between concepts"""
        if concept1 in self.concept_space and concept2 in self.concept_space:
            self.concept_space[concept1].entangled_with.append(concept2)
            self.concept_space[concept2].entangled_with.append(concept1)
            self.entanglement_map[(concept1, concept2)] = strength
            self.entanglement_map[(concept2, concept1)] = strength

    def apply_operator(self, operator: str, **params) -> Dict:
        """Apply a quantum cognitive operator"""
        if operator in self.cognitive_operators:
            return self.cognitive_operators[operator](**params)
        return {"status": "error", "message": f"Unknown operator: {operator}"}

    def _apply_hadamard(self, qubit: int) -> Dict:
        """Apply Hadamard gate to create superposition"""
        if 0 <= qubit < self.dimensions:
            H = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
            # For simplicity, we'll just modify the state vector directly
            if qubit < len(self.state_vector):
                # Create superposition
                self.state_vector[qubit] = (self.state_vector[qubit] + self.state_vector[(qubit+1)%self.dimensions]) / math.sqrt(2)
                return {"status": "success", "operation": "hadamard", "qubit": qubit}
        return {"status": "error", "message": "Invalid qubit index"}

    def _apply_cnot(self, control: int, target: int) -> Dict:
        """Apply CNOT gate for entanglement"""
        if 0 <= control < self.dimensions and 0 <= target < self.dimensions:
            # Simplified CNOT operation
            if abs(self.state_vector[control]) > 0.7:  # If control is in |1> state
                self.state_vector[target] = 1 - self.state_vector[target]
            return {"status": "success", "operation": "cnot", "control": control, "target": target}
        return {"status": "error", "message": "Invalid qubit indices"}

    def _apply_phase(self, qubit: int, angle: float) -> Dict:
        """Apply phase shift to a concept"""
        if 0 <= qubit < self.dimensions:
            phase_shift = math.e ** (1j * angle)
            self.state_vector[qubit] *= phase_shift
            return {"status": "success", "operation": "phase", "qubit": qubit, "angle": angle}
        return {"status": "error", "message": "Invalid qubit index"}

    def _apply_rotation(self, qubit: int, angle: float) -> Dict:
        """Apply rotation to a concept"""
        if 0 <= qubit < self.dimensions:
            # Simplified rotation
            self.state_vector[qubit] = (
                math.cos(angle/2) * self.state_vector[qubit] +
                math.sin(angle/2) * (1 - self.state_vector[qubit])
            )
            return {"status": "success", "operation": "rotation", "qubit": qubit, "angle": angle}
        return {"status": "error", "message": "Invalid qubit index"}

    def _measure(self, qubit: int = None, shots: int = 1) -> Dict:
        """Measure the quantum cognitive state"""
        probabilities = [abs(amp)**2 for amp in self.state_vector]
        total = sum(probabilities)

        if total > 0:
            probabilities = [p/total for p in probabilities]

        if qubit is not None:
            if 0 <= qubit < self.dimensions:
                probabilities = [probabilities[qubit]]
            else:
                return {"status": "error", "message": "Invalid qubit index"}

        results = []
        for _ in range(shots):
            # Get measurement result
            r = np.random.choice(len(probabilities), p=probabilities)
            results.append(r)

        # Collapse the state vector
        if shots == 1 and qubit is None:
            self.state_vector = np.zeros(self.dimensions, dtype=complex)
            self.state_vector[results[0]] = 1.0

        return {
            "status": "success",
            "operation": "measure",
            "results": results,
            "probabilities": probabilities,
            "state_vector": [float(abs(amp)) for amp in self.state_vector]
        }

    def cognitive_interference(self, concept1: str, concept2: str) -> float:
        """Calculate cognitive interference between concepts"""
        if concept1 in self.concept_space and concept2 in self.concept_space:
            return self.concept_space[concept1].interfere_with(self.concept_space[concept2])
        return 0.0

    def concept_probability(self, concept: str) -> float:
        """Get probability of a concept"""
        if concept in self.concept_space:
            return self.concept_space[concept].probability()
        return 0.0

    def cognitive_collapse(self, concept: str) -> Dict:
        """Collapse cognitive state to a specific concept"""
        if concept in self.concept_space:
            # Increase probability of this concept
            self.concept_space[concept].amplitude = 0.9 + 0.1j
            # Decrease others
            for c in self.concept_space:
                if c != concept:
                    self.concept_space[c].amplitude = (0.1 / (len(self.concept_space) - 1)) * (1 + 0.1j)

            return {"status": "success", "concept": concept}
        return {"status": "error", "message": f"Concept {concept} not found"}

    def get_entanglement_strength(self, concept1: str, concept2: str) -> float:
        """Get entanglement strength between concepts"""
        return self.entanglement_map.get((concept1, concept2), 0.0)

    def cognitive_decay(self, time_steps: int = 1):
        """Simulate cognitive decay over time"""
        for concept in self.concept_space.values():
            # Reduce amplitude slightly
            concept.amplitude *= (1 - self.decay_rate * time_steps)

        # Renormalize
        total = sum(abs(c.amplitude)**2 for c in self.concept_space.values())
        if total > 0:
            norm_factor = math.sqrt(total)
            for concept in self.concept_space.values():
                concept.amplitude /= norm_factor

    def get_cognitive_state(self) -> Dict:
        """Get current cognitive state"""
        return {
            "concepts": {
                label: {
                    "probability": concept.probability(),
                    "phase": concept.phase,
                    "entangled_with": concept.entangled_with
                }
                for label, concept in self.concept_space.items()
            },
            "state_vector": [float(abs(amp)) for amp in self.state_vector],
            "entanglement_map": self.entanglement_map,
            "dimensions": self.dimensions
        }
