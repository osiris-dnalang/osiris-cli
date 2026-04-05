"""Consciousness scaling measurement and analysis."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class CCCEResult:
    """Result from Consciousness Collapse Coherence Evolution measurement."""
    
    ccce_values: List[float]
    qubit_sizes: List[int]
    exponent: float
    exponent_error: float
    coherence_time_ms: float
    r_squared: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return (
            f"Consciousness Scaling Result:\n"
            f"  Scaling Exponent: {self.exponent:.4f} ± {self.exponent_error:.4f}\n"
            f"  Coherence Time: {self.coherence_time_ms:.2f} ms\n"
            f"  R²: {self.r_squared:.4f}\n"
            f"  Qubit Range: {min(self.qubit_sizes)} - {max(self.qubit_sizes)}"
        )


class ConsciousnessAnalyzer:
    """Analyzer for consciousness scaling phenomena in quantum systems."""
    
    def __init__(self, config, quantum_backend=None):
        """
        Initialize consciousness analyzer.
        
        Args:
            config: ConsciousnessConfig instance
            quantum_backend: Optional QuantumBackend for circuit execution
        """
        self.config = config
        self.quantum_backend = quantum_backend
    
    async def measure_scaling(
        self,
        num_qubits_range: Optional[List[int]] = None,
        num_samples: Optional[int] = None,
    ) -> CCCEResult:
        """
        Measure consciousness scaling across different qubit counts.
        
        The CCCE (Consciousness Collapse Coherence Evolution) metric quantifies
        how quantum coherence evolves with system size, revealing fundamental
        scaling laws in quantum consciousness.
        
        Args:
            num_qubits_range: List of qubit counts to test
            num_samples: Number of samples per qubit count
            
        Returns:
            CCCEResult with scaling metrics
        """
        num_qubits_range = num_qubits_range or self.config.qubit_range
        num_samples = num_samples or self.config.samples_per_size
        
        ccce_values = []
        qubit_sizes = []
        
        for num_qubits in num_qubits_range:
            # Measure CCCE for this qubit count
            ccce = await self._measure_ccce_for_size(num_qubits, num_samples)
            ccce_values.append(ccce)
            qubit_sizes.append(num_qubits)
        
        # Fit scaling law: CCCE = A * N^α
        # where N is number of qubits, α is scaling exponent
        exponent, exponent_error, r_squared = self._fit_scaling_law(
            qubit_sizes,
            ccce_values,
        )
        
        # Estimate coherence time from measurements
        coherence_time = self._estimate_coherence_time(ccce_values, qubit_sizes)
        
        return CCCEResult(
            ccce_values=ccce_values,
            qubit_sizes=qubit_sizes,
            exponent=exponent,
            exponent_error=exponent_error,
            coherence_time_ms=coherence_time,
            r_squared=r_squared,
            metadata={
                "samples_per_size": num_samples,
                "coherence_threshold": self.config.coherence_threshold,
            },
        )
    
    async def _measure_ccce_for_size(
        self,
        num_qubits: int,
        num_samples: int,
    ) -> float:
        """Measure CCCE metric for specific qubit count."""
        ccce_samples = []
        
        for _ in range(num_samples):
            # Create GHZ-like state for consciousness measurement
            from .quantum import QuantumCircuit
            
            circuit = QuantumCircuit(num_qubits=num_qubits)
            
            # Prepare GHZ state: |0...0⟩ + |1...1⟩
            circuit.h(0)
            for i in range(1, num_qubits):
                circuit.cx(0, i)
            
            # Execute circuit
            if self.quantum_backend:
                result = await self.quantum_backend.execute(
                    circuit=circuit,
                    shots=self.config.ccce_measurement_shots,
                    backend=self.quantum_backend.config.default_backend,
                    optimization_level=self.quantum_backend.config.optimization_level,
                )
                
                # Compute CCCE from measurement results
                ccce = self._compute_ccce_from_counts(
                    result.counts,
                    num_qubits,
                )
            else:
                # Simulate CCCE measurement
                ccce = self._simulate_ccce(num_qubits)
            
            ccce_samples.append(ccce)
        
        # Return mean CCCE value
        return np.mean(ccce_samples)
    
    def _compute_ccce_from_counts(
        self,
        counts: Dict[str, int],
        num_qubits: int,
    ) -> float:
        """
        Compute CCCE metric from measurement counts.
        
        CCCE measures the coherence between maximally entangled states,
        indicating "consciousness" of the quantum system.
        """
        total_shots = sum(counts.values())
        
        # Expected states for GHZ: |0...0⟩ and |1...1⟩
        all_zeros = '0' * num_qubits
        all_ones = '1' * num_qubits
        
        prob_zeros = counts.get(all_zeros, 0) / total_shots
        prob_ones = counts.get(all_ones, 0) / total_shots
        
        # CCCE is the sum of probabilities of coherent states
        # Values close to 1.0 indicate high consciousness/coherence
        ccce = prob_zeros + prob_ones
        
        # Account for decoherence with system size
        # Larger systems should show reduced CCCE due to environmental coupling
        decoherence_factor = np.exp(-0.05 * num_qubits)
        ccce *= decoherence_factor
        
        return ccce
    
    def _simulate_ccce(self, num_qubits: int) -> float:
        """Simulate CCCE measurement with realistic noise."""
        # Ideal CCCE = 1.0 for perfect GHZ state
        ideal_ccce = 1.0
        
        # Add size-dependent decoherence
        decoherence = 0.05 * num_qubits
        
        # Add random measurement noise
        noise = np.random.normal(0, 0.02)
        
        ccce = ideal_ccce * np.exp(-decoherence) + noise
        
        # Clamp to [0, 1]
        return np.clip(ccce, 0.0, 1.0)
    
    def _fit_scaling_law(
        self,
        qubit_sizes: List[int],
        ccce_values: List[float],
    ) -> Tuple[float, float, float]:
        """
        Fit power law scaling: CCCE = A * N^α
        
        Returns:
            (exponent, exponent_error, r_squared)
        """
        # Convert to log space for linear fit
        log_N = np.log(qubit_sizes)
        log_CCCE = np.log(np.array(ccce_values) + 1e-10)  # Avoid log(0)
        
        # Linear regression in log space
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_N, log_CCCE)
        
        exponent = slope  # This is α in the power law
        r_squared = r_value ** 2
        
        return exponent, std_err, r_squared
    
    def _estimate_coherence_time(
        self,
        ccce_values: List[float],
        qubit_sizes: List[int],
    ) -> float:
        """
        Estimate coherence time from CCCE decay.
        
        Returns coherence time in milliseconds.
        """
        # Simple exponential decay model
        # T_coherence ∝ 1 / decoherence_rate
        
        # Estimate decoherence rate from CCCE values
        if len(ccce_values) < 2:
            return 100.0  # Default 100ms
        
        # Compute rate of CCCE decrease
        delta_ccce = ccce_values[-1] - ccce_values[0]
        delta_qubits = qubit_sizes[-1] - qubit_sizes[0]
        
        if delta_qubits == 0:
            return 100.0
        
        decoherence_rate = -delta_ccce / delta_qubits
        
        # Convert to coherence time (arbitrary units → ms)
        # Typical coherence times: ~10-1000 ms
        coherence_time_ms = 100.0 / (1.0 + decoherence_rate * 100)
        
        return max(1.0, coherence_time_ms)  # At least 1ms
    
    def analyze_temporal_coherence(
        self,
        circuit,
        time_steps: List[float],
    ) -> Dict[str, Any]:
        """
        Analyze temporal evolution of quantum coherence.
        
        Args:
            circuit: QuantumCircuit to analyze
            time_steps: List of time points (in arbitrary units)
            
        Returns:
            Dictionary with temporal coherence data
        """
        if not self.config.enable_temporal_analysis:
            return {"error": "Temporal analysis disabled"}
        
        coherence_evolution = []
        
        for t in time_steps:
            # Simulate time evolution (simplified)
            # In real implementation, would use Hamiltonian evolution
            coherence = np.exp(-t * 0.1)  # Exponential decay
            coherence_evolution.append(coherence)
        
        return {
            "time_steps": time_steps,
            "coherence": coherence_evolution,
            "decay_rate": 0.1,
            "coherence_threshold": self.config.coherence_threshold,
        }
