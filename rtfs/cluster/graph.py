from pathlib import Path
from typing import List, Dict
from llama_index.core.schema import BaseNode
import networkx as nx
from dataclasses import dataclass
from pydantic import BaseModel

from rtfs.chunk_resolution.graph import ClusterNode, ChunkNode, ChunkMetadata, NodeKind
from rtfs.graph import CodeGraph


class ClusterGStats(BaseModel):
    num_clusters: int
    num_chunks: int
    avg_cluster_sz: float

    def __str__(self):
        return f"""
Clusters: {self.num_clusters}, 
Chunks: {self.num_chunks}, 
Avg Cluster Size: {self.avg_cluster_sz:.2f}
        """


class ClusterGraph(CodeGraph):
    def __init__(
        self,
        *,
        repo_path: Path,
        graph: nx.MultiDiGraph,
        cluster_roots: List[str] = [],
    ):
        super().__init__(graph=graph, node_types=[ChunkNode, ClusterNode])

        self.repo_path = repo_path
        self._cluster_roots = cluster_roots

    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[BaseNode]):
        raise NotImplementedError("Not implemented yet")

    @classmethod
    def from_json(cls, repo_path: Path, json_data: Dict):
        cg = nx.node_link_graph(json_data["link_data"])
        for _, node_data in cg.nodes(data=True):
            if "metadata" in node_data:
                node_data["metadata"] = ChunkMetadata(**node_data["metadata"])

        return cls(
            repo_path=repo_path,
            graph=cg,
            cluster_roots=json_data.get("cluster_roots", []),
        )

    def to_json(self):
        def custom_node_link_data(G):
            data = {
                "directed": G.is_directed(),
                "multigraph": G.is_multigraph(),
                "graph": G.graph,
                "nodes": [],
                "links": [],
            }

            for n, node_data in G.nodes(data=True):
                node_dict = node_data.copy()
                node_dict.pop("references", None)
                node_dict.pop("definitions", None)

                if "metadata" in node_dict and isinstance(
                    node_dict["metadata"], ChunkMetadata
                ):
                    node_dict["metadata"] = node_dict["metadata"].to_json()

                node_dict["id"] = n
                data["nodes"].append(node_dict)

            for u, v, edge_data in G.edges(data=True):
                edge = edge_data.copy()
                edge["source"] = u
                edge["target"] = v
                data["links"].append(edge)

            return data

        graph_dict = {}
        graph_dict["cluster_roots"] = self._cluster_roots
        graph_dict["link_data"] = custom_node_link_data(self._graph)

        return graph_dict

    # Utility methods
    def get_chunk_files(self) -> List[str]:
        return [
            chunk_node.metadata.file_path
            for chunk_node in self.filter_nodes({"kind": NodeKind.Chunk})
        ]

    def get_stats(self):
        clusters = self.filter_nodes({"kind": NodeKind.Cluster})

        num_chunks = 0
        for cluster in clusters:
            for child in [
                chunk_node
                for chunk_node in self.children(cluster.id)
                if self.get_node(chunk_node).kind == NodeKind.Chunk
            ]:
                num_chunks += 1

        return ClusterGStats(
            num_chunks=num_chunks,
            num_clusters=len(clusters),
            avg_cluster_sz=num_chunks / len(clusters),
        )
