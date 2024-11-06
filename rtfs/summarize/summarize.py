import yaml
from typing import Dict, List
import random
from dataclasses import dataclass

from ..chunk_resolution.graph import (
    ChunkNode,
    ClusterNode,
    NodeKind,
    SummarizedChunk,
    ClusterEdgeKind,
)
from .lmp import (
    summarize as summarize_llm,
    categorize_clusters as recategorize_llm,
    categorize_missing,
)
from .lmp import ClusterList

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
            provider="openai",
            model_name="gpt-4o-2024-08-06",
            temperature=0
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
        for cluster_id, child_content in self._iterate_clusters_with_text():
            summary_data = summarize_llm(self._model, child_content)

            print("updating node: ", cluster_id, "with summary: ", summary_data)
            cluster_node = ClusterNode(id=cluster_id, **summary_data.dict())
            self.graph.update_node(cluster_node)

    def gen_categories(self):
        """
        Attempts relabel of clusters. If relabel attempt misses any existing clusters, will iteratively
        retry relabeling until all clusters are accounted for.
        """

        def cluster_yaml_str(cluster_nodes):
            clusters_json = self.graph.clusters(cluster_nodes)
            for cluster in clusters_json:
                cluster.pop("chunks")
                cluster.pop("key_variables")

            return yaml.dump(
                clusters_json,
                Dumper=VerboseSafeDumper,
                sort_keys=False,
            ), [cluster["title"] for cluster in clusters_json]

        retries = 3
        previous_clusters = []
        cluster_yaml, og_clusters = self._clusters_to_yaml(
            self.graph.filter_nodes({"kind": NodeKind.Cluster})
        )
        while retries > 0:
            try:
                # TODO: redo this logic here
                generated_clusters: ClusterList = (
                    recategorize_llm(self._model, cluster_yaml)
                    if retries == 3
                    else categorize_missing(self._model, cluster_yaml, previous_clusters)
                )
                generated_child_clusters = []
                for category in generated_clusters.clusters:
                    # why do I still get empty clusters?
                    if not category.children:
                        continue

                    cluster_node = self.graph.find_node(
                        {"kind": NodeKind.Cluster, "title": category.category}
                    )
                    if not cluster_node:
                        cluster_node = ClusterNode(
                            id=get_cluster_id(),
                            title=category.category,
                            kind=NodeKind.Cluster,
                        )
                        self.graph.add_node(cluster_node)

                    for child in category.children:
                        child_node = self.graph.find_node(
                            {"kind": NodeKind.Cluster, "title": child}
                        )
                        if not child_node:
                            print("Childnode not found: ", child)
                            continue

                        self.graph._graph.add_edge(
                            child_node.id,
                            cluster_node.id,
                            kind=ClusterEdgeKind.ClusterToCluster,
                        )
                        generated_child_clusters.append(child_node.id)

                # TODO: if more, we dont really care, can prune
                if len(og_clusters) > len(generated_child_clusters):
                    missing = set(og_clusters) - set(generated_child_clusters)
                    raise LLMValidationError(
                        f"Missing clusters from generated categories: {list(missing)}"
                    )
                else:
                    break

            except LLMValidationError as e:
                cluster_yaml, og_clusters = cluster_yaml_str(
                    [self.graph.get_node(c) for c in generated_child_clusters]
                )
                previous_clusters = [
                    cluster.category for cluster in generated_clusters.clusters
                ]
                retries -= 1
                if retries == 0:
                    raise Exception("Failed to generate categories")

            except Exception as e:
                raise e

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

    def _clusters_to_yaml(self, cluster_nodes: List[ClusterNode]):
        clusters_json = self.graph.clusters(cluster_nodes)
        for cluster in clusters_json:
            del cluster["chunks"]
            del cluster["key_variables"]

        return yaml.dump(
            clusters_json,
            Dumper=VerboseSafeDumper,
            sort_keys=False,
        ), [cluster["id"] for cluster in clusters_json]
