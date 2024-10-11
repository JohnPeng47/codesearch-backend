import ell
from pydantic import BaseModel
from typing import List, NewType, Optional
from enum import Enum
import uuid

ell.init(
    store="logdir",
    autocommit=True,
)

class ClusterInputType(str, Enum):
    FILE = "file"
    CHUNK = "chunk"


class ClusterInput(BaseModel):
    """
    Input to the clustering algorithm that represents either a whole file
    or a partial partial input
    """
    index: int
    input_type: ClusterInputType
    content: str
    id: str = str(uuid.uuid4())
    filepath: Optional[str] = None

    def __str__(self):
        output = ""
        output += f"{self.sensible_id()}\n"
        output += f"Filename: {self.filepath}\n" if self.filepath else ""
        output += f"{self.content}\n\n"

        return output
        
    def sensible_id(self):
        """Generates a sensible ID for the LLM to latch onto"""
        return f"Chunk {self.index}"

class ClusteredTopic(BaseModel):
    """
    Output of the clustering algorithm
    """
    name: str
    chunk_ids: List[str]

    def __str__(self):
        chunk_list = "\n-> ".join([str(input) for input in self.chunk_ids])
        return f"{self.name}:\n{chunk_list}\n\n"

class ClusteredTopicList(BaseModel):
    topics: List[ClusteredTopic]


# TODO: Use dspy to auto-tune a list of topics
@ell.complex(model="gpt-4o-2024-08-06", response_format=ClusteredTopicList)
def generate_clusters(input: List[ClusterInput]) -> ClusteredTopicList:
    codebase = "".join([str(i) for i in input])

    CLUSTER_PROMPT = """
You are given a codebase. Identify clusters of code that accomplish a common goal. Make sure
that the topics you identify adhere to the following guidelines of SRP as best as possible:
- A cluster should have one, and only one, reason to change.
- Each cluser should focus on doing one thing well, rather than trying to handle multiple responsibilities.
- It promotes high cohesion within cluster, meaning that the chunks within a clusters are closely related and 
focused on a single purpose.

To reiterate, your output should be a list of clusters

Here is the codebase:
{codebase}
"""
    return CLUSTER_PROMPT.format(codebase=codebase)