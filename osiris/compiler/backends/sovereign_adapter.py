"""Sovereign backend — local mock/statevector execution (always available)."""

import time
import random
from typing import Any, Dict, Optional, Set

from ..dna_ir import IROpType, IROperation, QuantumCircuitIR, QuantumRegister, ClassicalRegister
from ..dna_runtime import ExecutionResult
from .base import BackendAdapter
from .registry import BackendRegistry


class SovereignAdapter(BackendAdapter):
    """Local execution backend that never requires an external SDK."""

    @property
    def name(self) -> str:
        return "sovereign"

    def native_gate_set(self) -> Set[str]:
        return {op.value for op in IROpType}

    def ir_to_native(self, circuit: QuantumCircuitIR) -> QuantumCircuitIR:
        """Sovereign's native format *is* the IR."""
        return circuit

    def native_to_ir(self, native_circuit: Any) -> QuantumCircuitIR:
        if isinstance(native_circuit, QuantumCircuitIR):
            return native_circuit
        raise TypeError(f"Expected QuantumCircuitIR, got {type(native_circuit).__name__}")

    def execute(self, circuit: QuantumCircuitIR, shots: int = 1024) -> ExecutionResult:
        t0 = time.time()
        n_qubits = circuit.qubit_count or sum(r.size for r in circuit.quantum_registers)
        counts: Dict[str, int] = {}
        for _ in range(shots):
            bits = "".join(str(random.randint(0, 1)) for _ in range(n_qubits))
            counts[bits] = counts.get(bits, 0) + 1
        dominant = max(counts, key=counts.get)
        fidelity = counts[dominant] / shots
        return ExecutionResult(
            job_id=f"sovereign_{int(time.time())}",
            backend="sovereign",
            status="completed",
            timestamp=str(time.time()),
            counts=counts,
            fidelity=fidelity,
            success_rate=fidelity,
            execution_time=time.time() - t0,
        )


# Auto-register on import
BackendRegistry.register(SovereignAdapter())
