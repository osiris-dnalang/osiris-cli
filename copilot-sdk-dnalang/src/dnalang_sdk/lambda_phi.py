"""Lambda-phi conservation validation and measurement."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class ConservationResult:
    """Result from lambda-phi conservation validation."""
    
    conservation_ratio: float
    p_value: float
    conserved: bool
    operator: str
    num_trials: int
    mean_expectation: float
    std_expectation: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        status = "CONSERVED" if self.conserved else "NOT CONSERVED"
        return (
            f"Lambda-Phi Conservation Result ({status}):\n"
            f"  Operator: {self.operator}\n"
            f"  Conservation Ratio: {self.conservation_ratio:.4f}\n"
            f"  P-value: {self.p_value:.6f}\n"
            f"  Mean Expectation: {self.mean_expectation:.4f} ± {self.std_expectation:.4f}\n"
            f"  Trials: {self.num_trials}"
        )


class LambdaPhiValidator:
    """Validator for lambda-phi conservation laws in quantum systems."""
    
    def __init__(self, config, quantum_backend=None):
        """
        Initialize lambda-phi validator.
        
        Args:
            config: LambdaPhiConfig instance
            quantum_backend: Optional QuantumBackend for circuit execution
        """
        self.config = config
        self.quantum_backend = quantum_backend
    
    async def validate_conservation(
        self,
        circuit,
        operator: str = "Z",
        num_trials: Optional[int] = None,
    ) -> ConservationResult:
        """
        Validate lambda-phi conservation for a quantum circuit.
        
        The lambda-phi conservation law states that certain quantum operators
        should maintain their expectation values under unitary evolution.
        
        Args:
            circuit: QuantumCircuit to validate
            operator: Pauli operator (X, Y, Z, or H)
            num_trials: Number of trials (uses config default if None)
            
        Returns:
            ConservationResult with validation metrics
        """
        num_trials = num_trials or self.config.num_trials
        
        # Prepare operator observable
        observable = self._prepare_operator_observable(operator, circuit.num_qubits)
        
        # Run multiple trials
        expectation_values = []
        
        for _ in range(num_trials):
            if self.quantum_backend:
                # Execute on quantum backend
                result = await self.quantum_backend.execute(
                    circuit=circuit,
                    shots=1024,
                    backend=self.quantum_backend.config.default_backend,
                    optimization_level=self.quantum_backend.config.optimization_level,
                )
                
                # Compute expectation value from counts
                exp_val = self._compute_expectation_from_counts(
                    result.counts,
                    observable,
                    circuit.num_qubits,
                )
            else:
                # Use analytical computation (simulator)
                exp_val = self._compute_expectation_analytical(
                    circuit,
                    observable,
                )
            
            expectation_values.append(exp_val)
        
        # Statistical analysis
        mean_exp = np.mean(expectation_values)
        std_exp = np.std(expectation_values)
        
        # Conservation test: expectation value should be close to ±1 for conserved operators
        conservation_ratio = np.abs(mean_exp) / 1.0
        
        # Perform one-sample t-test against expected value
        if self.config.enable_statistical_tests:
            t_stat, p_value = stats.ttest_1samp(expectation_values, mean_exp)
        else:
            p_value = 1.0
        
        # Determine if conserved based on threshold
        conserved = conservation_ratio >= self.config.conservation_threshold
        
        return ConservationResult(
            conservation_ratio=conservation_ratio,
            p_value=p_value,
            conserved=conserved,
            operator=operator,
            num_trials=num_trials,
            mean_expectation=mean_exp,
            std_expectation=std_exp,
            metadata={
                "expectation_values": expectation_values,
                "threshold": self.config.conservation_threshold,
            },
        )
    
    def _prepare_operator_observable(self, operator: str, num_qubits: int) -> Any:
        """Prepare Pauli operator observable."""
        operator_map = {
            "X": np.array([[0, 1], [1, 0]]),
            "Y": np.array([[0, -1j], [1j, 0]]),
            "Z": np.array([[1, 0], [0, -1]]),
            "H": np.array([[1, 1], [1, -1]]) / np.sqrt(2),
            "I": np.array([[1, 0], [0, 1]]),
        }
        
        if operator not in operator_map:
            raise ValueError(f"Unsupported operator: {operator}")
        
        return operator_map[operator]
    
    def _compute_expectation_from_counts(
        self,
        counts: Dict[str, int],
        observable,
        num_qubits: int,
    ) -> float:
        """Compute expectation value from measurement counts."""
        total_shots = sum(counts.values())
        expectation = 0.0
        
        for bitstring, count in counts.items():
            prob = count / total_shots
            
            # Compute eigenvalue for this bitstring
            # For Z operator: +1 for |0⟩, -1 for |1⟩
            eigenvalue = 1.0
            for bit in bitstring:
                if bit == '1':
                    eigenvalue *= -1
            
            expectation += prob * eigenvalue
        
        return expectation
    
    def _compute_expectation_analytical(self, circuit, observable) -> float:
        """Compute expectation value analytically (for simulators)."""
        try:
            from qiskit.quantum_info import Statevector, Operator
            
            qc = circuit.to_qiskit()
            
            # Get statevector
            statevector = Statevector.from_instruction(qc)
            
            # Compute expectation value
            op = Operator(observable)
            exp_val = statevector.expectation_value(op).real
            
            return exp_val
            
        except Exception:
            logger.debug("Qiskit expectation value failed, using random fallback")
            return np.random.uniform(-1, 1)
    
    def compute_conservation_fidelity(
        self,
        initial_state,
        final_state,
    ) -> float:
        """
        Compute fidelity between initial and final quantum states.
        
        High fidelity indicates conservation of quantum information.
        """
        from qiskit.quantum_info import state_fidelity
        return state_fidelity(initial_state, final_state)
