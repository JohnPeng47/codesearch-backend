from typing import Any, List, Dict, Tuple
from pathlib import Path
from networkx import DiGraph

from rtfs.fs import RepoFs
from rtfs.scope_resolution.scope_graph import ScopeGraph
from rtfs.scope_resolution.graph_types import ScopeID
from rtfs.build_scopes import build_scope_graph
from rtfs.scope_resolution import LocalImportStmt
from rtfs.utils import SysModules, ThirdPartyModules
from rtfs.config import LANGUAGE

from .imports import LocalImport, ModuleType, import_stmt_to_import
from .graph import EdgeKind, RepoNode, RepoNodeID, RefEdge
from rtfs.graph import CodeGraph

from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def repo_node_id(file: Path, scope_id: ScopeID):
    return "".join([str(file), "::", str(scope_id)])


# rename to import graph?
# probably not, since we do want struct to hold repo level info


# this graph is python specific
class RepoGraph(CodeGraph):
    """
    Constructs a graph of relation between the scopes of a repo
    """

    def __init__(self, path: Path):
        super().__init__(graph=DiGraph(), node_types=[RepoNode])
        if not path.exists():
            raise FileNotFoundError(f"Path {path} does not exist")

        self.fs = RepoFs(path)
        self.scopes_map: Dict[Path, ScopeGraph] = self._construct_scopes(self.fs)

        self._imports: Dict[Path, List[LocalImport]] = {}

        # FOR DEBUGGING
        self._missing_import_refs: Dict[Path, List[str]] = {}
        self._resolved_import_refs: Dict[Path, List[str]] = defaultdict(list)
        self.total_scopes = set()

        # TODO_PERF: Parallelizable
        # TODO: put everything into a function that can be measured with TQDM
        # construct imports
        # Original code commented out for reference
        for path, g in self.scopes_map.items():
            self._imports[path] = self._construct_import(g, path, self.fs)
            # print("Adding import: ", path, g)

            self._missing_import_refs[path] = [
                str(imp.namespace) for imp in self._imports[path]
            ]

        # map import ref to export scope
        for path, imports in self._imports.items():
            imp2def: List[Tuple[LocalImport, str, ScopeID, Path]] = []

            # resolve the different types of imports
            local_imports = [
                local_imp
                for local_imp in imports
                if local_imp.module_type == ModuleType.LOCAL
            ]
            # TODO_PERF: check perf for this
            imp2def.extend(self.map_local_to_exports(path, local_imports))

            for imp, def_scope, name, export_file in imp2def:
                if imp.module_type == ModuleType.LOCAL:
                    # establish an edge between all refs from all local scopes to the
                    # def scope in import_file
                    for ref_scope in imp.ref_scopes:

                        ref_node_id = repo_node_id(path, ref_scope)
                        ref_node = self.get_node(ref_node_id)
                        if not ref_node:
                            ref_node = RepoNode(
                                id=ref_node_id, file_path=path, scope=ref_scope
                            )
                            self.total_scopes.add(ref_node_id)
                            self.add_node(ref_node)

                        # self._missing_import_refs[path] = [
                        #     ref
                        #     for ref in self._missing_import_refs[path]
                        #     if ref != str(imp.namespace)
                        # ]
                        # self._resolved_import_refs[path].append(name)

                        imp_node_id = repo_node_id(export_file, def_scope)
                        imp_node = self.get_node(imp_node_id)
                        if not imp_node:
                            imp_node = RepoNode(
                                id=imp_node_id, file_path=export_file, scope=def_scope
                            )
                            self.total_scopes.add(imp_node_id)
                            self.add_node(imp_node)

                        self.add_edge(
                            ref_node_id,
                            imp_node_id,
                            name,
                            str(imp.namespace),
                        )

    def get_node(self, node_id: RepoNodeID) -> RepoNode:
        return super().get_node(node_id)

    def add_node(self, node: RepoNode):
        super().add_node(node)

    def add_edge(
        self, ref_node_id: RepoNodeID, def_node_id: RepoNodeID, ref: str, defn: str
    ):
        edge = RefEdge(src=ref_node_id, dst=def_node_id, ref=ref, defn=defn)
        super().add_edge(edge)

    def get_outgoing_edge(
        self, ref_node_id: RepoNodeID, exp_node_id: RepoNodeID
    ) -> List[RefEdge]:
        return [
            RefEdge(**e)
            for u, v, e in self._graph.out_edges(ref_node_id, data=True)
            if v == exp_node_id
        ]

    def import_to_export_scope(self, ref_node_id: RepoNodeID, ref: str) -> RepoNode:
        """
        Returns the export (def) scopes that are tied to the import (ref) scope
        """
        possible_exports = [
            self.get_node(v)
            for _, v, attrs in self._graph.edges(ref_node_id, data=True)
            if attrs["type"] == EdgeKind.ImportToExport and attrs["ref"] == ref
        ]

        if not possible_exports:
            return []

        if len(possible_exports) > 1:
            print("WTF ...")

        return possible_exports[0]

    # TODO: make this language dependent function implemented outside of
    # repo_graph
    def map_local_to_exports(
        self, path: Path, imports: List[LocalImport]
    ) -> List[Tuple[LocalImport, str, ScopeID, Path]]:
        """
        Given an import namespace, map it to the local (export) definitions in
        the resolved import namespace path
        """
        imp2def = []

        for imp in imports:
            export_file = self.fs.match_file(imp.namespace.to_path())
            if export_file:
                # TODO: make this a PythonLang Extension
                if "__init__.py" in str(export_file):
                    g = self.scopes_map[export_file]
                    init_imports = self._construct_import(g, export_file, self.fs)

                    for init_imp in init_imports:
                        init_file = self.fs.match_file(init_imp.namespace.to_path())
                        # print("Init file: ", init_file)

                        if not init_file:
                            continue

                        for name, def_scope in self._get_exports(
                            self.scopes_map[init_file], export_file
                        ):
                            if imp.namespace.child == name:
                                # TODO: currently mapping connections to actual imported file
                                # but could potentially also map it to __init__.py
                                imp2def.append((imp, def_scope, name, init_file))

                else:
                    # match with exports
                    # print("Export file: ", self.scopes_map.keys())
                    # print("Export file: ", export_file)
                    # print(export_file in self.scopes_map.keys())
                    # print(str(export_file) in self.scopes_map.keys())
                    for name, def_scope in self._get_exports(
                        self.scopes_map[export_file], export_file
                    ):
                        if imp.namespace.child == name:
                            imp2def.append((imp, def_scope, name, export_file))

        return imp2def

    # TODO: add some sort of hierarchal structure to the scopes?
    def _construct_scopes(self, fs: RepoFs) -> Dict[Path, ScopeGraph]:
        """
        Returns all the scopes associated with the files in the directory
        """
        scope_map = {}
        for path, file_content in fs.get_files_content():
            # index by full path
            sg = build_scope_graph(file_content, language=LANGUAGE)
            scope_map[path] = sg

        return scope_map

    # ultimately the output should be 3-tuple
    # (import_stmt, path, import_type)
    def _construct_import(
        self, g: ScopeGraph, file: Path, fs: RepoFs
    ) -> List[LocalImport]:
        """
        Returns a list of file imports
        """
        # lists for checking if python module is system or third party
        sys_modules_list = SysModules(LANGUAGE)
        third_party_modules_list = ThirdPartyModules(LANGUAGE)

        imports = []
        for scope in g.scopes():
            for imp in g.imports(scope):
                imp_node = g.get_node(imp)
                imp_stmt = LocalImportStmt(imp_node.range, **imp_node.data)
                imp_blocks = import_stmt_to_import(
                    import_stmt=imp_stmt,
                    filepath=file,
                    g=g,
                    fs=fs,
                    sys_modules=sys_modules_list,
                    third_party_modules=third_party_modules_list,
                )
                imports.extend(imp_blocks)

        return imports

    # NOTE: this would need to be handled differently for other langs
    def _get_exports(self, g: ScopeGraph, file: Path) -> List[Tuple[str, ScopeID]]:
        """
        Constructs a map from file to its exports (unreferenced definitions)
        """
        exports = []

        # have to do this because class/func defs are tied to the same scope
        # they open, so they are child of root instead of being defined at root
        outer_scopes = [g.root_idx] + [s for s in g.child_scopes(g.root_idx)]

        for scope in outer_scopes:
            for def_node in g.definitions(scope):
                # dont want to pick up non class/func defs in the root - 1 scope
                if scope != g.root_idx and (
                    def_node.data["def_type"] == "class"
                    or def_node.data["def_type"] == "function"
                ):
                    exports.append((def_node.name, scope))

        return exports

    def to_str(self):
        repr = ""
        for u, v, _ in self._graph.edges(data=True):
            u = self.get_node(u)
            v = self.get_node(v)

            repr += f"{u} -> {v}\n"

        return repr

    def print_missing_imports(self):
        for path, missing_imports in self._missing_import_refs.items():
            total_missing = 0
            total_resolved = 0

            print("Path: ", path)
            for missed in missing_imports:
                print("-", missed)
                total_missing += 1
            if self._resolved_import_refs.get(path, None):
                for resolved in self._resolved_import_refs[path]:
                    total_resolved += 1
                    print("Resolved: ", resolved)

            print(f"Total missing: {total_missing}, Total resolved: {total_resolved}")
