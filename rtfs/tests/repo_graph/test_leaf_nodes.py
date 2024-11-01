from rtfs.build_scopes import build_scope_graph


def test_leaf_scopes():
    test = """
def func1():
    pass
    
def func2():
    pass
"""
    scope_graph = build_scope_graph(
        bytearray(test, encoding="utf-8"), language="python"
    )
    leaf_scopes = list(scope_graph.get_leaf_scopes(scope_graph.root_idx))

    assert len(leaf_scopes) == 2
