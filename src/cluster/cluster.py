from pathlib import Path
from typing import List
import ell
import random
from openai import LengthFinishReasonError
import json

from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.aider_graph.aider_graph import AiderGraph
from rtfs.transforms.cluster import cluster as cluster_cg
from src.index.service import get_or_create_index
from src.utils import num_tokens_from_string

from .types import (
    CodeChunk,
    SummaryChunk,
    ClusterInput,
    ClusteredTopic,
    ClusterInputType,
    LMClusteredTopicList
)
from .sum_chunks import summarize_chunk
from .chunk_repo import chunk_repo, temp_index_dir, ChunkStrat
from .utils import get_attrs_or_key

# from .lmp.cluster_v1 import generate_clusters
from .lmp.cluster_v2 import generate_clusters

from src.config import GRAPH_ROOT

ell.init(
    store="./ell_storage/chunk_alt",
    autocommit=True,
)

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

# TODO: test how well LLM can select chunks using the short ID
# should prolly use this, to reduce code, if not increase token cost
# 2x more token usage ~ 5 tokens more per id
# 5 * 200 = 1000 tokens extra using this id ...
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
                    chunks=[
                        # TODO: need to do this or else pydantic shits bed
                        # for empty {} validation for metadata field
                        {k:v for k,v in chunk.dict().items()
                            if k != "metadata"} for chunk in chunks]
                ))
        
        print(f"Unclassified chunks, iter:[{i}]: ", len(unsorted_names))

    return new_clusters

def _generate_llm_clusters_v2(cluster_inputs: List[ClusterInput], tries: int = 4) -> List[ClusteredTopic]:
    new_clusters = []

    for i in range(1, tries + 1):
        if len(cluster_inputs) == 0:
            break
        
        output = generate_clusters(cluster_inputs)
        # TODO: add structured parsing support to ell
        parsed = get_attrs_or_key(output, "parsed")
        g_clusters = LMClusteredTopicList.parse_obj(parsed).topics # generated clusters
        if not isinstance(g_clusters, list):
            raise LLMException(f"Failed to generate list: {g_clusters}")

        for i, cluster in enumerate(g_clusters):
            chunks = []
            for chunk in cluster.chunks:
                try:
                    matching_chunk = next(filter(lambda c: c.get_name() == chunk, cluster_inputs))
                except StopIteration as e:
                    print(f"Chunk Name: {chunk} hallucinated, skipping...")
                    continue

                chunks.append(matching_chunk)
                cluster_inputs.remove(matching_chunk)

            print("New Cluster: ", cluster)

            new_clusters.append(
                ClusteredTopic(
                    name=cluster.name, 
                    chunks=[
                        {k:v for k,v in chunk.dict().items()
                            if k != "metadata"} for chunk in chunks]
                )
            )

        print(f"Unclassified chunks, iter:[{i}]: ", len(cluster_inputs))
        return

    return new_clusters

def generate_full_code_clusters(repo_path: Path, 
                                chunk_strat: ChunkStrat = ChunkStrat.VANILLA) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, chunk_strat, mode="full", exclusions=EXCLUSIONS)
    return _generate_llm_clusters_v2(chunks)


def generate_summarized_clusters(repo_path: Path,
                                chunk_strat: ChunkStrat = ChunkStrat.VANILLA) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, chunk_strat, mode="full", exclusions=EXCLUSIONS)

    summary_chunks = []
    for chunk in chunks:
        try:
            summary = summarize_chunk(chunk).parsed
        except LengthFinishReasonError as e:
            print(f"[Summarize Chunk] Chunk too long: {len(chunk.content)}, continuing...")
            continue

        summary_chunk = SummaryChunk.from_chunk(chunk, summary)
        summary_chunks.append(summary_chunk)

    summary_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in summary_chunks]))
    code_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in chunks]))

    print(f"Summary tokens: {summary_tokens}, \
          Code tokens: {code_tokens}, \
          Ratio: {summary_tokens / code_tokens}")

    return _generate_llm_clusters(summary_chunks)

# NOTE: generated clusters are not named
def generate_graph_clusters(repo_path: Path) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, ChunkStrat.VANILLA, mode="full", exclusions=EXCLUSIONS)
    cg = AiderGraph.from_chunks(repo_path, chunks)

    cluster_cg(cg)

    return [
        ClusteredTopic(
            name="Graph Cluster",
            chunks=[
                CodeChunk(
                    id=chunk.og_id,
                    content=chunk.content,
                    filepath=chunk.file_path,
                    input_type=ClusterInputType.CHUNK,
                ).dict() for chunk in cluster.chunks
            ],
        ) 
        for cluster in cg.get_clusters()
    ]


def generate_random_clusters(repo_path: Path, size: int = 4, num_clusters: int = 4) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, ChunkStrat.VANILLA, mode="full", exclusions=EXCLUSIONS)

    return [
        ClusteredTopic(
            name=f"Random {i}",
            chunks=[
                chunk.dict() for chunk in random.sample(chunks, size)
            ],
        )
        for i in range(num_clusters)
    ] 