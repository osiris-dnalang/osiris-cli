"""Tests for osiris.compiler — DNALang lexer, parser, IR, runtime, evolve, ledger."""
import pytest


# ---------------------------------------------------------------------------
# LEXER
# ---------------------------------------------------------------------------

class TestLexer:
    def test_import(self):
        from osiris.compiler import Lexer, TokenType, Token
        assert Lexer is not None

    def test_tokenize_simple(self):
        from osiris.compiler import Lexer
        lexer = Lexer("organism TestOrg {}")
        tokens = lexer.tokenize()
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_token_type_enum(self):
        from osiris.compiler import TokenType
        members = list(TokenType)
        assert len(members) >= 5

    def test_tokenize_quantum_ops(self):
        from osiris.compiler import Lexer
        lexer = Lexer("quantum_state |psi> { H(q[0]) }")
        tokens = lexer.tokenize()
        assert isinstance(tokens, list)
        assert len(tokens) > 0


# ---------------------------------------------------------------------------
# PARSER
# ---------------------------------------------------------------------------

class TestParser:
    def test_import(self):
        from osiris.compiler import Parser, ASTNode
        assert Parser is not None

    def test_parse_organism(self):
        from osiris.compiler import Lexer, Parser
        lexer = Lexer("organism TestOrg { genome MainGenome { gene G0 { action: test } } }")
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None

    def test_ast_node_types(self):
        from osiris.compiler import OrganismNode, GenomeNode, GeneNode
        assert OrganismNode is not None
        assert GenomeNode is not None
        assert GeneNode is not None

    def test_rdna_entry(self):
        from osiris.compiler import rDNAEntry
        entry = rDNAEntry(
            name="test_directive",
            purpose="testing",
            directive_raw="CANON",
            evolution_vector="north",
            coherence_target="0.95",
        )
        assert entry.name == "test_directive"
        assert entry.directive_raw == "CANON"


# ---------------------------------------------------------------------------
# INTERMEDIATE REPRESENTATION
# ---------------------------------------------------------------------------

class TestIR:
    def test_import(self):
        from osiris.compiler import IROpType, IROperation, QuantumCircuitIR
        assert IROpType is not None

    def test_ir_op_type_gates(self):
        from osiris.compiler import IROpType
        gate_names = [e.name for e in IROpType]
        assert "H" in gate_names
        assert "CX" in gate_names
        assert "MEASURE" in gate_names

    def test_ir_operation_creation(self):
        from osiris.compiler import IROpType, IROperation
        op = IROperation(op_type=IROpType.H, qubits=[0])
        assert op.op_type == IROpType.H
        qasm = op.to_qasm()
        assert isinstance(qasm, str)
        assert "h" in qasm.lower() or "H" in qasm

    def test_quantum_circuit_ir(self):
        from osiris.compiler import QuantumCircuitIR, IROperation, IROpType
        from osiris.compiler import QuantumRegister, ClassicalRegister
        qr = QuantumRegister(name="q", size=2)
        cr = ClassicalRegister(name="c", size=2)
        circuit = QuantumCircuitIR(
            name="test",
            quantum_registers=[qr],
            classical_registers=[cr],
            operations=[
                IROperation(op_type=IROpType.H, qubits=[0]),
                IROperation(op_type=IROpType.CX, qubits=[0, 1]),
                IROperation(op_type=IROpType.MEASURE, qubits=[0], classical_bits=[0]),
            ],
        )
        assert circuit.name == "test"
        circuit.compute_metrics()
        assert isinstance(circuit.to_dict(), dict)

    def test_ir_compiler(self):
        from osiris.compiler import IRCompiler
        compiler = IRCompiler()
        assert compiler is not None

    def test_ir_optimizer(self):
        from osiris.compiler import IROptimizer
        opt = IROptimizer()
        assert opt is not None


# ---------------------------------------------------------------------------
# EVOLUTIONARY OPTIMIZER
# ---------------------------------------------------------------------------

class TestEvolution:
    def test_import(self):
        from osiris.compiler import FitnessMetrics, FitnessEvaluator
        from osiris.compiler import EvolutionaryOptimizer, EvolutionResult
        assert FitnessEvaluator is not None

    def test_fitness_metrics(self):
        from osiris.compiler import FitnessMetrics
        fm = FitnessMetrics(
            lambda_coherence=0.95,
            gamma_decoherence=0.05,
            phi_integrated_info=0.8,
            w2_distance=0.1,
        )
        assert fm.lambda_coherence == 0.95

    def test_fitness_evaluator(self):
        from osiris.compiler import FitnessEvaluator
        evaluator = FitnessEvaluator()
        assert evaluator is not None

    def test_evolutionary_optimizer(self):
        from osiris.compiler import EvolutionaryOptimizer
        opt = EvolutionaryOptimizer()
        assert opt is not None


# ---------------------------------------------------------------------------
# RUNTIME
# ---------------------------------------------------------------------------

class TestRuntime:
    def test_import(self):
        from osiris.compiler import RuntimeConfig, ExecutionResult, QuantumRuntime
        assert QuantumRuntime is not None

    def test_runtime_config(self):
        from osiris.compiler import RuntimeConfig
        config = RuntimeConfig(shots=1024, backend_name="mock")
        assert config.shots == 1024

    def test_runtime_instantiation(self):
        from osiris.compiler import QuantumRuntime
        rt = QuantumRuntime()
        assert rt is not None


# ---------------------------------------------------------------------------
# LEDGER
# ---------------------------------------------------------------------------

class TestLedger:
    def test_import(self):
        from osiris.compiler import LineageEntry, EvolutionLineage, QuantumLedger
        assert QuantumLedger is not None

    def test_lineage_entry(self):
        from osiris.compiler import LineageEntry
        entry = LineageEntry(
            lineage_hash="abc123",
            organism_name="test_org",
            generation=0,
            fitness_score=0.85,
        )
        assert entry.generation == 0
        assert entry.fitness_score == 0.85

    def test_ledger_instantiation(self):
        from osiris.compiler import QuantumLedger
        ledger = QuantumLedger()
        assert ledger is not None

    def test_ledger_aliases(self):
        from osiris.compiler import DNALangParser, DNALangLexer, DNAIR
        from osiris.compiler import DNAEvolver, DNARuntime, DNALedger
        assert DNALangParser is not None
        assert DNALangLexer is not None
        assert DNAIR is not None
        assert DNAEvolver is not None
        assert DNARuntime is not None
        assert DNALedger is not None
