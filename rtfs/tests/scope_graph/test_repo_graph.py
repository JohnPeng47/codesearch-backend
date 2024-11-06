from rtfs.build_scopes import build_scope_graph
from repo_graph import Module


def test_get_exports():
    test = """
h = 1

def func1():
    a = 1
    b = 2

class A:
    def b(self):
        pass

"""
    scope_graph = build_scope_graph(
        bytearray(test, encoding="utf-8"), language="python"
    )
    module = Module(scope_graph)

    assert module.exports == ["h", "func1", "A"]
