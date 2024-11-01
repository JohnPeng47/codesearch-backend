from pathlib import Path
from src.chunk.lmp.classify_tree import classify_tree

import ell
from dir_tree import generate_tree

ell.init("ell_storage/chunk_alt")

repo_name = "dspy"
repo_path = Path("src/cluster/repos") / repo_name

tree = generate_tree(repo_path)
print(tree)