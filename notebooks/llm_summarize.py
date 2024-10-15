import sys
import ell
from typing import List
from pathlib import Path

sys.path.append("..")

from rtfs.fs import RepoFs
from src.repo.graph import summarize as graph_summarize

REPO_BASE = Path("../codesearch-data/repo")
INDEX_BASE = Path("../codesearch-data/index")
GRAPH_BASE = Path("../codesearch-data/graph")

repos = [
    "JohnPeng47_CrashOffsetFinder.git",
    # REPO_BASE / "Aider-AI_aider.git",
]


class ClusterList:
    clusters: List[str]


## TODO TMRW: complete the rest of this, with evals and shit


@ell.simple(model="gpt-4o-2024-08-06")
def summarize(repo_code):
    SUMMARY_PROMPT = """
You are charged with grouping the following source code into a set of different clusters. Each
cluster should capture a functional feature of the codebase. 

The generated clusters should be mutually exclusive
Each cluster should cover the non-trivial parts of the codebase
Focus on identifying clusters/features that implement some cross-file feature
Identify how parts of different files are used together to implement a feature

Lastly, simply return the cluster names in a list like so, without any additional info
or explanations:
1. <CLUSTER 1>
2. <CLUSTER 2>
....

Here is the code:
{code}
    """
    try:
        return SUMMARY_PROMPT.format(code=repo_code)
    except Exception as e:
        raise e


def gen_llm_clusters(repo):
    repo_contents = ""
    for f, content in RepoFs(REPO_BASE / repo).get_files_content():
        repo_contents += f"{f}\n{content}\n"

    return summarize(repo_contents)


def gen_manual_clusters(repo):
    return [
        cluster["title"]
        for cluster in graph_summarize(
            INDEX_BASE / repo,
            REPO_BASE / repo,
            GRAPH_BASE / repo,
        )
    ]


for repo in repos:
    llm_clusters = gen_llm_clusters(repo)
    manual_clusters = gen_manual_clusters(repo)
    print("LLM clusters:")
    print(llm_clusters)
    print("Manual clusters:")
    print(manual_clusters)
