from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


class Severity(Enum):
    NOTE = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass
class Diagnostic:
    severity: Severity
    message: str
    line: int = 0
    col: int = 0
    file: str = "<source>"

    def format(self) -> str:
        loc = f"{self.file}:{self.line}:{self.col}" if self.line else self.file
        return f"{self.severity.name.lower()}: {loc}: {self.message}"


class DiagnosticEngine:
    def __init__(self, file: str = "<source>", warnings_as_errors: bool = False):
        self.file = file
        self.warnings_as_errors = warnings_as_errors
        self.items: List[Diagnostic] = []

    def error(self, message: str, line: int = 0, col: int = 0) -> None:
        self.items.append(Diagnostic(Severity.ERROR, message, line, col, self.file))

    def warning(self, message: str, line: int = 0, col: int = 0) -> None:
        self.items.append(Diagnostic(Severity.WARNING, message, line, col, self.file))

    def note(self, message: str, line: int = 0, col: int = 0) -> None:
        self.items.append(Diagnostic(Severity.NOTE, message, line, col, self.file))

    def has_errors(self) -> bool:
        for d in self.items:
            if d.severity == Severity.ERROR:
                return True
            if d.severity == Severity.WARNING and self.warnings_as_errors:
                return True
        return False

    def format_all(self) -> str:
        return "\n".join(d.format() for d in self.items)

    def raise_if_errors(self) -> None:
        if self.has_errors():
            raise CompileFailure(self.format_all())


class CompileFailure(Exception):
    pass