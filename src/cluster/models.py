from pydantic import BaseModel
from typing import List
from src.chunk.models import CodeChunk

class ClusteredTopic(BaseModel):
    """Output of the clustering algorithm"""
    name: str
    chunks: List[CodeChunk]

    def __str__(self):
        chunk_list = "\n".join([chunk.id for chunk in self.chunks])
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