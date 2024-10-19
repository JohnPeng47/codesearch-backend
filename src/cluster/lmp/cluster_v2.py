from typing import List, Tuple
from pydantic import BaseModel
import ell
from ..types import (
    ClusterInput,
    ClusteredTopic,
    LMClusteredTopicList
)

DELIMETER = f"\n\n{'-' * 80}\n" # only 1 tokens good deal!

# TODO: try again with code at the top of the prompt to trigger caching
@ell.complex(model="gpt-4o-2024-08-06")
def identify_key_chunks(chunks: List[ClusterInput], 
                      n_chunks: int = 6) -> LMClusteredTopicList:
    codebase = ""
    for chunk in chunks:
        codebase += chunk.get_chunkinfo()
        codebase += chunk.get_content() + DELIMETER

    IMPORTANT_CHUNKS = """
List the {n_chunks} most important chunks in this code and give a short reason why. These
chunks are going to be used as seeds in a clustering algorithm, so its important
that they dont overlap in terms of functionality. Write a small rationale for each chunk

{code}
"""
    return IMPORTANT_CHUNKS.format(code=codebase, n_chunks=n_chunks)


@ell.complex(model="gpt-4o-2024-08-06", response_format=LMClusteredTopicList)
def generate_clusters(chunks: List[ClusterInput], 
                      chunk_range: Tuple[int, int] = (5, 10)) -> LMClusteredTopicList:
    codebase = ""
    for chunk in chunks:
        codebase += chunk.get_chunkinfo()
        codebase += chunk.get_content() + DELIMETER
    
    IMPORTANT_CHUNKS = """
Here are chunks of code representing a repo:
{code}

Now take each of the seed chunks below and identify a group of other chunks,
together with the seed chunk, which forms a coherent set code grouping that
implements some functionality in the codebase. You are encouraged to optimize
for file diversity in your clusters, and to keep the size of your clusters
within {chunk_range_0} to {chunk_range_1} chunks.

Here are the seed clusters:
{seed_chunks}
"""
    return IMPORTANT_CHUNKS.format(
        code=codebase, 
        seed_chunks=identify_key_chunks(chunks, n_chunks=6),
        chunk_range_0=chunk_range[0],
        chunk_range_1=chunk_range[1]
    )