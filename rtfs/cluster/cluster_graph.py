from pathlib import Path
from typing import List, Dict, Optional
from llama_index.core.schema import BaseNode
import networkx as nx
from dataclasses import dataclass
from pydantic import BaseModel

from rtfs.chunk_resolution.graph import ClusterNode, ChunkNode, ChunkMetadata, NodeKind
from rtfs.graph import CodeGraph, Edge
from rtfs.cluster.infomap import cluster_infomap
from rtfs.cluster.graph import (
    ClusterRefEdge,
    ClusterEdge,
    ClusterEdgeKind,
    Cluster,
    ClusterChunk,
    ClusterGStats
)

from src.cluster.models import ClusteredTopic

    
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
    
    def cluster(self, alg="infomap"):
        """
        Performs the actual clustering operation on the graph
        """
        if alg == "infomap":
            cluster_dict = cluster_infomap(self)
        else:
            raise Exception(f"{alg} not supported")

        for chunk_node, cluster in cluster_dict.items():
            if not self.has_node(cluster):
                self.add_node(ClusterNode(id=cluster))

            cluster_edge = ClusterEdge(
                src=chunk_node, dst=cluster, kind=ClusterEdgeKind.ChunkToCluster
            )
            self.add_edge(cluster_edge)

    def clusters(
        self, 
        cluster_nodes: List[ClusterNode], 
        return_content: bool = False,
        return_type: str = "json"
    ) -> List[Dict | Cluster]:
        """
        Returns a list of clusters and their child chunk nodes. Returns either
        JSON or as Cluster
        """

        def dfs_cluster(cluster_node: ClusterNode) -> Cluster:
            chunks = []
            children = []

            for child in self.children(cluster_node.id):
                child_node: ChunkNode = self.get_node(child)
                if child_node.kind == NodeKind.Chunk:
                    chunk_info = ClusterChunk(
                        id=child_node.id,
                        og_id=child_node.og_id,
                        file_path=child_node.metadata.file_path,
                        start_line=child_node.range.line_range()[0] + 1,
                        end_line=child_node.range.line_range()[1] + 1,
                        content=child_node.content if return_content else "",
                    )
                    chunks.append(chunk_info)
                elif child_node.kind == NodeKind.Cluster:
                    children.append(dfs_cluster(child_node))

            return Cluster(
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


    def get_clusters(self, return_content: bool = False) -> List[Cluster]:
        cluster_nodes = [
            node
            for node in self.filter_nodes({"kind": NodeKind.Cluster})
            # looking for top-level parent clusters
            if len(self.parents(node.id)) == 0
        ]

        return self.clusters(cluster_nodes, return_content, return_type="obj")
    
    def build_cluster_edges(self):
        """
        Construct edges between clusters based on the edges between their chunks
        """
        cluster_nodes = [
            node
            for node in self.filter_nodes({"kind": NodeKind.Cluster})
            # looking for bottom level child clusters
            if len(self.parents(node.id)) != 0
        ]

        # Create edges between clusters based on chunk relationships
        for cluster_node in cluster_nodes:
            cluster_chunks = [
                self.get_node(child) for child in self.children(cluster_node.id)
                if self.get_node(child).kind == NodeKind.Chunk
            ]
            
            # For each chunk in this cluster
            for chunk in cluster_chunks:
                # Get all edges from this chunk
                for src, dst, data in self._graph.edges(chunk.id, data=True):
                    target_chunk = self.get_node(dst)
                    
                    # Skip if target is not a chunk
                    if target_chunk.kind != NodeKind.Chunk:
                        continue
                        
                    # Find the cluster that contains the target chunk
                    target_parents = self.parents(target_chunk.id)
                    
                    if not target_parents:
                        continue
                        
                    target_cluster_id = target_parents[0]
                    parent_node = self.get_node(target_cluster_id)
                    if parent_node.kind != NodeKind.Cluster:
                        continue
                    
                    # Add edge between clusters if they're different
                    if target_cluster_id != cluster_node.id:
                        print("Adding edge: ", data["ref"], cluster_node.id, target_cluster_id)
                        self.add_edge(
                            ClusterRefEdge(
                                src=cluster_node.id,
                                dst=target_cluster_id,
                                ref=data["ref"]
                            )
                        )

    def get_longest_path(self, num_paths: int = 10):
        """
        Returns the num_paths longest paths between clusters connected by reference edges.
        Each path is a list of cluster IDs.
        """
        # Get subgraph of only cluster nodes and their reference edges
        cluster_nodes = [
            node.id for node in self.filter_nodes({"kind": NodeKind.Cluster})
        ]
        cluster_subgraph = self._graph.subgraph(cluster_nodes)

        # Find all simple paths between all pairs of nodes
        all_paths = []
        for src in cluster_nodes:
            for dst in cluster_nodes:
                if src != dst:
                    # Get all simple paths between src and dst
                    paths = list(nx.all_simple_paths(cluster_subgraph, src, dst))
                    all_paths.extend(paths)

        # Sort paths by length in descending order and return top num_paths
        all_paths.sort(key=len, reverse=True)
        
        # Convert paths to use titles instead of IDs
        all_paths = [
            [self.get_node(node).title for node in path] for path in all_paths
        ]
        return all_paths[:num_paths]


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
