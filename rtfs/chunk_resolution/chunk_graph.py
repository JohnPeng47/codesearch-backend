from networkx import MultiDiGraph, node_link_graph, node_link_data, DiGraph
from pathlib import Path
from llama_index.core.schema import BaseNode
from typing import List, Tuple, Dict
import os
from collections import deque

from rtfs.utils import dfs_json
from rtfs.scope_resolution.capture_refs import capture_refs
from rtfs.scope_resolution.graph_types import ScopeID
from rtfs.repo_resolution.repo_graph import RepoGraph, RepoNodeID, repo_node_id
from rtfs.fs import RepoFs
from rtfs.utils import TextRange

from rtfs.models import OpenAIModel, BaseModel
from rtfs.cluster.graph import ClusterGraph

from .graph import (
    ChunkMetadata,
    ClusterNode,
    ChunkNode,
    ImportEdge,
    CallEdge,
    ClusterEdgeKind,
    ChunkEdgeKind,
    ClusterEdge,
    NodeKind,
    ChunkNodeID,
)

import logging
from collections import defaultdict


logger = logging.getLogger(__name__)


# DESIGN_TODO: make a generic Graph object to handle add/update Node
class ChunkGraph(ClusterGraph):
    def __init__(
        self,
        repo_path: Path,
        graph: MultiDiGraph,
        cluster_roots=[],
    ):
        super().__init__(graph=graph, repo_path=repo_path, cluster_roots=cluster_roots)

        self.fs = RepoFs(repo_path)
        self._repo_graph = RepoGraph(repo_path)
        self._file2scope = defaultdict(set)
        self._chunkmap: Dict[Path, List[ChunkNode]] = defaultdict(list)
        self._lm: BaseModel = OpenAIModel()

    # TODO: design decisions
    # turn import => export mapping into a function
    # implement tqdm for chunk by chunk processing
    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[BaseNode], skip_tests=True):
        """
        Build chunk (import) to chunk (export) mapping by associating a chunk with
        the list of scopes, and then using the scope -> scope mapping provided in RepoGraph
        to resolve the exports
        """
        g = DiGraph()
        cg: ChunkGraph = cls(repo_path, g)
        cg._file2scope = defaultdict(set)

        # used to map range to chunks
        chunk_names = set()
        skipped_chunks = 0

        for i, chunk in enumerate(chunks, start=1):
            # print("Repopath: ", repo_path)
            # print("Metadata fullpath: ", chunk.metadata["file_path"])
            # print(
            #     "Metadata relpath: ",
            #     os.path.relpath(repo_path, chunk.metadata["file_path"]),
            # )
            # chunk.metadata["file_path"] = os.path.relpath(
            #     chunk.metadata["file_path"], repo_path
            # )
            try:
                metadata = ChunkMetadata(**chunk.metadata)
            except TypeError as e:
                print(f"Chunk error, skipping..: {e}")
                continue

            if skip_tests and metadata.file_name.startswith("test_"):
                skipped_chunks += 1
                continue

            short_name = cg._chunk_short_name(chunk, i)
            chunk_names.add(short_name)
            chunk_node = ChunkNode(
                id=short_name,
                og_id=chunk.node_id,
                metadata=metadata,
                content=chunk.get_content(),
            )
            cg.add_node(chunk_node)
            cg._chunkmap[Path(metadata.file_path)].append(chunk_node)

        # TODO: figure out what's going on here with ell...
        # shouldnt really happen but ...
        # if len(chunk_names) != len(chunks) - skipped_chunks:
        #     raise ValueError("Collision has occurred in chunk names")

        # main loop to build graph
        for chunk_node in cg.get_all_nodes():
            # chunk -> range -> scope
            cg.build_import_exports_chunks(chunk_node)

        for f, scopes in cg._file2scope.items():
            all_scopes = cg._repo_graph.scopes_map[f].scopes()
            all_scopes = set(all_scopes)

            unresolved = all_scopes - scopes

        return cg

    # TODO: confirm that node.filter_nodes({}) returns all nodes, then refactor this method
    def get_all_nodes(self) -> List[ChunkNode]:
        return [self.get_node(n) for n in self._graph.nodes]

    # TODO: REST OF THIS CODE SHOULD BE INSIDE CLUSTER NODE
    # TODO: use this to build the call graph
    # find unique paths:
    # find all root nodes (no incoming edges)
    # iterate dfs and add all nodes to seen list
    # start from another node
    def build_import_exports_chunks(self, chunk_node: ChunkNode):
        """
        Build the import to export mapping for a chunk
        need to do: import (chunk -> range -> scope) -> export (scope -> range -> chunk)
        """
        src_path = Path(chunk_node.metadata.file_path)
        scope_graph = self._repo_graph.scopes_map[src_path]
        chunk_refs = capture_refs(chunk_node.content.encode())

        for ref in chunk_refs:
            # align ref with chunks offset
            ref.range = ref.range.add_offset(
                chunk_node.metadata.start_line, chunk_node.metadata.start_line
            )
            # range -> scope
            ref_scope = scope_graph.scope_by_range(ref.range)
            # scope (import) -> scope (export)
            export = self._repo_graph.import_to_export_scope(
                repo_node_id(src_path, ref_scope), ref.name
            )
            # TODO: this would be alot better if we could search using
            # existing ts queries cuz we can narrow to import refs
            if not export:
                # print(f"Unmatched ref: {ref.name} in {src_path}")
                continue

            export_sg = self._repo_graph.scopes_map[Path(export.file_path)]
            export_range = export_sg.range_by_scope(export.scope)
            dst_chunk = self.find_chunk(Path(export.file_path), export_range)
            if dst_chunk:
                if scope_graph.is_call_ref(ref.range):
                    call_edge = CallEdge(
                        src=chunk_node.id, dst=dst_chunk.id, ref=ref.name
                    )
                    # print("adding call edge: ", call_edge.dict())
                    self.add_edge(call_edge)

                # differentiate between ImportToExport chunks and CallToExport chunks
                # so in the future we can use this for file level edges
                ref_edge = ImportEdge(src=chunk_node.id, dst=dst_chunk.id, ref=ref.name)
                # print(f"Adding edge: {chunk_node.id} -> {dst_chunk.id}")
                self.add_edge(ref_edge)

    # TODO: should really use IntervalGraph here but chunks are small enough
    def find_chunk(self, file_path: Path, range: TextRange):
        """
        Find a chunk given a range
        """
        chunks = self._chunkmap[file_path]
        for chunk in chunks:
            if chunk.range.contains_line(range, overlap=True):
                return chunk

        return None

    def find_cluster_node_by_title(self, title: str):
        """
        Find a cluster node by its ID
        """
        for node in self._graph.nodes:
            cluster_node = self.get_node(node)
            if isinstance(cluster_node, ClusterNode) and cluster_node.title == title:
                return cluster_node
        return None

    # def children(self, node_id: str):
    #     return [child for child, _ in self._graph.in_edges(node_id)]

    # # TODO: this only works for cluster nodes
    # def parent(self, node_id: str):
    #     parents = [parent for _, parent in self._graph.out_edges(node_id)]
    #     if parents:
    #         return parents[0]
    #     return None

    def get_clusters_at_depth(self, roots: List[ClusterNode], level):
        queue = deque([(root, 0) for root in roots])
        visited = set(roots)
        clusters_at_level = []

        while queue:
            node, depth = queue.popleft()

            if depth == level:
                clusters_at_level.append(node)
            elif depth > level:
                break

            for neighbor in self.children(node):
                if neighbor not in visited:
                    if self._graph.nodes[neighbor]["kind"] == NodeKind.Cluster:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))

        return clusters_at_level

    def _get_cluster_roots(self):
        """
        Gets the multiple root cluster nodes generated from Infomap
        """
        roots = []
        for node in self._graph.nodes:
            if isinstance(self.get_node(node), ClusterNode):
                if not self.parents(node)[0]:
                    roots.append(node)

        return roots

    # TODO: code quality degrades exponentially from this point forward .. dont look
    def get_chunks_attached_to_clusters(self):
        chunks_attached_to_clusters = {}
        clusters = defaultdict(int)

        total_chunks = len(
            [
                node
                for node, attrs in self._graph.nodes(data=True)
                if attrs["kind"] == "Chunk"
            ]
        )
        total_leaves = 0
        for u, v, attrs in self._graph.edges(data=True):
            if attrs.get("kind") == ClusterEdgeKind.ChunkToCluster:
                chunk_node = self.get_node(u)
                cluster_node = self.get_node(v)

                if cluster_node.id not in chunks_attached_to_clusters:
                    chunks_attached_to_clusters[cluster_node.id] = []

                chunks_attached_to_clusters[cluster_node.id].append(chunk_node)
                clusters[cluster_node.id] += 1
                total_leaves += 1

        # for cluster, chunks in chunks_attached_to_clusters.items():
        #     print(f"---------------------{cluster}------------------")
        #     for chunk in chunks:
        #         print(chunk.id)
        #         print(chunk.content)
        #         print("--------------------------------------------------")

        print(f"Total chunks: {total_chunks}")
        print(f"Total leaves: {total_leaves}")

        return chunks_attached_to_clusters

    def _chunk_short_name(self, chunk_node: BaseNode, i: int) -> str:
        # take out the root path and only last two subdirectories
        filename = "/".join(chunk_node.metadata["file_path"].split(os.sep)[1:-2])
        size = chunk_node.metadata["end_line"] - chunk_node.metadata["start_line"]

        return f"{filename}#{i}.{size}"

    def _get_classes_and_funcs(
        self, file_path: Path, scope_id: ScopeID
    ) -> List[RepoNodeID]:
        def_nodes = self._repo_graph.scopes_map[file_path].definitions(scope_id)

        return list(
            filter(lambda d: d.data["def_type"] in ["class", "function"], def_nodes)
        )

    # async def summarize(self, user_confirm: bool = False, test_run: bool = False):
    #     if self._cluster_depth is None:
    #         raise ValueError("Must cluster before summarizing")

    #     if user_confirm:
    #         agg_chunks = ""
    #         for _, chunk_text in self.iterate_clusters_with_text():
    #             agg_chunks += chunk_text

    #         tokens, cost = self._lm.calc_input_cost(agg_chunks)
    #         user_input = input(
    #             f"The summarization will cost ${cost} and use {tokens} tokens. Do you want to proceed? (yes/no): "
    #         )
    #         if user_input.lower() != "yes":
    #             print("Aborted.")
    #             exit()

    #     limit = 2 if test_run else float("inf")
    #     for cluster, chunk_text in self.iterate_clusters_with_text():
    #         try:
    #             summary_data = await summarize_chunk_text(chunk_text, self._lm)
    #         except LLMException:
    #             continue

    #         # limit run for tests
    #         if limit <= 0:
    #             break
    #         limit -= 1

    #         cluster_node = ClusterNode(id=cluster, summary_data=summary_data)
    #         self.update_node(cluster_node)

    #     # ...
    #     if limit <= 0:
    #         return

    ##### FOR testing prompt #####
    def get_chunk_imports(self):
        shared_refs = {}
        for cluster_id, node_data in self._graph.nodes(data=True):
            if node_data["kind"] == "Cluster":
                ref_edges = defaultdict(int)
                for child in self.children(cluster_id):
                    child_node = self.get_node(child)
                    if child_node.kind == NodeKind.Chunk:
                        try:
                            for _, _, attrs in self._graph.edges(child, data=True):
                                if attrs["kind"] == ChunkEdgeKind.ImportFrom:
                                    ref = attrs["ref"]
                                    ref_edges[ref] += 1
                        except Exception:
                            continue
                shared_refs[cluster_id] = ref_edges

        return shared_refs

    def get_chunks(self):
        cluster_dict = {}
        for cluster_id, node_data in self._graph.nodes(data=True):
            if node_data["kind"] == "Cluster":
                concatenated_content = []
                for child in self.children(cluster_id):
                    child_node = self.get_node(child)
                    if child_node.kind == NodeKind.Chunk:
                        # print("CHunk: ", child_node.id)
                        try:
                            chunk_node = self.get_node(child)
                            concatenated_content.append(chunk_node.get_content())
                        except Exception:
                            continue
                cluster_dict[cluster_id] = concatenated_content

        return cluster_dict

    ##### For debugging ####!SECTION
    def nodes(self):
        return self._graph.nodes(data=True)

    def to_str(self):
        repr = ""
        for u, v, attrs in self._graph.edges(data=True):
            ref = attrs["ref"]
            u_node = self.get_node(u)
            v_node = self.get_node(v)
            repr += (
                f"{u_node.metadata.file_name} --{ref}--> {v_node.metadata.file_name}\n"
            )
        return

    def to_str_cluster(self):
        repr = ""
        for node_id, node_data in self._graph.nodes(data=True):
            # print(node_data)
            if node_data["kind"] == "Cluster":
                repr += f"ClusterNode: {node_id}\n"
                for child, _, edge_data in self._graph.in_edges(node_id, data=True):
                    if edge_data["kind"] == ClusterEdgeKind.ChunkToCluster:
                        chunk_node = self.get_node(child)
                        repr += f"  ChunkNode: {chunk_node.id}\n"
                    elif edge_data["kind"] == ClusterEdgeKind.ClusterToCluster:
                        cluster_node = self.get_node(child)
                        repr += f"  ClusterNode: {cluster_node.id}\n"
        return repr

    def clusters_to_str(self):
        INDENT_SYM = lambda d: "-" * d + " " if d > 0 else ""

        clusters_json = self.clusters_to_json()
        result = ""

        for cluster_json in clusters_json:
            for node, depth in dfs_json(cluster_json):
                indent = "  " * depth
                result += f"{INDENT_SYM(depth)}Title: {node['title']}\n"
                # result += f"{indent}Keywords: {node['key_variables']}\n"
                # result += f"{indent}Summary: {node['summary']}\n"
                # for chunk in node["chunks"]:
                #     result += f"{indent}  ChunkNode: {chunk['id']}\n"

        return result

    # def get_import_refs(
    #     self, unresolved_refs: set[str], file_path: Path, scopes: List[ScopeID]
    # ):
    #     # get refs from the local scope that is a file-level import
    #     imported_refs = []
    #     file_imports = self._repo_graph.imports[file_path]

    #     for ref in unresolved_refs:
    #         if ref in [imp.namespace.child for imp in file_imports]:
    #             imported_refs.append(ref)

    #     return imported_refs

    # def unresolved_refs(
    #     self, file_path: Path, chunk_scopes: List[ScopeID]
    # ) -> Tuple[set, set]:
    #     """
    #     Find refs that
    #     """
    #     scope_graph = self.scopes_map[file_path]

    #     resolved = set()
    #     unresolved = set()

    #     # TODO: we also have the check definitions in the parent scope
    #     # TODO: also overlapped scopes/chunk ranges
    #     for scope in chunk_scopes:
    #         refs = [
    #             scope_graph.get_node(r).name
    #             for r in scope_graph.references_by_origin(scope)
    #         ]
    #         local_defs = [
    #             scope_graph.get_node(d).name for d in scope_graph.definitions(scope)
    #         ]

    #         # try to resolve refs with local defs
    #         for ref in refs:
    #             if ref in local_defs:
    #                 resolved.add(ref)
    #             else:
    #                 unresolved.add(ref)

    #     return resolved, unresolved

    # def get_modified_chunks(self):
    #     return self.chunks
