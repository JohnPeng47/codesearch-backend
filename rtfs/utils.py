from pydantic import BaseModel
from tree_sitter import Point
from collections import deque
from typing import TypeAlias, Tuple, List
import json
from rtfs.config import SYS_MODULES_LIST, THIRD_PARTY_MODULES_LIST
from pathlib import Path
from collections import deque
import yaml
from dataclasses import dataclass
from logging import getLogger

logger = getLogger(__name__)

SymbolId: TypeAlias = str


class VerboseSafeDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def dfs_json(json_data):
    """
    For traversing JSON representations of a tree linked by children key
    """
    stack = deque([(json_data, 0)])  # Stack of (node, depth) pairs

    while stack:
        node, depth = stack.pop()

        # Process the current node
        yield node, depth

        # Add children to the stack in reverse order
        # This ensures left-to-right traversal when popping from the stack
        for child in reversed(node.get("children", [])):
            stack.append((child, depth + 1))


@dataclass
class TextRange:
    start_byte: int
    end_byte: int 
    start_point: Point
    end_point: Point

    def __post_init__(self):    
        if type(self.start_point) is not Point:
            raise ValueError("start_point must be a Point object")
        if type(self.end_point) is not Point:
            raise ValueError("end_point must be a Point object")

    def add_offset(self, start_offset: int, end_offset: int):
        new_start_point = Point(
            self.start_point.row + start_offset,
            self.start_point.column,
        )
        new_end_point = Point(
            self.end_point.row + end_offset,
            self.end_point.column,
        )

        return TextRange(
            start_byte=self.start_byte,
            end_byte=self.end_byte,
            start_point=new_start_point,
            end_point=new_end_point,
        )

    def __lt__(self, other: "TextRange"):
        return self.contains_line(other)

    def line_range(self):
        return self.start_point.row, self.end_point.row

    def contains(self, range: "TextRange"):
        if not range.start_byte or not self.end_byte:
            raise ValueError(
                "Byte range is not set, did you mean to call contains_line?"
            )

        return range.start_byte >= self.start_byte and range.end_byte <= self.end_byte

    def contains_line(self, other: "TextRange", overlap=False):
        # print(type(self), type(other))
        # print(type(self.start_point), type(other.start_point))
        if overlap:
            # check that at least one of the points is within the range
            return (
                other.start_point.row >= self.start_point.row
                and other.start_point.row <= self.end_point.row
            ) or (
                other.end_point.row <= self.end_point.row
                and other.end_point.row >= self.start_point.row
            )

        return (
            other.start_point.row >= self.start_point.row
            and other.end_point.row <= self.end_point.row
        )


def get_shortest_subpath(path: Path, root: Path) -> Path:
    """
    Returns the shortest subpath of the given path that is relative to the root
    """
    return path.relative_to(root)


class SysModules:
    def __init__(self, lang):
        """
        Loads a list of system modules for a given language
        """

        try:
            sys_mod_file = open(SYS_MODULES_LIST, "r")
            self.sys_modules = json.loads(sys_mod_file.read())
        except Exception as e:
            logger.error(f"Error loading system modules: {e}")
            self.sys_modules = []

    def __iter__(self):
        return iter(self.sys_modules)

    def check(self, module_name):
        return module_name in self.sys_modules


class ThirdPartyModules:
    def __init__(self, lang):
        """
        Loads a list of third party modules for a given language
        """
        self.lang = lang

        try:
            with open(THIRD_PARTY_MODULES_LIST, "r") as file:
                self.third_party_modules = json.loads(file.read())["modules"]
        except Exception as e:
            logger.error(f"Error loading third party modules: {e}")
            self.third_party_modules = []

    def check(self, module_name):
        return module_name in self.third_party_modules

    def __iter__(self):
        return iter(self.third_party_modules)

    def update(self, new_modules: List[str]):
        """
        Updates the list of third party modules and writes back to the file
        """
        self.third_party_modules.extend(new_modules)

        try:
            with open(THIRD_PARTY_MODULES_LIST, "w") as file:
                json.dump({"modules": self.third_party_modules}, file, indent=4)
        except Exception as e:
            logger.error(f"Error writing third party modules: {e}")
