from __future__ import annotations

import json
from typing import Dict, List, Optional, Set

from . import ast
from .ir import IRBlock, IRFunction, IRGlobal, IRInstr, IRModule, IRStruct


TYPE_MAP = {
    "I8": "int8_t", "U8": "uint8_t", "I16": "int16_t", "U16": "uint16_t",
    "I32": "int32_t", "U32": "uint32_t", "I64": "int64_t", "U64": "uint64_t",
    "F64": "double", "Bool": "bool", "U0": "void",
    "Reg": "int64_t", "RegI8": "int8_t", "RegU8": "uint8_t",
    "RegI16": "int16_t", "RegU16": "uint16_t", "RegI32": "int32_t",
    "RegU32": "uint32_t", "RegI64": "int64_t", "RegU64": "uint64_t", "RegF64": "double",
}


class Lowerer:
    def __init__(self):
        self.module = IRModule()
        self.class_names: Set[str] = set()
        self.union_names: Set[str] = set()
        self._tmp = 0
        self._block_id = 0
        self._cur_fn: Optional[IRFunction] = None
        self._cur_block: Optional[IRBlock] = None

    def lower(self, program: ast.Program, opt_level: int = 0) -> IRModule:
        self.module = IRModule(source_file=program.source_file, opt_level=opt_level)
        self.class_names = {i.name for i in program.items if isinstance(i, ast.ClassDef)}
        self.union_names = {i.name for i in program.items if isinstance(i, ast.UnionDef)}

        for item in program.items:
            if isinstance(item, ast.ClassDef):
                fields = [(f.name, self._c_type(f.type)) for f in item.fields]
                self.module.structs.append(IRStruct(item.name, fields, False))
            elif isinstance(item, ast.UnionDef):
                fields = [(f.name, self._c_type(f.type)) for f in item.fields]
                self.module.structs.append(IRStruct(item.name, fields, True))
            elif isinstance(item, ast.GlobalVar):
                init = self._expr(item.init) if item.init else None
                self.module.globals.append(IRGlobal(item.name, self._c_type(item.type), init))
            elif isinstance(item, ast.FunctionDef):
                self._lower_function(item)

        return self.module

    def _c_type(self, typ: ast.TypeNode) -> str:
        if typ.base in self.class_names or typ.base in self.union_names:
            base = typ.base
        else:
            base = TYPE_MAP.get(typ.base, typ.base)
        if typ.is_array:
            size = self._expr(typ.array_size) if typ.array_size else ""
            base = f"{base}[{size}]" if size else f"{base}[]"
        result = base
        for _ in range(typ.pointer_depth):
            result = f"{result}*"
        if typ.is_register:
            result = f"register {result}"
        return result

    def _lower_function(self, fn: ast.FunctionDef) -> None:
        ir_fn = IRFunction(
            fn.name,
            self._c_type(fn.return_type),
            [(p.name, self._c_type(p.type)) for p in fn.params],
        )
        self._cur_fn = ir_fn
        self._cur_block = IRBlock("entry")
        ir_fn.blocks.append(self._cur_block)
        for stmt in fn.body:
            self._lower_stmt(stmt)
        if not self._block_ends_with_terminator():
            if fn.return_type.base == "U0":
                self._emit("ret")
            else:
                self._emit("ret", args=["0"])
        self.module.functions.append(ir_fn)
        self._cur_fn = None
        self._cur_block = None

    def _block_ends_with_terminator(self) -> bool:
        if not self._cur_block or not self._cur_block.instrs:
            return False
        return self._cur_block.instrs[-1].op in ("ret", "br", "jmp")

    def _emit(self, op: str, dest: Optional[str] = None, args: Optional[List[str]] = None, label: str = "") -> str:
        dest = dest or (self._tmp_name() if op in ("assign", "binop", "call", "unary") else None)
        self._cur_block.instrs.append(IRInstr(op, dest, args or [], label))
        return dest or ""

    def _tmp_name(self) -> str:
        self._tmp += 1
        return f"__t{self._tmp}"

    def _new_block(self, prefix: str = "bb") -> IRBlock:
        self._block_id += 1
        blk = IRBlock(f"{prefix}{self._block_id}")
        self._cur_fn.blocks.append(blk)
        return blk

    def _lower_stmt(self, stmt: ast.Stmt) -> None:
        if isinstance(stmt, ast.Block):
            for s in stmt.stmts:
                self._lower_stmt(s)
        elif isinstance(stmt, ast.VarDecl):
            t = self._c_type(stmt.type)
            self._cur_fn.locals[stmt.name] = t
            if stmt.init:
                val = self._expr(stmt.init)
                self._emit("assign", stmt.name, [val])
            else:
                self._emit("assign", stmt.name, ["0"])
        elif isinstance(stmt, ast.Assign):
            val = self._expr(stmt.value)
            tgt = self._lvalue(stmt.target)
            self._emit("assign", tgt, [val])
        elif isinstance(stmt, ast.If):
            cond = self._expr(stmt.cond)
            then_blk = self._new_block("then")
            else_blk = self._new_block("else") if stmt.else_body else None
            merge_blk = self._new_block("endif")
            self._emit("br", args=[cond], label=then_blk.name)
            self._cur_block = then_blk
            for s in stmt.then_body:
                self._lower_stmt(s)
            if not self._block_ends_with_terminator():
                self._emit("jmp", label=merge_blk.name)
            if else_blk:
                self._cur_block = else_blk
                for s in stmt.else_body or []:
                    self._lower_stmt(s)
                if not self._block_ends_with_terminator():
                    self._emit("jmp", label=merge_blk.name)
            else:
                self._emit("jmp", label=merge_blk.name, dest=None)
            self._cur_block = merge_blk
        elif isinstance(stmt, ast.While):
            hdr = self._new_block("while_hdr")
            body = self._new_block("while_body")
            end = self._new_block("while_end")
            self._emit("jmp", label=hdr.name)
            self._cur_block = hdr
            cond = self._expr(stmt.cond)
            self._emit("br", args=[cond], label=body.name)
            self._emit("jmp", label=end.name)
            self._cur_block = body
            for s in stmt.body:
                self._lower_stmt(s)
            if not self._block_ends_with_terminator():
                self._emit("jmp", label=hdr.name)
            self._cur_block = end
        elif isinstance(stmt, ast.DoWhile):
            body = self._new_block("dowhile_body")
            hdr = self._new_block("dowhile_hdr")
            self._emit("jmp", label=body.name)
            self._cur_block = body
            for s in stmt.body:
                self._lower_stmt(s)
            if not self._block_ends_with_terminator():
                self._emit("jmp", label=hdr.name)
            self._cur_block = hdr
            cond = self._expr(stmt.cond)
            self._emit("br", args=[cond], label=body.name)
        elif isinstance(stmt, ast.For):
            if isinstance(stmt.init, ast.VarDecl):
                self._lower_stmt(stmt.init)
            elif isinstance(stmt.init, ast.Assign):
                self._lower_stmt(stmt.init)
            elif stmt.init:
                self._emit("expr", args=[self._expr(stmt.init)])
            hdr = self._new_block("for_hdr")
            body = self._new_block("for_body")
            step_blk = self._new_block("for_step")
            end = self._new_block("for_end")
            self._emit("jmp", label=hdr.name)
            self._cur_block = hdr
            if stmt.cond:
                cond = self._expr(stmt.cond)
                self._emit("br", args=[cond], label=body.name)
            self._emit("jmp", label=end.name)
            self._cur_block = body
            for s in stmt.body:
                self._lower_stmt(s)
            if not self._block_ends_with_terminator():
                self._emit("jmp", label=step_blk.name)
            self._cur_block = step_blk
            if stmt.step:
                self._emit("expr", args=[self._expr(stmt.step)])
            self._emit("jmp", label=hdr.name)
            self._cur_block = end
        elif isinstance(stmt, ast.RangeFor):
            t = self._c_type(stmt.var_type)
            self._cur_fn.locals[stmt.name] = t
            start = self._expr(stmt.start)
            end = self._expr(stmt.end)
            self._emit("assign", stmt.name, [start])
            hdr = self._new_block("range_hdr")
            body = self._new_block("range_body")
            step_blk = self._new_block("range_step")
            end_blk = self._new_block("range_end")
            self._emit("jmp", label=hdr.name)
            self._cur_block = hdr
            cmp_tmp = self._emit("binop", args=[stmt.name, "<", end])
            self._emit("br", args=[cmp_tmp], label=body.name)
            self._emit("jmp", label=end_blk.name)
            self._cur_block = body
            for s in stmt.body:
                self._lower_stmt(s)
            if not self._block_ends_with_terminator():
                self._emit("jmp", label=step_blk.name)
            self._cur_block = step_blk
            inc = self._emit("binop", args=[stmt.name, "+", "1"])
            self._emit("assign", stmt.name, [inc])
            self._emit("jmp", label=hdr.name)
            self._cur_block = end_blk
        elif isinstance(stmt, ast.Switch):
            val = self._expr(stmt.expr)
            end_blk = self._new_block("sw_end")
            default_blk = None
            case_blks: List[IRBlock] = []
            for i, case in enumerate(stmt.cases):
                case_blks.append(self._new_block(f"case{i}"))
                if case.is_default:
                    default_blk = case_blks[-1]
            for i, case in enumerate(stmt.cases):
                if case.is_default:
                    continue
                cmp = self._emit("binop", args=[val, "==", self._expr(case.value)])
                self._emit("br", args=[cmp], label=case_blks[i].name)
            if default_blk:
                self._emit("jmp", label=default_blk.name)
            else:
                self._emit("jmp", label=end_blk.name)
            for i, case in enumerate(stmt.cases):
                self._cur_block = case_blks[i]
                for s in case.body:
                    self._lower_stmt(s)
                if not self._block_ends_with_terminator():
                    self._emit("jmp", label=end_blk.name)
            self._cur_block = end_blk
        elif isinstance(stmt, ast.Return):
            if stmt.value:
                v = self._expr(stmt.value)
                self._emit("ret", args=[v])
            else:
                self._emit("ret")
        elif isinstance(stmt, ast.Break):
            self._emit("jmp", label="while_end")
        elif isinstance(stmt, ast.Continue):
            self._emit("jmp", label="while_hdr")
        elif isinstance(stmt, ast.Goto):
            self._emit("jmp", label=stmt.label)
        elif isinstance(stmt, ast.Label):
            self._cur_block = self._find_or_add_block(stmt.name)
        elif isinstance(stmt, ast.Asm):
            self._emit("asm", args=[json.dumps(stmt.code)])
        elif isinstance(stmt, ast.Print):
            args = [self._expr(a) for a in stmt.args]
            self._emit("print", args=args)
        elif isinstance(stmt, ast.ExprStmt):
            self._emit("expr", args=[self._expr(stmt.expr)])

    def _find_block(self, name: str) -> IRBlock:
        for b in self._cur_fn.blocks:
            if b.name == name:
                return b
        raise RuntimeError(f"block {name} not found")

    def _find_or_add_block(self, name: str) -> IRBlock:
        for b in self._cur_fn.blocks:
            if b.name == name:
                return b
        blk = IRBlock(name)
        self._cur_fn.blocks.append(blk)
        return blk

    def _lvalue(self, expr: ast.Expr) -> str:
        return self._expr(expr)

    def _expr(self, expr: Optional[ast.Expr]) -> str:
        if expr is None:
            return "0"
        if isinstance(expr, ast.IntLit):
            return str(expr.value)
        if isinstance(expr, ast.FloatLit):
            return repr(expr.value)
        if isinstance(expr, ast.StringLit):
            return json.dumps(expr.value)
        if isinstance(expr, ast.CharLit):
            return json.dumps(expr.value)
        if isinstance(expr, ast.BoolLit):
            return "1" if expr.value else "0"
        if isinstance(expr, ast.NullLit):
            return "NULL"
        if isinstance(expr, ast.Ident):
            return expr.name
        if isinstance(expr, ast.Unary):
            v = self._expr(expr.expr)
            if expr.op in ("++pre", "--pre", "++post", "--post"):
                return self._emit("unary", args=[expr.op, v])
            return self._emit("unary", args=[expr.op, v])
        if isinstance(expr, ast.Binary):
            if expr.op == "=":
                tgt = self._expr(expr.left)
                val = self._expr(expr.right)
                self._emit("assign", tgt, [val])
                return tgt
            l, r = self._expr(expr.left), self._expr(expr.right)
            return self._emit("binop", args=[l, expr.op, r])
        if isinstance(expr, ast.Call):
            callee = self._expr(expr.callee)
            args = [self._expr(a) for a in expr.args]
            return self._emit("call", args=[callee, *args])
        if isinstance(expr, ast.Index):
            return self._emit("binop", args=[self._expr(expr.obj), "[]", self._expr(expr.index)])
        if isinstance(expr, ast.Member):
            op = "->" if expr.is_arrow else "."
            return self._emit("binop", args=[self._expr(expr.obj), op, expr.field])
        if isinstance(expr, ast.Cast):
            inner = self._expr(expr.expr)
            return f"({self._c_type(expr.type)})({inner})"
        if isinstance(expr, ast.Ternary):
            c, t, e = self._expr(expr.cond), self._expr(expr.then_expr), self._expr(expr.else_expr)
            return self._emit("binop", args=[c, "?:", t, e])
        if isinstance(expr, ast.Sizeof):
            if expr.type:
                return f"sizeof({self._c_type(expr.type)})"
            return f"sizeof({self._expr(expr.expr)})"
        if isinstance(expr, ast.ArrayInit):
            elems = ", ".join(self._expr(e) for e in expr.elements)
            return "{" + elems + "}"
        return "0"