import ell
from typing import List

from src.cluster.types import SourceChunk, LMClusteredTopic, LMClusteredTopicList

ell.init(
    store="logdir",
    autocommit=True,
)




# TODO: Use dspy to auto-tune a list of topics
@ell.complex(model="gpt-4o-2024-08-06", response_format=LMClusteredTopicList)
def generate_clusters(chunks: List[SourceChunk], 
                      simple_names: List[str]) -> LMClusteredTopicList:
    
    codebase = "".join([chunk.to_str(name=name) for name, chunk in zip(simple_names, chunks)])

    CLUSTER_PROMPT = """
You are given a codebase. Identify clusters of code that accomplish a common goal. Make sure
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

Here is the codebase:
{codebase}
"""
    return CLUSTER_PROMPT.format(codebase=codebase)
