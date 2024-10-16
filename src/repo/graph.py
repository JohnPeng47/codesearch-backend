import os
import json
from pathlib import Path
from enum import Enum

from moatless.index import CodeIndex

from src.index.service import get_or_create_index
from rtfs.summarize.summarize import Summarizer
from rtfs.transforms.cluster import cluster
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.aider_graph.aider_graph import AiderGraph
from rtfs.cluster.graph import ClusterGraph
from src.utils import rm_tree

from logging import getLogger

logger = getLogger(__name__)


class GraphType(str, Enum):
    STANDARD = "standard"
    AIDER = "aider"


def get_or_create_chunk_graph(
    code_index: CodeIndex, repo_path: str, graph_path: str, type: GraphType
) -> ClusterGraph:
    graph_path = f"{graph_path}_{type}.json"
    nodes = code_index._docstore.docs.values()
    try:
        if os.path.exists(graph_path):
            with open(graph_path, "r") as f:
                graph_dict = json.load(f)

            if type == GraphType.STANDARD:
                cg = ChunkGraph.from_json(Path(repo_path), graph_dict)
            elif type == GraphType.AIDER:
                cg = AiderGraph.from_json(Path(repo_path), graph_dict)
            return cg

        else:
            if type == GraphType.STANDARD:
                cg = ChunkGraph.from_chunks(Path(repo_path), nodes)
            elif type == GraphType.AIDER:
                cg = AiderGraph.from_chunks(repo_path, nodes)

            with open(graph_path, "w") as f:
                json.dump(cg.to_json(), f)

            return cg
    except Exception as e:
        if os.path.exists(graph_path):
            rm_tree(graph_path)

        raise e


def summarize(
    index_path: str,
    repo_path: str,
    graph_path: str,
    graph_type: GraphType = GraphType.STANDARD,
):
    code_index = get_or_create_index(repo_path, index_path)
    cg = get_or_create_chunk_graph(code_index, repo_path, graph_path, graph_type)

    cluster(cg)

    # TODO: move summarizer to ClusterGraph
    summarizer = Summarizer(cg)
    summarizer.summarize()
    summarizer.gen_categories()

    logger.info(f"Summarizing stats: {graph_type} for {repo_path}: \n{cg.get_stats()}")

    return summarizer.to_json()
