from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .codegen import IRCodeGen
from .diagnostics import CompileFailure, DiagnosticEngine
from .lexer import Lexer, LexError
from .lower import Lowerer
from .optimize import Optimizer
from .parser import Parser, ParseError
from .preprocessor import Preprocessor
from .sema import SemanticAnalyzer


class CompileError(Exception):
    pass


@dataclass
class CompileOptions:
    opt_level: int = 1
    include_paths: List[Path] = field(default_factory=list)
    defines: dict[str, str] = field(default_factory=dict)
    warnings_as_errors: bool = False
    dump_tokens: bool = False
    dump_ast: bool = False
    dump_ir: bool = False
    skip_sema: bool = False


@dataclass
class CompileResult:
    c_code: str
    diagnostics: DiagnosticEngine
    tokens: Optional[list] = None
    ast: Optional[object] = None
    ir: Optional[object] = None


def compile_source(source: str, options: Optional[CompileOptions] = None, file: str = "<source>") -> str:
    return compile_source_full(source, options, file).c_code


def compile_source_full(
    source: str,
    options: Optional[CompileOptions] = None,
    file: str = "<source>",
) -> CompileResult:
    opts = options or CompileOptions()
    diags = DiagnosticEngine(file, opts.warnings_as_errors)

    try:
        pp = Preprocessor(opts.include_paths)
        for k, v in opts.defines.items():
            pp.add_define(k, v)
        expanded = pp.process(source, Path(file) if file != "<source>" else None)

        tokens = Lexer(expanded).tokenize()
        if opts.dump_tokens:
            for t in tokens:
                diags.note(repr(t))

        program = Parser(tokens).parse()
        program.source_file = file

        if not opts.skip_sema:
            SemanticAnalyzer(diags).analyze(program)

        if diags.has_errors():
            raise CompileFailure(diags.format_all())

        module = Lowerer().lower(program, opts.opt_level)
        module = Optimizer(opts.opt_level).run(module)
        c_code = IRCodeGen().generate(module)

        return CompileResult(c_code, diags, tokens, program, module)

    except LexError as exc:
        raise CompileError(str(exc)) from exc
    except ParseError as exc:
        raise CompileError(str(exc)) from exc
    except CompileFailure as exc:
        raise CompileError(str(exc)) from exc


def compile_file(path: str | Path, options: Optional[CompileOptions] = None) -> str:
    return compile_file_full(path, options).c_code


def compile_file_full(path: str | Path, options: Optional[CompileOptions] = None) -> CompileResult:
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    return compile_source_full(source, options, str(p.resolve()))