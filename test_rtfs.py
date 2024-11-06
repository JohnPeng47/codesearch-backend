from new_rtfs import ScopeGraph
from pathlib import Path

repo_name = "cowboy-server"
repo_dir = Path("src/cluster/repos") / repo_name

ScopeGraph.from_file(repo_dir)
