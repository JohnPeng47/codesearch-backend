from pathlib import Path
from .lmp import generate_clusters
from .chunk_repo import chunk_repo

EXCLUSIONS = [
    "**/tests/**",
    "**/examples/**"
]

def generate_clusters(repo_path: Path):
    chunked_content = chunk_repo(repo_path, exclusions=EXCLUSIONS)

    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(chunked_content)