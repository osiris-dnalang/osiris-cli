"""Configuration classes for DNALang SDK."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class QuantumConfig:
    """Configuration for quantum backend connections."""
    
    backend: str = "aer_simulator"
    default_backend: str = "aer_simulator"
    api_token: Optional[str] = None
    api_token_env: str = "IBM_QUANTUM_TOKEN"
    optimization_level: int = 3
    shots: int = 1024
    max_qubits: int = 127
    timeout: int = 300


@dataclass
class LambdaPhiConfig:
    """Configuration for lambda-phi conservation validation."""
    
    num_trials: int = 100
    significance_level: float = 0.05
    operators: List[str] = field(default_factory=lambda: ["X", "Y", "Z", "H"])
    conservation_threshold: float = 0.95
    enable_statistical_tests: bool = True


@dataclass
class ConsciousnessConfig:
    """Configuration for consciousness scaling measurements."""
    
    qubit_range: List[int] = field(default_factory=lambda: [2, 4, 8, 16, 32])
    samples_per_size: int = 50
    coherence_threshold: float = 0.7
    enable_temporal_analysis: bool = True
    ccce_measurement_shots: int = 1024
