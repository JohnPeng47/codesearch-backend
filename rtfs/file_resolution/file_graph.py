from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
from networkx import MultiDiGraph

from rtfs.fs import RepoFs
from rtfs.repo_resolution.repo_graph import RepoGraph, repo_node_id
from rtfs.scope_resolution.capture_refs import capture_refs
from rtfs.utils import TextRange
from rtfs.models import OpenAIModel, BaseModel


class FileNode:
    def __init__(self, path: Path, content: bytes):
        self.path = path.resolve()
        self.content = content


class FileEdge:
    def __init__(self, ref: str):
        self.ref = ref


class ImportEdge(FileEdge):
    pass


class CallEdge(FileEdge):
    pass


class FileGraph:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.fs = RepoFs(repo_path)
        self._graph = MultiDiGraph()
        self._repo_graph = RepoGraph(repo_path)
        self._file2scope = defaultdict(set)
        self._lm: BaseModel = OpenAIModel()

    @classmethod
    def from_repo(cls, repo_path: Path):
        fg = cls(repo_path)
        fg._build_graph()
        return fg

    def _build_graph(self):
        for file_path, content in self.fs.get_files_content():
            file_node = FileNode(file_path, content)
            self.add_node(file_node)
            self._build_file_connections(file_node)

    def add_node(self, file_node: FileNode):
        self._graph.add_node(file_node.path, file=file_node)

    def add_edge(self, src_path: Path, dst_path: Path, edge: FileEdge):
        self._graph.add_edge(src_path, dst_path, **edge.__dict__)

    def _build_file_connections(self, file_node: FileNode):
        src_path = file_node.path
        scope_graph = self._repo_graph.scopes_map[src_path]
        file_refs = capture_refs(file_node.content)

        for ref in file_refs:
            ref_scope = scope_graph.scope_by_range(ref.range)
            export = self._repo_graph.import_to_export_scope(
                repo_node_id(src_path, ref_scope), ref.name
            )
            if not export:
                continue

            export_file = Path(export.file_path)
            if scope_graph.is_call_ref(ref.range):
                self.add_edge(src_path, export_file, CallEdge(ref=ref.name))
            self.add_edge(src_path, export_file, ImportEdge(ref=ref.name))

    def get_file_imports(self, file_path: Path) -> List[Tuple[Path, str]]:
        imports = []
        for _, dst, data in self._graph.out_edges(file_path, data=True):
            if isinstance(data, ImportEdge):
                imports.append((dst, data.ref))
        return imports

    def get_file_calls(self, file_path: Path) -> List[Tuple[Path, str]]:
        calls = []
        for _, dst, data in self._graph.out_edges(file_path, data=True):
            if isinstance(data, CallEdge):
                calls.append((dst, data.ref))
        return calls

    def get_file_content(self, file_path: Path) -> str:
        return self._graph.nodes[file_path]["file"].content.decode("utf-8")

    def get_file_range(self, file_path: Path, range: TextRange) -> str:
        return self.fs.get_file_range(file_path, range)

    def to_str(self):
        repr = ""
        for u, v, data in self._graph.edges(data=True):
            edge_type = type(data).__name__
            repr += f"{u.name} --{edge_type}:{data.ref}--> {v.name}\n"
        return repr
