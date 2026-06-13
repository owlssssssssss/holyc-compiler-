from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class Macro:
    name: str
    params: List[str]
    body: str
    is_function: bool = False


class Preprocessor:
    def __init__(self, include_paths: Optional[List[Path]] = None):
        self.defines: Dict[str, str] = {}
        self.macros: Dict[str, Macro] = {}
        self.include_paths = include_paths or []
        self._included: Set[Path] = set()

    def add_define(self, name: str, value: str = "1") -> None:
        self.defines[name] = value

    def process(self, source: str, file_path: Optional[Path] = None) -> str:
        lines = source.splitlines(keepends=True)
        out: List[str] = []
        if_stack: List[bool] = [True]
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            if stripped.startswith("#"):
                i = self._handle_directive(
                    stripped, lines, i, out, if_stack, file_path
                )
                continue
            if all(if_stack):
                out.append(self._expand_line(line))
            i += 1
        return "".join(out)

    def _handle_directive(
        self,
        line: str,
        lines: List[str],
        i: int,
        out: List[str],
        if_stack: List[bool],
        file_path: Optional[Path],
    ) -> int:
        body = line[1:].strip()
        parts = body.split(None, 1)
        cmd = parts[0] if parts else ""
        rest = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "define":
            self._parse_define(rest)
        elif cmd == "undef":
            name = rest.split()[0] if rest else ""
            self.defines.pop(name, None)
            self.macros.pop(name, None)
        elif cmd == "include":
            path = rest.strip('"<>')
            inc = self._resolve_include(path, file_path)
            if inc and inc.exists():
                if inc not in self._included:
                    self._included.add(inc)
                    nested = self.process(inc.read_text(encoding="utf-8"), inc)
                    if all(if_stack):
                        out.append(nested)
            elif all(if_stack):
                out.append(f"/* include not found: {path} */\n")
        elif cmd == "ifdef":
            name = rest.split()[0] if rest else ""
            active = name in self.defines or name in self.macros
            if_stack.append(if_stack[-1] and active)
        elif cmd == "ifndef":
            name = rest.split()[0] if rest else ""
            active = name not in self.defines and name not in self.macros
            if_stack.append(if_stack[-1] and active)
        elif cmd == "else":
            if len(if_stack) > 1:
                parent = if_stack[-2]
                current = if_stack[-1]
                if_stack[-1] = parent and not current
        elif cmd == "endif":
            if len(if_stack) > 1:
                if_stack.pop()
        elif cmd == "pragma" and all(if_stack):
            out.append(f"/* pragma {rest} */\n")
        return i + 1

    def _parse_define(self, rest: str) -> None:
        if not rest:
            return
        m = re.match(r"(\w+)(\(([^)]*)\))?\s*(.*)", rest)
        if not m:
            return
        name, _, params, body = m.groups()
        if params is not None:
            plist = [p.strip() for p in params.split(",") if p.strip()]
            self.macros[name] = Macro(name, plist, body.strip(), True)
        else:
            self.defines[name] = body.strip() or "1"

    def _resolve_include(self, name: str, parent: Optional[Path]) -> Optional[Path]:
        candidates: List[Path] = []
        if parent:
            candidates.append(parent.parent / name)
        for p in self.include_paths:
            candidates.append(p / name)
        candidates.append(Path(name))
        for c in candidates:
            if c.exists():
                return c.resolve()
        return None

    def _expand_line(self, line: str) -> str:
        result = line
        for name, val in sorted(self.defines.items(), key=lambda x: -len(x[0])):
            result = re.sub(rf"\b{re.escape(name)}\b", val, result)
        for name, macro in sorted(self.macros.items(), key=lambda x: -len(x[0])):
            if macro.is_function:
                pattern = rf"{re.escape(name)}\(([^)]*)\)"

                def repl(m: re.Match[str], mac=macro) -> str:
                    args = [a.strip() for a in m.group(1).split(",")]
                    body = mac.body
                    for p, a in zip(mac.params, args):
                        body = re.sub(rf"\b{re.escape(p)}\b", a, body)
                    return body

                result = re.sub(pattern, repl, result)
        return result