from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class TokenKind(Enum):
    # Types
    I8 = auto()
    U8 = auto()
    I16 = auto()
    U16 = auto()
    I32 = auto()
    U32 = auto()
    I64 = auto()
    U64 = auto()
    F64 = auto()
    BOOL = auto()
    U0 = auto()
    REG = auto()

    # Keywords
    CLASS = auto()
    UNION = auto()
    PUBLIC = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    DO = auto()
    FOR = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    GOTO = auto()
    ASM = auto()
    SIZEOF = auto()

    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    CHAR = auto()
    IDENT = auto()

    # Operators / punctuation
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    AND = auto()
    OR = auto()
    BANG = auto()
    PIPE = auto()
    CARET = auto()
    TILDE = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    PLUSPLUS = auto()
    MINUSMINUS = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    STAREQ = auto()
    SLASHEQ = auto()
    PERCENTEQ = auto()
    AMPERSAND = auto()
    ARROW = auto()
    DOT = auto()
    DOTDOT = auto()
    QMARK = auto()
    COLON = auto()
    COMMA = auto()
    SEMI = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    DOLLAR = auto()

    EOF = auto()


HOLYC_TYPES = {
    "I8", "U8", "I16", "U16", "I32", "U32", "I64", "U64", "F64", "Bool", "U0",
    "Reg", "RegI8", "RegU8", "RegI16", "RegU16", "RegI32", "RegU32",
    "RegI64", "RegU64", "RegF64",
}

KEYWORDS = {
    "class": TokenKind.CLASS,
    "union": TokenKind.UNION,
    "public": TokenKind.PUBLIC,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "do": TokenKind.DO,
    "for": TokenKind.FOR,
    "return": TokenKind.RETURN,
    "break": TokenKind.BREAK,
    "continue": TokenKind.CONTINUE,
    "TRUE": TokenKind.TRUE,
    "FALSE": TokenKind.FALSE,
    "NULL": TokenKind.NULL,
    "switch": TokenKind.SWITCH,
    "case": TokenKind.CASE,
    "default": TokenKind.DEFAULT,
    "goto": TokenKind.GOTO,
    "asm": TokenKind.ASM,
    "sizeof": TokenKind.SIZEOF,
    "I8": TokenKind.I8,
    "U8": TokenKind.U8,
    "I16": TokenKind.I16,
    "U16": TokenKind.U16,
    "I32": TokenKind.I32,
    "U32": TokenKind.U32,
    "I64": TokenKind.I64,
    "U64": TokenKind.U64,
    "F64": TokenKind.F64,
    "Bool": TokenKind.BOOL,
    "U0": TokenKind.U0,
    "Reg": TokenKind.REG,
    "RegI8": TokenKind.REG,
    "RegU8": TokenKind.REG,
    "RegI16": TokenKind.REG,
    "RegU16": TokenKind.REG,
    "RegI32": TokenKind.REG,
    "RegU32": TokenKind.REG,
    "RegI64": TokenKind.REG,
    "RegU64": TokenKind.REG,
    "RegF64": TokenKind.REG,
}


@dataclass
class Token:
    kind: TokenKind
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.value!r}, {self.line}:{self.col})"