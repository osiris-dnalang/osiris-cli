"""Backend adapter and converter tests."""

import importlib.util

from osiris.compiler.converter import OrganismConverter
from osiris.compiler.backends.registry import BackendRegistry
from osiris.compiler.backends.base import BackendAdapter
from osiris.compiler.dna_ir import (
    QuantumCircuitIR,
    QuantumRegister,
    ClassicalRegister,
    IROperation,
    IROpType,
)
from osiris.compiler.dna_runtime import QuantumRuntime, RuntimeConfig


def _simple_ir() -> QuantumCircuitIR:
    circuit = QuantumCircuitIR(
        name="test_circuit",
        quantum_registers=[QuantumRegister("q", 2)],
        classical_registers=[ClassicalRegister("c", 2)],
        operations=[
            IROperation(IROpType.H, [0]),
            IROperation(IROpType.CX, [0, 1]),
            IROperation(IROpType.MEASURE, [0, 1], classical_bits=[0, 1]),
        ],
        source_organism="test",
        lineage_hash="abc123",
    )
    circuit.compute_metrics()
    return circuit


def test_backend_registry_includes_sovereign():
    names = BackendRegistry.list_backends()
    assert "sovereign" in names


def test_runtime_executes_with_sovereign_backend():
    runtime = QuantumRuntime(RuntimeConfig(backend_name="sovereign", shots=32))
    result = runtime.execute(_simple_ir())
    assert result.status == "completed"
    assert result.backend == "sovereign"
    assert sum(result.counts.values()) == 32


def test_converter_compile_default_source():
    converter = OrganismConverter()
    circuit = converter.compile("BellState")
    assert isinstance(circuit, QuantumCircuitIR)
    assert circuit.gate_count >= 1
    assert circuit.qubit_count >= 1


def test_converter_translate_sovereign_round_trip():
    converter = OrganismConverter()
    circuit = _simple_ir()
    translated = converter.translate(circuit, source_backend="sovereign", target_backend="sovereign")
    assert translated.gate_count == circuit.gate_count
    assert translated.depth == circuit.depth


def test_converter_translate_returns_report_when_requested():
    converter = OrganismConverter()
    circuit = _simple_ir()
    translated, report = converter.translate(
        circuit,
        source_backend="sovereign",
        target_backend="sovereign",
        return_report=True,
    )
    assert translated.gate_count == circuit.gate_count
    assert report["source_backend"] == "sovereign"
    assert report["target_backend"] == "sovereign"
    assert report["possible_loss"] is False
    assert report["measurement_count_delta"] == 0
    assert report["dropped_operation_signatures"] == {}


def test_converter_translate_strict_raises_on_lossy_backend():
    class LossyAdapter(BackendAdapter):
        @property
        def name(self) -> str:
            return "lossy-test"

        def native_gate_set(self):
            return set()

        def ir_to_native(self, circuit: QuantumCircuitIR):
            return circuit

        def native_to_ir(self, native_circuit):
            # Deliberately drop all operations to simulate unsupported-gate loss.
            out = QuantumCircuitIR(
                name="lossy",
                quantum_registers=[QuantumRegister("q", 2)],
                classical_registers=[ClassicalRegister("c", 2)],
                operations=[],
                source_organism="lossy",
                lineage_hash="lossyhash",
            )
            out.compute_metrics()
            return out

        def execute(self, circuit: QuantumCircuitIR, shots: int = 1024):
            raise NotImplementedError

    BackendRegistry.register(LossyAdapter())
    converter = OrganismConverter()

    try:
        converter.translate(
            _simple_ir(),
            source_backend="sovereign",
            target_backend="lossy-test",
            strict=True,
        )
    except ValueError as exc:
        assert "Strict translation failed" in str(exc)
    else:
        assert False, "expected strict translation to fail on lossy backend"


def test_converter_export_qasm_and_json():
    converter = OrganismConverter()
    circuit = _simple_ir()
    qasm = converter.export(circuit, fmt="qasm")
    payload = converter.export(circuit, fmt="json")
    assert "OPENQASM" in qasm
    assert '"operations_detail"' in payload


def test_converter_execute_with_sovereign():
    converter = OrganismConverter()
    result = converter.execute(_simple_ir(), backend="sovereign", shots=16)
    assert result.status == "completed"
    assert result.backend == "sovereign"


def test_qiskit_adapter_roundtrip_if_available():
    if importlib.util.find_spec("qiskit") is None:
        return

    from osiris.compiler.backends.qiskit_adapter import QiskitAdapter

    adapter = QiskitAdapter()
    native = adapter.ir_to_native(_simple_ir())
    ir = adapter.native_to_ir(native)
    assert ir.qubit_count == 2
    assert ir.gate_count >= 2
