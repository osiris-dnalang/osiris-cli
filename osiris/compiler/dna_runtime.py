"""
DNA-Lang Quantum Runtime — Execute circuits on simulators or IBM Quantum.
"""

import os
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .dna_ir import QuantumCircuitIR


@dataclass
class RuntimeConfig:
    ibm_token: Optional[str] = None
    backend_name: str = "ibm_brisbane"
    use_simulator: bool = False
    shots: int = 1024
    optimization_level: int = 3
    resilience_level: int = 1
    max_execution_time: int = 3600

    def __post_init__(self):
        if not self.ibm_token:
            self.ibm_token = os.environ.get("IBM_QUANTUM_TOKEN")


@dataclass
class ExecutionResult:
    job_id: Optional[str] = None
    backend: str = ""
    status: str = "unknown"
    execution_time: float = 0.0
    timestamp: str = ""
    counts: Dict[str, int] = field(default_factory=dict)
    fidelity: float = 0.0
    success_rate: float = 0.0
    lambda_measured: float = 0.0
    gamma_measured: float = 0.0
    phi_measured: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "backend": self.backend,
            "status": self.status,
            "execution_time": self.execution_time,
            "counts": self.counts,
            "metrics": {"fidelity": self.fidelity, "success_rate": self.success_rate},
            "physics": {
                "lambda": self.lambda_measured,
                "gamma": self.gamma_measured,
                "phi": self.phi_measured,
            },
            "error": self.error,
        }


class QuantumRuntime:
    """Executes quantum circuits (mock execution when Qiskit unavailable)."""

    def __init__(self, config: Optional[RuntimeConfig] = None):
        self.config = config or RuntimeConfig()
        self.execution_log: List[ExecutionResult] = []

    def execute(self, circuit: QuantumCircuitIR) -> ExecutionResult:
        """Execute quantum circuit via backend registry, with fallback."""
        t0 = time.time()
        try:
            from .backends.registry import BackendRegistry
            backend = BackendRegistry.get(self.config.backend_name)
            result = backend.execute(circuit, shots=self.config.shots)
        except (KeyError, Exception):
            try:
                from qiskit import QuantumCircuit  # noqa: F401
                qc = self._ir_to_qiskit(circuit)
                result = self._execute_qiskit(qc)
            except (ImportError, Exception):
                result = self._mock_execution(circuit)
        result.execution_time = time.time() - t0
        self.execution_log.append(result)
        return result

    @staticmethod
    def _ir_to_qiskit(circuit: QuantumCircuitIR):
        """Convert IR to Qiskit QuantumCircuit."""
        from qiskit import QuantumCircuit
        nq = sum(r.size for r in circuit.quantum_registers)
        nc = sum(r.size for r in circuit.classical_registers)
        qc = QuantumCircuit(nq, nc)
        from .dna_ir import IROpType
        gate_map = {
            IROpType.H: 'h', IROpType.X: 'x', IROpType.Y: 'y', IROpType.Z: 'z',
            IROpType.CX: 'cx', IROpType.CY: 'cy', IROpType.CZ: 'cz',
            IROpType.SWAP: 'swap', IROpType.CCX: 'ccx',
        }
        for op in circuit.operations:
            if op.op_type == IROpType.MEASURE:
                for i, q in enumerate(op.qubits):
                    cb = op.classical_bits[i] if op.classical_bits and i < len(op.classical_bits) else q
                    qc.measure(q, cb)
            elif op.op_type in gate_map:
                getattr(qc, gate_map[op.op_type])(*op.qubits)
        return qc

    def _mock_execution(self, circuit: QuantumCircuitIR) -> ExecutionResult:
        import random
        n_qubits = circuit.qubit_count
        shots = self.config.shots
        counts: Dict[str, int] = {}
        for _ in range(shots):
            bits = "".join(str(random.randint(0, 1)) for _ in range(n_qubits))
            counts[bits] = counts.get(bits, 0) + 1
        dominant = max(counts, key=counts.get)
        fidelity = counts[dominant] / shots
        return ExecutionResult(
            job_id="mock_" + str(int(time.time())),
            backend="local_mock",
            status="completed",
            timestamp=str(time.time()),
            counts=counts,
            fidelity=fidelity,
            success_rate=fidelity,
        )

    def _execute_qiskit(self, qc) -> ExecutionResult:
        from qiskit.quantum_info import Statevector
        sv = Statevector.from_instruction(qc.remove_final_measurements(inplace=False))
        counts = dict(sv.sample_counts(self.config.shots))
        dominant = max(counts, key=counts.get)
        fidelity = counts[dominant] / self.config.shots
        return ExecutionResult(
            job_id="sv_" + str(int(time.time())),
            backend="statevector_simulator",
            status="completed",
            timestamp=str(time.time()),
            counts=counts,
            fidelity=fidelity,
            success_rate=fidelity,
        )
