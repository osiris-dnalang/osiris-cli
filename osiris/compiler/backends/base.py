"""Abstract base class for quantum backend adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Set

from ..dna_ir import QuantumCircuitIR
from ..dna_runtime import ExecutionResult


class BackendAdapter(ABC):
    """Abstract adapter that translates QuantumCircuitIR to/from a backend."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique backend identifier (e.g. 'qiskit', 'cirq', 'pyquil')."""

    @abstractmethod
    def native_gate_set(self) -> Set[str]:
        """Return the set of gate names natively supported by this backend."""

    @abstractmethod
    def ir_to_native(self, circuit: QuantumCircuitIR) -> Any:
        """Convert QuantumCircuitIR to the backend's native circuit object."""

    @abstractmethod
    def native_to_ir(self, native_circuit: Any) -> QuantumCircuitIR:
        """Convert a backend-native circuit back to QuantumCircuitIR."""

    @abstractmethod
    def execute(self, circuit: QuantumCircuitIR, shots: int = 1024) -> ExecutionResult:
        """Execute a circuit and return results."""

    def topology(self) -> Optional[Dict[str, Any]]:
        """Return backend qubit connectivity (optional)."""
        return None

    def is_available(self) -> bool:
        """Return True if the backend SDK is importable."""
        return True
