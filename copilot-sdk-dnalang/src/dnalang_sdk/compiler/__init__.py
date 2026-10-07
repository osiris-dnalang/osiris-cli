"""DNA-Lang Compiler v2 — Full Lexer→Parser→IR→Runtime→Evolution→Ledger pipeline."""

from .dna_parser import Lexer, Parser, TokenType, Token, ASTNode, rDNAEntry
from .dna_ir import IRCompiler, IROptimizer, IROpType, IROperation, QuantumCircuitIR
from .dna_evolve import EvolutionaryOptimizer, FitnessEvaluator, EvolutionResult
from .dna_runtime import QuantumRuntime, ExecutionResult, RuntimeConfig
from .dna_ledger import QuantumLedger, EvolutionLineage, LineageEntry

# Aliases for convenience
DNALangParser = Parser
DNALangLexer = Lexer
DNAIR = IRCompiler
IRNode = IROperation
DNAEvolver = EvolutionaryOptimizer
DNARuntime = QuantumRuntime
DNALedger = QuantumLedger

__all__ = [
    # Core classes
    "Lexer", "Parser", "TokenType", "Token", "ASTNode", "rDNAEntry",
    "IRCompiler", "IROptimizer", "IROpType", "IROperation", "QuantumCircuitIR",
    "EvolutionaryOptimizer", "FitnessEvaluator", "EvolutionResult",
    "QuantumRuntime", "ExecutionResult", "RuntimeConfig",
    "QuantumLedger", "EvolutionLineage", "LineageEntry",
    # Convenience aliases
    "DNALangParser", "DNALangLexer", "DNAIR", "IRNode",
    "DNAEvolver", "DNARuntime", "DNALedger",
]
