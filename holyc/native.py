from __future__ import annotations

import tempfile
from pathlib import Path

from .compiler import CompileOptions, compile_file_full
from .toolchain import compile_c_to_exe, run_exe


def default_exe_path(source: Path) -> Path:
    return source.with_suffix(".exe" if _is_windows() else "")


def _is_windows() -> bool:
    import sys
    return sys.platform == "win32"


def run_holyc(
    source: Path,
    *,
    options: CompileOptions | None = None,
    exe_path: Path | None = None,
    keep_c: bool = False,
    program_args: list[str] | None = None,
    quiet: bool = False,
) -> int:
    """Compile HolyC source to a native exe and run it. Returns program exit code."""
    opts = options or CompileOptions()
    result = compile_file_full(source, opts)

    c_out = source.with_suffix(".c") if keep_c else None

    with tempfile.TemporaryDirectory(prefix="hcc_", dir=source.parent) as tmp:
        if keep_c and c_out:
            c_path = c_out
            c_path.write_text(result.c_code, encoding="utf-8")
        else:
            c_path = Path(tmp) / (source.stem + ".c")
            c_path.write_text(result.c_code, encoding="utf-8")

        out = exe_path or default_exe_path(source)
        compile_c_to_exe(c_path, out, opt=opts.opt_level, quiet=quiet)
        return run_exe(out, program_args)


def build_holyc(
    source: Path,
    *,
    options: CompileOptions | None = None,
    exe_path: Path | None = None,
    keep_c: bool = True,
    quiet: bool = False,
) -> Path:
    """Compile HolyC to a native .exe next to the source file."""
    opts = options or CompileOptions()
    result = compile_file_full(source, opts)

    c_path = source.with_suffix(".c")
    if keep_c:
        c_path.write_text(result.c_code, encoding="utf-8")

    out = exe_path or default_exe_path(source)
    compile_c_to_exe(
        c_path if keep_c else _write_temp_c(result.c_code, source),
        out,
        opt=opts.opt_level,
        quiet=quiet,
    )
    return out


def _write_temp_c(code: str, source: Path) -> Path:
    import tempfile
    p = Path(tempfile.mkdtemp(dir=source.parent)) / (source.stem + ".c")
    p.write_text(code, encoding="utf-8")
    return p