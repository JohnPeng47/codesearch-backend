from src.cluster.cluster import generate_full_code
from pathlib import Path

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

generate_full_code(repo_path)