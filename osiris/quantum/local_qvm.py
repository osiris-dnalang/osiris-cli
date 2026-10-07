"""Re-export from osiris_local_qvm for backward compatibility."""
from osiris_local_qvm import (
    QuantumState, QuantumGate, QuantumCircuit, QuantumMeasurement,
    LocalQVM, GateType, NoiseModel, QuantumRegister,
    CircuitOptimizer, StateVector,
)

__all__ = [
    "QuantumState", "QuantumGate", "QuantumCircuit", "QuantumMeasurement",
    "LocalQVM", "GateType", "NoiseModel", "QuantumRegister",
    "CircuitOptimizer", "StateVector",
]
