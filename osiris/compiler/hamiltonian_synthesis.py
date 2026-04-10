"""
Hamiltonian Synthesis Engine — Auto-generate QuantumCircuitIR
=============================================================

Given a problem type (Ising, MaxCut, chemistry, QAOA, etc.),
automatically synthesises a QuantumCircuitIR using only stdlib math.
Zero external dependencies — no numpy, no scipy, no qiskit.

Generates gate-level IR that can be exported to QASM or sent to
any supported backend via the existing compiler pipeline.
"""

import math
import hashlib
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from osiris.compiler.dna_ir import (
    IROpType,
    IROperation,
    QuantumCircuitIR,
    QuantumRegister,
    ClassicalRegister,
)


class ProblemType(Enum):
    ISING_1D = "ising_1d"
    MAXCUT = "maxcut"
    QAOA = "qaoa"
    VQE_H2 = "vqe_h2"
    GROVER = "grover"
    QFT = "qft"
    BELL = "bell"
    GHZ = "ghz"
    RANDOM_RQC = "random_rqc"


@dataclass
class SynthesisResult:
    circuit: QuantumCircuitIR
    problem_type: ProblemType
    parameters: Dict[str, Any]
    qubit_count: int
    gate_count: int
    depth: int
    synthesis_time_s: float
    lineage_hash: str


class HamiltonianSynthesisEngine:
    """Auto-detect problem type and emit QuantumCircuitIR."""

    _DISPATCH = {}  # populated by _register below

    def __init__(self):
        self.history: List[SynthesisResult] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def synthesize(
        self,
        problem: ProblemType,
        n_qubits: int = 4,
        depth: int = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> SynthesisResult:
        params = params or {}
        t0 = time.time()
        builder = self._DISPATCH.get(problem)
        if builder is None:
            raise ValueError(f"Unsupported problem type: {problem}")
        circuit = builder(self, n_qubits, depth, params)
        circuit.compute_metrics()
        lineage = hashlib.sha256(
            f"{problem.value}:{n_qubits}:{depth}:{time.time()}".encode()
        ).hexdigest()[:16]
        circuit.lineage_hash = lineage
        result = SynthesisResult(
            circuit=circuit,
            problem_type=problem,
            parameters={"n_qubits": n_qubits, "depth": depth, **params},
            qubit_count=circuit.qubit_count,
            gate_count=circuit.gate_count,
            depth=circuit.depth,
            synthesis_time_s=round(time.time() - t0, 6),
            lineage_hash=lineage,
        )
        self.history.append(result)
        return result

    def auto_detect(self, description: str, n_qubits: int = 4) -> SynthesisResult:
        """Infer problem type from a natural-language description."""
        desc = description.lower()
        if "ising" in desc or "spin" in desc:
            pt = ProblemType.ISING_1D
        elif "maxcut" in desc or "max-cut" in desc or "graph" in desc:
            pt = ProblemType.MAXCUT
        elif "qaoa" in desc:
            pt = ProblemType.QAOA
        elif "vqe" in desc or "h2" in desc or "hydrogen" in desc or "chemistry" in desc:
            pt = ProblemType.VQE_H2
        elif "grover" in desc or "search" in desc or "oracle" in desc:
            pt = ProblemType.GROVER
        elif "qft" in desc or "fourier" in desc:
            pt = ProblemType.QFT
        elif "bell" in desc:
            pt = ProblemType.BELL
        elif "ghz" in desc:
            pt = ProblemType.GHZ
        else:
            pt = ProblemType.RANDOM_RQC
        return self.synthesize(pt, n_qubits=n_qubits)

    def list_problems(self) -> List[str]:
        return [p.value for p in ProblemType]

    # ------------------------------------------------------------------
    # Circuit builders
    # ------------------------------------------------------------------
    def _build_bell(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        n = max(n_qubits, 2)
        ops = [
            IROperation(IROpType.H, [0]),
            IROperation(IROpType.CX, [0, 1]),
        ]
        # Add measurements
        for q in range(min(n, 2)):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("bell_state", n, ops)

    def _build_ghz(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        ops = [IROperation(IROpType.H, [0])]
        for q in range(1, n_qubits):
            ops.append(IROperation(IROpType.CX, [0, q]))
        for q in range(n_qubits):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("ghz_state", n_qubits, ops)

    def _build_qft(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        ops: List[IROperation] = []
        for i in range(n_qubits):
            ops.append(IROperation(IROpType.H, [i]))
            for j in range(i + 1, n_qubits):
                angle = math.pi / (2 ** (j - i))
                ops.append(IROperation(IROpType.RZ, [j], params=[angle]))
                ops.append(IROperation(IROpType.CX, [j, i]))
                ops.append(IROperation(IROpType.RZ, [j], params=[-angle]))
                ops.append(IROperation(IROpType.CX, [j, i]))
        # Swap for bit reversal
        for i in range(n_qubits // 2):
            ops.append(IROperation(IROpType.SWAP, [i, n_qubits - 1 - i]))
        for q in range(n_qubits):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("qft", n_qubits, ops)

    def _build_ising_1d(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        J = params.get("coupling", 1.0)
        h_field = params.get("field", 0.5)
        dt = params.get("dt", 0.1)
        ops: List[IROperation] = []
        # Initial superposition
        for q in range(n_qubits):
            ops.append(IROperation(IROpType.H, [q]))
        # Trotter steps
        for _ in range(depth):
            # ZZ interaction
            for q in range(n_qubits - 1):
                ops.append(IROperation(IROpType.CX, [q, q + 1]))
                ops.append(IROperation(IROpType.RZ, [q + 1], params=[2 * J * dt]))
                ops.append(IROperation(IROpType.CX, [q, q + 1]))
            # Transverse field
            for q in range(n_qubits):
                ops.append(IROperation(IROpType.RX, [q], params=[2 * h_field * dt]))
        for q in range(n_qubits):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("ising_1d", n_qubits, ops)

    def _build_maxcut(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        gamma = params.get("gamma", 0.5)
        beta = params.get("beta", 0.3)
        # Default: ring graph
        edges = params.get("edges", [(i, (i + 1) % n_qubits) for i in range(n_qubits)])
        ops: List[IROperation] = []
        for q in range(n_qubits):
            ops.append(IROperation(IROpType.H, [q]))
        for _ in range(depth):
            for u, v in edges:
                ops.append(IROperation(IROpType.CX, [u, v]))
                ops.append(IROperation(IROpType.RZ, [v], params=[gamma]))
                ops.append(IROperation(IROpType.CX, [u, v]))
            for q in range(n_qubits):
                ops.append(IROperation(IROpType.RX, [q], params=[2 * beta]))
        for q in range(n_qubits):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("maxcut_qaoa", n_qubits, ops)

    def _build_qaoa(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        return self._build_maxcut(n_qubits, depth, params)

    def _build_vqe_h2(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        n = max(n_qubits, 4)
        theta = params.get("theta", 0.2)
        ops: List[IROperation] = []
        # HF reference: |0011>
        ops.append(IROperation(IROpType.X, [0]))
        ops.append(IROperation(IROpType.X, [1]))
        # UCCSD-like ansatz
        for _ in range(depth):
            for q in range(n - 1):
                ops.append(IROperation(IROpType.CX, [q, q + 1]))
            for q in range(n):
                ops.append(IROperation(IROpType.RY, [q], params=[theta]))
            for q in range(n - 1, 0, -1):
                ops.append(IROperation(IROpType.CX, [q - 1, q]))
        for q in range(n):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("vqe_h2", n, ops)

    def _build_grover(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        n = max(n_qubits, 2)
        target = params.get("target", 0)
        iterations = max(1, int(math.pi / 4 * math.sqrt(2 ** n)))
        ops: List[IROperation] = []
        # Superposition
        for q in range(n):
            ops.append(IROperation(IROpType.H, [q]))
        for _ in range(min(iterations, depth or iterations)):
            # Oracle: flip target state
            for q in range(n):
                if not (target >> q) & 1:
                    ops.append(IROperation(IROpType.X, [q]))
            if n >= 3:
                ops.append(IROperation(IROpType.CCX, list(range(min(n, 3)))))
            else:
                ops.append(IROperation(IROpType.CZ, [0, 1]))
            for q in range(n):
                if not (target >> q) & 1:
                    ops.append(IROperation(IROpType.X, [q]))
            # Diffuser
            for q in range(n):
                ops.append(IROperation(IROpType.H, [q]))
                ops.append(IROperation(IROpType.X, [q]))
            if n >= 3:
                ops.append(IROperation(IROpType.CCX, list(range(min(n, 3)))))
            else:
                ops.append(IROperation(IROpType.CZ, [0, 1]))
            for q in range(n):
                ops.append(IROperation(IROpType.X, [q]))
                ops.append(IROperation(IROpType.H, [q]))
        for q in range(n):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("grover_search", n, ops)

    def _build_random_rqc(self, n_qubits: int, depth: int, params: Dict) -> QuantumCircuitIR:
        import random
        seed = params.get("seed", 42)
        rng = random.Random(seed)
        single_gates = [IROpType.H, IROpType.X, IROpType.Y, IROpType.Z, IROpType.S, IROpType.T]
        param_gates = [IROpType.RX, IROpType.RY, IROpType.RZ]
        ops: List[IROperation] = []
        for _ in range(depth):
            for q in range(n_qubits):
                if rng.random() < 0.6:
                    ops.append(IROperation(rng.choice(single_gates), [q]))
                else:
                    ops.append(IROperation(rng.choice(param_gates), [q], params=[rng.uniform(0, 2 * math.pi)]))
            for q in range(0, n_qubits - 1, 2):
                ops.append(IROperation(IROpType.CX, [q, q + 1]))
            for q in range(1, n_qubits - 1, 2):
                ops.append(IROperation(IROpType.CX, [q, q + 1]))
        for q in range(n_qubits):
            ops.append(IROperation(IROpType.MEASURE, [q], classical_bits=[q]))
        return self._make_ir("random_rqc", n_qubits, ops)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_ir(self, name: str, n_qubits: int, ops: List[IROperation]) -> QuantumCircuitIR:
        return QuantumCircuitIR(
            name=name,
            quantum_registers=[QuantumRegister("q", n_qubits)],
            classical_registers=[ClassicalRegister("c", n_qubits)],
            operations=ops,
            source_organism="hamiltonian_synthesis",
        )


# Register builders
for _pt, _method in [
    (ProblemType.BELL, "_build_bell"),
    (ProblemType.GHZ, "_build_ghz"),
    (ProblemType.QFT, "_build_qft"),
    (ProblemType.ISING_1D, "_build_ising_1d"),
    (ProblemType.MAXCUT, "_build_maxcut"),
    (ProblemType.QAOA, "_build_qaoa"),
    (ProblemType.VQE_H2, "_build_vqe_h2"),
    (ProblemType.GROVER, "_build_grover"),
    (ProblemType.RANDOM_RQC, "_build_random_rqc"),
]:
    HamiltonianSynthesisEngine._DISPATCH[_pt] = getattr(HamiltonianSynthesisEngine, _method)
