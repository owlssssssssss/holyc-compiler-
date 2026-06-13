#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from holyc.compiler import CompileOptions, compile_file_full

EXAMPLES = [
    "examples/hello.HC",
    "examples/fib.HC",
    "examples/point.HC",
    "examples/advanced.HC",
]

failed = 0
for ex in EXAMPLES:
    path = Path(__file__).parent / ex
    try:
        result = compile_file_full(path, CompileOptions(opt_level=2))
        assert result.c_code
        print(f"OK  {ex} ({len(result.c_code)} bytes)")
    except Exception as e:
        print(f"FAIL {ex}: {e}")
        failed += 1

raise SystemExit(1 if failed else 0)