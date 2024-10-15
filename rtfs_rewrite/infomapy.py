import networkx as nx
from infomap import Infomap
from typing import Dict, List

from logging import getLogger

logger = getLogger(__name__)


def cluster_infomap(digraph: nx.DiGraph) -> Dict[str, int]:
    # Initialize Infomap
    infomap = Infomap("--seed 42 --two-level", silent=True)

    # Create a mapping from NetworkX node IDs to integer IDs
    node_id_map = {node: idx for idx, node in enumerate(digraph.nodes())}
    reverse_node_id_map = {idx: node for node, idx in node_id_map.items()}

    # Add nodes and edges to Infomap using integer IDs
    for edge in digraph.edges():
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
