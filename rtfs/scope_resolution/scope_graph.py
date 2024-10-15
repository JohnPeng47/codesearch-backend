from networkx import DiGraph
from typing import Dict, Optional, Iterator, List, NewType, Tuple
from enum import Enum
from collections import defaultdict

from rtfs.graph import Node, CodeGraph
from rtfs.utils import TextRange

from rtfs.scope_resolution import (
    LocalImportStmt,
    LocalDef,
    Reference,
    LocalScope,
    ScopeStack,
    LocalCall,
)
from rtfs.scope_resolution.graph_types import NodeKind, EdgeKind, ScopeNode, ScopeID
from rtfs.scope_resolution.interval_tree import IntervalGraph


class ScopeGraph(CodeGraph):
    def __init__(self, range: TextRange):
        super().__init__(graph=DiGraph(), node_types=[ScopeNode])

        # TODO: put all this logic into a separate Graph class
        self._node_counter = 0

        self.scope2range: Dict[ScopeID, TextRange] = {}

        root_scope = ScopeNode(range=range, type=NodeKind.SCOPE)
        self.root_idx = self.add_node(root_scope)
        self.scope2range[self.root_idx] = range

        # lookup tables for faster lookups, especially for references resolution
        self.defn_dict: Dict[str, List[Tuple[TextRange, ScopeID]]] = defaultdict(list)
        self.imp_dict: Dict[str, List[Tuple[TextRange, ScopeID]]] = defaultdict(list)

        # use this to faster resolve range -> scope queries
        self._ig = IntervalGraph(range, self.root_idx)

    def insert_local_scope(self, new: LocalScope):
        """
        Insert local scope to smallest enclosing parent scope
        """
        parent_scope = self.scope_by_range(new.range, self.root_idx)
        if parent_scope is not None:
            new_node = ScopeNode(range=new.range, type=NodeKind.SCOPE)
            new_idx = self.add_node(new_node)
            self._graph.add_edge(new_idx, parent_scope, type=EdgeKind.ScopeToScope)
            self._ig.add_scope(new.range, new_idx)

            self.scope2range[new_idx] = new.range

    def insert_local_import(self, new: LocalImportStmt):
        """
        Insert import into smallest enclosing parent scope
        """
        parent_scope = self.scope_by_range(new.range, self.root_idx)
        if parent_scope is not None:
            new_node = ScopeNode(
                range=new.range,
                type=NodeKind.IMPORT,
                data={
                    "from_name": new.from_name,
                    "aliases": new.aliases,
                    "names": new.names,
                    "relative": new.relative,
                },
            )
            new_idx = self.add_node(new_node)
            self._graph.add_edge(new_idx, parent_scope, type=EdgeKind.ImportToScope)

            for names in new.names:
                self.imp_dict[names].append((new.range, new_idx))

    def insert_local_def(self, new: LocalDef) -> None:
        """
        Insert a def into the scope-graph
        """
        defining_scope = self.scope_by_range(new.range, self.root_idx)
        if defining_scope is not None:
            new_def = ScopeNode(
                range=new.range,
                name=new.name,
                type=NodeKind.DEFINITION,
                data={"def_type": new.symbol},
            )
            new_idx = self.add_node(new_def)
            self._graph.add_edge(new_idx, defining_scope, type=EdgeKind.DefToScope)

            self.defn_dict[new.name].append((new.range, new_idx))

    def insert_hoisted_def(self, new: LocalDef) -> None:
        """
        Insert a def into the scope-graph, at the parent scope of the defining scope
        """
        defining_scope = self.scope_by_range((new.range, self.root_idx))
        if defining_scope is not None:
            new_def = ScopeNode(
                range=new.range,
                name=new.name,
                type=NodeKind.DEFINITION,
            )
            new_idx = self.add_node(new_def)

            # if the parent scope exists, insert this def there, if not,
            # insert into the defining scope
            parent_scope = self.parent_scope(defining_scope)
            target_scope = parent_scope if parent_scope is not None else defining_scope
            self._graph.add_edge(new_idx, target_scope, type=EdgeKind.DefToScope)

            self.defn_dict[new.name].append((new.range, new_idx))

    def insert_global_def(self, new: LocalDef) -> None:
        """
        Insert a def into the scope-graph, at the root scope
        """
        new_def = ScopeNode(
            range=new.range,
            name=new.name,
            type=NodeKind.DEFINITION,
        )
        new_idx = self.add_node(new_def)
        self._graph.add_edge(new_idx, self.root_idx, type=EdgeKind.DefToScope)

        self.defn_dict[new.name].append((new.range, new_idx))

    def insert_ref(self, new: Reference) -> None:
        possible_defs = []
        possible_imports = []

        local_scope_idx = self.scope_by_range(new.range, self.root_idx)

        # find the minimum enclosing/closest parent scope
        if local_scope_idx is not None:
            defs = self.defn_dict.get(new.name, [])
            if defs:
                # print("Found ref: ", new.name)
                possible_defs.append(min(defs, key=lambda x: x[0]))

            imports = self.imp_dict.get(new.name, [])
            if imports:
                # print("Found ref import: ", new.name)
                possible_imports.append(min(imports, key=lambda x: x[0]))

        if possible_defs or possible_imports:
            new_ref = ScopeNode(range=new.range, name=new.name, type=NodeKind.REFERENCE)
            ref_idx = self.add_node(new_ref)

            for _, def_idx in possible_defs:
                self._graph.add_edge(ref_idx, def_idx, type=EdgeKind.RefToDef)

            for _, imp_idx in possible_imports:
                self._graph.add_edge(ref_idx, imp_idx, type=EdgeKind.RefToImport)

            # add an edge back to the originating scope of the reference
            self._graph.add_edge(ref_idx, local_scope_idx, type=EdgeKind.RefToOrigin)

    def insert_local_call(self, call: LocalCall):
        call_node = ScopeNode(
            range=call.range,
            name=call.name,
            type=NodeKind.CALL,
            # data={"parameters": call.parameters},
        )
        call_idx = self.add_node(call_node)

        # Find the reference node that matches the call name
        found = False
        for ref_idx, node_attrs in self._graph.nodes(data=True):
            if (
                node_attrs["type"] == NodeKind.REFERENCE
                and node_attrs["name"] == call.name
            ):
                ref_node = self.get_node(ref_idx)
                if call_node.range.contains_line(ref_node.range):
                    found = True
                    break

        if not found:
            # print(f"Could not find reference for call {call.name}")
            return

        # Add an edge from the call to the refeaddrenc
        self._graph.add_edge(call_idx, ref_idx, type=EdgeKind.CallToRef)

    def scopes(self) -> List[ScopeID]:
        """
        Return all scopes in the graph
        """
        return [
            u
            for u, attrs in self._graph.nodes(data=True)
            if attrs["type"] == NodeKind.SCOPE
        ]

    def imports(self, start: int) -> List[int]:
        """
        Get all imports in the scope
        """
        return [
            u
            for u, v, attrs in self._graph.in_edges(start, data=True)
            if attrs["type"] == EdgeKind.ImportToScope
        ]

    def definitions(self, start: int) -> List[ScopeNode]:
        """
        Get all definitions in the scope and child scope
        """
        return [
            self.get_node(u)
            for u, v, attrs in self._graph.in_edges(start, data=True)
            if attrs["type"] == EdgeKind.DefToScope
        ]

    def references_by_origin(self, start: int) -> List[int]:
        """
        Get all references in the scope and child scope
        """
        return [
            u
            for u, v, attrs in self._graph.in_edges(start, data=True)
            if attrs["type"] == EdgeKind.RefToOrigin
        ]

    def child_scopes(self, start: ScopeID) -> List[ScopeID]:
        """
        Get all child scopes of the given scope
        """
        return [
            u
            for u, v, attrs in self._graph.edges(data=True)
            if attrs["type"] == EdgeKind.ScopeToScope and v == start
        ]

    def parent_scope(self, start: ScopeID) -> Optional[ScopeID]:
        """
        Produce the parent scope of a given scope
        """
        if self.get_node(start).type == NodeKind.SCOPE:
            for src, dst, attrs in self._graph.out_edges(start, data=True):
                if attrs["type"] == EdgeKind.ScopeToScope:
                    return dst
        return None

    def is_call_ref(self, range: TextRange) -> bool:
        """
        Checks that the call range matches the ref range
        """
        for node, attrs in self._graph.nodes(data=True):
            if attrs["type"] == NodeKind.REFERENCE:
                ref_node = self.get_node(node)
                if range.contains_line(ref_node.range):
                    return True

        return False

    def scope_by_range(
        self, range: TextRange, start: ScopeID = None
    ) -> Optional[ScopeID]:
        """
        Returns the smallest child scope that contains the given range
        """
        if not start:
            start = self.root_idx

        resolved_scope_id = self._ig.contains(range, overlap=False)
        if resolved_scope_id is not None:
            return resolved_scope_id

        return start

    def range_by_scope(self, scope: ScopeID) -> Optional[TextRange]:
        """
        Returns the range of a scope
        """
        return self.scope2range.get(scope, None)

    def child_scope_stack(self, start: ScopeID) -> List[ScopeID]:
        stack = self.child_scopes(start)

        for child in self.child_scoes(start):
            stack += self.child_scope_stack(child)

        return stack

    def parent_scope_stack(self, start: ScopeID):
        """
        Returns stack of parent scope traversed
        """
        return ScopeStack(self._graph, start)

    def add_node(self, node: ScopeNode) -> int:
        """
        Adds node and increments node_counter for its id
        """
        node.id = self._node_counter
        super().add_node(node)

        self._node_counter += 1
        return node.id

    # def get_node(self, idx: int) -> ScopeNode:
    #     return ScopeNode(**self._graph.nodes(data=True)[idx])

    def to_str(self):
        """
        A str representation of the graph
        """
        repr = "\n"

        for u, v, attrs in self._graph.edges(data=True):
            edge_type = attrs["type"]
            u_data = ""
            v_data = ""

            if (
                edge_type == EdgeKind.RefToDef
                or edge_type == EdgeKind.RefToImport
                or EdgeKind.DefToScope
            ):
                u_data = self.get_node(u).name
                v_data = self.get_node(v).name

            repr += f"{u}:{u_data} --{edge_type}-> {v}:{v_data}\n"

        return repr
