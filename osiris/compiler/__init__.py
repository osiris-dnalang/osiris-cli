"""osiris.compiler — DNA parser, IR, runtime, ledger, evolve, backends, synthesis."""

from .dna_parser import (
    Lexer, Parser, TokenType, Token, ASTNode, OrganismNode, GenomeNode,
    GeneNode, QuantumStateNode, QuantumOpNode, rDNAEntry,
    KEYWORDS, QUANTUM_OPS, CANON_PREFIX,
)
from .dna_ir import (
    IROpType, IROperation, QuantumRegister, ClassicalRegister,
    QuantumCircuitIR, IRCompiler, IROptimizer,
)
from .dna_evolve import (
    FitnessMetrics, FitnessEvaluator, EvolutionaryOptimizer, EvolutionResult,
)
from .dna_runtime import RuntimeConfig, ExecutionResult, QuantumRuntime
from .dna_ledger import LineageEntry, EvolutionLineage, QuantumLedger
from .converter import OrganismConverter, TranslationReport
from .backends import BackendAdapter, BackendRegistry
from .hamiltonian_synthesis import (
    HamiltonianSynthesisEngine,
    ProblemType as SynthesisProblemType,
    SynthesisResult,
)

# Compatibility aliases
DNALangParser = Parser
DNALangLexer = Lexer
DNAIR = QuantumCircuitIR
IRNode = IROperation
DNAEvolver = EvolutionaryOptimizer
DNARuntime = QuantumRuntime
DNALedger = QuantumLedger
