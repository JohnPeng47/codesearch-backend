from pathlib import Path
from typing import List
import ell

from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.aider_graph.aider_graph import AiderGraph
from rtfs.transforms.cluster import cluster as cluster_cg
from src.index.service import get_or_create_index

from .types import (
    CodeChunk,
    SummaryChunk,
    ClusterInput,
    ClusteredTopic,
    ClusterInputType,
    LMClusteredTopicList
)
from .sum_chunks import summarize_chunk
from .chunk_repo import chunk_repo, temp_index_dir
from .utils import get_attrs_or_key

ell.init(
    store="logdir",
    autocommit=True,
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
You are given a codebase comprised of chunks separated by {delimiter}. Identify clusters of code that accomplish a common goal. Make sure
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
    return CLUSTER_PROMPT.format(codebase=codebase, delimiter=DELIMETER)

EXCLUSIONS = [
    "**/tests/**",
    "**/examples/**"
]

class LLMException(Exception):
    pass


# NOTE: maybe we can run the clustering algorithm beforehand to seed the order
# of the chunks, reducing the "distance" penalty in classification
def _calculate_clustered_range(matched_indices, length):
    """Measures how wide the range of the clustered chunks are"""
    pass

# TODO: need to add way to dedup chunks -> wait but we want overlapping clusters though
# Should track how good we are at tracking faraway chunks
def _generate_llm_clusters(cluster_inputs: List[ClusterInput], tries: int = 4) -> List[ClusteredTopic]:
    new_clusters = []

    # need sensible name because its easier for LLm to track
    unsorted_names = [f"Chunk {i}" for i, _ in enumerate(cluster_inputs)]
    name_to_chunk = {f"Chunk {i}": chunk for i, chunk in enumerate(cluster_inputs)}

    for i in range(1, tries + 1):
        if len(unsorted_names) == 0:
            break
        
        output = generate_clusters(cluster_inputs, unsorted_names)
        # TODO: add structured parsing support to ell
        parsed = get_attrs_or_key(output, "parsed")
        g_clusters = LMClusteredTopicList.parse_obj(parsed).topics # generated clusters
        if not isinstance(g_clusters, list):
            raise LLMException(f"Failed to generate list: {g_clusters}")
        
        # calculate the clustered range
        # NOTE: chunk_name != chunk.id, former is for LLM, later is for us
        matched_indices = [i for cluster in g_clusters for i, chunk in enumerate(unsorted_names) 
                           if chunk in cluster.chunks]
        _calculate_clustered_range(matched_indices, len(unsorted_names))

        # remove chunks that have already been clustered
        cluster_inputs = [chunk for i, chunk in enumerate(cluster_inputs) 
                          if i not in matched_indices]
        unsorted_names = [chunk_name for i, chunk_name in enumerate(unsorted_names)
                          if i not in matched_indices]

        # convert LMClusteredTopic to ClusteredTopic
        for g_cluster in g_clusters:
            chunks = []
            # in case of hallucinating chunk name
            try:
                for g_chunk_name in g_cluster.chunks:
                    chunks.append(name_to_chunk[g_chunk_name])
            except KeyError as e:
                print(f"Chunk Name: {g_chunk_name} hallucinated, skipping...")
                continue

            new_clusters.append(
                ClusteredTopic(
                    name=g_cluster.name, 
                    # yep, gotta convert pydantic to dict before it accepts it
                    # as a valid input ...
                    chunks=[chunk.dict() for chunk in chunks]
                ))
        
        print(f"Unclassified chunks, iter:[{i}]: ", len(unsorted_names))

    return new_clusters

def generate_full_code_clusters(repo_path: Path) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, mode="full", exclusions=EXCLUSIONS)

    return _generate_llm_clusters(chunks)


def generate_summarized_clusters(repo_path: Path) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, mode="full", exclusions=EXCLUSIONS)

    return _generate_llm_clusters(
        [
            SummaryChunk.from_chunk(chunk, summarize_chunk(chunk).parsed) 
            for chunk in chunks
        ]
    )

# NOTE: generated clusters are not named
def generate_graph_clusters(repo_path: Path) -> List[ClusteredTopic]:
    chunks = get_or_create_index(str(repo_path), str(temp_index_dir(repo_path.name)), 
                                 exclusions=EXCLUSIONS)._docstore.docs.values()
    cg = AiderGraph.from_chunks(repo_path, chunks)
    
    cluster_cg(cg)

    return [
        ClusteredTopic(
            name="random",
            chunks=[
                CodeChunk(
                    id=chunk.og_id,
                    content=chunk.content,
                    filepath=chunk.file_path,
                    input_type=ClusterInputType.CHUNK
                ) for chunk in cluster.chunks
            ],
        ) 
        for cluster in cg.get_clusters()
    ]
