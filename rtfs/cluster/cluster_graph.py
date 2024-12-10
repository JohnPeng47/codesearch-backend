from pydantic import BaseModel
from pathlib import Path
from typing import List, Dict
from llama_index.core.schema import BaseNode
import networkx as nx
import random
from llm import LLMModel
from collections import defaultdict

from rtfs.chunk_resolution.graph import ChunkNode
from rtfs.graph import CodeGraph, EdgeKind, NodeKind
from rtfs.cluster.infomap import cluster_infomap
from rtfs.cluster.graph import (
    ClusterNode,
    ClusterRefEdge,
    ClusterEdge,
    Cluster
)
from src.models import CodeSummary, ChunkMetadata, CodeChunk

from .graph import ClusterSummary, ClusterMetadata
from .path import ClusterPath, ChunkPathSegment
from .lmp import (
    regroup_clusters, 
    split_cluster, 
    summarizev2, 
    summarizev3,
    create_2tier_hierarchy,
    create_2tier_hierarchy_with_existing
)
from .lmp.graph_ops import ApplyMoves

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
        clustered: List[str] = [],
    ):
        super().__init__(graph=graph, node_types=[ChunkNode, ClusterNode])
        for node, node_data in self._graph.nodes(data=True):
            if not node_data.get("kind"):
                raise ValueError("Node kind not found in node data")
            if node_data["kind"] not in self.node_types:
                raise ValueError(f"Node kind {node_data['kind']} not supported")

        self.model = LLMModel(provider="openai")
        self.repo_path = repo_path
        self._clustered = clustered

    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[BaseNode]):
        raise NotImplementedError("Not implemented yet")

    @classmethod
    def from_json(cls, repo_path: Path, json_data: Dict) -> "ClusterGraph":
        cg = nx.node_link_graph(json_data["link_data"])
        for _, node_data in cg.nodes(data=True):
            if node_data["kind"] == NodeKind.Chunk:
                node_data["metadata"] = ChunkMetadata.from_json(node_data["metadata"])
                node_data["summary"] = CodeSummary(**node_data["summary"])

            elif node_data["kind"] == NodeKind.Cluster:
                node_data["metadata"] = ClusterMetadata.from_json(node_data["metadata"])
                node_data["summary"] = ClusterSummary(**node_data["summary"])

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
                self.add_node(ClusterNode(id=cluster, title=""))

            cluster_edge = ClusterEdge(
                src=chunk_node, dst=cluster, kind=EdgeKind.ChunkToCluster
            )
            self.add_edge(cluster_edge)

        # TODO: this part feels like it needs tests
        # TODO: implement these using graphops
        # perform recollection operations
        self._split_clusters()
        self._regroup_chunks(use_summaries=use_summaries)

        print("Finished regrouping clusters")
 
        # TODO: this takes infinity to run
        # cluster the clusters
        # self._build_cluster_edges()

        # TODO: should take in cluster edges using summaries
        self._summarize_clusters()
        print("Finished summarizing clusters")

        self._create_hierarchal_clusters()
        self._clustered = True

    def _summarize_clusters(self):
        clusters = self.get_clusters(return_content=True)
        for cluster in clusters:
            print("Summarizing cluster: ", cluster.id)

            cluster_node = self.get_node(cluster.id)
            if not cluster_node:
                continue

            # Summarize cluster
            summary_data = summarizev3(self.model, cluster)
            print(f"Generated summary {summary_data.title}: \n{summary_data.summary}")

            cluster_node.summary = summary_data
            self.update_node(cluster_node)

    def _create_hierarchal_clusters(self):
        clusters = self.get_clusters(return_content=True)
        moves = create_2tier_hierarchy(self.model, clusters)
        ApplyMoves(moves).apply(self)

        existing_parents = defaultdict(list)  # maps parent name -> list of child ids
        unclustered = [cluster for cluster in clusters if self.children(cluster.id) == 0]
        while unclustered:
            moves = create_2tier_hierarchy_with_existing(
                self.model,
                unclustered, 
                existing_parents
            )
            
            # Apply the moves which will create parent nodes and add edges
            ApplyMoves(moves).apply(self)
            
            # Track which clusters were processed
            for move in moves:
                if move.op_type == "AdoptCluster":
                    unclustered.remove(move.child_cluster)
                    existing_parents[move.parent_cluster].append(move.child_cluster)

            unclustered = [cluster for cluster in clusters if self.children(cluster.id) == 0]

    def _split_clusters(self, threshold=8):
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
            new_cluster = ClusterNode(id=random.randint(40, 100000), title="")
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


    def _regroup_chunks(self, use_summaries=False):
        """
        Use LLM to generate reassignments of chunks to better fitting clusters
        """
        clusters = self.get_clusters(return_content=True)
        _, moves = regroup_clusters(self.model, clusters, self, use_summaries=use_summaries)

        ApplyMoves(moves).apply(self)

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
        return Cluster.from_cluster_node(cluster_id, self, return_content=return_content)

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
        return [self.node_to_cluster(node, return_content=return_content) for node in cluster_nodes]


    def get_clusters(self,
                     parents_only: bool = False, 
                     return_content: bool = False) -> List[Cluster]:
        cluster_nodes = [
            node.id
            for node in self.filter_nodes({"kind": NodeKind.Cluster})
        ]
        if parents_only:
            cluster_nodes = [
                node
                for node in cluster_nodes
                if self.children(node, edge_types=[EdgeKind.ClusterToCluster])
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
