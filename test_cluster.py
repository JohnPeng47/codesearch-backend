from src.cluster.cluster import generate_llm_clusters, generate_graph_clusters
from src.cluster.eval import compare_eval
from src.cluster.methods.sum_chunks import summarize_chunks
from pathlib import Path

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

summaries = summarize_chunks(repo_path)

# graph_clusters = generate_graph_clusters(repo_path)
# llm_clusters = generate_llm_clusters(repo_path)

# # print(graph_clusters)

# matching = compare_eval(graph_clusters, llm_clusters, "Graph", "LLM")
