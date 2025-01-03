import itertools
import copy
from typing import List, Tuple
from pydantic import BaseModel

from llm import LLMModel
from rtfs.cluster.graph import Cluster
from src.utils import DELIMETER

from .graph_ops import MoveOp

# TODO: use this with the proper apply code
# from .graph_ops import MoveOp

class MoveOpList(BaseModel):
    moves: List[MoveOp]

def compare_pairwise_llm(model: LLMModel, 
                         clusters: List[Cluster], 
                         use_summaries: bool) -> str:
    cluster_flags = {"return_content": not use_summaries, "return_summaries": use_summaries}

    COMPARE_PAIRWISE = """
You are given two groups of code clusters. They are outputted from a previous clustering algorithm, which may or may not have constructed suboptimum clusters
Your task is to move chunks in-between clusters in order to maximize the overall coherence and cohesion of the chunks within a single cluster
Don't be afraid to merge two clusters completely ie. move all the chunks from one cluster to another

Write out a series of moves that you woud make in the following format:
(src_cluster, dst_cluster, chunk_name)   

Here are some examples:
(10, 1, storage\indexing.py::2)
(2, 4, storage\compression.py::1)

Here are the clusters:
{clusters}
"""
    return model.invoke(
        COMPARE_PAIRWISE.format(clusters=f"\n\n{DELIMETER}".join(
            [cluster.to_str(**cluster_flags) for cluster in clusters])
        ), 
        model_name="gpt-4o"
    )

def convert(model: LLMModel, move_text: str) -> MoveOpList:
    CONVERT = """
Parse the following text that contains cluster move operations.
Each line should be in the format: (src_cluster, dst_cluster, chunk_name)

Convert these into a list of JSON objects with the fields:
- src_cluster: string
- dst_cluster: string  
- chunk: string

Text to parse:
{moves}
"""
    return model.invoke(
        CONVERT.format(moves=move_text),
        model_name="gpt-4o-mini",
        response_format=MoveOpList
    )

def split_clusters(clusters: List[Cluster], groups: int = 3) -> List[List[Cluster]]:
    """
    Takes a list of clusters, and splits into groups such that the number of chunks in each
    group is about the equal
    """
    # Sort clusters by number of chunks in descending order
    sorted_clusters = sorted(clusters, key=lambda c: len(c.chunks), reverse=True)
    
    # Initialize groups with empty lists
    cluster_groups = [[] for _ in range(groups)]
    chunk_counts = [0] * groups
    used_clusters = set()
    
    # Use greedy approach - assign each cluster to group with fewest chunks
    for cluster in sorted_clusters:
        # Skip if cluster already assigned
        if cluster in used_clusters:
            continue
            
        # Find group with minimum chunks
        min_chunks_idx = chunk_counts.index(min(chunk_counts))
        
        # Add cluster to that group and mark as used
        cluster_groups[min_chunks_idx].append(cluster)
        chunk_counts[min_chunks_idx] += len(cluster.chunks)
        used_clusters.add(cluster)
        
    return cluster_groups

# TODO: should have some way isolating hallucination potential in code 
# like, maybe wrap it all inside a LMP interface
# TODO-EVAL: evaluate this by running this again on output clusters to see if additional moves are suggested
# TODO: rewrie this using MoveOps/GraphOps framework
# - provide a series of LLM ops to the prompt
# - each op has executed side effect on the graph
# - how to we combine the moveOp prompt with a generic command that requires several moveOps?
# In general, should investigate this a way to achieve combinatorial flexibility between prompt space and code space
def regroup_clusters(model: LLMModel,
                     clusters: List[Cluster], 
                     cg,
                     use_summaries: bool) -> Tuple[List[Cluster], List[MoveOp]]:
    """
    Compares groups of clusters together and generates a list of move ops that move a single
    chunk from one cluster to another to better maximize the coherence of the clusters
    """
    cluster_sets = split_clusters(clusters)
    cgroups = itertools.combinations(cluster_sets, 2)
    all_moves = []

    # Create a deep copy of clusters to modify
    new_clusters = copy.deepcopy(clusters)
    cluster_map = {c.id: c for c in new_clusters}

    for cs1, cs2 in cgroups:
        raw_moves = compare_pairwise_llm(model, cs1 + cs2, use_summaries)
        movelist = convert(model, raw_moves)
        all_moves.extend(movelist.moves)

    return new_clusters, all_moves