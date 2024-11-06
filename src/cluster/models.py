from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, String
from typing import List

from src.database.core import Base
from src.chunk.models import CodeChunk
from src.utils import DELIMETER

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
    
    def full_code(self):
        chunk_list = "\n".join([chunk.id + "\n" + chunk.get_content() + DELIMETER 
                                for chunk in self.chunks])
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