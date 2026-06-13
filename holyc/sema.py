from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from . import ast
from .diagnostics import DiagnosticEngine


TYPE_SIZES = {
    "I8": 1, "U8": 1, "I16": 2, "U16": 2, "I32": 4, "U32": 4,
    "I64": 8, "U64": 8, "F64": 8, "Bool": 1, "U0": 0,
    "Reg": 8, "RegI8": 1, "RegU8": 1, "RegI16": 2, "RegU16": 2,
    "RegI32": 4, "RegU32": 4, "RegI64": 8, "RegU64": 8, "RegF64": 8,
}


@dataclass
class Symbol:
    name: str
    kind: str
    type_name: str = "I64"
    is_function: bool = False


@dataclass
class Scope:
    symbols: Dict[str, Symbol] = field(default_factory=dict)
    parent: Optional["Scope"] = None
    loop_depth: int = 0
    switch_depth: int = 0

    def define(self, sym: Symbol) -> bool:
        if sym.name in self.symbols:
            return False
        self.symbols[sym.name] = sym
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


class SemanticAnalyzer:
    def __init__(self, diags: DiagnosticEngine):
        self.diags = diags
        self.scope: Optional[Scope] = None
        self.functions: Dict[str, ast.FunctionDef] = {}
        self.classes: Dict[str, ast.ClassDef] = {}
        self.unions: Dict[str, ast.UnionDef] = {}
        self.labels: Set[str] = set()

    def analyze(self, program: ast.Program) -> None:
        self.scope = Scope()
        for item in program.items:
            if isinstance(item, ast.ClassDef):
                self.classes[item.name] = item
                self.scope.define(Symbol(item.name, "class", item.name))
            elif isinstance(item, ast.UnionDef):
                self.unions[item.name] = item
                self.scope.define(Symbol(item.name, "union", item.name))
            elif isinstance(item, ast.FunctionDef):
                if not self.scope.define(Symbol(item.name, "function", item.return_type.base, True)):
                    self.diags.error(f"Redefinition of function '{item.name}'")
                self.functions[item.name] = item
            elif isinstance(item, ast.GlobalVar):
                if not self.scope.define(Symbol(item.name, "var", item.type.base)):
                    self.diags.error(f"Redefinition of global '{item.name}'")

        for item in program.items:
            if isinstance(item, ast.FunctionDef):
                self._check_function(item)

    def _check_function(self, fn: ast.FunctionDef) -> None:
        fn_scope = Scope(parent=self.scope, loop_depth=0)
        old = self.scope
        self.scope = fn_scope
        self.labels = set()
        for p in fn.params:
            if not self.scope.define(Symbol(p.name, "param", p.type.base)):
                self.diags.error(f"Duplicate parameter '{p.name}'")
        self._collect_labels(fn.body)
        for stmt in fn.body:
            self._check_stmt(stmt)
        if fn.return_type.base != "U0" and not self._has_return(fn.body):
            self.diags.warning(f"Function '{fn.name}' may not return a value")
        self.scope = old

    def _collect_labels(self, stmts: List[ast.Stmt]) -> None:
        for s in stmts:
            if isinstance(s, ast.Label):
                self.labels.add(s.name)
            elif isinstance(s, ast.Block):
                self._collect_labels(s.stmts)
            elif isinstance(s, ast.If):
                self._collect_labels(s.then_body)
                if s.else_body:
                    self._collect_labels(s.else_body)
            elif isinstance(s, ast.While):
                self._collect_labels(s.body)
            elif isinstance(s, ast.DoWhile):
                self._collect_labels(s.body)
            elif isinstance(s, ast.For):
                self._collect_labels(s.body)
            elif isinstance(s, ast.RangeFor):
                self._collect_labels(s.body)
            elif isinstance(s, ast.Switch):
                for c in s.cases:
                    self._collect_labels(c.body)

    def _has_return(self, stmts: List[ast.Stmt]) -> bool:
        for s in stmts:
            if isinstance(s, ast.Return):
                return True
            if isinstance(s, ast.If):
                if s.else_body and self._has_return(s.then_body) and self._has_return(s.else_body):
                    return True
            if isinstance(s, ast.Block) and self._has_return(s.stmts):
                return True
        return False

    def _check_stmt(self, stmt: ast.Stmt) -> None:
        if isinstance(stmt, ast.VarDecl):
            if not self.scope.define(Symbol(stmt.name, "var", stmt.type.base)):
                self.diags.error(f"Redefinition of '{stmt.name}'")
            if stmt.init:
                self._check_expr(stmt.init)
        elif isinstance(stmt, ast.Assign):
            self._check_expr(stmt.target)
            self._check_expr(stmt.value)
        elif isinstance(stmt, ast.If):
            self._check_expr(stmt.cond)
            for s in stmt.then_body:
                self._check_stmt(s)
            if stmt.else_body:
                for s in stmt.else_body:
                    self._check_stmt(s)
        elif isinstance(stmt, ast.While):
            self.scope.loop_depth += 1
            self._check_expr(stmt.cond)
            for s in stmt.body:
                self._check_stmt(s)
            self.scope.loop_depth -= 1
        elif isinstance(stmt, ast.DoWhile):
            self.scope.loop_depth += 1
            for s in stmt.body:
                self._check_stmt(s)
            self._check_expr(stmt.cond)
            self.scope.loop_depth -= 1
        elif isinstance(stmt, ast.For):
            self.scope.loop_depth += 1
            if isinstance(stmt.init, ast.VarDecl):
                self.scope.define(Symbol(stmt.init.name, "var", stmt.init.type.base))
                if stmt.init.init:
                    self._check_expr(stmt.init.init)
            elif isinstance(stmt.init, ast.Assign):
                self._check_expr(stmt.init.target)
                self._check_expr(stmt.init.value)
            elif stmt.init:
                self._check_expr(stmt.init)
            if stmt.cond:
                self._check_expr(stmt.cond)
            if stmt.step:
                self._check_expr(stmt.step)
            for s in stmt.body:
                self._check_stmt(s)
            self.scope.loop_depth -= 1
        elif isinstance(stmt, ast.RangeFor):
            self.scope.loop_depth += 1
            self.scope.define(Symbol(stmt.name, "var", stmt.var_type.base))
            self._check_expr(stmt.start)
            self._check_expr(stmt.end)
            for s in stmt.body:
                self._check_stmt(s)
            self.scope.loop_depth -= 1
        elif isinstance(stmt, ast.Return):
            if stmt.value:
                self._check_expr(stmt.value)
        elif isinstance(stmt, ast.Break):
            if self.scope.loop_depth == 0 and self.scope.switch_depth == 0:
                self.diags.error("break outside of loop or switch")
        elif isinstance(stmt, ast.Continue):
            if self.scope.loop_depth == 0:
                self.diags.error("continue outside of loop")
        elif isinstance(stmt, ast.Goto):
            if stmt.label not in self.labels:
                self.diags.error(f"Undefined label '{stmt.label}'")
        elif isinstance(stmt, ast.Switch):
            self._check_expr(stmt.expr)
            self.scope.switch_depth += 1
            for case in stmt.cases:
                if case.value:
                    self._check_expr(case.value)
                for s in case.body:
                    self._check_stmt(s)
            self.scope.switch_depth -= 1
        elif isinstance(stmt, ast.Print):
            for a in stmt.args:
                self._check_expr(a)
        elif isinstance(stmt, ast.ExprStmt):
            self._check_expr(stmt.expr)
        elif isinstance(stmt, ast.Block):
            block_scope = Scope(
                parent=self.scope,
                loop_depth=self.scope.loop_depth,
                switch_depth=self.scope.switch_depth,
            )
            old = self.scope
            self.scope = block_scope
            for s in stmt.stmts:
                self._check_stmt(s)
            self.scope = old

    def _check_expr(self, expr: ast.Expr) -> None:
        if isinstance(expr, ast.Ident):
            if not self.scope or not self.scope.lookup(expr.name):
                if expr.name not in self.functions and expr.name not in self.classes:
                    self.diags.warning(f"Use of undeclared identifier '{expr.name}'")
        elif isinstance(expr, ast.Binary):
            self._check_expr(expr.left)
            self._check_expr(expr.right)
        elif isinstance(expr, ast.Unary):
            self._check_expr(expr.expr)
        elif isinstance(expr, ast.Call):
            self._check_expr(expr.callee)
            for a in expr.args:
                self._check_expr(a)
        elif isinstance(expr, ast.Index):
            self._check_expr(expr.obj)
            self._check_expr(expr.index)
        elif isinstance(expr, ast.Member):
            self._check_expr(expr.obj)
        elif isinstance(expr, ast.Cast):
            self._check_expr(expr.expr)
        elif isinstance(expr, ast.Ternary):
            self._check_expr(expr.cond)
            self._check_expr(expr.then_expr)
            self._check_expr(expr.else_expr)
        elif isinstance(expr, ast.ArrayInit):
            for e in expr.elements:
                self._check_expr(e)