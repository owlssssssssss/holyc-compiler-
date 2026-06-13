from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parent.parent
TOOLCHAIN_DIR = ROOT / "toolchain"
TCC_DIR = TOOLCHAIN_DIR / "tcc"


def _tcc_root() -> Path:
    nested = TCC_DIR / "tcc"
    return nested if (nested / "tcc.exe").is_file() else TCC_DIR


def _tcc_exe() -> Path:
    return _tcc_root() / "tcc.exe"


TCC_BASE = "https://download-mirror.savannah.gnu.org/releases/tinycc"
TCC_URL = f"{TCC_BASE}/tcc-0.9.27-win64-bin.zip"
WINAPI_URL = f"{TCC_BASE}/winapi-full-for-0.9.27.zip"
TCC_ZIP = TOOLCHAIN_DIR / "tcc-win64-bin.zip"
WINAPI_ZIP = TOOLCHAIN_DIR / "winapi.zip"


def have_bundled_tcc() -> bool:
    return _tcc_exe().is_file()


def ensure_toolchain(verbose: bool = True) -> Path:
    """Download TinyCC if missing. Returns path to tcc.exe."""
    if have_bundled_tcc():
        return _tcc_exe()

    TOOLCHAIN_DIR.mkdir(parents=True, exist_ok=True)
    if verbose:
        print("Setting up HolyC toolchain (one-time download)...", file=sys.stderr)

    try:
        urlretrieve(TCC_URL, TCC_ZIP)
        urlretrieve(WINAPI_URL, WINAPI_ZIP)
    except Exception as exc:
        raise RuntimeError(
            f"Could not download TinyCC: {exc}\n"
            "Run: powershell -File install.ps1\n"
            "Or install gcc/MSVC and ensure it is on PATH."
        ) from exc

    TCC_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TCC_ZIP, "r") as zf:
        zf.extractall(TCC_DIR)
    with zipfile.ZipFile(WINAPI_ZIP, "r") as zf:
        zf.extractall(TCC_DIR)

    TCC_ZIP.unlink(missing_ok=True)
    WINAPI_ZIP.unlink(missing_ok=True)

    exe = _tcc_exe()
    if not exe.is_file():
        raise RuntimeError("TinyCC download succeeded but tcc.exe was not found.")

    if verbose:
        print(f"Toolchain ready: {exe}", file=sys.stderr)
    return exe


def find_c_compiler(prefer_bundled: bool = True) -> tuple[Path | str, str]:
    """
    Find a C compiler. Returns (executable, kind).
    kind is one of: tcc, gcc, clang, cl
    """
    if prefer_bundled:
        try:
            if have_bundled_tcc():
                return _tcc_exe(), "tcc"
        except Exception:
            pass

    for name in ("tcc", "gcc", "clang", "cc"):
        found = shutil.which(name)
        if found:
            return Path(found), name

    cl = shutil.which("cl")
    if cl:
        return Path(cl), "cl"

    if prefer_bundled:
        return ensure_toolchain(), "tcc"

    raise RuntimeError("No C compiler found. Run install.ps1 first.")


def compile_c_to_exe(
    c_path: Path,
    exe_path: Path,
    *,
    opt: int = 1,
    cc: Path | str | None = None,
    quiet: bool = False,
) -> None:
    compiler, kind = (cc, "custom") if cc else find_c_compiler()
    compiler = Path(compiler) if isinstance(compiler, str) and os.path.isabs(compiler) else compiler
    if isinstance(compiler, str):
        compiler = Path(compiler)

    exe_path.parent.mkdir(parents=True, exist_ok=True)
    c_path = c_path.resolve()
    exe_path = exe_path.resolve()

    if kind == "tcc" or Path(compiler).name.lower() == "tcc.exe":
        tcc_root = Path(compiler).parent
        cmd = [str(compiler), "-B", str(tcc_root), str(c_path), "-o", str(exe_path)]
    elif kind in ("gcc", "clang", "cc"):
        flags = ["-std=c99", "-Wall"]
        if opt >= 2:
            flags.append(f"-O{min(opt, 3)}")
        cmd = [str(compiler), *flags, str(c_path), "-o", str(exe_path)]
    elif kind == "cl":
        cmd = [str(compiler), str(c_path), f"/Fe:{exe_path}"]
    else:
        cmd = [str(compiler), str(c_path), "-o", str(exe_path)]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=c_path.parent)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        if not err:
            err = f"exit code {result.returncode} (no output)\ncmd: {' '.join(cmd)}"
        raise RuntimeError(f"C compiler failed ({compiler}):\n{err}")


def run_exe(exe_path: Path, args: list[str] | None = None) -> int:
    cmd = [str(exe_path), *(args or [])]
    return subprocess.run(cmd, cwd=exe_path.parent).returncode