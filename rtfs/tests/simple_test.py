from rtfs.build_scopes import build_scope_graph

from rtfs.repo_resolution.repo_graph import RepoGraph
from pathlib import Path


## Failing tests
# Dotted assignment/ref
test = """
h.a = 1
h.a = h.b

def func1():
    c = b
    d = 2
"""

# test = """
# from .abc import b

# b.c = 1

# class EpicSplitter(NodeParser):
#     a: int

# """

scope_graph = build_scope_graph(bytearray(test, encoding="utf-8"), language="python")
print(scope_graph.to_str())

# print(scope_graph.to_str())
# repo_graph = RepoGraph(Path("tests/repos/small_repo"))
# repo_graph.print_missing_imports()
# print(repo_graph.to_str())
