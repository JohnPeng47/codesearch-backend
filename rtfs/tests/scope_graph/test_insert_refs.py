from rtfs.build_scopes import build_scope_graph
from rtfs.languages import PythonParse
from rtfs.scope_resolution.definition import LocalDef
from rtfs.scope_resolution.scope import LocalScope
from rtfs.scope_resolution.scope_graph import ScopeGraph
from rtfs.utils import TextRange


def test_insert_refs():
    test = """
import abc
a = 1

def func1(self):
    abc()
"""

    g = build_scope_graph(bytearray(test, encoding="utf-8"), language="python")
    print(g.to_str())


def test_unresolved_refs():
    test = """
def _create_span_id(self, block: CodeBlock, label: Optional[str] = None):
    if block.type.group == CodeBlockTypeGroup.STRUCTURE:
        structure_block = block
    else:
        structure_block = block.find_type_group_in_parents(
            CodeBlockTypeGroup.STRUCTURE
        )

    span_id = structure_block.path_string()
    if label and span_id:
        span_id += f":{label}"
    elif label and not span_id:
        span_id = label
    elif not span_id:
        span_id = "impl"

    if span_id in self._span_counter:
        self._span_counter[span_id] += 1
        span_id += f":{self._span_counter[span_id]}"
    else:
        self._span_counter[span_id] = 1

    return span_id

def _count_tokens(self, content: str):
    if not self.tokenizer:
        return 0
    return len(self.tokenizer(content))

def debug_log(self, message: str):
    if self.debug:
        logger.debug(message)

"""

    g = build_scope_graph(bytearray(test, encoding="utf-8"), language="python")

    print([g.get_node(r).name for r in g.references_by_origin(1)])
