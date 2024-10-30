from typing import List, Tuple
from pydantic import BaseModel
import ell
from enum import Enum
from src.chunk.models import ClusterInput
from ..models import (
    ClusteredTopic,
    LMClusteredTopicList,
)

DELIMETER = f"\n\n{'-' * 80}\n" # only 1 tokens good deal!

class ChunkType(str, Enum):
    LOGIC = "\{code\}"
    DATA_STRUCTURE = "\{data_structure\}"


# TODO: try again with code at the top of the prompt to trigger caching
@ell.complex(model="gpt-4o-2024-08-06")
def enrich_cluster(cluster: ClusteredTopic, 
                      chunks: List[ClusterInput]) -> LMClusteredTopicList:
    codebase = ""
    for chunk in chunks:
        codebase += chunk.get_chunkinfo()
        codebase += chunk.get_content() + DELIMETER

    IMPORTANT_CHUNKS = """
Here are chunks of code representing a repo:
{code}

Here is a cluster of code that was generated from a clustering algorithm. The algorithm is prone to making mistakes.
Can you enrich the cluster by adding more related  

Now generate the output
"""
    important_chunks = IMPORTANT_CHUNKS.format(code=codebase, n_chunks=n_chunks, chunk_type=chunk_type)
    print("Important chunks:", important_chunks)
    return important_chunks