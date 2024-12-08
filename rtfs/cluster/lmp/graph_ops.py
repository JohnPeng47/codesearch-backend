from pydantic import BaseModel
from enum import Enum
from typing import List
from abc import ABC, abstractmethod
from rtfs.graph import NodeKind, CodeGraph, EdgeKind
from rtfs.cluster.graph import ClusterEdge, Cluster, ClusterNode

# from logging import getLogger

# logger = getLogger(__name__)

#IDEA: can we come up with something similar to DocETL that can generate a novel set of operations
# that can improve the clusters generated?
# NOT USED IN CODE
# class GraphOp(BaseModel):
#     def __call__(self, graph: CodeGraph):
#         return self.apply(graph)

#     @abstractmethod
#     def apply(self, graph: CodeGraph):
#         raise NotImplementedError

class MoveOp(BaseModel):
    src_cluster: int
    dst_cluster: int
    chunk: str

    def apply(self, cg: CodeGraph):
        src_cluster = cg.get_node(self.src_cluster)
        dst_cluster = cg.get_node(self.dst_cluster)
        chunk_node = cg.get_node(self.chunk)

        # node hallucination
        if not src_cluster or not dst_cluster or not chunk_node:
            print("Hallucinated node skipping moveOp: ")
            return
        
        # edge hallucination
        if cg._graph.has_edge(chunk_node.id, src_cluster.id):
            cg.remove_edge(chunk_node.id, src_cluster.id)

        print("Moving chunk: ", chunk_node.id, " from ", src_cluster.id, " to ", dst_cluster.id)
        
        cg.add_edge(ClusterEdge(
            src=chunk_node.id,
            dst=dst_cluster.id,
            kind=EdgeKind.ChunkToCluster
        ))

        if cg.children(src_cluster.id, edge_types=[EdgeKind.ChunkToCluster]) == 0:
            cg.remove_node(src_cluster.id)
            print("Removing empty cluster: ", src_cluster.id)

    def __eq__(self, other):
        return (self.src_cluster, self.dst_cluster, self.chunk) == (other.src_cluster, other.dst_cluster, other.chunk)

class AdoptCluster(BaseModel):
    child_cluster: int
    parent_cluster: int

    def apply(self, cg: CodeGraph):
        child_cluster = cg.get_node(self.child_cluster)
        parent_cluster = cg.get_node(self.parent_cluster)

        # node hallucination
        if not child_cluster or not parent_cluster:
            return

        if cg._graph.has_edge(child_cluster.id, parent_cluster.id):
            return

        print("Adopting cluster: ", child_cluster.id, " into ", parent_cluster.id)
        cg.add_edge(ClusterEdge(
            src=child_cluster.id,
            dst=parent_cluster.id,
            kind=EdgeKind.ClusterToCluster
        ))

class CreateOp(BaseModel):
    id: int
    title: str
    kind: NodeKind

    def apply(self, cg: CodeGraph):
        cluster_node = ClusterNode(id=self.id, title=self.title)
        cluster_node.summary.title = self.title
        
        print("Creating cluster node: ", cluster_node)
        cg.add_node(cluster_node)


class OpType(str, Enum):
    Move = "MoveOp"
    Create = "CreateOp"
    Adopt = "AdoptCluster"

OP_MAP = {
    OpType.Move: MoveOp,
    OpType.Create: CreateOp,
    OpType.Adopt: AdoptCluster
}

class GraphOp:
    def __init__(self, *, op_type: OpType, **kwargs):
        self.op_type = op_type
        self.op_args = kwargs

    def to_op(self):
        return OP_MAP[self.op_type](**self.op_args)

# Should this be a function?
# possibly can track the stae of applied moves here ie. created clusters
class ApplyMoves:
    """
    Apply all the moves in one batch
    """
    def __init__(self, moves: List[GraphOp]):
        self.moves = moves

    def apply(self, cg: CodeGraph):
        moves = self.filter_moves(cg)        
        for move in moves:
            print("Applying move: ", move)
            move.apply(cg)

    def filter_moves(self, cg: CodeGraph) -> List[MoveOp]:
        """
        Checks if there are any collisions in the list of MoveOps
        """
        moves_by_src = {}
        for move_op in self.moves:
            if not isinstance(move_op, MoveOp):
                print("Skipping non-move op: ", move_op)
                continue

            key = (move_op.src_cluster, move_op.chunk)
            if key not in moves_by_src:
                moves_by_src[key] = []
            moves_by_src[key].append(move_op)

        # Separate colliding and non-colliding moves
        colliding_moves = {
            key: moves for key, moves in moves_by_src.items() 
            if len(moves) > 1
        }
        non_colliding_moves = [
            moves[0] for key, moves in moves_by_src.items()
            if len(moves) == 1
        ]

        print("Colliding moves: ", len(colliding_moves))
        print("Non-colliding moves: ", len(non_colliding_moves))

        return [
            move for move in self.moves 
            if not isinstance(move, MoveOp) or move in non_colliding_moves
        ]