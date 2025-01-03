from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from abc import ABC, abstractmethod

from .lmp.summarize import CodeSummary
from src.models import ChunkMetadata, ChunkType
from moatless.types import MoatlessChunkID


class ClusterInput(ABC):
    @abstractmethod
    def get_chunkinfo(self) -> str:
        pass

    @abstractmethod
    def get_content(self) -> str:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

# NOTE: currently using CodeChunk from src/models in favor of this one
# deprecated for now 
class CodeChunk(BaseModel, ClusterInput):
    """
    Input to the clustering algorithm that represents either a whole file
    or a partial partial input
    """
    id: MoatlessChunkID 
    input_type: ChunkType
    content: str
    filepath: Optional[str] = None

    # for backwards compat with BaseNode
    metadata: Optional[ChunkMetadata] = Field(default=None, validate_default=False)
    node_id: MoatlessChunkID = Field(default="", validate_default=False)

    summary: Optional[CodeSummary] = None

    def get_chunkinfo(self) -> str:
        return f"Chunk: {self.id}\n\n"

    def get_content(self) -> str:
        return self.content
    
    def get_name(self) -> str:
        return self.id

    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CodeChunk):
            return False
        return self.id == other.id
    
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

class FILE_CLASSIFICATIONS(str, Enum):
    CORE = "CORE"
    PERIPHERY = "PERIPHERY"
    DOCUMENTATION = "DOCUMENTATION"
    CONFIGURATION = "CONFIGURATION"

FILE_CLASSIFICATIONS_DICT = {
    FILE_CLASSIFICATIONS.CORE : "Core is core logic that is distinct, and largely differentiated from other software that aims to do different tasks",
    FILE_CLASSIFICATIONS.PERIPHERY : "Periphery code are the opposite, being commodified pieces of logic that is used to support the core",
    FILE_CLASSIFICATIONS.DOCUMENTATION : "Documentation is documentation",
    FILE_CLASSIFICATIONS.CONFIGURATION : "Configuration is configuration"
}

class ClassifiedFile(BaseModel):
    fp: str
    classification: str

class ClassifiedFilesList(BaseModel):
    classified_files: List[ClassifiedFile]
