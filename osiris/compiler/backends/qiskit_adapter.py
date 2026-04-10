"""Qiskit backend adapter — IBM Quantum / Aer statevector simulation."""

import hashlib
import time
from typing import Any, Dict, Optional, Set

from ..dna_ir import (
    IROpType, IROperation, QuantumCircuitIR,
    QuantumRegister, ClassicalRegister,
)
from ..dna_runtime import ExecutionResult
from ..gate_map import (
    SINGLE_QUBIT_GATES, PARAMETERISED_SINGLE_QUBIT_GATES,
    TWO_QUBIT_GATES, THREE_QUBIT_GATES, QISKIT_GATE_NAMES,
)
from .base import BackendAdapter
from .registry import BackendRegistry


_QISKIT_AVAILABLE: Optional[bool] = None


def _check_qiskit() -> bool:
    global _QISKIT_AVAILABLE
    if _QISKIT_AVAILABLE is None:
        try:
            import qiskit  # noqa: F401
            _QISKIT_AVAILABLE = True
        except ImportError:
            _QISKIT_AVAILABLE = False
    return _QISKIT_AVAILABLE


class QiskitAdapter(BackendAdapter):
    """Translate QuantumCircuitIR ↔ Qiskit QuantumCircuit."""

    @property
    def name(self) -> str:
        return "qiskit"

    def is_available(self) -> bool:
        return _check_qiskit()

    def native_gate_set(self) -> Set[str]:
        return set(QISKIT_GATE_NAMES.values())

    # ── IR → Qiskit QuantumCircuit ──────────────────────────────────────

    def ir_to_native(self, circuit: QuantumCircuitIR) -> Any:
        from qiskit import QuantumCircuit as QC

        nq = sum(r.size for r in circuit.quantum_registers)
        nc = sum(r.size for r in circuit.classical_registers)
        qc = QC(nq, nc)

        for op in circuit.operations:
            self._apply_op(qc, op)
        return qc

    @staticmethod
    def _apply_op(qc: Any, op: IROperation) -> None:
        ot = op.op_type

        if ot == IROpType.MEASURE:
            for i, q in enumerate(op.qubits):
                cb = (op.classical_bits[i]
                      if op.classical_bits and i < len(op.classical_bits)
                      else q)
                qc.measure(q, cb)
            return

        if ot == IROpType.BARRIER:
            qc.barrier(*op.qubits) if op.qubits else qc.barrier()
            return

        if ot == IROpType.RESET:
            for q in op.qubits:
                qc.reset(q)
            return

        gate_name = QISKIT_GATE_NAMES.get(ot)
        if gate_name is None:
            return  # unknown gate — skip silently

        if ot in SINGLE_QUBIT_GATES:
            getattr(qc, gate_name)(*op.qubits)
        elif ot in PARAMETERISED_SINGLE_QUBIT_GATES:
            getattr(qc, gate_name)(op.params[0], *op.qubits)
        elif ot == IROpType.U3:
            theta, phi, lam = op.params[:3]
            if hasattr(qc, "u"):
                qc.u(theta, phi, lam, *op.qubits)
            elif hasattr(qc, "u3"):
                qc.u3(theta, phi, lam, *op.qubits)
        elif ot in TWO_QUBIT_GATES | THREE_QUBIT_GATES:
            getattr(qc, gate_name)(*op.qubits)

    # ── Qiskit QuantumCircuit → IR ──────────────────────────────────────

    def native_to_ir(self, native_circuit: Any) -> QuantumCircuitIR:
        from qiskit import QuantumCircuit as QC

        if not isinstance(native_circuit, QC):
            raise TypeError(f"Expected qiskit.QuantumCircuit, got {type(native_circuit).__name__}")

        nq = native_circuit.num_qubits
        nc = native_circuit.num_clbits

        _name_to_op = {v: k for k, v in QISKIT_GATE_NAMES.items()}
        ops: list[IROperation] = []

        for instruction in native_circuit.data:
            gate = instruction.operation
            gate_name = gate.name.lower()
            qubits = [native_circuit.find_bit(q).index for q in instruction.qubits]
            clbits = [native_circuit.find_bit(c).index for c in instruction.clbits]
            params = list(gate.params) if hasattr(gate, "params") else []

            if gate_name == "measure":
                ops.append(IROperation(IROpType.MEASURE, qubits, classical_bits=clbits))
            elif gate_name == "barrier":
                ops.append(IROperation(IROpType.BARRIER, qubits))
            elif gate_name == "reset":
                ops.append(IROperation(IROpType.RESET, qubits))
            elif gate_name in _name_to_op:
                ops.append(IROperation(_name_to_op[gate_name], qubits, params=[float(p) for p in params]))
            elif gate_name == "u":
                ops.append(IROperation(IROpType.U3, qubits, params=[float(p) for p in params[:3]]))
            # else: skip unknown gate

        lineage = hashlib.sha256(f"qiskit_import:{nq}:{len(ops)}".encode()).hexdigest()[:16]
        circuit = QuantumCircuitIR(
            name=getattr(native_circuit, "name", "imported_circuit"),
            quantum_registers=[QuantumRegister("q", nq)],
            classical_registers=[ClassicalRegister("c", nc)],
            operations=ops,
            source_organism="qiskit_import",
            lineage_hash=lineage,
        )
        circuit.compute_metrics()
        return circuit

    # ── Execute ─────────────────────────────────────────────────────────

    def execute(self, circuit: QuantumCircuitIR, shots: int = 1024) -> ExecutionResult:
        from qiskit.quantum_info import Statevector

        qc = self.ir_to_native(circuit)
        t0 = time.time()
        sv = Statevector.from_instruction(qc.remove_final_measurements(inplace=False))
        counts = dict(sv.sample_counts(shots))
        dominant = max(counts, key=counts.get)
        fidelity = counts[dominant] / shots
        return ExecutionResult(
            job_id=f"qiskit_{int(time.time())}",
            backend="qiskit_statevector",
            status="completed",
            timestamp=str(time.time()),
            counts=counts,
            fidelity=fidelity,
            success_rate=fidelity,
            execution_time=time.time() - t0,
        )


# Auto-register on import
if _check_qiskit():
    BackendRegistry.register(QiskitAdapter())
