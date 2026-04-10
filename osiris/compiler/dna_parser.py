"""
DNA-Lang Parser — Lexer and AST generation for quantum consciousness organisms.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

CANON_PREFIX = "AURA::"
KEYWORDS = {
    "organism", "genome", "gene", "quantum_state", "control", "fitness",
    "encode", "superpose", "entangle", "measure", "evolve", "mutate",
    "if", "while", "for", "return", "lambda", "phi",
}
QUANTUM_OPS = {
    "helix": "h", "bond": "cx", "evolve": "u3", "measure": "measure",
    "entangle": "bell", "teleport": "teleport", "phase": "rz",
    "rotate_x": "rx", "rotate_y": "ry", "rotate_z": "rz",
    "swap": "swap", "toffoli": "ccx",
}


class TokenType(Enum):
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    KEYWORD = "KEYWORD"
    QUANTUM_OP = "QUANTUM_OP"
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    EQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    ASSIGN = "="
    ARROW = "->"
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
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    CANON = "CANON"


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.value}, {self.value!r}, {self.line}:{self.column})"


@dataclass
class ASTNode:
    node_type: str
    line: int
    column: int


@dataclass
class OrganismNode(ASTNode):
    name: str = ""
    genome: Optional["GenomeNode"] = None
    quantum_state: Optional["QuantumStateNode"] = None


@dataclass
class GenomeNode(ASTNode):
    genes: List["GeneNode"] = field(default_factory=list)


@dataclass
class GeneNode(ASTNode):
    name: str = ""
    encoding: str = ""
    target_qubits: List[int] = field(default_factory=list)


@dataclass
class QuantumStateNode(ASTNode):
    operations: List["QuantumOpNode"] = field(default_factory=list)


@dataclass
class QuantumOpNode(ASTNode):
    operation: str = ""
    qubits: List[int] = field(default_factory=list)
    params: List[float] = field(default_factory=list)


@dataclass
class rDNAEntry:
    name: str
    purpose: str
    directive_raw: str
    evolution_vector: str
    coherence_target: str

    def get_directive_syntax(self) -> Tuple[str, str]:
        match = re.search(r"(AURA::[A-Z-]+)(\(.*\))?", self.directive_raw)
        if match:
            return match.group(1), match.group(2) or ""
        return "", ""


class Lexer:
    """DNA-Lang lexical analyzer."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in " \t\r":
                self._advance()
            elif ch == "#":
                self._skip_comment()
            elif ch == "\n":
                self.tokens.append(Token(TokenType.NEWLINE, "\\n", self.line, self.column))
                self._advance()
            elif ch.isdigit() or (ch == "." and self._peek_is_digit()):
                self.tokens.append(self._read_number())
            elif ch.isalpha() or ch == "_":
                self.tokens.append(self._read_identifier())
            elif ch == '"' or ch == "'":
                self.tokens.append(self._read_string(ch))
            else:
                self.tokens.append(self._read_operator())
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens

    def _advance(self):
        if self.pos < len(self.source):
            if self.source[self.pos] == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def _peek_is_digit(self) -> bool:
        return self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit()

    def _skip_comment(self):
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            self._advance()

    def _read_number(self) -> Token:
        sl, sc = self.line, self.column
        n = ""
        dot = False
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == "."):
            if self.source[self.pos] == ".":
                if dot:
                    break
                dot = True
            n += self.source[self.pos]
            self._advance()
        return Token(TokenType.NUMBER, float(n) if dot else int(n), sl, sc)

    def _read_identifier(self) -> Token:
        sl, sc = self.line, self.column
        ident = ""
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
            ident += self.source[self.pos]
            self._advance()
        if ident in KEYWORDS:
            return Token(TokenType.KEYWORD, ident, sl, sc)
        if ident in QUANTUM_OPS:
            return Token(TokenType.QUANTUM_OP, ident, sl, sc)
        return Token(TokenType.IDENTIFIER, ident, sl, sc)

    def _read_string(self, quote: str) -> Token:
        sl, sc = self.line, self.column
        self._advance()
        s = ""
        while self.pos < len(self.source) and self.source[self.pos] != quote:
            s += self.source[self.pos]
            self._advance()
        if self.pos < len(self.source):
            self._advance()
        return Token(TokenType.STRING, s, sl, sc)

    def _read_operator(self) -> Token:
        ops = {
            "(": TokenType.LPAREN, ")": TokenType.RPAREN,
            "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
            ",": TokenType.COMMA, ";": TokenType.SEMICOLON,
            ":": TokenType.COLON, ".": TokenType.DOT,
            "+": TokenType.PLUS, "-": TokenType.MINUS,
            "*": TokenType.MULTIPLY, "/": TokenType.DIVIDE,
            "<": TokenType.LT, ">": TokenType.GT,
            "=": TokenType.ASSIGN,
        }
        ch = self.source[self.pos]
        sl, sc = self.line, self.column
        self._advance()
        return Token(ops.get(ch, TokenType.IDENTIFIER), ch, sl, sc)


class Parser:
    """DNA-Lang recursive descent parser."""

    def __init__(self, tokens: List[Token]):
        self.tokens = [t for t in tokens if t.type != TokenType.NEWLINE]
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def expect(self, ttype: TokenType) -> Token:
        t = self.current()
        if t.type != ttype:
            raise SyntaxError(f"Expected {ttype}, got {t.type} at {t.line}:{t.column}")
        self.pos += 1
        return t

    def parse(self) -> List[ASTNode]:
        nodes: List[ASTNode] = []
        while self.current().type != TokenType.EOF:
            t = self.current()
            if t.type == TokenType.KEYWORD and t.value == "organism":
                nodes.append(self._parse_organism())
            else:
                self.pos += 1
        return nodes

    def _parse_organism(self) -> OrganismNode:
        t = self.expect(TokenType.KEYWORD)
        name_t = self.expect(TokenType.IDENTIFIER)
        node = OrganismNode(node_type="organism", line=t.line, column=t.column, name=name_t.value)
        if self.current().type == TokenType.LBRACE:
            self.pos += 1
            while self.current().type != TokenType.RBRACE and self.current().type != TokenType.EOF:
                self.pos += 1
            if self.current().type == TokenType.RBRACE:
                self.pos += 1
        return node
