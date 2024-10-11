from src.cluster.cluster import generate_clusters
from pathlib import Path

repo_name = "ell"
repo_path = Path("src/cluster/repos") / repo_name

print(generate_clusters(repo_path))