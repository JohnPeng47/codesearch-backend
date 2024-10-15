from dataclasses import dataclass, field
from networkx import MultiDiGraph
from typing import List, Type, Dict, Optional
import uuid


class MultipleNodesException(Exception):
    pass


class DictMixin:
    def dict(self):
        return {k: v for k, v in self.__dict__.items() if not k == "id"}


@dataclass
class Node(DictMixin):
    kind: str
    id: str = field(default=str(uuid.uuid4()))

    def get_content(self):
        raise NotImplementedError(f"Method not implemented on {self.__name__}")

    def __hash__(self):
        return hash(self.id)


@dataclass
class Edge(DictMixin):
    src: str
    dst: str


class CodeGraph:
    def __init__(self, *, graph=MultiDiGraph, node_types: List[Type[Node]]):
        self._graph = graph
        self.node_types: Dict[str, Type[Node]] = {nt.__name__: nt for nt in node_types}

    def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    def has_edge(self, src: str, dst: str) -> bool:
        return self._graph.has_edge(src, dst)

    def add_node(self, node: Node):
        if node.kind not in self.node_types:
            raise ValueError(
                f"NodeType {node.kind} not supported for {self.__class__.__name__}"
            )

        self._graph.add_node(node.id, **node.dict())
        return node.id

    def add_edge(self, edge: Edge):
        self._graph.add_edge(edge.src, edge.dst, **edge.dict())

    def get_node(self, node_id: str) -> Node:
        if not self._graph.has_node(node_id):
            return None

        node_data = self._graph.nodes[node_id]
        node_kind = node_data.get("kind")

        if node_kind not in self.node_types:
            raise ValueError(f"Unknown node kind: {node_kind}")

        node_class = self.node_types[node_kind]
        return node_class(id=node_id, **node_data)

    def update_node(self, node: Node):
        self.add_node(node)

    def children(self, node_id: str):
        return list(self._graph.predecessors(node_id))

    def parents(self, node_id: str):
        return list(self._graph.successors(node_id))

    def filter_nodes(self, node_filter: Dict) -> List[Node]:
        """
        Replace this function later with GraphDB
        For now only supports single atrribute filters
        Single attribute filter on node_data
        kg = KnowledgeGraph()
        kg.add_node("key", node_data={"hello": "woild"})
        kg.add_node("key", node_data={"hello": "1234"})
        kg.filter_nodes({"hello": "1234"})

        Output:
        [('key', {'hello': '1234'})]
        """
        # TODO: think about how to better support this operation
        GRAPH_FUNCS = ["children"]

        if node_filter == {}:
            return self.nodes.data()

        filter_ops = []
        for key, v in node_filter.items():
            if not isinstance(v, dict):
                # LEARN: default behaviour is to capture the variable by ref
                # not value, need default arg to create essentially a new scope
                # that gets assigned the value
                filter_ops.append((key, lambda a, v=v: a == v))
            else:
                if v["op"] == "=":
                    filter_ops.append((key, lambda a, v=v: a == v["val"]))
                elif v["op"] == ">":
                    filter_ops.append((key, lambda a, v=v: a > v["val"]))
                elif v["op"] == "<":
                    filter_ops.append((key, lambda a, v=v: a < v["val"]))

        return_val = []
        for node_id, data in self._graph.nodes(data=True):
            op_results = []
            for k, op in filter_ops:
                # # NOTE: this part is a little insane...
                # # also doesnt quite work with children since we are comparing len
                # if k in GRAPH_FUNCS:
                #     func = getattr(self._graph, k)
                #     val = func(node_id)
                val = data.get(k, None)
                op_result = op(val)
                op_results.append(op_result)

            if all(op_results):
                return_val.append(self.get_node(node_id))

        return return_val

    # TODO: think there is an error here
    def find_node(self, node_filter: Dict) -> Optional[Node]:
        """
        Finds a single node
        """
        filtered_nodes = self.filter_nodes(node_filter)
        if not filtered_nodes:
            return None

        if len(filtered_nodes) > 1:
            raise MultipleNodesException(
                f"Multiple nodes found matching filter: {node_filter}"
            )

        return filtered_nodes[0] if len(filtered_nodes) == 1 else None
