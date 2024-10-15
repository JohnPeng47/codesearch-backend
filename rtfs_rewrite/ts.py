import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from importlib import resources as pkg_resources
from enum import Enum
from pathlib import Path

# QUERY_FOLDER = pkg_resources.files("rtfs") / "queries"
QUERY_FOLDER = Path(__file__).parent / "queries"
LANG_QUERY = "{language}-cap.scm"


class TSLangs(str, Enum):
    PYTHON = "python"


def cap_ts_queries(file_content: bytearray, language: TSLangs):
    query_file = open(QUERY_FOLDER / LANG_QUERY.format(language=language), "rb").read()

    PY_LANGUAGE = Language(tspython.language())

    parser = Parser()
    parser.set_language(PY_LANGUAGE)

    root = parser.parse(file_content).root_node
    query = PY_LANGUAGE.query(query_file)

    return query.captures(root)
