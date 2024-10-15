from typing import Any, Tuple, List, Sequence
from llama_index.core.node_parser.interface import NodeParser
from llama_index.core.schema import BaseNode
from pydantic import Field

from dataclasses import dataclass
from ts import cap_ts_queries, TSLangs
from pathlib import Path


class TextRange:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def __str__(self):
        return f"({self.start}, {self.end})"

    def to_range(self):
        return (self.start, self.end)

    def overlap(self, other: "TextRange"):
        return (other.start >= self.start and other.start <= self.end) or (
            other.end <= self.end and other.end >= self.start
        )


class TSCapture:
    def __init__(self, name: str, range: TextRange):
        self.name = name
        self.range = range

    def __str__(self):
        return f"{self.name}: {self.range}"


class CapRanges:
    def __init__(self):
        self.caps: List[TSCapture] = []

    def __iter__(self):
        return iter(self.caps)

    def add_range(self, cap: TSCapture):
        if not self.caps or self.caps[-1].range.end < cap.range.start:
            self.caps.append(cap)
            return

        print("not added: ", self.caps[-1].range.to_range(), cap.range.to_range())


class File:
    def __init__(self, file_name: str, caps: CapRanges, file_content: str):
        self.file_name = file_name
        self.caps: List[TSCapture] = caps.caps
        self.contents = file_content.split("\n")

        # add blank ranges in between captures
        self.captures: List[TSCapture] = []

        for i in range(len(self.caps)):
            curr_cap = self.caps[i]
            if i == 0 and curr_cap.range.start != 0:
                self.captures.append(
                    TSCapture("UNKNOWN", TextRange(0, curr_cap.range.start - 1))
                )

            elif i > 0:
                unknown_range = curr_cap.range.start - self.captures[-1].range.end
                # print("UR: ", unknown_range)
                if unknown_range > 0:
                    self.captures.append(
                        TSCapture(
                            "UNKNOWN",
                            TextRange(
                                self.captures[-1].range.end + 1,
                                curr_cap.range.start - 1,
                            ),
                        )
                    )

            # lol lets just ignore the last range
            # if i == len(self.caps) - 1 and curr_cap.range !=
            self.captures.append(curr_cap)

    def __str__(self):
        repr = f"FILE: {self.file_name}\n"
        for cap in self.captures:
            # cap_content = "\n".join(self.contents[cap.range.start : cap.range.end])
            # repr += f"{cap.name}:{cap.range}\n{cap_content}\n"
            repr += f"{cap.name}:{cap.range}\n"

        return repr


@dataclass
class Definition:
    name: str
    range: TextRange
    type: str


class CodeChunker(NodeParser):
    max_size: int = Field(default=4096)
    language: str = Field(default="python")

    def _add_range(
        self, r: Tuple[str, TextRange], range_list: List[Tuple[str, TextRange]]
    ):
        """
        Add non-overlapping to list. This is basically the global scope
        """
        if not range_list or range_list[-1][1].end < r[1].start:
            range_list.append(r)

    def _parse_nodes(
        self, nodes: Sequence[BaseNode], show_progress: bool = False
    ) -> List[BaseNode]:
        # cant use self.language because it just prints Field.__str__() .....
        language = "python"

        for node in nodes:
            captures = cap_ts_queries(
                bytearray(node.get_content(), encoding="utf-8"), language
            )

            def_stack = []
            file_range = CapRanges()

            # in ts-query (at least for python), the def name will awlays get captured first
            # TODO: check if this is True for everything else
            for ts_node, name in captures:
                match name:
                    case "definition.class":
                        range = TextRange(
                            ts_node.range.start_point.row,
                            ts_node.range.end_point.row,
                        )
                        def_stack.append(range)

                    case "definition.function":
                        range = TextRange(
                            ts_node.range.start_point.row,
                            ts_node.range.end_point.row,
                        )
                        def_stack.append(range)

                    case "name.definition.class":
                        class_range = def_stack.pop()
                        class_name = ts_node.text.decode()

                        file_range.add_range(
                            TSCapture(name=class_name, range=class_range)
                        )

                    case "name.definition.function":
                        f_range = def_stack.pop()
                        f_name = ts_node.text.decode()

                        if f_name == "default_env_file":
                            pass

                        file_range.add_range(TSCapture(name=f_name, range=f_range))

            f = File(node.metadata["file_name"], file_range, node.get_content())

        return nodes
