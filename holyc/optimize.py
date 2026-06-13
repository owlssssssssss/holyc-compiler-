from __future__ import annotations

import json
import re
from typing import List, Optional

from .ir import IRBlock, IRFunction, IRInstr, IRModule


class Optimizer:
    def __init__(self, level: int = 1):
        self.level = max(0, min(3, level))

    def run(self, module: IRModule) -> IRModule:
        if self.level == 0:
            return module
        for fn in module.functions:
            for blk in fn.blocks:
                blk.instrs = self._fold_block(blk.instrs)
            if self.level >= 2:
                self._remove_unreachable(fn)
            if self.level >= 3:
                for blk in fn.blocks:
                    blk.instrs = self._copy_prop(blk.instrs)
        return module

    def _fold_block(self, instrs: List[IRInstr]) -> List[IRInstr]:
        out: List[IRInstr] = []
        for ins in instrs:
            if ins.op == "binop" and len(ins.args) == 3:
                folded = self._fold_binop(ins.args[0], ins.args[1], ins.args[2])
                if folded is not None:
                    out.append(IRInstr("assign", ins.dest, [folded]))
                    continue
            if ins.op == "binop" and len(ins.args) == 4 and ins.args[1] == "?:":
                if self._is_const(ins.args[0]):
                    pick = ins.args[2] if ins.args[0] not in ("0", "false") else ins.args[3]
                    out.append(IRInstr("assign", ins.dest, [pick]))
                    continue
            out.append(ins)
        return out

    def _fold_binop(self, left: str, op: str, right: str) -> Optional[str]:
        if not (self._is_num(left) and self._is_num(right)):
            if op == "+" and right == "0":
                return left
            if op == "+" and left == "0":
                return right
            if op == "*" and right == "1":
                return left
            if op == "*" and left == "1":
                return right
            if op == "*" and (right == "0" or left == "0"):
                return "0"
            return None
        a, b = self._num(left), self._num(right)
        ops = {
            "+": lambda x, y: x + y,
            "-": lambda x, y: x - y,
            "*": lambda x, y: x * y,
            "/": lambda x, y: x // y if y else 0,
            "%": lambda x, y: x % y if y else 0,
            "<<": lambda x, y: x << y,
            ">>": lambda x, y: x >> y,
            "&": lambda x, y: x & y,
            "|": lambda x, y: x | y,
            "^": lambda x, y: x ^ y,
            "==": lambda x, y: int(x == y),
            "!=": lambda x, y: int(x != y),
            "<": lambda x, y: int(x < y),
            ">": lambda x, y: int(x > y),
            "<=": lambda x, y: int(x <= y),
            ">=": lambda x, y: int(x >= y),
        }
        if op in ops:
            return str(ops[op](a, b))
        return None

    def _is_num(self, s: str) -> bool:
        return bool(re.match(r"^-?\d+$", s.strip()))

    def _num(self, s: str) -> int:
        return int(s.strip())

    def _is_const(self, s: str) -> bool:
        return s in ("0", "1") or self._is_num(s)

    def _remove_unreachable(self, fn: IRFunction) -> None:
        if not fn.blocks:
            return
        reachable = {fn.blocks[0].name}
        changed = True
        while changed:
            changed = False
            for blk in fn.blocks:
                if blk.name not in reachable:
                    continue
                for ins in blk.instrs:
                    for target in self._jump_targets(ins):
                        if target not in reachable:
                            reachable.add(target)
                            changed = True
        fn.blocks = [b for b in fn.blocks if b.name in reachable]

    def _jump_targets(self, ins: IRInstr) -> List[str]:
        if ins.op in ("jmp", "br") and ins.label:
            return [ins.label]
        return []

    def _copy_prop(self, instrs: List[IRInstr]) -> List[IRInstr]:
        copies: dict[str, str] = {}
        out: List[IRInstr] = []
        for ins in instrs:
            if ins.op == "assign" and len(ins.args) == 1 and self._is_num(ins.args[0]):
                copies[ins.dest or ""] = ins.args[0]
                out.append(ins)
                continue
            new_args = [copies.get(a, a) for a in ins.args]
            out.append(IRInstr(ins.op, ins.dest, new_args, ins.label))
        return out