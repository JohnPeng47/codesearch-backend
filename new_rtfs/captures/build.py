from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Parser


def build_query(language: str, file_content: bytearray, query_file: str):
    query_file = open(Path(__file__) / "ts_queries" / f"{language}.scm", "rb").read()

    PY_LANGUAGE = Language(tspython.language())
    parser = Parser()
    parser.set_language(PY_LANGUAGE)
    root = parser.parse(file_content).root_node
    query = PY_LANGUAGE.query(query_file)

    return query, root
