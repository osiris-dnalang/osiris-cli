"""Cirq backend adapter — Google Quantum AI circuit translation."""

import hashlib
import time
from typing import Any, Dict, Optional, Set

from ..dna_ir import (
    IROpType, IROperation, QuantumCircuitIR,
    QuantumRegister, ClassicalRegister,
)
from ..dna_runtime import ExecutionResult
from ..gate_map import CIRQ_GATE_NAMES
from .base import BackendAdapter
from .registry import BackendRegistry


_CIRQ_AVAILABLE: Optional[bool] = None


def _check_cirq() -> bool:
    global _CIRQ_AVAILABLE
    if _CIRQ_AVAILABLE is None:
        try:
            import cirq  # noqa: F401
            _CIRQ_AVAILABLE = True
        except ImportError:
            _CIRQ_AVAILABLE = False
    return _CIRQ_AVAILABLE


class CirqAdapter(BackendAdapter):
    """Translate QuantumCircuitIR ↔ cirq.Circuit."""

    @property
    def name(self) -> str:
        return "cirq"

    def is_available(self) -> bool:
        return _check_cirq()

    def native_gate_set(self) -> Set[str]:
        return set(CIRQ_GATE_NAMES.values())

    # ── IR → cirq.Circuit ───────────────────────────────────────────────

    def ir_to_native(self, circuit: QuantumCircuitIR) -> Any:
        import cirq

        nq = sum(r.size for r in circuit.quantum_registers)
        qubits = cirq.LineQubit.range(nq)
        moments: list = []

        for op in circuit.operations:
            gate_op = self._ir_op_to_cirq(op, qubits)
            if gate_op is not None:
                if isinstance(gate_op, list):
                    moments.extend(gate_op)
                else:
                    moments.append(gate_op)

        return cirq.Circuit(moments)

    @staticmethod
    def _ir_op_to_cirq(op: IROperation, qubits: list) -> Any:
        import cirq

        ot = op.op_type
        qs = [qubits[q] for q in op.qubits]

        if ot == IROpType.MEASURE:
            return cirq.measure(*qs, key="m")
        if ot in (IROpType.BARRIER, IROpType.RESET):
            return None  # cirq has no direct barrier; reset via cirq.ResetChannel

        _simple = {
            IROpType.H: cirq.H, IROpType.X: cirq.X, IROpType.Y: cirq.Y,
            IROpType.Z: cirq.Z, IROpType.S: cirq.S, IROpType.T: cirq.T,
            IROpType.CX: cirq.CNOT, IROpType.CZ: cirq.CZ,
            IROpType.SWAP: cirq.SWAP, IROpType.CCX: cirq.CCX,
            IROpType.CSWAP: cirq.CSWAP,
        }
        if ot in _simple:
            return _simple[ot].on(*qs)

        if ot == IROpType.RX:
            return cirq.rx(op.params[0]).on(*qs)
        if ot == IROpType.RY:
            return cirq.ry(op.params[0]).on(*qs)
        if ot == IROpType.RZ:
            return cirq.rz(op.params[0]).on(*qs)
        if ot == IROpType.U3:
            # Decompose U3(θ,φ,λ) into Rz(φ)·Ry(θ)·Rz(λ)
            theta, phi, lam = op.params[:3]
            return [
                cirq.rz(lam).on(*qs),
                cirq.ry(theta).on(*qs),
                cirq.rz(phi).on(*qs),
            ]
        if ot == IROpType.CY:
            # CY = (I⊗S†)·CX·(I⊗S)
            return cirq.ControlledGate(cirq.Y).on(*qs)

        return None

    # ── cirq.Circuit → IR ───────────────────────────────────────────────

    def native_to_ir(self, native_circuit: Any) -> QuantumCircuitIR:
        import cirq

        if not isinstance(native_circuit, cirq.Circuit):
            raise TypeError(f"Expected cirq.Circuit, got {type(native_circuit).__name__}")

        all_qubits = sorted(native_circuit.all_qubits())
        qubit_index = {q: i for i, q in enumerate(all_qubits)}
        nq = len(all_qubits)

        _gate_map = {
            "H": IROpType.H, "X": IROpType.X, "Y": IROpType.Y, "Z": IROpType.Z,
            "S": IROpType.S, "T": IROpType.T,
            "CNOT": IROpType.CX, "CZ": IROpType.CZ,
            "SWAP": IROpType.SWAP, "CCX": IROpType.CCX,
            "CSWAP": IROpType.CSWAP, "CCNOT": IROpType.CCX,
        }

        ops: list[IROperation] = []
        for moment in native_circuit:
            for gate_op in moment.operations:
                qubits_idx = [qubit_index[q] for q in gate_op.qubits]
                gate = gate_op.gate
                gate_name = type(gate).__name__

                if isinstance(gate, cirq.MeasurementGate):
                    ops.append(IROperation(IROpType.MEASURE, qubits_idx,
                                           classical_bits=qubits_idx))
                    continue

                if gate_name in _gate_map:
                    ops.append(IROperation(_gate_map[gate_name], qubits_idx))
                    continue

                # Parameterised rotations
                if gate_name in ("Rz", "ZPowGate"):
                    exponent = getattr(gate, "exponent", None)
                    if exponent is not None:
                        rad = float(exponent) * 3.141592653589793
                        ops.append(IROperation(IROpType.RZ, qubits_idx, params=[rad]))
                        continue
                if gate_name in ("Ry", "YPowGate"):
                    exponent = getattr(gate, "exponent", None)
                    if exponent is not None:
                        rad = float(exponent) * 3.141592653589793
                        ops.append(IROperation(IROpType.RY, qubits_idx, params=[rad]))
                        continue
                if gate_name in ("Rx", "XPowGate"):
                    exponent = getattr(gate, "exponent", None)
                    if exponent is not None:
                        rad = float(exponent) * 3.141592653589793
                        ops.append(IROperation(IROpType.RX, qubits_idx, params=[rad]))
                        continue

                if isinstance(gate, cirq.Rz):
                    ops.append(IROperation(IROpType.RZ, qubits_idx,
                                           params=[float(gate._rads)]))
                elif isinstance(gate, cirq.Ry):
                    ops.append(IROperation(IROpType.RY, qubits_idx,
                                           params=[float(gate._rads)]))
                elif isinstance(gate, cirq.Rx):
                    ops.append(IROperation(IROpType.RX, qubits_idx,
                                           params=[float(gate._rads)]))
                # else: skip unrecognised gate

        lineage = hashlib.sha256(f"cirq_import:{nq}:{len(ops)}".encode()).hexdigest()[:16]
        circuit = QuantumCircuitIR(
            name="cirq_imported",
            quantum_registers=[QuantumRegister("q", nq)],
            classical_registers=[ClassicalRegister("c", nq)],
            operations=ops,
            source_organism="cirq_import",
            lineage_hash=lineage,
        )
        circuit.compute_metrics()
        return circuit

    # ── Execute ─────────────────────────────────────────────────────────

    def execute(self, circuit: QuantumCircuitIR, shots: int = 1024) -> ExecutionResult:
        import cirq

        cirq_circuit = self.ir_to_native(circuit)
        t0 = time.time()
        sim = cirq.Simulator()
        result = sim.run(cirq_circuit, repetitions=shots)
        counts: Dict[str, int] = {}
        for row in result.measurements.get("m", []):
            key = "".join(str(int(b)) for b in row)
            counts[key] = counts.get(key, 0) + 1
        if not counts:
            counts = {"0" * circuit.qubit_count: shots}
        dominant = max(counts, key=counts.get)
        fidelity = counts[dominant] / shots
        return ExecutionResult(
            job_id=f"cirq_{int(time.time())}",
            backend="cirq_simulator",
            status="completed",
            timestamp=str(time.time()),
            counts=counts,
            fidelity=fidelity,
            success_rate=fidelity,
            execution_time=time.time() - t0,
        )


# Auto-register on import (only if cirq is installed)
if _check_cirq():
    BackendRegistry.register(CirqAdapter())
