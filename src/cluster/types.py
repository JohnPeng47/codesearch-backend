from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path

from rtfs.chunk_resolution.graph import ChunkMetadata
from moatless.types import MoatlessChunkID

CHUNK_DELMITER = "\n===================================================================="

class ClusterInput(ABC):
    @abstractmethod
    def get_chunkinfo(self) -> str:
        pass

    @abstractmethod
    def get_content(self) -> str:
        pass

class ClusterInputType(str, Enum):
    FILE = "file"
    CHUNK = "chunk"

class CodeChunk(BaseModel, ClusterInput):
    """
    Input to the clustering algorithm that represents either a whole file
    or a partial partial input
    """
    id: MoatlessChunkID 
    input_type: ClusterInputType
    content: str
    filepath: Optional[str] = None

    # for backwards compat
    metadata: ChunkMetadata
    node_id: MoatlessChunkID
    
    def get_chunkinfo(self) -> str:
        return  (
            f"Filename: {self.short_fn()}\n" if self.filepath else ""
        )
    
    # def get_short_id(self) -> str:
        

    def short_fn(self) -> str:
        return "/".join(Path(self.filepath).parts[-3:])

    def get_content(self) -> str:
        return self.content

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __str__(self) -> str:
        return self.get_chunkinfo() + "\n" + self.get_content()
    
class CodeType(str, Enum):
    LOGIC = "logic"
    DATA = "data"

# TODO(Prompt Optimizations):
# order of summary wrt to defs/refs? Adding it after could benefit
# from the refs/defs being used as the scratchpad
class LMSummaryChunk(BaseModel):
    """
    Version of SummaryChunk as output from LM
    """
    title: str
    summary: str
    code_type: CodeType
    definitions: List[str]
    references: List[str]

class SummaryChunk(CodeChunk, ClusterInput):
    """
    Input to the clustering algorithm that represents a summary of a chunk of 
    source code, derived from SourceChunk
    """
    title: str # NOTE: not actually used since we are using generic chunk name
    summary: str
    code_type: CodeType # NOTE: not tuned, this ouptut is kinda sketchy
    definitions: List[str]
    references: List[str]

    @classmethod
    def from_chunk(cls, code_chunk: CodeChunk, 
                   summary_chunk: LMSummaryChunk) -> "SummaryChunk":
        return cls(
            id=code_chunk.id,
            input_type=code_chunk.input_type,
            content=code_chunk.content,
            filepath=code_chunk.filepath,
            title=summary_chunk.title,
            summary=summary_chunk.summary,
            code_type=summary_chunk.code_type,
            definitions=summary_chunk.definitions,
            references=summary_chunk.references
        )

    def get_content(self) -> str:
        return self.summary
    
    def get_filecontent(self) -> str:
        return self.content

class ClusteredTopic(BaseModel):
    """Output of the clustering algorithm"""
    name: str
    chunks: List[CodeChunk]

    def __str__(self):
        chunk_list = "\n-> " + "\n-> ".join([str(input) + CHUNK_DELMITER for input in self.chunks])
        return (
            f"{self.name}:\n"
            f"{chunk_list}\n\n"
        )

class LMClusteredTopic(ClusteredTopic):
    """
    Output of the clustering algorithm
    """
    name: str
    chunks: List[str]

class LMClusteredTopicList(BaseModel):
    topics: List[LMClusteredTopic]