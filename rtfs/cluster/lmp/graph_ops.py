from pydantic import BaseModel

from abc import ABC, abstractmethod
from rtfs.graph import NodeKind, CodeGraph, EdgeKind
from rtfs.cluster.graph import ClusterEdge

#IDEA: can we come up with something similar to DocETL that can generate a novel set of operations
# that can improve the clusters generated?

class GraphOp(BaseModel):
    def __call__(self, graph: CodeGraph):
        return self.apply(graph)

    @abstractmethod
    def apply(self, graph: CodeGraph):
        raise NotImplementedError

class MoveOp(GraphOp):
    src_cluster: int
    dst_cluster: int
    chunk: str

    def apply(self, graph: CodeGraph):
        src_cluster = graph.get_node(self.src_cluster)
        dst_cluster = graph.get_node(self.dst_cluster)
        chunk_node = graph.get_node(self.chunk)

        # node hallucination ...
        if not src_cluster or not dst_cluster or not chunk_node:
            print("Hallucinated...")
            return
        
        # also edge hallucination??
        # maybe hallucinate edge but we still consider it a valid move
        if graph.has_edge(chunk_node.id, dst_cluster.id):
            graph.remove_edge(chunk_node.id, src_cluster.id)
        
        # TODO: should parameterize this somehow
        graph(ClusterEdge(
            src=chunk_node.id,
            dst=dst_cluster.id,
            kind=EdgeKind.ChunkToCluster
        ))

        if graph.children(src_cluster.id, edge_types=[EdgeKind.ChunkToCluster]) == 0:
            graph.remove_node(src_cluster.id)
            print("Removing cluster: ", src_cluster.id)

class CreateOp(BaseModel):
    title: str
    kind: NodeKind


