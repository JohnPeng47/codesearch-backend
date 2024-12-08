from datetime import datetime
from sqlalchemy import Column, DateTime, event
from pydantic import BaseModel, Field
from pydantic.types import SecretStr
from dataclasses import dataclass, field
from llama_index.core.schema import TextNode
from collections import defaultdict
from enum import Enum

from typing import DefaultDict, Annotated, Optional, Any, List, Dict, Set

from src.utils import normalize_fp_to_posix

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
CHUNK_ID = Annotated[str, Field(descrition="Chunk identifier")]
CLUSTER_ID = Annotated[int, Field(description="Cluster identifier")]

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

    imports: DefaultDict[CHUNK_ID, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    contexts: Optional[List[ChunkContext]] = field(default_factory=list)
    type: MetadataType = MetadataType.CODE

    def __post_init__(self):
        self.file_path = normalize_fp_to_posix(self.file_path)

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
            "imports": {k: list(v) for k, v in self.imports.items()},
            "contexts": [ctxt.__dict__ for ctxt in self.contexts],
            "type": self.type
        }

    @classmethod
    def from_json(cls, data):        
        return cls(
            file_path=data["file_path"],
            file_name=data["file_name"],
            file_type=data["file_type"],
            category=data["category"],
            tokens=data["tokens"],
            span_ids=data["span_ids"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            imports=defaultdict(set, {k: set(v) for k, v in data.get("imports", {}).items()}),
            contexts=[ChunkContext(**ctx) for ctx in data.get("contexts", [])],
            type=data.get("type", MetadataType.CODE)
        )
    
# CHUNK AUGMENTATIONS
class CodeSummary(BaseModel):
    long_description: str = ""
    short_description: str = ""
    questions: List[str] = Field(default_factory=list)

@dataclass
class CodeChunk:
    id: CHUNK_ID
    metadata: ChunkMetadata
    content: str
    input_type: ChunkType
    
    # additional augmentations
    # Note: unsure what field because of CodeSummary in ClusterChunk
    summary: Optional[CodeSummary] = field(default_factory=CodeSummary)

    @classmethod
    def from_json(cls, data: Dict):
        try:
            return cls(
                id=data["id"],
                metadata=ChunkMetadata.from_json(data["metadata"]),
                content=data["content"],
                input_type=data["input_type"],
                summary=CodeSummary(**data["summary"]) if data["summary"] else CodeSummary().dict()
            )
        except Exception as e:
            print("Failed to deserilaize: ", data)
            raise e
        
    def to_json(self):
        return {
            "id": self.id,
            "metadata": self.metadata.to_json(),
            "content": self.content,
            "input_type": self.input_type,
            "summary": self.summary.dict() if self.summary else CodeSummary().dict()
        }
        
    def to_str(self, 
               return_content: bool = False, 
               return_summaries: bool = False) -> str:
        # s = f"{self.id}"
        s = f"{self.metadata.file_path}"
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
