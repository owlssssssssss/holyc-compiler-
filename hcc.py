#!/usr/bin/env python3
"""
HolyC compiler for Windows — write .HC, run with:  hcc myfile.HC

Default: compile to native .exe and run (like python script.py).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from holyc.compiler import CompileError, CompileOptions, compile_file_full
from holyc.native import build_holyc, default_exe_path, run_holyc
from holyc.toolchain import compile_c_to_exe, run_exe


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="hcc",
        description="HolyC compiler — compile and run .HC programs on Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hcc mytest.HC              compile + run (default)
  hcc mytest.HC --build      compile to mytest.exe only
  hcc mytest.HC --emit-c     show generated C source
  hcc mytest.HC -O2          optimize then run
  hcc mytest.HC -- arg1      pass args to your program
        """,
    )
    parser.add_argument("input", nargs="?", help="HolyC source file (.HC)")
    parser.add_argument("program_args", nargs=argparse.REMAINDER, help="Args passed to your program (after --)")
    parser.add_argument("-o", "--output", help="Output .exe or .c path")
    parser.add_argument("-O", "--opt", type=int, default=1, choices=[0, 1, 2, 3],
                        help="Optimization level")
    parser.add_argument("-I", "--include", action="append", default=[], dest="includes")
    parser.add_argument("-D", "--define", action="append", default=[])
    parser.add_argument("-Werror", action="store_true")
    parser.add_argument("--build", action="store_true",
                        help="Build .exe only (do not run)")
    parser.add_argument("--emit-c", action="store_true",
                        help="Print generated C and exit")
    parser.add_argument("--no-run", action="store_true",
                        help="Only write .c file, do not compile or run")
    parser.add_argument("--dump-ast", action="store_true")
    parser.add_argument("--dump-ir", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Less compiler chatter")
    args = parser.parse_args()

    if args.program_args and args.program_args[0] == "--":
        args.program_args = args.program_args[1:]

    if not args.input:
        parser.print_help()
        return 0

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"error: file not found: {input_path}", file=sys.stderr)
        return 1

    defines = {}
    for d in args.define:
        if "=" in d:
            k, v = d.split("=", 1)
            defines[k] = v
        else:
            defines[d] = "1"

    opts = CompileOptions(
        opt_level=args.opt,
        include_paths=[Path(p) for p in args.includes],
        defines=defines,
        warnings_as_errors=args.Werror,
    )

    try:
        result = compile_file_full(input_path, opts)
    except CompileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        for w in result.diagnostics.items:
            if w.severity.name == "WARNING":
                print(w.format(), file=sys.stderr)

    if args.dump_ast and result.ast:
        print(_dump_ast(result.ast), file=sys.stderr)
    if args.dump_ir and result.ir:
        print(_dump_ir(result.ir), file=sys.stderr)

    if args.emit_c:
        print(result.c_code)
        return 0

    if args.no_run:
        c_path = Path(args.output) if args.output else input_path.with_suffix(".c")
        c_path.write_text(result.c_code, encoding="utf-8")
        if not args.quiet:
            print(f"wrote {c_path}", file=sys.stderr)
        return 0

    # --build or default run
    exe_path = Path(args.output) if args.output and not str(args.output).endswith(".c") else None
    if args.output and str(args.output).endswith(".c"):
        Path(args.output).write_text(result.c_code, encoding="utf-8")
        if not args.quiet:
            print(f"wrote {args.output}", file=sys.stderr)
        if args.build:
            exe_path = default_exe_path(input_path) if not exe_path else exe_path
            compile_c_to_exe(Path(args.output), exe_path, opt=args.opt)
            if not args.quiet:
                print(f"built {exe_path}", file=sys.stderr)
            return 0

    try:
        if args.build:
            out = build_holyc(input_path, options=opts, exe_path=exe_path, quiet=args.quiet)
            if not args.quiet:
                print(f"built {out}", file=sys.stderr)
            return 0

        # Default: compile + run
        if not args.quiet:
            print(f"running {input_path.name} ...", file=sys.stderr)
        return run_holyc(
            input_path,
            options=opts,
            exe_path=exe_path,
            keep_c=True,
            program_args=args.program_args,
            quiet=args.quiet,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("Tip: run  powershell -File install.ps1  to set up the C compiler.", file=sys.stderr)
        return 1


def _dump_ast(program) -> str:
    items = [type(item).__name__ + ":" + getattr(item, "name", "?") for item in program.items]
    return json.dumps({"file": program.source_file, "items": items}, indent=2)


def _dump_ir(module) -> str:
    fns = []
    for fn in module.functions:
        blocks = [{
            "name": blk.name,
            "instrs": [{"op": i.op, "dest": i.dest, "args": i.args, "label": i.label} for i in blk.instrs],
        } for blk in fn.blocks]
        fns.append({"name": fn.name, "blocks": blocks})
    return json.dumps({"opt": module.opt_level, "functions": fns}, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())