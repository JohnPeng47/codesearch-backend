from infomap import Infomap
import networkx as nx
from logging import getLogger
from typing import List, Tuple, Dict

from rtfs.chunk_resolution.graph import (
    ClusterNode,
    ClusterEdgeKind,
    ClusterEdge,
    ChunkNodeID,
)
from rtfs.graph import CodeGraph

logger = getLogger(__name__)


def cluster_infomap(network: CodeGraph) -> Dict[str, int]:
    # Initialize Infomap
    infomap = Infomap("--seed 42 --two-level", silent=True)

    # Taking the first element of the tuple as the node id
    node_id_map = {node: idx for idx, node in enumerate(network._graph.nodes())}
    reverse_node_id_map = {idx: node for node, idx in node_id_map.items()}

    # Add nodes and edges to Infomap using integer IDs
    for edge in network._graph.edges():
        infomap.addLink(node_id_map[edge[0]], node_id_map[edge[1]])

    # Run Infomap clustering
    infomap.run()

    cluster_dict: Dict[int, List] = {}
    # node_id, path
    # 1 (1, 2, 2)
    for node, levels in infomap.get_multilevel_modules().items():
        node_id = reverse_node_id_map[node]
        cluster_dict[node_id] = levels[-1]

    # replace leaf nodes with their original id
    return cluster_dict


def cluster(graph: CodeGraph, alg: str = "infomap") -> Dict[ChunkNodeID, Tuple]:
    """
    Entry method for cluster construction on ChunkGraph
    """
    if alg == "infomap":
        cluster_dict = cluster_infomap(graph)
    else:
        raise Exception(f"{alg} not supported")

    for chunk_node, cluster in cluster_dict.items():
        if not graph.has_node(cluster):
            graph.add_node(ClusterNode(id=cluster))

        cluster_edge = ClusterEdge(
            src=chunk_node, dst=cluster, kind=ClusterEdgeKind.ChunkToCluster
        )
        graph.add_edge(cluster_edge)

    return cluster_dict
