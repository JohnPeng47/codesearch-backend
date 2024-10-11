import ell
from pydantic import BaseModel
from typing import List, NewType
from enum import Enum


class ClusterInputType(str, Enum):
    FILE = "file"
    CHUNK = "chunk"


class ClusterInput(BaseModel):
    """
    Input to the clustering algorithm that represents either a whole file
    or a partial partial input
    """
    input_type: ClusterInputType
    input_id: str
    content: str

    def __str__(self):
        return f"{self.input_id}:\n\n{self.content}\n\n"

class ClusteredTopic(BaseModel):
    """
    Output of the clustering algorithm
    """
    name: str
    cluster_id: str
    input_list: List[str]


# TODO: Use dspy to auto-tune a list of topics
@ell.complex(model="gpt-4o-2024-08-06")
def generate_clusters(input: List[ClusterInput]) -> ClusteredTopic:
    codebase = "".join([str(i) for i in input])

    CLUSTER_PROMPT = """
You are given a codebase. Identify clusters of code that accomplish a common goal. Make sure
that the topics you identify adhere to the following guidelines of SRP as best as possible:
- A cluster should have one, and only one, reason to change.
- Each cluser should focus on doing one thing well, rather than trying to handle multiple responsibilities.
- It promotes high cohesion within cluster, meaning that the chunks within a clusters are closely related and 
focused on a single purpose.

Here is the codebase:
{codebase}
"""
    return CLUSTER_PROMPT.format(codebase=codebase)