from typing import List, Tuple
import ell
from enum import Enum

from src.utils import DELIMETER
from src.chunk.models import ClusterInput
from ..models import (
    ClusteredTopic,
    LMClusteredTopicList
)


class SeedChunkType(str, Enum):
    LOGIC = "CORE_LOGIC"
    DATASTRUCTS = "DATASTRUCTS"

# TODO: try again with code at the top of the prompt to trigger caching
@ell.complex(model="gpt-4o-2024-08-06")
def identify_key_chunks(chunks: List[ClusterInput],
                        seed_chunk_type: SeedChunkType = SeedChunkType.LOGIC, 
                        n_chunks: int = 6) -> LMClusteredTopicList:
    codebase = ""
    for chunk in chunks:
        codebase += chunk.get_chunkinfo()
        codebase += chunk.get_content() + DELIMETER

    IMPORTANT_CHUNKS = """
Here are chunks of code representing a repo:
{code}

List the {n_chunks} most important chunks of type {seed_chunk_type} in this code and 
give a short reason why. These chunks are going to be used as seeds in a clustering algorithm, so its important
that they dont overlap in terms of functionality

Here is an example output:
Chunk ID: embedding\generator.py::2
Reason: This chunk implements the core generate_embedding function, which is
fundamental to the vector embedding search component. It handles text
preprocessing, model selection, and integration with various embedding
providers. This is crucial for the library's main functionality of converting
text into vector representations for efficient similarity search.

Now generate the output
"""
    return IMPORTANT_CHUNKS.format(code=codebase, n_chunks=n_chunks)


@ell.complex(model="gpt-4o-2024-08-06", response_format=LMClusteredTopicList)
def generate_clusters(chunks: List[ClusterInput], 
                      chunk_range: Tuple[int, int] = (10, 10),
                      seed_chunk_type: SeedChunkType = SeedChunkType.LOGIC) -> LMClusteredTopicList:
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

Here are some example outputs on what you clusters should look like:

1. Vector Embedding Generation Cluster:

Seed: embedding\generator.py::2 (Core embedding generation functionality)
embedding\models.py::1 (Definitions of different embedding models)
embedding\tokenizer.py::3 (Text tokenization for embedding generation)
utils\text_processing.py::2 (Text preprocessing utilities)
providers\openai_embeddings.py::1 (OpenAI API integration for embeddings)


2. Vector Storage and Indexing Cluster:

Seed: storage\vector_store.py::3 (Main vector storage implementation)
storage\indexing.py::2 (Indexing strategies for fast retrieval)
storage\compression.py::1 (Vector compression techniques)
utils\serialization.py::4 (Serialization methods for vector data)
config\storage_config.py::1 (Configuration for vector storage)

Here are the seed clusters:
{seed_chunks}

Now generate the list of clusters according to the examples above
"""
    return IMPORTANT_CHUNKS.format(
        code=codebase, 
        seed_chunks=identify_key_chunks(chunks, seed_chunk_type=seed_chunk_type, n_chunks=6),
        chunk_range_0=chunk_range[0],
        chunk_range_1=chunk_range[1]
    )