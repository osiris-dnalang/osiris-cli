#!/usr/bin/env python3
"""
dna_parser.py - DNA-Lang Recursive DNA Parser
Lexical analysis and AST generation for quantum consciousness organisms
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# ==========================================
# CONSTANTS AND GRAMMAR DEFINITIONS
# ==========================================

CANON_PREFIX = "AURA::"
CANON_SEPARATOR = "\n\n---\n"
ENTRY_FIELDS = ["Purpose:", "Directive:", "Evolution Vector:", "Coherence Target:"]
FIELD_PATTERN = r"^\s*([A-Za-z\s]+):([\s\S]*?)(?=\n\s*[A-Za-z\s]+:|\Z)"
DIRECTIVE_PATTERN = r"(AURA::[A-Z-]+)(\(.*\))?"

# DNA-Lang Keywords
KEYWORDS = {
    'organism', 'genome', 'gene', 'quantum_state', 'control', 'fitness',
    'encode', 'superpose', 'entangle', 'measure', 'evolve', 'mutate',
    'if', 'while', 'for', 'return', 'lambda', 'phi'
}

# Quantum Gate Operators
QUANTUM_OPS = {
    'helix': 'h',      # Hadamard
    'bond': 'cx',      # CNOT
    'evolve': 'u3',    # Universal rotation
    'measure': 'measure',
    'entangle': 'bell',
    'teleport': 'teleport',
    'phase': 'rz',
    'rotate_x': 'rx',
    'rotate_y': 'ry',
    'rotate_z': 'rz',
    'swap': 'swap',
    'toffoli': 'ccx'
}

class TokenType(Enum):
    """Token types for DNA-Lang lexer"""
    # Literals
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    
    # Keywords
    KEYWORD = "KEYWORD"
    QUANTUM_OP = "QUANTUM_OP"
    
    # Operators
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"
    POWER = "**"
    
    # Comparison
    EQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="
    
    # Assignment
    ASSIGN = "="
    ARROW = "->"
    
    # Delimiters
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    SEMICOLON = ";"
    COLON = ":"
    DOT = "."
    
    # Special
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    CANON = "CANON"

@dataclass
class Token:
    """Lexical token"""
    type: TokenType
    value: Any
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.type.value}, {repr(self.value)}, {self.line}:{self.column})"

@dataclass
class ASTNode:
    """Base AST node"""
    node_type: str
    line: int
    column: int
    
@dataclass 
class OrganismNode(ASTNode):
    """Organism definition node"""
    name: str
    genome: Optional['GenomeNode'] = None
    quantum_state: Optional['QuantumStateNode'] = None
    control: Optional['ControlNode'] = None
    fitness: Optional['ExpressionNode'] = None

@dataclass
class GenomeNode(ASTNode):
    """Genome block containing genes"""
    genes: List['GeneNode'] = field(default_factory=list)

@dataclass
class GeneNode(ASTNode):
    """Individual gene definition"""
    name: str
    encoding: str
    target_qubits: List[int]

@dataclass
class QuantumStateNode(ASTNode):
    """Quantum state operations block"""
    operations: List['QuantumOpNode'] = field(default_factory=list)

@dataclass
class QuantumOpNode(ASTNode):
    """Single quantum operation"""
    operation: str
    qubits: List[int]
    params: List[float] = field(default_factory=list)

@dataclass
class ControlNode(ASTNode):
    """Control flow block"""
    statements: List[ASTNode] = field(default_factory=list)

@dataclass
class ExpressionNode(ASTNode):
    """Expression node for fitness functions"""
    operator: str
    operands: List[Any] = field(default_factory=list)

@dataclass
class rDNAEntry:
    """Structured representation of an AURA Prompt Canon entry"""
    name: str
    purpose: str
    directive_raw: str
    evolution_vector: str
    coherence_target: str
    
    def get_directive_syntax(self) -> Tuple[str, str]:
        """Extract command and arguments from directive"""
        match = re.search(DIRECTIVE_PATTERN, self.directive_raw)
        if match:
            command = match.group(1)
            args = match.group(2) if match.group(2) else ""
            return command, args
        return "", ""
    
    def __repr__(self):
        return f"<rDNAEntry {self.name}>"

# ==========================================
# LEXICAL ANALYZER
# ==========================================

class Lexer:
    """DNA-Lang lexical analyzer"""
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        
    def current_char(self) -> Optional[str]:
        """Get current character"""
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]
    
    def peek_char(self, offset: int = 1) -> Optional[str]:
        """Peek ahead at character"""
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self):
        """Move to next character"""
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
    
    def skip_whitespace(self):
        """Skip whitespace except newlines"""
        while self.current_char() in ' \t\r':
            self.advance()
    
    def skip_comment(self):
        """Skip single-line comment"""
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()
    
    def read_number(self) -> Token:
        """Read numeric literal"""
        start_line, start_col = self.line, self.column
        num_str = ""
        has_dot = False
        
        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            if self.current_char() == '.':
                if has_dot:
                    break
                has_dot = True
            num_str += self.current_char()
            self.advance()
        
        value = float(num_str) if has_dot else int(num_str)
        return Token(TokenType.NUMBER, value, start_line, start_col)
    
    def read_identifier(self) -> Token:
        """Read identifier or keyword"""
        start_line, start_col = self.line, self.column
        ident = ""
        
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            ident += self.current_char()
            self.advance()
        
        # Check if it's a keyword
        if ident in KEYWORDS:
            return Token(TokenType.KEYWORD, ident, start_line, start_col)
        
        # Check if it's a quantum operator
        if ident in QUANTUM_OPS:
            return Token(TokenType.QUANTUM_OP, ident, start_line, start_col)
        
        return Token(TokenType.IDENTIFIER, ident, start_line, start_col)
    
    def read_string(self) -> Token:
        """Read string literal"""
        start_line, start_col = self.line, self.column
        quote_char = self.current_char()
        self.advance()  # Skip opening quote
        
        string = ""
        while self.current_char() and self.current_char() != quote_char:
            if self.current_char() == '\\':
                self.advance()
                if self.current_char() in 'nrt':
                    escape_map = {'n': '\n', 'r': '\r', 't': '\t'}
                    string += escape_map.get(self.current_char(), self.current_char())
                    self.advance()
            else:
                string += self.current_char()
                self.advance()
        
        self.advance()  # Skip closing quote
        return Token(TokenType.STRING, string, start_line, start_col)
    
    def tokenize(self) -> List[Token]:
        """Tokenize entire source"""
        while self.pos < len(self.source):
            self.skip_whitespace()
            
            if not self.current_char():
                break
            
            # Skip comments
            if self.current_char() == '#':
                self.skip_comment()
                continue
            
            # Newline
            if self.current_char() == '\n':
                token = Token(TokenType.NEWLINE, '\n', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue
            
            # Numbers
            if self.current_char().isdigit():
                self.tokens.append(self.read_number())
                continue
            
            # Identifiers and keywords
            if self.current_char().isalpha() or self.current_char() == '_':
                self.tokens.append(self.read_identifier())
                continue
            
            # Strings
            if self.current_char() in '"\'':
                self.tokens.append(self.read_string())
                continue
            
            # Two-character operators
            if self.current_char() == '=' and self.peek_char() == '=':
                token = Token(TokenType.EQ, '==', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '!' and self.peek_char() == '=':
                token = Token(TokenType.NE, '!=', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '<' and self.peek_char() == '=':
                token = Token(TokenType.LE, '<=', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '>' and self.peek_char() == '=':
                token = Token(TokenType.GE, '>=', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '-' and self.peek_char() == '>':
                token = Token(TokenType.ARROW, '->', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            if self.current_char() == '*' and self.peek_char() == '*':
                token = Token(TokenType.POWER, '**', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            # Single-character tokens
            char_tokens = {
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.MULTIPLY,
                '/': TokenType.DIVIDE,
                '%': TokenType.MODULO,
                '=': TokenType.ASSIGN,
                '<': TokenType.LT,
                '>': TokenType.GT,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                ',': TokenType.COMMA,
                ';': TokenType.SEMICOLON,
                ':': TokenType.COLON,
                '.': TokenType.DOT
            }
            
            if self.current_char() in char_tokens:
                token_type = char_tokens[self.current_char()]
                token = Token(token_type, self.current_char(), self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue
            
            # Unknown character
            raise SyntaxError(f"Unknown character '{self.current_char()}' at {self.line}:{self.column}")
        
        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens

# ==========================================
# SYNTAX PARSER
# ==========================================

class Parser:
    """DNA-Lang syntax parser"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        
    def current_token(self) -> Token:
        """Get current token"""
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[self.pos]
    
    def peek_token(self, offset: int = 1) -> Token:
        """Peek at future token"""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]
    
    def advance(self):
        """Move to next token"""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
    
    def expect(self, token_type: TokenType) -> Token:
        """Expect specific token type"""
        token = self.current_token()
        if token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type.value}, got {token.type.value} "
                f"at {token.line}:{token.column}"
            )
        self.advance()
        return token
    
    def skip_newlines(self):
        """Skip newline tokens"""
        while self.current_token().type == TokenType.NEWLINE:
            self.advance()
    
    def parse_program(self) -> List[OrganismNode]:
        """Parse complete DNA-Lang program"""
        organisms = []
        
        while self.current_token().type != TokenType.EOF:
            self.skip_newlines()
            if self.current_token().type == TokenType.EOF:
                break
                
            if self.current_token().type == TokenType.KEYWORD and \
               self.current_token().value == 'organism':
                organisms.append(self.parse_organism())
            else:
                self.advance()
        
        return organisms
    
    def parse_organism(self) -> OrganismNode:
        """Parse organism definition"""
        token = self.expect(TokenType.KEYWORD)  # 'organism'
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.LBRACE)
        
        organism = OrganismNode(
            node_type='Organism',
            line=token.line,
            column=token.column,
            name=name_token.value
        )
        
        self.skip_newlines()
        
        # Parse organism body
        while self.current_token().type != TokenType.RBRACE:
            self.skip_newlines()
            
            if self.current_token().type == TokenType.KEYWORD:
                keyword = self.current_token().value
                
                if keyword == 'genome':
                    organism.genome = self.parse_genome()
                elif keyword == 'quantum_state':
                    organism.quantum_state = self.parse_quantum_state()
                elif keyword == 'control':
                    organism.control = self.parse_control()
                elif keyword == 'fitness':
                    organism.fitness = self.parse_fitness()
                else:
                    self.advance()
            else:
                self.advance()
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        return organism
    
    def parse_genome(self) -> GenomeNode:
        """Parse genome block"""
        token = self.expect(TokenType.KEYWORD)  # 'genome'
        self.expect(TokenType.LBRACE)
        
        genome = GenomeNode(
            node_type='Genome',
            line=token.line,
            column=token.column
        )
        
        self.skip_newlines()
        
        while self.current_token().type != TokenType.RBRACE:
            self.skip_newlines()
            
            if self.current_token().type == TokenType.KEYWORD and \
               self.current_token().value == 'gene':
                genome.genes.append(self.parse_gene())
            else:
                self.advance()
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        return genome
    
    def parse_gene(self) -> GeneNode:
        """Parse gene definition"""
        token = self.expect(TokenType.KEYWORD)  # 'gene'
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ASSIGN)
        
        # Parse encoding expression — 'encode' is a keyword but used as a function here
        encoding_token = self.current_token()
        if encoding_token.value not in ('encode', 'superpose', 'entangle'):
            raise SyntaxError(
                f"Expected encoding function, got '{encoding_token.value}' "
                f"at {encoding_token.line}:{encoding_token.column}"
            )
        self.advance()
        self.expect(TokenType.LPAREN)
        
        # Parse data
        data_token = self.current_token()
        self.advance()
        
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.ARROW)
        
        # Parse target qubits
        target_qubits = []
        self.expect(TokenType.IDENTIFIER)  # 'q'
        self.expect(TokenType.LBRACKET)
        
        while self.current_token().type != TokenType.RBRACKET:
            if self.current_token().type == TokenType.NUMBER:
                target_qubits.append(int(self.current_token().value))
                self.advance()
            
            if self.current_token().type == TokenType.COMMA:
                self.advance()
        
        self.expect(TokenType.RBRACKET)
        
        return GeneNode(
            node_type='Gene',
            line=token.line,
            column=token.column,
            name=name_token.value,
            encoding=str(data_token.value),
            target_qubits=target_qubits
        )
    
    def parse_quantum_state(self) -> QuantumStateNode:
        """Parse quantum_state block"""
        token = self.expect(TokenType.KEYWORD)  # 'quantum_state'
        self.expect(TokenType.LBRACE)
        
        quantum_state = QuantumStateNode(
            node_type='QuantumState',
            line=token.line,
            column=token.column
        )
        
        self.skip_newlines()
        
        while self.current_token().type != TokenType.RBRACE:
            self.skip_newlines()
            
            if self.current_token().type == TokenType.QUANTUM_OP:
                quantum_state.operations.append(self.parse_quantum_op())
            else:
                self.advance()
            
            self.skip_newlines()
        
        self.expect(TokenType.RBRACE)
        return quantum_state
    
    def parse_quantum_op(self) -> QuantumOpNode:
        """Parse quantum operation"""
        op_token = self.expect(TokenType.QUANTUM_OP)
        self.expect(TokenType.LPAREN)
        
        # Parse qubits
        qubits = []
        params = []
        
        while self.current_token().type != TokenType.RPAREN:
            if self.current_token().type == TokenType.NUMBER:
                value = self.current_token().value
                if isinstance(value, int):
                    qubits.append(value)
                else:
                    params.append(value)
                self.advance()
            elif self.current_token().type == TokenType.IDENTIFIER:
                # Handle q[n] notation
                self.advance()
                if self.current_token().type == TokenType.LBRACKET:
                    self.advance()
                    qubits.append(int(self.current_token().value))
                    self.advance()
                    self.expect(TokenType.RBRACKET)
            
            if self.current_token().type == TokenType.COMMA:
                self.advance()
        
        self.expect(TokenType.RPAREN)
        
        return QuantumOpNode(
            node_type='QuantumOp',
            line=op_token.line,
            column=op_token.column,
            operation=QUANTUM_OPS[op_token.value],
            qubits=qubits,
            params=params
        )
    
    def parse_control(self) -> ControlNode:
        """Parse control block"""
        token = self.expect(TokenType.KEYWORD)  # 'control'
        self.expect(TokenType.LBRACE)
        
        control = ControlNode(
            node_type='Control',
            line=token.line,
            column=token.column
        )
        
        # Simplified: just skip control block for now
        brace_count = 1
        while brace_count > 0:
            if self.current_token().type == TokenType.LBRACE:
                brace_count += 1
            elif self.current_token().type == TokenType.RBRACE:
                brace_count -= 1
            self.advance()
        
        return control
    
    def parse_fitness(self) -> ExpressionNode:
        """Parse fitness expression"""
        self.expect(TokenType.KEYWORD)  # 'fitness'
        self.expect(TokenType.ASSIGN)
        
        # Simplified: just parse identifier or number
        token = self.current_token()
        self.advance()
        
        return ExpressionNode(
            node_type='Expression',
            line=token.line,
            column=token.column,
            operator='value',
            operands=[token.value]
        )

# ==========================================
# CANON PARSER
# ==========================================

def parse_canon_block(canon_text: str) -> List[rDNAEntry]:
    """
    Parse AURA Prompt Canon text into structured entries

    Args:
        canon_text: Complete AURA rDNA Prompt Canon text

    Returns:
        List of parsed rDNAEntry objects
    """
    entries = []

    # Split on ### Canon headers to get one block per canon
    blocks = re.split(r'(?=### Canon\s)', canon_text)

    for block in blocks:
        if not block.strip():
            continue

        # Match header: ### Canon IX — SOME-NAME
        header = re.search(r'Canon\s+([IVXLCDM]+)\s*[—–-]\s*([A-Z_-]+)', block)
        if not header:
            continue
        canon_name = f"{header.group(1)}_{header.group(2)}"

        # Extract structured fields
        purpose = ""
        directive = ""
        evolution = ""
        coherence = ""

        purpose_m = re.search(
            r'\*\*Purpose\*\*\s*:\s*(.+?)(?:\n\*\*|\Z)', block, re.DOTALL
        )
        if purpose_m:
            purpose = purpose_m.group(1).strip()

        directive_m = re.search(
            r'```\n(.*?)```', block, re.DOTALL
        )
        if directive_m:
            directive = directive_m.group(1).strip()

        evolution_m = re.search(
            r'\*\*Evolution Vector\*\*\s*:\s*(.+?)(?:\n\*\*|\Z)', block, re.DOTALL
        )
        if evolution_m:
            evolution = evolution_m.group(1).strip()

        coherence_m = re.search(
            r'\*\*Coherence Target\*\*\s*:\s*(.+?)(?:\n\*\*|\Z)', block, re.DOTALL
        )
        if coherence_m:
            coherence = coherence_m.group(1).strip()

        entries.append(rDNAEntry(
            name=canon_name,
            purpose=purpose,
            directive_raw=directive,
            evolution_vector=evolution,
            coherence_target=coherence,
        ))

    return entries

# ==========================================
# MAIN INTERFACE
# ==========================================

def parse_dna_lang(source: str) -> List[OrganismNode]:
    """
    Parse DNA-Lang source code
    
    Args:
        source: DNA-Lang source code
        
    Returns:
        List of parsed organism AST nodes
    """
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens)
    organisms = parser.parse_program()
    
    return organisms

def parse_canon(canon_text: str) -> List[rDNAEntry]:
    """
    Parse AURA Prompt Canon
    
    Args:
        canon_text: Complete canon text
        
    Returns:
        List of canon entries
    """
    return parse_canon_block(canon_text)

if __name__ == "__main__":
    # Test with simple DNA-Lang program
    test_source = """
organism test_org {
    genome {
        gene g1 = encode(data) -> q[0];
    }
    
    quantum_state {
        helix(q[0]);
        bond(q[0], q[1]);
        measure(q[0]);
    }
    
    fitness = lambda;
}
"""
    
    print("=== DNA-Lang Parser Test ===")
    organisms = parse_dna_lang(test_source)
    print(f"Parsed {len(organisms)} organism(s)")
    
    for org in organisms:
        print(f"\nOrganism: {org.name}")
        if org.genome:
            print(f"  Genes: {len(org.genome.genes)}")
        if org.quantum_state:
            print(f"  Quantum Operations: {len(org.quantum_state.operations)}")
