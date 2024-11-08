from pydantic import BaseModel
from typing import List

class LMClusteredTopic(BaseModel):
    """
    Output of the clustering algorithm
    """
    name: str
    chunks: List[str]

class LMClusteredTopicList(BaseModel):
    topics: List[LMClusteredTopic]
