from enum import Enum
from typing import List, Optional, NewType
from dataclasses import dataclass, field
from moatless.types import MoatlessChunkID

from rtfs.graph import Node, Edge
from rtfs.utils import TextRange
from rtfs.cluster.graph import ClusterNode, ClusterEdge
from rtfs.graph import EdgeKind

from tree_sitter import Point

ChunkNodeID = NewType("ChunkNodeID", str)

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
        if not self.functions:
            return ""

        ctxt_namespace = (
            f"{self.scope_name}:" if self.scope_type == ScopeType.CLASS else ""
        )
        return "\n".join(ctxt_namespace + str(func) for func in self.functions)


@dataclass
class SummarizedChunk:
    title: str = ""
    summary: str = ""
    key_variables: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "title": self.title,
            "summary": self.summary,
            "key_variables": self.key_variables,
        }

@dataclass(kw_only=True)
class ChunkMetadata:
    file_path: str
    file_name: str
    file_type: str
    category: str
    tokens: int
    span_ids: List[str]
    start_line: int
    end_line: int
    community: Optional[int] = None

    def to_json(self):
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "category": self.category,
            "tokens": self.tokens,
            "span_ids": self.span_ids,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "community": self.community,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def __json__(self):
        return self.to_dict()

    @classmethod
    def __from_json__(cls, data):
        return cls.from_dict(data)

class NodeKind(str, Enum):
    Chunk = "ChunkNode"
    Cluster = "ClusterNode"

@dataclass(kw_only=True)
class ChunkNode(Node):
    kind: str = "ChunkNode"
    og_id: MoatlessChunkID  # original ID on the BaseNode
    metadata: ChunkMetadata
    content: str
    summary: Optional[str] = ""
    ctxt_list: List[ChunkContext] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    definitions: List[str] = field(default_factory=list)

    @property
    def range(self):
        return TextRange(
            start_byte=0,
            end_byte=0,
            # HACK
            # NOTE: subtract 1 to convert to 0-based to conform with TreeSitter 0 based indexing
            start_point=Point(row=self.metadata.start_line - 1, column=0),
            end_point=Point(row=self.metadata.end_line - 1, column=0),
        )

    def set_community(self, community: int):
        self.metadata.community = community

    def __hash__(self):
        return hash(self.id + "".join(self.metadata.span_ids))

    def __str__(self):
        return f"{self.id}"

    def get_content(self):
        return self.content

class ChunkEdgeKind(str, Enum):
    ImportFrom = "ImportFrom"
    CallTo = "CallTo"

@dataclass(kw_only=True)
class ImportEdge(Edge):
    kind: ChunkEdgeKind = ChunkEdgeKind.ImportFrom
    ref: str

@dataclass(kw_only=True)
class CallEdge(Edge):
    kind: ChunkEdgeKind = ChunkEdgeKind.CallTo
    ref: str
