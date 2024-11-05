from enum import Enum
from typing import List, Optional, NewType
from dataclasses import dataclass, field

from rtfs.graph import Node, Edge
from rtfs.moatless.epic_split import CodeNode
from rtfs.utils import TextRange
from rtfs.cluster.graph import ClusterNode, ClusterEdge, ClusterEdgeKind

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
    og_id: str  # original ID on the BaseNode
    metadata: ChunkMetadata
    content: str

    @property
    def range(self):
        return TextRange(
            start_byte=0,
            end_byte=0,
            # NOTE: subtract 1 to convert to 0-based to conform with TreeSitter 0 based indexing
            start_point=(self.metadata.start_line - 1, 0),
            end_point=(self.metadata.end_line - 1, 0),
        )

    def set_community(self, community: int):
        self.metadata.community = community

    def __hash__(self):
        return hash(self.id + "".join(self.metadata.span_ids))

    def __str__(self):
        return f"{self.id}"

    def to_node(self):
        return CodeNode(
            id=self.id,
            text=self.content,
            metadata=self.metadata.__dict__,
            content=self.content,
        )

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
