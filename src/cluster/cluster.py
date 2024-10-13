from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
import json

from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.transforms.cluster import cluster as cluster_cg
from src.index.service import get_or_create_index

from .types import LMClusteredTopic, ClusteredTopic, ClusterChunk, ClusterInputType, LMClusteredTopicList
from .methods.lmp import generate_clusters
from .chunk_repo import chunk_repo, temp_index_dir
from .utils import get_attrs_or_key


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

# Should track how good we are at tracking faraway chunks
def generate_llm_clusters(repo_path: Path, tries: int = 1) -> List[ClusteredTopic]:
    new_clusters = []
    cluster_inputs = chunk_repo(repo_path, mode="full", exclusions=EXCLUSIONS)

    # need sensible name because its easier for LLm to track
    unsorted_names = [f"Chunk {i}" for i, _ in enumerate(cluster_inputs)]
    name_to_chunk = {f"Chunk {i}": chunk for i, chunk in enumerate(cluster_inputs)}

    for _ in range(tries):
        output = generate_clusters(cluster_inputs, unsorted_names)
        # TODO: add structured parsing support to ell
        parsed = get_attrs_or_key(output, "parsed")
        clusters = LMClusteredTopicList.parse_obj(parsed).topics
        if not isinstance(clusters, list):
            raise LLMException(f"Failed to generate list: {clusters}")
        
        # calculate the clustered range
        # NOTE: chunk_name != chunk.id, former is for LLM, later is for us
        matched_indices = [i for cluster in clusters for i, chunk in enumerate(unsorted_names) 
                           if chunk in cluster.chunks]
        _calculate_clustered_range(matched_indices, len(unsorted_names))

        # convert LMClusteredTopic to ClusteredTopic
        for cluster in clusters:
            cluster.chunks = [name_to_chunk[chunk_name] for chunk_name in cluster.chunks]
            new_clusters.append(cluster)

        # remove chunks that have already been clustered
        cluster_inputs = [chunk for i, chunk in enumerate(cluster_inputs) 
                          if i not in matched_indices]
        unsorted_names = [chunk_name for i, chunk_name in enumerate(unsorted_names)
                          if i not in matched_indices]
        
        print("Unclassified chunks: ", len(unsorted_names))

    return new_clusters

# NOTE: generated clusters are not named
def generate_graph_clusters(repo_path: Path) -> List[ClusteredTopic]:
    chunks = get_or_create_index(str(repo_path), str(temp_index_dir(repo_path.name)), 
                                 exclusions=EXCLUSIONS)._docstore.docs.values()
    cg = ChunkGraph.from_chunks(repo_path, chunks)
    
    cluster_cg(cg)

    return [
        ClusteredTopic(
            name="random",
            chunks=[
                ClusterChunk(
                    id=chunk.og_id,
                    content=chunk.content,
                    filepath=chunk.file_path,
                    input_type=ClusterInputType.CHUNK
                ) for chunk in cluster.chunks
            ],
        ) 
        for cluster in cg.get_clusters()
    ]