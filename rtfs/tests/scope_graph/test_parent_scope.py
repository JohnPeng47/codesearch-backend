from rtfs.build_scopes import build_scope_graph
from rtfs.languages import PythonParse
from rtfs.scope_resolution.definition import LocalDef
from rtfs.scope_resolution.scope import LocalScope
from rtfs.scope_resolution.scope_graph import ScopeGraph
from rtfs.utils import TextRange

from conftest import range


def test_parent_scope():
    scope_graph = ScopeGraph(range(1, 6))

    scope1 = LocalScope(range=range(1, 5))
    scope2 = LocalScope(range=range(2, 4))
    scope3 = LocalScope(range=range(3, 4))
    scope4 = LocalScope(range=range(1, 4))

    scope_graph.insert_local_scope(scope1)
    scope_graph.insert_local_scope(scope2)
    scope_graph.insert_local_scope(scope3)
    scope_graph.insert_local_scope(scope4)

    graph_state = """
1: --ScopeToScope-> 0:
2: --ScopeToScope-> 1:
3: --ScopeToScope-> 2:
4: --ScopeToScope-> 3:
"""

    assert scope_graph.to_str() == graph_state

    assert scope_graph.parent_scope(3) == 2
    assert list(scope_graph.parent_scope_stack(3)) == [3, 2, 1, 0]


def test_child_scopes():
    scope_graph = ScopeGraph(range(1, 6))

    scope1 = LocalScope(range=range(1, 5))
    scope2 = LocalScope(range=range(2, 4))
    scope3 = LocalScope(range=range(3, 4))
    scope4 = LocalScope(range=range(1, 4))

    scope_graph.insert_local_scope(scope1)
    scope_graph.insert_local_scope(scope2)
    scope_graph.insert_local_scope(scope3)
    scope_graph.insert_local_scope(scope4)

    graph_state = """
1: --ScopeToScope-> 0:
2: --ScopeToScope-> 1:
3: --ScopeToScope-> 2:
4: --ScopeToScope-> 3:
"""

    assert scope_graph.to_str() == graph_state
    assert scope_graph.child_scope_stack(0) == [1, 2, 3, 4]
