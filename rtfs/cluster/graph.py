from pathlib import Path
from typing import List, Dict
from llama_index.core.schema import BaseNode
import networkx as nx
from dataclasses import dataclass
from pydantic import BaseModel

from rtfs.chunk_resolution.graph import ClusterNode, ChunkNode, ChunkMetadata, NodeKind
from rtfs.graph import CodeGraph


import yaml
from typing import Dict, List
import random
from dataclasses import dataclass

from ..chunk_resolution.graph import (
    ChunkNode,
    ClusterNode,
    NodeKind,
    SummarizedChunk,
)

from rtfs.graph import CodeGraph
from moatless.types import MoatlessChunkID


def get_cluster_id():
    return random.randint(1, 10000000)


@dataclass(kw_only=True)
class SummarizedChunk:
    id: str
    og_id: MoatlessChunkID # this is the original ID of the chunk
    file_path: str
    content: str
    start_line: int
    end_line: int


@dataclass(kw_only=True)
class SummarizedCluster:
    id: str
    title: str
    key_variables: List[str]
    summary: str
    chunks: List[SummarizedChunk]
    children: List["SummarizedCluster"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "key_variables": self.key_variables,
            "summary": self.summary,
            "chunks": [chunk.__dict__ for chunk in self.chunks],
            "children": [child.to_dict() for child in self.children],
        }


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

    def get_clusters(self) -> List[SummarizedCluster]:
        cluster_nodes = [
            node
            for node in self.filter_nodes({"kind": NodeKind.Cluster})
            if len(self.parents(node.id)) == 0
        ]

        return self._clusters(cluster_nodes, return_type="obj")

    def _clusters(
        self, cluster_nodes: List[ClusterNode], return_type: str = "json"
    ) -> List[Dict | SummarizedCluster]:
        """
        Returns a list of clusters and their child chunk nodes. Returns either
        JSON or as SummarizedCluster
        """

        def dfs_cluster(cluster_node: ClusterNode) -> SummarizedCluster:
            chunks = []
            children = []

            for child in self.children(cluster_node.id):
                child_node: ChunkNode = self.get_node(child)
                if child_node.kind == NodeKind.Chunk:
                    chunk_info = SummarizedChunk(
                        id=child_node.id,
                        og_id=child_node.og_id,
                        file_path=child_node.metadata.file_path,
                        content=child_node.content,
                        start_line=child_node.range.line_range()[0],
                        end_line=child_node.range.line_range()[1],
                    )
                    chunks.append(chunk_info)
                elif child_node.kind == NodeKind.Cluster:
                    children.append(dfs_cluster(child_node))

            return SummarizedCluster(
                id=cluster_node.id,
                title=cluster_node.title,
                key_variables=cluster_node.key_variables[:4],
                summary=cluster_node.summary,
                chunks=chunks,
                children=children,
            )

        if return_type == "json":
            return [dfs_cluster(node).to_dict() for node in cluster_nodes]
        else:
            return [dfs_cluster(node) for node in cluster_nodes]


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
