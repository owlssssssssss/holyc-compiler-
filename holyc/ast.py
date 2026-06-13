from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class TypeNode:
    base: str
    pointer_depth: int = 0
    is_array: bool = False
    array_size: Optional["Expr"] = None
    is_register: bool = False


@dataclass
class Program:
    items: List[Union["ClassDef", "UnionDef", "FunctionDef", "GlobalVar"]]
    source_file: str = "<source>"


@dataclass
class ClassDef:
    name: str
    fields: List["FieldDecl"]


@dataclass
class UnionDef:
    name: str
    fields: List["FieldDecl"]


@dataclass
class FieldDecl:
    type: TypeNode
    name: str


@dataclass
class FunctionDef:
    return_type: TypeNode
    name: str
    params: List["Param"]
    body: List["Stmt"]
    is_public: bool = False


@dataclass
class Param:
    type: TypeNode
    name: str


@dataclass
class GlobalVar:
    type: TypeNode
    name: str
    init: Optional["Expr"] = None
    is_public: bool = False


Stmt = Union[
    "Block", "VarDecl", "Assign", "If", "While", "DoWhile", "For",
    "RangeFor", "Return", "Break", "Continue", "ExprStmt", "Print",
    "Switch", "Goto", "Label", "Asm", "SwitchCase",
]


@dataclass
class Block:
    stmts: List[Stmt]


@dataclass
class VarDecl:
    type: TypeNode
    name: str
    init: Optional["Expr"] = None


@dataclass
class Assign:
    target: "Expr"
    value: "Expr"


@dataclass
class If:
    cond: "Expr"
    then_body: List[Stmt]
    else_body: Optional[List[Stmt]] = None


@dataclass
class While:
    cond: "Expr"
    body: List[Stmt]


@dataclass
class DoWhile:
    body: List[Stmt]
    cond: "Expr"


@dataclass
class For:
    init: Optional[Union[VarDecl, Assign, "Expr"]]
    cond: Optional["Expr"]
    step: Optional["Expr"]
    body: List[Stmt]


@dataclass
class RangeFor:
    var_type: TypeNode
    name: str
    start: "Expr"
    end: "Expr"
    body: List[Stmt]


@dataclass
class Return:
    value: Optional["Expr"] = None


@dataclass
class Break:
    pass


@dataclass
class Continue:
    pass


@dataclass
class ExprStmt:
    expr: "Expr"


@dataclass
class Print:
    args: List["Expr"]


@dataclass
class Switch:
    expr: "Expr"
    cases: List["SwitchCase"]


@dataclass
class SwitchCase:
    value: Optional["Expr"]
    body: List[Stmt]
    is_default: bool = False


@dataclass
class Goto:
    label: str


@dataclass
class Label:
    name: str


@dataclass
class Asm:
    code: str


Expr = Union[
    "IntLit", "FloatLit", "StringLit", "CharLit", "BoolLit", "NullLit",
    "Ident", "Unary", "Binary", "Call", "Index", "Member", "Cast",
    "Ternary", "Sizeof", "ArrayInit",
]


@dataclass
class IntLit:
    value: int


@dataclass
class FloatLit:
    value: float


@dataclass
class StringLit:
    value: str


@dataclass
class CharLit:
    value: str


@dataclass
class BoolLit:
    value: bool


@dataclass
class NullLit:
    pass


@dataclass
class Ident:
    name: str


@dataclass
class Unary:
    op: str
    expr: Expr


@dataclass
class Binary:
    op: str
    left: Expr
    right: Expr


@dataclass
class Call:
    callee: Expr
    args: List[Expr]


@dataclass
class Index:
    obj: Expr
    index: Expr


@dataclass
class Member:
    obj: Expr
    field: str
    is_arrow: bool = False


@dataclass
class Cast:
    type: TypeNode
    expr: Expr


@dataclass
class Ternary:
    cond: Expr
    then_expr: Expr
    else_expr: Expr


@dataclass
class Sizeof:
    type: Optional[TypeNode] = None
    expr: Optional[Expr] = None


@dataclass
class ArrayInit:
    elements: List[Expr]