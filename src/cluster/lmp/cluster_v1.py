from typing import List
import ell

from src.chunk.models import ClusterInput
from ..models import (
    LMClusteredTopicList
)

DELIMETER = "\n\n########" # only 3 tokens lol

# TODO: Use dspy to auto-tune a list of topics
@ell.complex(model="gpt-4o-2024-08-06", response_format=LMClusteredTopicList)
def generate_clusters(chunks: List[ClusterInput], 
                      simple_names: List[str]) -> LMClusteredTopicList:
    codebase = ""
    for name, chunk in zip(simple_names, chunks):
        codebase += f"NAME: {name}" + "\n"
        codebase += chunk.get_chunkinfo()
        codebase += chunk.get_content() + DELIMETER

    CLUSTER_PROMPT = """
Here are chunks of code representing a repo:
{codebase}

Identify clusters of code from above that accomplish a common goal. Make sure
that the topics you identify adhere to the following guidelines of SRP as best as possible:
- A cluster should have one, and only one, reason to change.
- Each cluser should focus on doing one thing well, rather than trying to handle multiple responsibilities.
- It promotes high cohesion within cluster, meaning that the chunks within a clusters are closely related and 
focused on a single purpose.

To reiterate, your output should be a list of clusters, where each chunk should be identified by the name provided:

ie. topics: [
    "Chunk 1",
    "Chunk 3",
    "Chunk 2"
    ...
]
"""
    return CLUSTER_PROMPT.format(codebase=codebase)
