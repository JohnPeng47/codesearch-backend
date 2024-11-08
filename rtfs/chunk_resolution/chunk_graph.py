from networkx import MultiDiGraph, node_link_graph, node_link_data, DiGraph
from pathlib import Path
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
from rtfs.cluster.cluster_graph import ClusterGraph

# Note: ideally we probably want to either move rtfs into src.graph
# or chunk out of src
from src.chunk.chunk import CodeChunk
from src.chunk.lmp.summarize import CodeSummary
from .graph import (
    ChunkMetadata,
    ClusterNode,
    ChunkNode,
    ImportEdge,
    CallEdge,
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
        clustered=[],
    ):
        super().__init__(graph=graph, repo_path=repo_path, clustered=clustered)

        self.fs = RepoFs(repo_path)
        self._repo_graph = RepoGraph(repo_path)
        self._file2scope = defaultdict(set)
        self._chunkmap: Dict[Path, List[ChunkNode]] = defaultdict(list)
        self._lm: BaseModel = OpenAIModel()

    # TODO: design decisions
    # turn import => export mapping into a function
    # implement tqdm for chunk by chunk processing
    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[CodeChunk], skip_tests=True) -> "ChunkGraph":
        """
        Build chunk (import) to chunk (export) mapping by associating a chunk with
        the list of scopes, and then using the scope -> scope mapping provided in RepoGraph
        to resolve the exports
        """
        g = MultiDiGraph()
        cg: ChunkGraph = cls(repo_path, g)
        cg._file2scope = defaultdict(set)

        # used to map range to chunks
        chunk_names = set()
        skipped_chunks = 0

        for i, chunk in enumerate(chunks, start=1):
            try:
                metadata = chunk.metadata
            except TypeError as e:
                print(f"Chunk error, skipping..: {e}")
                continue

            if skip_tests and metadata.file_name.startswith("test_"):
                skipped_chunks += 1
                continue

            chunk_node = ChunkNode(
                id=chunk.node_id,
                og_id=chunk.node_id,
                metadata=metadata,
                summary=chunk.summary,
                content=chunk.content,
            )
            chunk_names.add(chunk_node.id)
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

                # print(f"Adding chunkedge: {chunk_node.id} -> {dst_chunk.id}")
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

        # for cluster, chunks in chunks_attached_to_clusters.items():
        #     print(f"---------------------{cluster}------------------")
        #     for chunk in chunks:
        #         print(chunk.id)
        #         print(chunk.content)
        #         print("--------------------------------------------------")

        print(f"Total chunks: {total_chunks}")
        print(f"Total leaves: {total_leaves}")

        return chunks_attached_to_clusters

    def _chunk_short_name(self, chunk_node: CodeChunk, i: int) -> str:
        # take out the root path and only last two subdirectories
        filename = "/".join(chunk_node.metadata["file_path"].split(os.sep)[1:-2])
        size = chunk_node.metadata["end_line"] - chunk_node.metadata["start_line"]

        return f"{filename}#{i}.{size}"

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