"""OpenQASM export: what QuantumCircuitIR.to_qasm emits must parse, and mean the IR."""

import math

import pytest

from osiris.compiler.dna_ir import (
    ClassicalRegister,
    IRCompiler,
    IROperation,
    IROpType,
    QuantumCircuitIR,
    QuantumRegister,
)
from osiris.compiler.hamiltonian_synthesis import HamiltonianSynthesisEngine, ProblemType


def _circuit(ops, nq=3, nc=3):
    circuit = QuantumCircuitIR(
        name="t",
        quantum_registers=[QuantumRegister("q", nq)],
        classical_registers=[ClassicalRegister("c", nc)],
        operations=ops,
    )
    circuit.compute_metrics()
    return circuit


def _statements(qasm):
    return [line for line in qasm.splitlines() if line and not line.startswith("//")]


def _corpus():
    engine = HamiltonianSynthesisEngine()
    circuits = [("ircompiler_default", IRCompiler().compile("BellState"))]
    for problem in ProblemType:
        for n in (2, 3, 4, 5):
            try:
                circuits.append((f"{problem.value}_n{n}", engine.synthesize(problem, n_qubits=n).circuit))
            except Exception:
                continue  # not every problem type takes every size
    return circuits


@pytest.mark.parametrize("version", ["2.0", "3.0"])
def test_multi_qubit_measure_is_one_statement_per_qubit(version):
    qasm = IRCompiler().compile("BellState").to_qasm(version)
    assert "measure q[0] -> c[0];" in qasm and "measure q[1] -> c[1];" in qasm
    assert "measure q[0], q[1]" not in qasm


def test_measure_without_bits_uses_the_same_index():
    qasm = _circuit([IROperation(IROpType.MEASURE, [2])]).to_qasm()
    assert "measure q[2] -> c[2];" in qasm


def test_reset_is_one_statement_per_qubit():
    qasm = _circuit([IROperation(IROpType.RESET, [0, 1])]).to_qasm()
    assert "reset q[0];" in qasm and "reset q[1];" in qasm


def test_version_3_uses_its_own_standard_library_and_declarations():
    qasm = IRCompiler().compile("BellState").to_qasm("3.0")
    assert 'include "stdgates.inc";' in qasm and "qelib1.inc" not in qasm
    assert "qubit[2] q;" in qasm and "bit[2] c;" in qasm


def test_version_2_defines_gates_qelib1_lacks_only_when_used():
    plain = _circuit([IROperation(IROpType.CX, [0, 1])]).to_qasm()
    assert "gate swap" not in plain and "gate cswap" not in plain
    swaps = _circuit([IROperation(IROpType.SWAP, [0, 1]), IROperation(IROpType.CSWAP, [0, 1, 2])])
    assert "gate swap" in swaps.to_qasm() and "gate cswap" in swaps.to_qasm()
    assert "gate swap" not in swaps.to_qasm("3.0")


def test_registers_are_flattened_to_match_flat_operation_indices():
    circuit = QuantumCircuitIR(
        name="t",
        quantum_registers=[QuantumRegister("a", 2), QuantumRegister("b", 1)],
        classical_registers=[ClassicalRegister("m", 3)],
        operations=[IROperation(IROpType.CX, [1, 2])],
    )
    statements = _statements(circuit.to_qasm())
    assert "qreg q[3];" in statements and "creg c[3];" in statements
    assert "cx q[1], q[2];" in statements


@pytest.mark.parametrize("angle", [math.pi / 3, -0.1, 1e-5, 2.0, 1e16])
def test_parameters_read_back_exactly(angle):
    qasm = _circuit([IROperation(IROpType.RZ, [0], params=[angle])]).to_qasm()
    line = next(s for s in _statements(qasm) if s.startswith("rz("))
    text = line[len("rz("):line.index(")")]
    assert "." in text  # OpenQASM 2 reals need a decimal point
    assert float(text) == angle


def test_non_finite_parameters_and_unknown_versions_are_refused():
    with pytest.raises(ValueError):
        _circuit([IROperation(IROpType.RX, [0], params=[math.nan])]).to_qasm()
    with pytest.raises(ValueError):
        _circuit([]).to_qasm("1.0")


@pytest.mark.parametrize("version", ["2.0", "3.0"])
def test_every_synthesized_circuit_parses_and_matches_the_qiskit_adapter(version):
    pytest.importorskip("qiskit")
    if version.startswith("3"):
        pytest.importorskip("qiskit_qasm3_import")
    from qiskit import qasm2, qasm3
    from qiskit.quantum_info import Operator
    from osiris.compiler.backends.qiskit_adapter import QiskitAdapter

    loads = qasm2.loads if version.startswith("2") else qasm3.loads
    adapter = QiskitAdapter()
    for name, ir in _corpus():
        parsed = loads(ir.to_qasm(version)).remove_final_measurements(inplace=False)
        reference = adapter.ir_to_native(ir).remove_final_measurements(inplace=False)
        assert Operator(parsed).equiv(Operator(reference), rtol=0, atol=1e-12), name
