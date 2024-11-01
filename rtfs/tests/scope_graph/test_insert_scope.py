from rtfs.build_scopes import build_scope_graph
from rtfs.languages import PythonParse
from rtfs.scope_resolution.scope import LocalScope
from rtfs.scope_resolution.scope_graph import ScopeGraph
from rtfs.utils import TextRange

from conftest import range

def test_insert_scope():
    scope_graph = ScopeGraph(range(start=1, end=6))

    # scope 1:
    #   -> scope2
    #       -> scope 3
    #   -> scope 4
    scope1 = LocalScope(range(1, 5))
    scope2 = LocalScope(range(2, 4))
    scope3 = LocalScope(range(3, 4))
    scope4 = LocalScope(range(1, 4))

    scope_graph.insert_local_scope(scope1)
    scope_graph.insert_local_scope(scope2)
    scope_graph.insert_local_scope(scope3)
    scope_graph.insert_local_scope(scope4)

    print(scope_graph.to_str())
    graph_state = """
1: --ScopeToScope-> 0:
2: --ScopeToScope-> 1:
3: --ScopeToScope-> 2:
4: --ScopeToScope-> 1:
"""

    assert scope_graph.to_str() == graph_state


def test_interval_scopes():
    file_path = "C:\\Users\\jpeng\\Documents\\projects\\cowboy_baseline\\tests\\repos\\small_repo\\a.py"

    with open(file_path, "rb") as file:
        code = file.read()

    scope_graph = build_scope_graph(code)

    graph_state = """
1: --ScopeToScope-> 0:
2: --ScopeToScope-> 1:
3: --ScopeToScope-> 0:
4: --ScopeToScope-> 3:
5: --ImportToScope-> 0:
6:main --DefToScope-> 1:
7:func2 --DefToScope-> 2:
8:a --DefToScope-> 1:
9:A --DefToScope-> 3:
10:func1 --DefToScope-> 4:
11:main2 --RefToImport-> 5:
11:main2 --RefToOrigin-> 1:
12:main2 --RefToImport-> 5:
12:main2 --RefToOrigin-> 4:
"""

    assert scope_graph.to_str() == graph_state
