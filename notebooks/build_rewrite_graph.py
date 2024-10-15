import sys

from pathlib import Path
from dataclasses import dataclass
from typing import List

from ..rtfs.chunk_resolution.graph import ChunkNode, ChunkMetadata
from rtfs_rewrite.ts import cap_ts_queries, TSLangs
from rtfs_rewrite.fs import RepoFs
from rtfs_rewrite.ingest import ingest

from networkx import DiGraph
import networkx as nx
import json



# define a cluster interface to search code over
class Chunk:
    def __init__(self, file_path: Path, id: str):
        self.id = id
        self.file_path = file_path
        self.definitions = []
        self.references = []

    def __str__(self):
        repr = f"[FILE]: {self.file_path.name}\n"
        repr += "".join([f"  [DEFINITIONS]: {d}\n" for d in self.definitions])
        repr += "".join([f"  [REFERENCES]: {r}\n" for r in self.references])
        return repr


repo_path = "test_repos/aider"
chunks = ingest(repo_path)
graph = DiGraph()

all_chunks: List[ChunkNode] = []
for chunk in chunks:
  chunk_node = ChunkNode(
    id=chunk.node_id,
    og_id=chunk.node_id,
    metadata=ChunkMetadata(**chunk.metadata),
    content=chunk.get_content()
  )
  definitions = []
  references = []
  for node, capture_name in cap_ts_queries(
    bytearray(chunk.get_content(), encoding="utf-8"), TSLangs.PYTHON
  ):
    match capture_name:
      case "name.definition.class":
        definitions.append(node.text.decode())
      case "name.definition.function":
        definitions.append(node.text.decode())
      case "name.reference.call":
        references.append(node.text.decode())
  
  chunk_node.definitions = definitions
  chunk_node.references = references
  all_chunks.append(chunk_node)
  graph.add_node(chunk_node.id)


# build relation ships
for c1 in all_chunks:
    for c2 in all_chunks:
        for ref in c1.references:
            if (
                ref in c2.definitions
                and c1.id != c2.id
                and not graph.has_edge(c1.id, c2.id)
            ):
                graph.add_edge(c1.id, c2.id, ref=ref)

graph_dict = {}
# Convert the graph to a dictionary
graph_dict["link_data"] = nx.node_link_data(graph)

# Write the graph to a JSON file
with open("repo_graph.json", "w") as json_file:
    json.dump(graph_dict, json_file, indent=2)


# load into chunk graph and cluster
print("Graph has been written to 'repo_graph.json'")
