from enum import Enum
from typing import List, NewType
from dataclasses import dataclass, field
from moatless.types import MoatlessChunkID
from tree_sitter import Point

from rtfs.graph import Node, Edge
from rtfs.utils import TextRange
from rtfs.graph import NodeKind

from src.models import CodeChunk

ChunkNodeID = NewType("ChunkNodeID", str)

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
class ChunkNode(CodeChunk, Node):
    kind: NodeKind = NodeKind.Chunk

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
    
    def to_code_chunk(self) -> CodeChunk:
        return CodeChunk(
            id=self.id,
            metadata=self.metadata,
            content=self.content,
            input_type=self.input_type,
            summary=self.summary
        )
    
    def to_json(self):
        return {
            "id": self.id,
            "metadata": self.metadata.to_json(),
            "content": self.content,
            "input_type": self.input_type,
            "summary": self.summary.dict() if self.summary else None,
            "kind": self.kind
        }

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
