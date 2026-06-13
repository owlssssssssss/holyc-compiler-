from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class IRValue:
    kind: str
    data: str = ""
    const: bool = False


@dataclass
class IRInstr:
    op: str
    dest: Optional[str] = None
    args: List[str] = field(default_factory=list)
    label: str = ""


@dataclass
class IRBlock:
    name: str
    instrs: List[IRInstr] = field(default_factory=list)


@dataclass
class IRFunction:
    name: str
    return_type: str
    params: List[tuple[str, str]]
    blocks: List[IRBlock] = field(default_factory=list)
    locals: Dict[str, str] = field(default_factory=dict)


@dataclass
class IRGlobal:
    name: str
    type_name: str
    init: Optional[str] = None


@dataclass
class IRStruct:
    name: str
    fields: List[tuple[str, str]]
    is_union: bool = False


@dataclass
class IRModule:
    structs: List[IRStruct] = field(default_factory=list)
    globals: List[IRGlobal] = field(default_factory=list)
    functions: List[IRFunction] = field(default_factory=list)
    source_file: str = "<source>"
    opt_level: int = 0