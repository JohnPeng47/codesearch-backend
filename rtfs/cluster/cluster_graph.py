from pathlib import Path
from typing import List, Dict
from llama_index.core.schema import BaseNode
import networkx as nx
import random
from llm import LLMModel

from rtfs.chunk_resolution.graph import ChunkNode
from rtfs.graph import CodeGraph, EdgeKind, NodeKind
from rtfs.cluster.infomap import cluster_infomap
from rtfs.cluster.graph import (
    ClusterNode,
    ClusterRefEdge,
    ClusterEdge,
    Cluster,
    ClusterGStats
)
from src.models import ChunkMetadata, CodeChunk

from .path import ClusterPath, ChunkPathSegment
from .lmp import regroup_clusters, split_cluster, summarize

class ClusterGraph(CodeGraph):
    def __init__(
        self,
        *,
        repo_path: Path,
        graph: nx.MultiDiGraph,
        clustered: List[str] = [],
    ):
        super().__init__(graph=graph, node_types=[ChunkNode, ClusterNode])

        self.model = LLMModel(provider="openai")
        self.repo_path = repo_path
        self._clustered = clustered

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
            clustered=json_data.get("clustered", []),
        )

    def to_json(self):
        data = {
            "directed": self._graph.is_directed(),
            "multigraph": self._graph.is_multigraph(),
            "graph": self._graph.graph,
            "nodes": [],
            "links": [],
        }

        # for n, node_data in G.nodes(data=True):
        #     node_dict = node_data.copy()
        #     node_dict.pop("references", None)
        #     node_dict.pop("definitions", None)

        #     if "metadata" in node_dict and isinstance(
        #         node_dict["metadata"], ChunkMetadata
        #     ):
        #         node_dict["metadata"] = node_dict["metadata"].to_json()

        #     node_dict["id"] = n
        #     data["nodes"].append(node_dict)

        for node_id in self._graph.nodes:
            node = self.get_node(node_id)
            data["nodes"].append(node.to_json())

        for u, v, edge_data in self._graph.edges(data=True):
            edge = edge_data.copy()
            edge["source"] = u
            edge["target"] = v
            data["links"].append(edge)

        

        graph_dict = {}
        graph_dict["clustered"] = self._clustered
        graph_dict["link_data"] = data
        return graph_dict
        
    # TODO: we have two control flags, use_summaries and reutrn_content
    def cluster(self, 
                summarize=True,
                use_summaries=False, 
                alg="infomap"):
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
                src=chunk_node, dst=cluster, kind=EdgeKind.ChunkToCluster
            )
            self.add_edge(cluster_edge)

        # TODO: this part feels like it needs tests
        # TODO: implement these using graphops
        # perform recollection operations
        self.split_clusters()
        self.regroup_chunks(use_summaries=use_summaries)

        print("Finished regrouping clusters")
 
        # TODO: this takes infinity to run
        # cluster the clusters
        # self._build_cluster_edges()

        # TODO: should take in cluster edges using summaries
        self.summarize_clusters()
        print("Finished summarizing clusters")

        self._clustered = True

    def summarize_clusters(self):
        clusters = self.get_clusters(return_content=True)
        for cluster in clusters:
            cluster_node = self.get_node(cluster.id)
            if not cluster_node:
                continue

            # Summarize cluster
            summary_data = summarize(self.model, cluster)
            print(f"Generated summary {summary_data.title}: \n{summary_data.summary}")
            
            cluster_node.summary = summary_data
            self.update_node(cluster_node)

    def split_clusters(self, threshold=8):
        clusters = self.get_clusters(return_content=True)
        largest_cluster = max(clusters, key=lambda c: len(c.chunks))
        if len(largest_cluster.chunks) < threshold:
            return
        
        print("Breaking cluster: ", largest_cluster.id, len(largest_cluster.chunks))
        new_clusters = split_cluster(self.model, largest_cluster)
        
        # Add new clusters and reassign chunks
        for cluster_info in new_clusters.topics:
            print("New cluster: ", cluster_info.name, len(cluster_info.chunks))
            
            # BUG: this actually goes against the Node id=str gurantee
            # but we have already hardcoded this into the regroup_clusters prompt
            new_cluster = ClusterNode(id=random.randint(40, 100000))
            self.add_node(new_cluster)
            
            # Move chunks to new cluster
            for chunk_name in cluster_info.chunks:
                chunk_node = self.get_node(chunk_name)
                if chunk_node:
                    # Remove edge to old cluster
                    self.remove_edge(chunk_name, largest_cluster.id)
                    # Add edge to new cluster 
                    self.add_edge(ClusterEdge(
                        src=chunk_name,
                        dst=new_cluster.id,
                        kind=EdgeKind.ChunkToCluster
                    ))
                        
        # Remove old cluster if empty
        if len(self.children(largest_cluster.id, edge_types=[EdgeKind.ChunkToCluster])) == 0:
            self.remove_node(largest_cluster.id)


    def regroup_chunks(self, use_summaries=False):
        # regroup clusters
        clusters = self.get_clusters(return_content=True)
        _, moves = regroup_clusters(self.model, clusters, use_summaries=use_summaries)
        valid_moves = 0

        for move in moves:
            src_cluster = self.get_node(move.src_cluster)
            dst_cluster = self.get_node(move.dst_cluster)
            chunk_node = self.get_node(move.chunk)

            # node hallucination
            if not src_cluster or not dst_cluster or not chunk_node:
                continue
            
            # edge hallucination
            if self._graph.has_edge(chunk_node.id, src_cluster.id):
                self.remove_edge(chunk_node.id, src_cluster.id)
            
            self.add_edge(ClusterEdge(
                src=chunk_node.id,
                dst=dst_cluster.id,
                kind=EdgeKind.ChunkToCluster
            ))

            if self.children(src_cluster.id, edge_types=[EdgeKind.ChunkToCluster]) == 0:
                self.remove_node(src_cluster.id)
                print("Removing cluster: ", src_cluster.id)

            valid_moves += 1

        print("Valid moves: ", valid_moves)

    def _build_cluster_edges(self):
        """
        Construct edges between clusters based on the edges between their chunks
        """
        total_edges = 0
        
        # TODO: we don't create a a cluster hierarchy until summarize clusters is called
        # need to move actual cluster to cluster connection in here
        cluster_nodes = [
            node
            for node in self.filter_nodes({"kind": NodeKind.Cluster})
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
                        # print("Adding edge: ", data["ref"], cluster_node.id, target_cluster_id)
                        total_edges += 1
                        self.add_edge(
                            ClusterRefEdge(
                                src=cluster_node.id,
                                dst=target_cluster_id,
                                ref=data["ref"],
                                src_node=chunk.id,
                                dst_node=target_chunk.id
                            )
                        )
        print("Total edges: ", total_edges)


    def node_to_cluster(self, 
                    cluster_id: str, 
                    return_content = False) -> Cluster:
        """
        Converts graph ClusterNode to Cluster by node ID
        """
        cluster_node: ClusterNode = self.get_node(cluster_id)
        if not cluster_node or cluster_node.kind != NodeKind.Cluster:
            raise ValueError(f"Node {cluster_node} is the wrong input type")

        chunks = []
        children = []
        for child in self.children(cluster_id, edge_types=[EdgeKind.ChunkToCluster, 
                                                           EdgeKind.ClusterToCluster]):
            if child == cluster_id:
                raise ValueError(f"Cluster {cluster_id} has a self-reference")

            child_node: ChunkNode = self.get_node(child)
            if child_node.kind == NodeKind.Chunk:
                chunk_info = self.node_to_chunk(child, return_content=return_content)
                chunks.append(chunk_info)
            elif child_node.kind == NodeKind.Cluster:
                children.append(self.node_to_cluster(child, return_content=return_content))

        return Cluster(
            id=cluster_node.id,
            title=cluster_node.title,
            summary=cluster_node.summary,
            chunks=chunks,
            children=children,
        )

    def node_to_chunk(self, 
                      chunk_id: str, 
                      return_content = False) -> CodeChunk:
        """
        Converts graph ChunkNode to ClusterChunk by node ID
        """
        chunk_node: ChunkNode = self.get_node(chunk_id)
        if chunk_node.kind != NodeKind.Chunk:
            raise ValueError(f"Node {chunk_id} is not a chunk node")

        code_chunk = chunk_node.to_code_chunk()
        if not return_content:
            code_chunk.content = ""

        return code_chunk

    def clusters(
        self, 
        cluster_nodes: List[ClusterNode], 
        return_type: str = "json",
        *,
        return_content: bool = False
    ) -> List[Dict | Cluster]:
        """
        Returns a list of clusters and their child chunk nodes. Returns either
        JSON or as Cluster
        """
        if return_type == "json":
            return [self.node_to_cluster(node, return_content=return_content).to_dict() for node in cluster_nodes]
        else:
            return [self.node_to_cluster(node, return_content=return_content) for node in cluster_nodes]


    def get_clusters(self, return_content: bool = False) -> List[Cluster]:
        cluster_nodes = [
            node.id
            for node in self.filter_nodes({"kind": NodeKind.Cluster})
        ]

        return self.clusters(cluster_nodes, return_type="obj", return_content=return_content)
    
    def get_longest_path(self, num_paths: int = 10) -> List[ClusterPath]:
        """
        Returns the num_paths longest paths between clusters as a list of (source, edge, target) tuples.
        """
        if not self._clustered:
            raise Exception("Graph not clustered yet")
        
        cluster_nodes = [
            node.id for node in self.filter_nodes({"kind": NodeKind.Cluster})
        ]
        cluster_subgraph = self._graph.subgraph(cluster_nodes)

        # Find all simple paths between all pairs of nodes
        all_paths = []
        # Only iterate through unique pairs to avoid duplicates
        for i, src in enumerate(cluster_nodes):
            for dst in cluster_nodes[i+1:]:  # Start from i+1 to avoid duplicates
                # Get all simple paths between src and dst
                for path in nx.all_simple_paths(cluster_subgraph, src, dst):
                    cluster_path = ClusterPath()

                    # Check if any edges in the path are not ClusterRef
                    skip_path = False
                    for i in range(len(path) - 1):
                        edge_datas = cluster_subgraph.get_edge_data(path[i], path[i+1]).values()
                        if any(edge_data["kind"] != EdgeKind.ClusterRef for edge_data in edge_datas):
                            skip_path = True
                            break
                    if skip_path:
                        continue

                    for i in range(len(path) - 1):
                        src_cluster = self.node_to_cluster(path[i])
                        dst_cluster = self.node_to_cluster(path[i + 1])
                        edge_datas = cluster_subgraph.get_edge_data(src_cluster.id, dst_cluster.id).values()
                        # add up all the chunk segments between two clusters
                        chunk_segments = set()
                        for edge_data in edge_datas:
                            src_chunk = self.node_to_chunk(edge_data["src_node"])
                            dst_chunk = self.node_to_chunk(edge_data["dst_node"])
                            ref = edge_data["ref"]
                            chunk_segments.add(ChunkPathSegment(src_chunk, ref, dst_chunk))
                        cluster_path.add_segment((src_cluster, dst_cluster, chunk_segments))

                    # NOTE: not sure why I have to do this but set doesnt seem to work here?                    
                    if not any([p.__hash__() == cluster_path.__hash__() for p in all_paths]):
                        all_paths.append(cluster_path)

    # return all_paths
        # # Sort paths by length in descending order and return top num_paths
        all_paths = list(all_paths)
        all_paths.sort(key=len, reverse=True)
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
