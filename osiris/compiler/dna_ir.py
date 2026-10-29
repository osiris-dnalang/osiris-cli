"""
DNA-Lang Intermediate Representation — AST to executable quantum circuit IR.
"""

import hashlib
import math
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class IROpType(Enum):
    H = "h"
    X = "x"
    Y = "y"
    Z = "z"
    S = "s"
    T = "t"
    RX = "rx"
    RY = "ry"
    RZ = "rz"
    U3 = "u3"
    CX = "cx"
    CY = "cy"
    CZ = "cz"
    SWAP = "swap"
    CCX = "ccx"
    CSWAP = "cswap"
    MEASURE = "measure"
    BARRIER = "barrier"
    RESET = "reset"


@dataclass
class IROperation:
    op_type: IROpType
    qubits: List[int]
    params: List[float] = field(default_factory=list)
    classical_bits: Optional[List[int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_qasm(self) -> str:
        """OpenQASM statement(s) for this operation, valid in versions 2 and 3.

        Qubits and bits index the circuit's flat registers ``q`` and ``c``.
        """
        if self.op_type == IROpType.MEASURE:
            # OpenQASM measures one qubit per statement. A qubit with no bit
            # given lands in the bit of the same index, as in the Qiskit adapter.
            bits = self.classical_bits or []
            return "\n".join(
                f"measure q[{q}] -> c[{bits[i] if i < len(bits) else q}];"
                for i, q in enumerate(self.qubits)
            )
        if self.op_type == IROpType.RESET:
            return "\n".join(f"reset q[{q}];" for q in self.qubits)
        qubit_str = ", ".join(f"q[{q}]" for q in self.qubits)
        if self.op_type == IROpType.BARRIER and not self.qubits:
            qubit_str = "q"
        if self.params:
            param_str = ", ".join(_qasm_real(p) for p in self.params)
            return f"{self.op_type.value}({param_str}) {qubit_str};"
        return f"{self.op_type.value} {qubit_str};"


def _qasm_real(value: float) -> str:
    """Shortest literal that reads back as exactly ``value``.

    OpenQASM 2 needs a decimal point before any exponent, so 1e-05 becomes 1.0e-05.
    """
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"Gate parameter must be finite, got {value}")
    text = repr(value)
    return text.replace("e", ".0e", 1) if "e" in text and "." not in text else text


# Gates OpenQASM 2's qelib1.inc lacks, defined in the program when it uses them.
_QASM2_GATE_DEFS = {
    IROpType.SWAP: "gate swap a, b { cx a, b; cx b, a; cx a, b; }",
    IROpType.CSWAP: "gate cswap a, b, c { cx c, b; ccx a, b, c; cx c, b; }",
}


@dataclass
class QuantumRegister:
    name: str
    size: int


@dataclass
class ClassicalRegister:
    name: str
    size: int


@dataclass
class QuantumCircuitIR:
    """Intermediate representation of quantum circuit."""
    name: str
    quantum_registers: List[QuantumRegister]
    classical_registers: List[ClassicalRegister]
    operations: List[IROperation]
    source_organism: str = ""
    lineage_hash: str = ""
    generation: int = 0
    parent_hash: Optional[str] = None
    gate_count: int = 0
    depth: int = 0
    qubit_count: int = 0
    lambda_coherence: float = 0.0
    gamma_decoherence: float = 0.0
    phi_integrated_info: float = 0.0
    w2_distance: float = 0.0

    def compute_metrics(self):
        self.gate_count = len([op for op in self.operations if op.op_type != IROpType.MEASURE])
        self.qubit_count = sum(reg.size for reg in self.quantum_registers)
        self.depth = self._compute_depth()

    def _compute_depth(self) -> int:
        if not self.operations:
            return 0
        qubit_times: Dict[int, int] = {}
        max_time = 0
        for op in self.operations:
            current_time = max((qubit_times.get(q, 0) for q in op.qubits), default=0)
            for q in op.qubits:
                qubit_times[q] = current_time + 1
            max_time = max(max_time, current_time + 1)
        return max_time

    def to_qasm(self, version: str = "2.0") -> str:
        """OpenQASM 2 or 3 source for this circuit.

        Operations index qubits and bits across all registers, so the program
        declares one flat register of each: ``q`` and ``c``.
        """
        major = version.split(".")[0]
        if major not in ("2", "3"):
            raise ValueError(f"OpenQASM version must be 2.x or 3.x, got {version!r}")
        v3 = major == "3"
        lines = [
            f"// DNA-Lang Quantum Circuit: {self.name}",
            f"// Lineage: {self.lineage_hash}",
            f"OPENQASM {version};",
            'include "stdgates.inc";' if v3 else 'include "qelib1.inc";',
        ]
        if not v3:
            used = {op.op_type for op in self.operations}
            lines += [d for op_type, d in _QASM2_GATE_DEFS.items() if op_type in used]
        lines.append("")
        nq = sum(r.size for r in self.quantum_registers)
        nc = sum(r.size for r in self.classical_registers)
        lines.append(f"qubit[{nq}] q;" if v3 else f"qreg q[{nq}];")
        if nc:
            lines.append(f"bit[{nc}] c;" if v3 else f"creg c[{nc}];")
        lines.append("")
        for op in self.operations:
            lines.append(op.to_qasm())
        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_organism": self.source_organism,
            "lineage_hash": self.lineage_hash,
            "generation": self.generation,
            "gate_count": self.gate_count,
            "depth": self.depth,
            "qubit_count": self.qubit_count,
            "operations": len(self.operations),
        }


class IRCompiler:
    """Compiles organism AST nodes into QuantumCircuitIR."""

    def compile(self, organism_name: str, qubits: int = 2,
                operations: Optional[List[IROperation]] = None) -> QuantumCircuitIR:
        ops = operations or [
            IROperation(IROpType.H, [0]),
            IROperation(IROpType.CX, [0, 1]),
            IROperation(IROpType.MEASURE, list(range(qubits)),
                        classical_bits=list(range(qubits))),
        ]
        lineage_data = f"{organism_name}:{qubits}:{len(ops)}"
        lineage_hash = hashlib.sha256(lineage_data.encode()).hexdigest()[:16]
        circuit = QuantumCircuitIR(
            name=f"{organism_name}_circuit",
            quantum_registers=[QuantumRegister("q", qubits)],
            classical_registers=[ClassicalRegister("c", qubits)],
            operations=ops,
            source_organism=organism_name,
            lineage_hash=lineage_hash,
        )
        circuit.compute_metrics()
        return circuit


class IROptimizer:
    """Basic IR optimization passes."""

    def optimize(self, circuit: QuantumCircuitIR) -> QuantumCircuitIR:
        circuit.operations = self._remove_adjacent_inverses(circuit.operations)
        circuit.compute_metrics()
        return circuit

    @staticmethod
    def _remove_adjacent_inverses(ops: List[IROperation]) -> List[IROperation]:
        if len(ops) < 2:
            return ops
        result = []
        i = 0
        inverses = {
            (IROpType.H, IROpType.H), (IROpType.X, IROpType.X),
            (IROpType.Y, IROpType.Y), (IROpType.Z, IROpType.Z),
        }
        while i < len(ops):
            if i + 1 < len(ops):
                a, b = ops[i], ops[i + 1]
                if (a.op_type, b.op_type) in inverses and a.qubits == b.qubits:
                    i += 2
                    continue
            result.append(ops[i])
            i += 1
        return result
