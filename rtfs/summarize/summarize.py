import yaml
from typing import Dict, List
import random
from dataclasses import dataclass

from src.config import MODEL_CONFIG
from ..chunk_resolution.graph import (
    ClusterNode,
    NodeKind,
)
from .lmp import (
    summarize as summarize_llm,
    categorize_clusters as recategorize_llm,
    categorize_missing,
)
from .lmp import ClusterList

from rtfs.graph import EdgeKind
from rtfs.cluster.cluster_graph import ClusterGraph
from rtfs.utils import VerboseSafeDumper
from rtfs.exceptions import LLMValidationError

from llm import LLMModel
from moatless.types import MoatlessChunkID


def get_cluster_id():
    return random.randint(1, 10000000)

class Summarizer:
    def __init__(self, graph: ClusterGraph):
        self._model = LLMModel(
            provider=MODEL_CONFIG["ClusterSummarizer"]["provider"],
        )
        self.graph = graph

    # TODO: can generalize this to only generating summaries for parent nodes
    # this way we can use generic CodeGraph abstraction
    # OR
    # we can make use of only the edge information -> tag special parent ch
    # actually... this is pointless?

    # TODO: we can parallelize this
    # TODO: reimplement test_run
    def summarize(self):
        previous_names = []
        for cluster_id, child_content in self._iterate_clusters_with_text():
            summary_data = summarize_llm(self._model, child_content, previous_names)
            previous_names.append(summary_data.title)

            print("updating node: ", cluster_id, "with summary: ", summary_data)
            cluster_node = ClusterNode(id=cluster_id, **summary_data.dict())
            self.graph.update_node(cluster_node)

    def _iterate_clusters_with_text(self):
        """
        Concatenates the content of all children of a cluster node
        """
        for cluster in [
            node
            for node, data in self.graph._graph.nodes(data=True)
            if data["kind"] == NodeKind.Cluster
        ]:
            child_content = "\n".join(
                [
                    self.graph.get_node(c).get_content()
                    for c in self.graph.children(cluster)
                    if self.graph.get_node(c).kind
                    in [NodeKind.Chunk, NodeKind.Cluster]
                ]
            )
            yield (cluster, child_content)

    def get_output(self):
        return self.graph.get_clusters()