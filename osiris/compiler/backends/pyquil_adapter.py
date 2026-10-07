"""PyQuil backend adapter — Rigetti QVM / QPU circuit translation."""

import hashlib
import time
from typing import Any, Dict, Optional, Set

from ..dna_ir import (
    IROpType, IROperation, QuantumCircuitIR,
    QuantumRegister, ClassicalRegister,
)
from ..dna_runtime import ExecutionResult
from ..gate_map import PYQUIL_GATE_NAMES
from .base import BackendAdapter
from .registry import BackendRegistry


_PYQUIL_AVAILABLE: Optional[bool] = None


def _check_pyquil() -> bool:
    global _PYQUIL_AVAILABLE
    if _PYQUIL_AVAILABLE is None:
        try:
            import pyquil  # noqa: F401
            _PYQUIL_AVAILABLE = True
        except ImportError:
            _PYQUIL_AVAILABLE = False
    return _PYQUIL_AVAILABLE


class PyQuilAdapter(BackendAdapter):
    """Translate QuantumCircuitIR ↔ pyquil.Program."""

    @property
    def name(self) -> str:
        return "pyquil"

    def is_available(self) -> bool:
        return _check_pyquil()

    def native_gate_set(self) -> Set[str]:
        return set(PYQUIL_GATE_NAMES.values())

    # ── IR → pyquil.Program ─────────────────────────────────────────────

    def ir_to_native(self, circuit: QuantumCircuitIR) -> Any:
        from pyquil import Program
        from pyquil.gates import (
            H, X, Y, Z, S, T, RX, RY, RZ, CNOT, CZ, SWAP, CCNOT, CSWAP, MEASURE,
        )
        from pyquil.quilatom import MemoryReference

        nq = sum(r.size for r in circuit.quantum_registers)
        p = Program()
        p.declare("ro", "BIT", nq)

        _simple = {
            IROpType.H: H, IROpType.X: X, IROpType.Y: Y, IROpType.Z: Z,
            IROpType.S: S, IROpType.T: T,
            IROpType.CX: CNOT, IROpType.CZ: CZ, IROpType.SWAP: SWAP,
            IROpType.CCX: CCNOT, IROpType.CSWAP: CSWAP,
        }
        _param = {IROpType.RX: RX, IROpType.RY: RY, IROpType.RZ: RZ}

        for op in circuit.operations:
            ot = op.op_type
            qs = op.qubits

            if ot == IROpType.MEASURE:
                for i, q in enumerate(qs):
                    cb = (op.classical_bits[i]
                          if op.classical_bits and i < len(op.classical_bits) else q)
                    p += MEASURE(q, MemoryReference("ro", cb))
                continue

            if ot in (IROpType.BARRIER, IROpType.RESET):
                continue  # PyQuil has RESET but we skip for portability

            if ot in _simple:
                p += _simple[ot](*qs)
            elif ot in _param:
                p += _param[ot](op.params[0], *qs)
            elif ot == IROpType.U3:
                # Decompose U3(θ,φ,λ) → RZ(φ)·RY(θ)·RZ(λ)
                theta, phi, lam = op.params[:3]
                p += RZ(lam, *qs)
                p += RY(theta, *qs)
                p += RZ(phi, *qs)
            elif ot == IROpType.CY:
                # CY via S†·CX·S decomposition
                target = qs[1]
                p += S(target).dagger()
                p += CNOT(*qs)
                p += S(target)

        return p

    # ── pyquil.Program → IR ─────────────────────────────────────────────

    def native_to_ir(self, native_circuit: Any) -> QuantumCircuitIR:
        from pyquil import Program
        from pyquil.quilbase import Gate as PyQuilGate, Measurement

        if not isinstance(native_circuit, Program):
            raise TypeError(f"Expected pyquil.Program, got {type(native_circuit).__name__}")

        _name_map = {v: k for k, v in PYQUIL_GATE_NAMES.items()}
        ops: list[IROperation] = []
        max_qubit = 0

        for inst in native_circuit.instructions:
            if isinstance(inst, Measurement):
                q = inst.qubit.index
                max_qubit = max(max_qubit, q)
                cb = inst.classical_reg.offset if inst.classical_reg else q
                ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[cb]))
            elif isinstance(inst, PyQuilGate):
                qs = [q.index for q in inst.qubits]
                max_qubit = max(max_qubit, *qs) if qs else max_qubit
                gate_name = inst.name
                params = [float(p) for p in inst.params] if inst.params else []
                if gate_name in _name_map:
                    ops.append(IROperation(_name_map[gate_name], qs, params=params))

        nq = max_qubit + 1
        lineage = hashlib.sha256(f"pyquil_import:{nq}:{len(ops)}".encode()).hexdigest()[:16]
        circuit = QuantumCircuitIR(
            name="pyquil_imported",
            quantum_registers=[QuantumRegister("q", nq)],
            classical_registers=[ClassicalRegister("c", nq)],
            operations=ops,
            source_organism="pyquil_import",
            lineage_hash=lineage,
        )
        circuit.compute_metrics()
        return circuit

    # ── Execute ─────────────────────────────────────────────────────────

    def execute(self, circuit: QuantumCircuitIR, shots: int = 1024) -> ExecutionResult:
        """Execute via QVM (requires quilc + qvm running locally)."""
        from pyquil import get_qc

        program = self.ir_to_native(circuit)
        t0 = time.time()
        qc = get_qc(f"{circuit.qubit_count}q-qvm")
        executable = qc.compile(program)
        results = qc.run(executable)
        bitstrings = results.readout_data.get("ro", [])

        counts: Dict[str, int] = {}
        for row in bitstrings:
            key = "".join(str(int(b)) for b in row)
            counts[key] = counts.get(key, 0) + 1
        if not counts:
            counts = {"0" * circuit.qubit_count: shots}
        dominant = max(counts, key=counts.get)
        fidelity = counts[dominant] / shots
        return ExecutionResult(
            job_id=f"pyquil_{int(time.time())}",
            backend="pyquil_qvm",
            status="completed",
            timestamp=str(time.time()),
            counts=counts,
            fidelity=fidelity,
            success_rate=fidelity,
            execution_time=time.time() - t0,
        )


# Auto-register on import (only if pyquil is installed)
if _check_pyquil():
    BackendRegistry.register(PyQuilAdapter())
