import os
from src.config import REPOS_ROOT, INDEX_ROOT, GRAPH_ROOT, SUMMARIES_ROOT, EVAL_ROOT, CLUSTER_ROOT


def create_directories():
    directories = [REPOS_ROOT, INDEX_ROOT, GRAPH_ROOT, SUMMARIES_ROOT, EVAL_ROOT, CLUSTER_ROOT]

    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Directory created successfully: {directory}")
        except OSError as error:
            print(f"Error creating directory {directory}: {error}")


if __name__ == "__main__":
    create_directories()
