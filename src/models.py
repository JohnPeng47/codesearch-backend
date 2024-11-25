from datetime import datetime
from sqlalchemy import Column, DateTime, event
from pydantic import BaseModel, Field
from pydantic.types import SecretStr
from dataclasses import dataclass, field
from llama_index.core.schema import TextNode

from enum import Enum
from typing import Annotated, Optional, Any, List, Dict

PrimaryKey = Annotated[int, Field(gt=0, lt=2147483647)]
NameStr = Annotated[
    str, Field(pattern=r"^.+\S.*$", strip_whitespace=True, min_length=3)
]
UUID = Annotated[str, Field(
    description="UUID string in hex format"
)]
FULL_PATH = Annotated[
    str, Field(
        pattern=r"^([A-Za-z]:[\\/]|/).+",  # Matches C:\ or C:/ or / at start
        strip_whitespace=True,
        description="Absolute filesystem path (Windows or Unix)"
    )
]
REL_PATH = Annotated[
    str, Field(
        pattern=r"^(?![A-Za-z]:[\\/]|/).+",  # Does not match absolute paths
        strip_whitespace=True,
        description="Relative filesystem path (Windows or Unix)"
    )
]


class TimeStampMixin(object):
    """Timestamping mixin"""

    created_at = Column(DateTime, default=datetime.utcnow)
    created_at._creation_order = 9998
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_at._creation_order = 9998

    @staticmethod
    def _updated_at(mapper, connection, target):
        target.updated_at = datetime.utcnow()

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, "before_update", cls._updated_at)


class RTFSBase(BaseModel):
    class Config:
        from_attributes = True
        validate_assignment = True
        arbitrary_types_allowed = True
        str_strip_whitespace = True

        json_encoders = {
            # custom output conversion for datetime
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%SZ") if v else None,
            SecretStr: lambda v: v.get_secret_value() if v else None,
        }


class HTTPSuccess(BaseModel):
    msg: str = "Success"



class ScopeType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"


# Temporary place to keep these defs until we get rtfs integrated under src
class MetadataType(str, Enum):
    CODE = "chunk"
    CLUSTER = "cluster"
    
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


# TODO: need to implement a deserialization method for this
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

class ChunkType(str, Enum):
    FILE = "file"    
    CHUNK = "chunk"


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

    contexts: Optional[List[ChunkContext]] = field(default_factory=list)
    type: MetadataType = MetadataType.CODE

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
            "contexts": [ctxt.__dict__ for ctxt in self.contexts],
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def __json__(self):
        return self.to_dict()

    @classmethod
    def __from_json__(cls, data):
        return cls.from_dict(data)
    
# CHUNK AUGMENTATIONS
class CodeSummary(BaseModel):
    long_description: str
    short_description: str
    questions: List[str]


CHUNK_ID = Annotated[str, Field(descrition="Chunk identifier")]
CLUSTER_ID = Annotated[int, Field(description="Cluster identifier")]

@dataclass
class CodeChunk:
    id: CHUNK_ID
    metadata: ChunkMetadata
    content: str
    input_type: ChunkType
    
    # additional augmentations
    # Note: unsure what field because of CodeSummary in ClusterChunk
    summary: Optional[CodeSummary] = None

    @classmethod
    def from_json(cls, data: Dict):
        return cls(
            id=data["id"],
            metadata=ChunkMetadata(**data["metadata"]),
            content=data["content"],
            input_type=data["input_type"],
            summary=CodeSummary(**data["summary"]) if data["summary"] else None
        )

    def to_json(self):
        return {
            "id": self.id,
            "metadata": self.metadata.to_json(),
            "content": self.content,
            "input_type": self.input_type,
            "summary": self.summary.dict() if self.summary else None
        }

    def to_str(self, 
               return_content: bool = False, 
               return_summaries: bool = False) -> str:
        s = f"Chunk: {self.id}"
        s += f"\nSummary: {self.summary.short_description}" if return_summaries else ""
        if return_content and self.content:
            s += f"\n{self.content}"
        return s
    
    def to_text_node(self) -> TextNode:
        return TextNode(
            text=self.content,
            id_=self.id,
            metadata=self.metadata.to_json(),
            embedding=None,
        )

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id
    
class ClusterMetadata(BaseModel):
    chunk_ids: List[CHUNK_ID]

@dataclass
class Cluster:
    id: CLUSTER_ID
    title: str
    summary: str
    chunks: List[CodeChunk]
    children: List["Cluster"]

    def to_str(self, return_content: bool = False, return_summaries: bool = False) -> str:
        s = f"Cluster {self.id}: {self.title}\n"
        s += f"Summary: {self.summary}\n" if self.summary and return_summaries else ""
        
        for chunk in self.chunks:
            chunk_str = chunk.to_str(return_content)
            s += "  " + chunk_str.replace("\n", "\n  ") + "\n"

        if self.children:
            s += f"Children ({len(self.children)}):\n"
            for child in self.children:
                child_str = child.to_str(return_content)
                s += "  " + child_str.replace("\n", "\n  ") + "\n"

        return s

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "chunks": [chunk.__dict__ for chunk in self.chunks],
            "children": [child.to_dict() for child in self.children],
        }
    
    @classmethod
    def from_json(cls, data: Dict):
        # Process chunks
        processed_chunks = [
            CodeChunk.from_json(chunk) for chunk in data["chunks"]
        ]
    
        # Process children recursively 
        processed_children = [
            Cluster.from_json(child) for child in data["children"]
        ]

        # Create instance
        result = cls(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            chunks=processed_chunks,
            children=processed_children
        )

        return result   
    
    def __hash__(self):
        return self.id
    
    def __eq__(self, other):
        if len(self.chunks) != len(other.chunks):
            return False
        
        chunks_equal = all([chunk == other_chunk for chunk, other_chunk in zip(self.chunks, other.chunks)])
        return self.id == other.id and chunks_equal
    
    def to_text_node(self) -> TextNode:
        return TextNode(
            text=self.summary,
            metadata={"chunk_ids": [chunk.id for chunk in self.chunks]},
            id_=self.id,
            embedding=None,
        )
