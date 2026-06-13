from __future__ import annotations

from typing import List

from .tokens import KEYWORDS, Token, TokenKind


class LexError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"Lexer error at {line}:{col}: {message}")
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.kind == TokenKind.EOF:
                break
        return tokens

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.source[i] if i < len(self.source) else ""

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _skip_whitespace(self) -> None:
        while self._peek() and self._peek() in " \t\r\n":
            self._advance()

    def _skip_comment(self) -> bool:
        if self._peek() == "/" and self._peek(1) == "/":
            while self._peek() and self._peek() != "\n":
                self._advance()
            return True
        if self._peek() == "/" and self._peek(1) == "*":
            self._advance()
            self._advance()
            while self._peek():
                if self._peek() == "*" and self._peek(1) == "/":
                    self._advance()
                    self._advance()
                    return True
                self._advance()
            raise LexError("Unterminated block comment", self.line, self.col)
        return False

    def _make(self, kind: TokenKind, value: str, line: int, col: int) -> Token:
        return Token(kind, value, line, col)

    def _next_token(self) -> Token:
        while True:
            self._skip_whitespace()
            if self._skip_comment():
                continue
            break

        line, col = self.line, self.col
        ch = self._peek()

        if not ch:
            return self._make(TokenKind.EOF, "", line, col)

        if ch.isalpha() or ch == "_":
            return self._read_ident(line, col)

        if ch.isdigit():
            return self._read_number(line, col)

        if ch == '"':
            return self._read_string(line, col)

        if ch == "'":
            return self._read_char(line, col)

        two = ch + self._peek(1)
        three = two + self._peek(2)

        multi = {
            "==": TokenKind.EQEQ,
            "!=": TokenKind.NEQ,
            "<=": TokenKind.LTE,
            ">=": TokenKind.GTE,
            "<<": TokenKind.LSHIFT,
            ">>": TokenKind.RSHIFT,
            "++": TokenKind.PLUSPLUS,
            "--": TokenKind.MINUSMINUS,
            "+=": TokenKind.PLUSEQ,
            "-=": TokenKind.MINUSEQ,
            "*=": TokenKind.STAREQ,
            "/=": TokenKind.SLASHEQ,
            "%=": TokenKind.PERCENTEQ,
            "->": TokenKind.ARROW,
            "&&": TokenKind.AND,
            "||": TokenKind.OR,
            "..": TokenKind.DOTDOT,
        }
        if three in multi:
            self._advance()
            self._advance()
            self._advance()
            return self._make(multi[three], three, line, col)
        if two in multi:
            self._advance()
            self._advance()
            return self._make(multi[two], two, line, col)

        singles = {
            "+": TokenKind.PLUS,
            "-": TokenKind.MINUS,
            "*": TokenKind.STAR,
            "/": TokenKind.SLASH,
            "%": TokenKind.PERCENT,
            "=": TokenKind.EQ,
            "<": TokenKind.LT,
            ">": TokenKind.GT,
            "!": TokenKind.BANG,
            "&": TokenKind.AMPERSAND,
            "|": TokenKind.PIPE,
            "^": TokenKind.CARET,
            "~": TokenKind.TILDE,
            ".": TokenKind.DOT,
            ",": TokenKind.COMMA,
            ";": TokenKind.SEMI,
            ":": TokenKind.COLON,
            "?": TokenKind.QMARK,
            "(": TokenKind.LPAREN,
            ")": TokenKind.RPAREN,
            "{": TokenKind.LBRACE,
            "}": TokenKind.RBRACE,
            "[": TokenKind.LBRACKET,
            "]": TokenKind.RBRACKET,
            "$": TokenKind.DOLLAR,
        }
        if ch in singles:
            self._advance()
            return self._make(singles[ch], ch, line, col)

        raise LexError(f"Unexpected character {ch!r}", line, col)

    def _read_ident(self, line: int, col: int) -> Token:
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.source[start:self.pos]
        kind = KEYWORDS.get(text, TokenKind.IDENT)
        return self._make(kind, text, line, col)

    def _read_number(self, line: int, col: int) -> Token:
        start = self.pos
        is_float = False
        if self._peek() == "0" and self._peek(1) in "xX":
            self._advance()
            self._advance()
            while self._peek().isalnum():
                self._advance()
            return self._make(TokenKind.INT, self.source[start:self.pos], line, col)
        if self._peek() == "0" and self._peek(1) in "bB":
            self._advance()
            self._advance()
            while self._peek() in "01":
                self._advance()
            bits = self.source[start + 2 : self.pos]
            return self._make(TokenKind.INT, str(int(bits or "0", 2)), line, col)

        while self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit():
                self._advance()

        text = self.source[start:self.pos]
        return self._make(TokenKind.FLOAT if is_float else TokenKind.INT, text, line, col)

    def _read_string(self, line: int, col: int) -> Token:
        self._advance()  # opening quote
        chars: list[str] = []
        while self._peek() and self._peek() != '"':
            if self._peek() == "\\":
                self._advance()
                esc = self._peek()
                mapping = {
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    "\\": "\\",
                    '"': '"',
                    "'": "'",
                    "0": "\0",
                }
                if esc not in mapping:
                    raise LexError(f"Invalid escape \\{esc}", self.line, self.col)
                chars.append(mapping[esc])
                self._advance()
            else:
                chars.append(self._advance())
        if not self._peek():
            raise LexError("Unterminated string", line, col)
        self._advance()  # closing quote
        return self._make(TokenKind.STRING, "".join(chars), line, col)

    def _read_char(self, line: int, col: int) -> Token:
        self._advance()
        if self._peek() == "\\":
            self._advance()
            esc = self._peek()
            mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", "0": "\0"}
            if esc not in mapping:
                raise LexError(f"Invalid escape \\{esc}", self.line, self.col)
            value = mapping[esc]
            self._advance()
        else:
            value = self._advance()
        if not self._peek() or self._peek() != "'":
            raise LexError("Unterminated character literal", line, col)
        self._advance()
        return self._make(TokenKind.CHAR, value, line, col)