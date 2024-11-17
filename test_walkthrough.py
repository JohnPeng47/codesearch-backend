from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.summarize.summarize import Summarizer
from src.config import GRAPH_ROOT
from src.chunk.chunk import chunk_repo, ChunkStrat
from src.chat.lmp.walkthrough import identify_transitions, generate_walkthroughs
from src.config import WALKTHROUGH_ROOT

from llm import LLMModel

import json
from pathlib import Path


def write_new(name, walkthroughs):
    walkthrough_path = WALKTHROUGH_ROOT / "aorwall_moatless-tools"
    # Read existing content
    try:
        with open(walkthrough_path, "r") as f:
            old = json.loads(f.read())
            if not isinstance(old, list):
                old = []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Starting fresh file due to: {e}")
        old = []

    # Add new walkthrough
    old.append({
        "name": name,
        "walkthroughs": [c.dict() for c in walkthroughs]
    })

    # Write back entire file
    with open(walkthrough_path, "w") as f:
        json.dump(old, f, indent=2)

    print(f"Wrote {len(old)} walkthroughs: {[w['name'] for w in old]}")

model = LLMModel(provider="openai")

WALKTHROUGH = """
1. Entry Point - `benchmark/claude_evaluation.py`:
- The process starts in the Claude evaluation module where functions like `evaluate_search()` or `evaluate_search_and_identify()` initialize the evaluation
- These functions set up the transition rules and evaluation parameters

2. Evaluation Setup - `benchmark/evaluation.py`:
- The `Evaluation` class creates an evaluation instance with configured parameters
- It handles setting up directories, managing trajectories, and initializing the workspace

3. State Management - `AgenticLoop`:
- The `AgenticLoop` class manages the state transitions and execution flow
- It starts with the initial state (SearchCode) and handles transitions between states

4. Search Execution - `SearchCode` State:
- Initial state that handles the search request
- Interacts with the `CodeIndex` class to perform the actual search
- Uses the file context and workspace to manage code access

5. Search Engine - `CodeIndex`:
- The `semantic_search()` method orchestrates the search process
- Calls `_vector_search()` to perform the actual vector-based search
- Filters and processes results based on parameters like:
  - file patterns
  - class/function names
  - exact matches
  - token limits

6. Vector Search - `_vector_search()`:
- Performs the low-level vector search operation
- Creates query embeddings
- Applies filters and retrieves results from the vector store
- Processes and filters the results based on:
  - File patterns
  - Test file exclusions
  - Exact matches
  - Token counts

7. Result Processing:
- Results are returned as `SearchCodeResponsle` objects
- Contains hits with file paths and relevant code spans
- Includes metadata about the search results

8. State Transitions:
- Search results trigger transitions to subsequent states:
  - `IdentifyCode`: Processes and identifies reevant code spans
  - `DecideRelevance`: Makes decisions about the relevance of identified code
  - Finally transitions to either `Finished` or `Rejected` states
"""

chunk_paths = [
    "index/code_index.py::13",
    "index/code_index.py::7",
    "index/code_index.py::6", 
    "find/search.py::6",
    "moatless/loop.py::2",
    "moatless/loop.py::3",
    "moatless/loop.py::4",
    "moatless/transition_rules.py::1",
    "moatless/transition_rules.py::2", 
    "moatless/transition_rules.py::3",
    "moatless/transition_rules.py::4",
    "moatless/transition_rules.py::5",
    "benchmark/claude_evaluation.py::4",
    "benchmark/evaluation.py::2",
    "benchmark/evaluation.py::9",
    "benchmark/evaluation.py::5"
]

def get_cluster_from_chunk(chunks, cg):
    """Find the largest clusters containing each chunk.
    
    Args:
        chunks: List of chunk IDs to search for
        cg: ChunkGraph containing the clusters
        
    Returns:
        Set of clusters that contain the input chunks
    """
    clusters = set()
    
    for chunk in chunks:
        # Find all clusters containing this chunk
        matching_clusters = [
            cluster for cluster in cg.get_clusters(return_content=True)
            if chunk in [c.id for c in cluster.chunks]
        ]
        if matching_clusters:
            # Add the largest cluster containing this chunk
            largest_cluster = max(matching_clusters, key=lambda x: len(x.chunks))
            clusters.add(largest_cluster)
        else:
            print(f"Chunk {chunk} not found in any cluster")
            
    return clusters

# MOATLESS
repo_path = Path(r"C:\Users\jpeng\Documents\projects\codesearch-backend\src\cluster\repos\moatless-tools")
graph_path = GRAPH_ROOT / "aorwall_moatless-tools"
chunks = chunk_repo(repo_path, ChunkStrat.VANILLA)

graph_json = json.loads(open("full_code.json", "r").read())
cg = ChunkGraph.from_json(graph_path, graph_json)
matched_clusters = get_cluster_from_chunk(chunk_paths, cg)

transitions = identify_transitions(model, matched_clusters, WALKTHROUGH, start_cluster=10)
walkthroughs = generate_walkthroughs(model, WALKTHROUGH, transitions.transitions, matched_clusters)
write_new("New Test", walkthroughs)