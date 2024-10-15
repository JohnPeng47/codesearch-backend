import sys

sys.path.append("rtfs_rewrite")

from dataclasses import dataclass, field
from typing import List
from enum import Enum

from rtfs.chunk_resolution.graph import ChunkNode
from rtfs.graph import Edge


class ScopeType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"


@dataclass
class FuncArg:
    name: str
    arg_type: str | None

    def __str__(self):
        return f"{self.name}: {self.arg_type if self.arg_type else 'Any'}"


@dataclass
class FunctionContext:
    name: str
    args_list: List[FuncArg] = field(default_factory=list)

    def __str__(self):
        args_str = ", ".join(str(arg) for arg in self.args_list)
        return f"{self.name}({args_str})"


@dataclass
class ChunkContext:
    scope_name: str
    scope_type: ScopeType
    functions: List[FunctionContext]

    def __str__(self):
        functions_str = "\n  ".join(str(func) for func in self.functions)
        return f"{self.scope_name} ({self.scope_type}):\n  {functions_str}"


@dataclass(kw_only=True)
class AltChunkNode(ChunkNode):
    ctxt: List[ChunkContext]
    # references: List[str] = field(default_factory=list)
    # definitions: List[str] = field(default_factory=list)

    def __str__(self):
        ctxt_str = "\n".join(str(ctxt) for ctxt in self.ctxt)
        return f"{self.id}:\n{ctxt_str}\n"


@dataclass
class AltChunkEdge(Edge):
    ref: str = field(default="")
