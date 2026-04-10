"""
Organism Converter — Cross-backend translation of quantum organisms.

Mirrors the dnalang-organism-converter Converter.translate() pattern:
  converter = OrganismConverter()
  ir = converter.compile("bell_state.dna")
  translated = converter.translate(ir, source_backend="qiskit", target_backend="cirq")
  qasm = converter.export(translated, format="qasm")
"""

import hashlib
import time
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .dna_ir import (
    IRCompiler, IROptimizer, QuantumCircuitIR, IROperation, IROpType,
    QuantumRegister, ClassicalRegister,
)
from .dna_parser import Lexer, Parser
from .dna_runtime import ExecutionResult, RuntimeConfig
from .backends.registry import BackendRegistry


@dataclass
class TranslationReport:
    """Structured translation quality report for backend-to-backend conversion."""

    source_backend: str
    target_backend: str
    source_operation_count: int
    translated_operation_count: int
    source_non_measure_ops: int
    translated_non_measure_ops: int
    source_gate_histogram: Dict[str, int]
    translated_gate_histogram: Dict[str, int]
    dropped_operation_signatures: Dict[str, int]
    added_operation_signatures: Dict[str, int]
    measurement_count_delta: int
    possible_loss: bool
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OrganismConverter:
    """High-level API for compiling, translating, and executing organisms."""

    def __init__(self) -> None:
        self._ir_compiler = IRCompiler()
        self._ir_optimizer = IROptimizer()

    # ── Compile ─────────────────────────────────────────────────────────

    def compile(
        self,
        source: str,
        backend: str = "sovereign",
        optimize: bool = True,
    ) -> QuantumCircuitIR:
        """Compile DNA-Lang source code into a QuantumCircuitIR.

        Parameters
        ----------
        source : str
            DNA-Lang source text or organism name for default circuit.
        backend : str
            Target backend name (used for metadata, not execution).
        optimize : bool
            Run IR optimizer after compilation.
        """
        # Try parsing as DNA-Lang source
        try:
            tokens = Lexer(source).tokenize()
            ast_nodes = Parser(tokens).parse()
            if ast_nodes:
                organism = ast_nodes[0]
                name = getattr(organism, "name", "organism")
                # Count qubits from quantum_state operations
                qubits = 2
                ops: List[IROperation] = []
                if hasattr(organism, "quantum_state") and organism.quantum_state:
                    used = set()
                    for qop in organism.quantum_state.operations:
                        for q in qop.qubits:
                            used.add(q)
                        op_type = _resolve_op_type(qop.operation)
                        if op_type:
                            ops.append(IROperation(op_type, qop.qubits,
                                                   params=qop.params))
                    if used:
                        qubits = max(used) + 1
                    # Add measurements
                    ops.append(IROperation(IROpType.MEASURE, list(range(qubits)),
                                           classical_bits=list(range(qubits))))
                circuit = self._ir_compiler.compile(name, qubits=qubits,
                                                    operations=ops if ops else None)
                circuit.source_organism = name
            else:
                circuit = self._ir_compiler.compile(source)
        except Exception:
            # Treat as organism name for default Bell-state circuit
            circuit = self._ir_compiler.compile(source)

        if optimize:
            circuit = self._ir_optimizer.optimize(circuit)

        return circuit

    # ── Translate ───────────────────────────────────────────────────────

    def translate(
        self,
        circuit: QuantumCircuitIR,
        source_backend: str,
        target_backend: str,
        strict: bool = False,
        return_report: bool = False,
    ) -> QuantumCircuitIR | tuple[QuantumCircuitIR, Dict[str, Any]]:
        """Translate a circuit from one backend to another.

        1. IR → source backend native circuit
        2. source native → IR (normalises through source backend's representation)
        3. IR → target backend native circuit
        4. target native → IR (captures target representation)

        CRSM metrics and lineage are preserved with translation metadata.
        """
        src_adapter = BackendRegistry.get(source_backend)
        tgt_adapter = BackendRegistry.get(target_backend)

        # If both are sovereign, just return a copy
        if source_backend == target_backend == "sovereign":
            return circuit

        # Step 1-2: normalise through source backend
        if source_backend != "sovereign":
            native_src = src_adapter.ir_to_native(circuit)
            normalised = src_adapter.native_to_ir(native_src)
        else:
            normalised = circuit

        # Step 3-4: translate through target backend
        if target_backend != "sovereign":
            native_tgt = tgt_adapter.ir_to_native(normalised)
            translated = tgt_adapter.native_to_ir(native_tgt)
        else:
            translated = normalised

        # Preserve CRSM metrics from original
        translated.lambda_coherence = circuit.lambda_coherence
        translated.gamma_decoherence = circuit.gamma_decoherence
        translated.phi_integrated_info = circuit.phi_integrated_info
        translated.w2_distance = circuit.w2_distance
        translated.source_organism = circuit.source_organism
        translated.generation = circuit.generation

        # Update lineage with translation provenance
        translation_data = (
            f"{circuit.lineage_hash}:"
            f"{source_backend}->{target_backend}:"
            f"{int(time.time())}"
        )
        translated.lineage_hash = hashlib.sha256(
            translation_data.encode()
        ).hexdigest()[:16]
        translated.parent_hash = circuit.lineage_hash

        translated.compute_metrics()

        report = self.translation_report(
            circuit,
            translated,
            source_backend=source_backend,
            target_backend=target_backend,
        )
        if strict and report.possible_loss:
            warning = report.warnings[0] if report.warnings else "possible semantic loss detected"
            raise ValueError(f"Strict translation failed: {warning}")

        if return_report:
            return translated, report.to_dict()
        return translated

    def translation_report(
        self,
        source: QuantumCircuitIR,
        translated: QuantumCircuitIR,
        source_backend: str,
        target_backend: str,
    ) -> TranslationReport:
        """Produce a structured quality report for a translation result."""
        source_sigs = Counter(self._operation_signature(op) for op in source.operations)
        translated_sigs = Counter(self._operation_signature(op) for op in translated.operations)

        dropped = source_sigs - translated_sigs
        added = translated_sigs - source_sigs

        source_hist = Counter(op.op_type.value for op in source.operations)
        translated_hist = Counter(op.op_type.value for op in translated.operations)

        warnings: List[str] = []
        possible_loss = False
        if dropped:
            possible_loss = True
            warnings.append("Some operation signatures were dropped during translation")

        measurement_delta = translated_hist.get("measure", 0) - source_hist.get("measure", 0)
        if measurement_delta != 0:
            possible_loss = True
            warnings.append("Measurement operation count changed during translation")

        source_non_measure = sum(
            1 for op in source.operations if op.op_type != IROpType.MEASURE
        )
        translated_non_measure = sum(
            1 for op in translated.operations if op.op_type != IROpType.MEASURE
        )
        if translated_non_measure < source_non_measure:
            possible_loss = True
            warnings.append("Translated circuit has fewer non-measure gates than source")

        return TranslationReport(
            source_backend=source_backend,
            target_backend=target_backend,
            source_operation_count=len(source.operations),
            translated_operation_count=len(translated.operations),
            source_non_measure_ops=source_non_measure,
            translated_non_measure_ops=translated_non_measure,
            source_gate_histogram=dict(source_hist),
            translated_gate_histogram=dict(translated_hist),
            dropped_operation_signatures=dict(dropped),
            added_operation_signatures=dict(added),
            measurement_count_delta=measurement_delta,
            possible_loss=possible_loss,
            warnings=warnings,
        )

    @staticmethod
    def _operation_signature(op: IROperation) -> str:
        """Stable operation identity used for translation quality diffs."""
        params = ",".join(f"{float(p):.8f}" for p in op.params)
        qubits = ",".join(str(q) for q in op.qubits)
        cbs = ""
        if op.classical_bits:
            cbs = ",".join(str(cb) for cb in op.classical_bits)
        return f"{op.op_type.value}|q:{qubits}|p:{params}|c:{cbs}"

    # ── Export ───────────────────────────────────────────────────────────

    def export(
        self,
        circuit: QuantumCircuitIR,
        fmt: str = "qasm",
    ) -> str:
        """Export circuit to a string format.

        Parameters
        ----------
        fmt : str
            One of "qasm", "json", "dict".
        """
        if fmt == "qasm":
            return circuit.to_qasm()
        if fmt in ("json", "dict"):
            import json
            data = circuit.to_dict()
            data["operations_detail"] = [
                {
                    "op": op.op_type.value,
                    "qubits": op.qubits,
                    "params": op.params,
                    "classical_bits": op.classical_bits,
                }
                for op in circuit.operations
            ]
            return json.dumps(data, indent=2)
        raise ValueError(f"Unknown format '{fmt}'. Use 'qasm' or 'json'.")

    # ── Execute ─────────────────────────────────────────────────────────

    def execute(
        self,
        circuit: QuantumCircuitIR,
        backend: str = "sovereign",
        shots: int = 1024,
    ) -> ExecutionResult:
        """Execute a circuit on the specified backend."""
        adapter = BackendRegistry.get(backend)
        return adapter.execute(circuit, shots=shots)


def _resolve_op_type(op_name: str) -> Optional[IROpType]:
    """Map a quantum operation name to IROpType."""
    _map = {
        "h": IROpType.H, "helix": IROpType.H,
        "x": IROpType.X, "cleave": IROpType.X,
        "y": IROpType.Y, "z": IROpType.Z,
        "s": IROpType.S, "t": IROpType.T,
        "rx": IROpType.RX, "splice": IROpType.RX,
        "ry": IROpType.RY, "fold": IROpType.RY,
        "rz": IROpType.RZ, "twist": IROpType.RZ,
        "u3": IROpType.U3, "evolve": IROpType.U3,
        "cx": IROpType.CX, "bond": IROpType.CX, "cnot": IROpType.CX,
        "cy": IROpType.CY, "cz": IROpType.CZ,
        "swap": IROpType.SWAP,
        "ccx": IROpType.CCX, "toffoli": IROpType.CCX,
        "cswap": IROpType.CSWAP, "fredkin": IROpType.CSWAP,
        "measure": IROpType.MEASURE,
        "barrier": IROpType.BARRIER,
        "reset": IROpType.RESET,
    }
    return _map.get(op_name.lower())
