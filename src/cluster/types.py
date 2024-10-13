from pydantic import BaseModel
from typing import List, NewType, Optional
from enum import Enum
import uuid

from moatless.types import MoatlessChunkID


class ClusterInputType(str, Enum):
    FILE = "file"
    CHUNK = "chunk"


class ClusterChunk(BaseModel):
    """
    Input to the clustering algorithm that represents either a whole file
    or a partial partial input
    """
    id: MoatlessChunkID 
    input_type: ClusterInputType
    content: str
    filepath: Optional[str] = None

    def to_str(self, name: str = "") -> str:
        output = ""
        output += f"{name}\n" if name else f"Chunk {self.id}\n"
        output += f"Filename: {self.filepath}\n" if self.filepath else ""
        output += f"{self.content}\n\n"

        return output
    
    def __hash__(self) -> int:
        return hash(self.id)

# LLM unnion type lol:
# A LLM reduced type that contains a subset of the parent class
# with lower granularity
# Going from parent -> child is easy
# Going from child -> parent .. requires additional args to be supplied
# in the context of the "upscaling" event 
# Tmrw: 
class ClusteredTopic(BaseModel):
    """
    Output of the clustering algorithm
    """
    name: str
    chunks: List[ClusterChunk]

    def __str__(self):
        chunk_list = "\n-> " \
            + "\n-> ".join([str(input) for input in self.chunks])
        
        return f"{self.name}:\n{chunk_list}\n\n"

class LMClusteredTopic(ClusteredTopic):
    """
    Output of the clustering algorithm
    """
    name: str
    chunks: List[str]

class LMClusteredTopicList(BaseModel):
    topics: List[LMClusteredTopic]