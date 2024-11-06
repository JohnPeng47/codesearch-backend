from rtfs.build_scopes import build_scope_graph
from rtfs.languages import PythonParse
from rtfs.scope_resolution.definition import LocalDef
from rtfs.scope_resolution.scope import LocalScope
from rtfs.scope_resolution.scope_graph import ScopeGraph
from rtfs.utils import TextRange


def test_insert_def():
    scope_graph = ScopeGraph(
        TextRange(start_byte=1, end_byte=6, start_point=(0, 0), end_point=(0, 0))
    )

    # modeling the following code:
    #
    #     fn main() {
    #        let a = 2;
    #        let b = 3;
    #     }

    local_scope = LocalScope(
        TextRange(start_byte=1, end_byte=5, start_point=(0, 0), end_point=(0, 0))
    )
    scope_graph.insert_local_scope(local_scope)

    # Insert a local definition
    local_def = LocalDef(
        TextRange(start_byte=2, end_byte=3, start_point=(0, 0), end_point=(0, 0)),
        buffer=bytearray(b"a"),
        symbol="a",
    )
    scope_graph.insert_local_def(local_def)

    # Insert a hoisted definition
    hoisted_def = LocalDef(
        TextRange(start_byte=3, end_byte=4, start_point=(0, 0), end_point=(0, 0)),
        buffer=bytearray(b"b"),
        symbol="b",
    )
    scope_graph.insert_hoisted_def(hoisted_def)

    # Insert a global definition
    global_def = LocalDef(
        TextRange(start_byte=4, end_byte=5, start_point=(0, 0), end_point=(0, 0)),
        buffer=bytearray(b"global"),
        symbol="global",
    )
    scope_graph.insert_global_def(global_def)

    graph_state = """
1: --ScopeToScope-> 0:
2: --DefToScope-> 1:
3: --DefToScope-> 0:
4:a --DefToScope-> 0:
"""

    assert scope_graph.to_str() == graph_state
