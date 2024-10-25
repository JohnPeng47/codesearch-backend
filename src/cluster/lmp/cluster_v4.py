from typing import List, Tuple
from pydantic import BaseModel
import ell
from enum import Enum
from src.chunk.models import ClusterInput
from ..models import (
    ClusteredTopic,
    LMClusteredTopicList,
    LMClusteredTopic
)

DELIMETER = f"\n\n{'-' * 80}\n" # only 1 tokens good deal!

class ChunkType(str, Enum):
    LOGIC = "\{code\}"
    DATA_STRUCTURE = "\{data_structure\}"


# TODO: try again with code at the top of the prompt to trigger caching
@ell.complex(model="gpt-4o-2024-08-06")
def identify_key_chunks(chunks: List[ClusterInput], 
                      n_chunks: int = 6,
                      chunk_type: ChunkType = ChunkType.LOGIC) -> LMClusteredTopicList:
    codebase = ""
    for chunk in chunks:
        codebase += chunk.get_chunkinfo()
        codebase += chunk.get_content() + DELIMETER

    IMPORTANT_CHUNKS = """
Here are chunks of code representing a repo:
{code}

List the {n_chunks} most important chunks of type {chunk_type} in this code and 
give a short reason why. These chunks are going to be used as seeds in a clustering algorithm,
so its important that they dont overlap in terms of functionality

Here is an example output:
Chunk ID: embedding\generator.py::2
Reason: This chunk implements the core generate_embedding function, which is
fundamental to the vector embedding search component. It handles text
preprocessing, model selection, and integration with various embedding
providers. This is crucial for the library's main functionality of converting
text into vector representations for efficient similarity search.

Now generate the output
"""
    return IMPORTANT_CHUNKS.format(code=codebase, n_chunks=n_chunks, chunk_type=chunk_type)


@ell.complex(model="gpt-4o-2024-08-06")
def generate_clusters_raw(chunks: List[ClusterInput],
                      chunk_type: ChunkType = ChunkType.LOGIC) -> LMClusteredTopicList:
    codebase = ""
    for chunk in chunks:
        codebase += chunk.get_chunkinfo()
        codebase += chunk.get_content() + DELIMETER
    
    GEN_CLUSTERS = """
Here are chunks of code representing a repo:
{code}

Now take each of the seed chunks below and identify a group of other chunks,
together with the seed chunk, which forms a coherent set code grouping that
implements some functionality in the codebase. You are encouraged to optimize
for file diversity in your clusters. You are also encouraged to not create clusters
of less than 3. There are no upper bound restrictions
Here are some example outputs on what you clusters should look like:

# 1. Vector Embedding Generation Cluster:

# Seed: embedding\generator.py::2 (Core embedding generation functionality)
# embedding\models.py::1 (Definitions of different embedding models)
# embedding\tokenizer.py::3 (Text tokenization for embedding generation)
# utils\text_processing.py::2 (Text preprocessing utilities)
# providers\openai_embeddings.py::1 (OpenAI API integration for embeddings)


# 2. Vector Storage and Indexing Cluster:

# Seed: storage\vector_store.py::3 (Main vector storage implementation)
# storage\indexing.py::2 (Indexing strategies for fast retrieval)
# storage\compression.py::1 (Vector compression techniques)
# utils\serialization.py::4 (Serialization methods for vector data)
# config\storage_config.py::1 (Configuration for vector storage)

Here are the seed chunks:
{seed_chunks}

Now generate the list of clusters according to the examples above
"""
    return GEN_CLUSTERS.format(
        code=codebase, 
        seed_chunks=identify_key_chunks(chunks, n_chunks=6, chunk_type=chunk_type)
    )

class LMChunkWithDescription(BaseModel):
    name: str
    description: str

class LMClusteredTopicDescr(ClusteredTopic):
    """
    Output of the clustering algorithm
    """
    name: str
    chunks: List[LMChunkWithDescription]

class LMClusteredTopicListDescr(BaseModel):
    topics: List[LMClusteredTopicDescr]


# TODO: potentially eliminating this last step
@ell.complex(model="gpt-4o-mini", response_format=LMClusteredTopicList)
def generate_clusters_lmp(chunks: List[ClusterInput], 
                      chunk_type: ChunkType = ChunkType.LOGIC) -> LMClusteredTopicList:
    CONVERT_LLM_RES = """
Convert the following LLM response to JSON. When converting to the chunks field, make sure
you only take the chunk name and without the description in parenthesis, which looks like the following:

storage\indexing.py::2 
storage\compression.py::1 
config\storage_config.py::1 (Configuration for vector storage)
storage\indexing.py::2 (Indexing strategies for fast retrieval)

Here is the LLM response:

{llm_res}
"""
    return CONVERT_LLM_RES.format(llm_res=generate_clusters_raw(chunks, chunk_type))

def generate_clusters(chunks: List[ClusterInput], 
                      chunk_type: ChunkType = ChunkType.LOGIC) -> List[LMClusteredTopic]: 
    all_clusters = []
    for chunk_type in ChunkType:
        clusters: LMClusteredTopicList = generate_clusters_lmp(chunks, chunk_type=chunk_type.value).parsed
        all_clusters.extend(clusters.topics)

    return all_clusters
