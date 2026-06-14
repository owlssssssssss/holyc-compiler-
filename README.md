# HolyC Compiler (hcc)

A HolyC-flavored compiler for **Windows** that transpiles `.HC` source to C, then builds and runs native `.exe` files using a bundled [TinyCC](https://bellard.org/tcc/) toolchain.

Inspired by [TempleOS HolyC](https://templeos.org/), but this project targets everyday Windows development: write HolyC-style code in Notepad (or any editor), run it like a script.Compile code just as god intended.

```
hcc myprogram.HC
```

## Requirements

- **Windows 10/11**
- **Python 3.10+** (stdlib only — no pip packages)

## Quick start

1. Clone this repo (or download and unzip).
2. Run setup once:

   ```powershell
   cd holyc-compiler
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```

   This adds `hcc` to your user PATH and downloads TinyCC (~few MB).

3. Open a **new** terminal and try:

   ```powershell
   hcc examples\hello.HC
   ```

Without PATH setup you can also run:

```powershell
.\hcc.cmd examples\hello.HC
```

## Usage

| Command | What it does |
|---------|----------------|
| `hcc file.HC` | Compile + run (default) |
| `hcc file.HC --build` | Build `file.exe` only |
| `hcc file.HC --emit-c` | Print generated C |
| `hcc file.HC -O2` | Optimize (`-O0` … `-O3`) |
| `hcc file.HC -- arg1 arg2` | Pass args to your program |

### Example program

```holyc
I64 Main()
{
  "Hello from HolyC!\n";
  $("Answer = %d\n", 42);
  return 0;
}
```

Save as `mytest.HC`, then `hcc mytest.HC`.

## Project layout

```
hcc.py              CLI entry point
hcc.cmd             Windows launcher (no PATH needed)
install.ps1         One-time setup (PATH + TinyCC download)
holyc/              Compiler: lexer, parser, sema, IR, codegen
examples/           Sample .HC programs
stdlib/             Optional HolyC standard helpers
test_suite.py       Compile-check all examples
toolchain/          TinyCC lives here after install (gitignored)
```

## Features

- Preprocessor (`#define`, `#include`, `#if`)
- Types: `I8`–`I64`, `U8`–`U64`, `F64`, `Bool`, structs, unions, enums
- Control flow: `if`, `while`, `for`, `switch`, `goto`, ternary
- HolyC-style string literals and `$()` printf sugar
- Range-for, `sizeof`, inline asm passthrough
- IR + optimizer (`-O0` through `-O3`)

## Tests

```powershell
python test_suite.py
```

## Not TempleOS HolyC

TempleOS HolyC compiles to native x86 inside Adam with OS APIs baked in. **hcc** is a practical subset that emits portable C and uses TinyCC on Windows. Syntax and spirit are similar; behavior and the standard library are not identical.

## License

MIT — see [LICENSE](LICENSE).

TinyCC is downloaded separately at install time and is LGPL/GPL — see [bellard.org/tcc](https://bellard.org/tcc/).

## Uploading to GitHub

This repo is ready to push. The `toolchain/` binaries are intentionally excluded (see [toolchain/README.md](toolchain/README.md)). After cloning, users run `install.ps1` to fetch them.

```powershell
git init
git add .
git commit -m "Initial commit: HolyC compiler for Windows"
git branch -M main
git remote add origin https://github.com/YOUR_USER/holyc-compiler.git
git push -u origin main
```

Create an empty repo on GitHub first, replace `YOUR_USER/holyc-compiler` with your URL, then push.
