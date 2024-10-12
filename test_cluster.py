from src.cluster.cluster import generate_full_code, generate_graph_cluster
from src.cluster.eval import compare_eval
from pathlib import Path

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

graph_clusters = generate_graph_cluster(repo_path)
llm_clusters = generate_full_code(repo_path)

print("Graph Clusters:")
for i, cluster in enumerate(graph_clusters):
    print(f"Cluster {i + 1}:")
    for chunk in cluster.chunks:
        print(f"  - {chunk.id}")
    print()

print("LLM Clusters:")
for i, cluster in enumerate(llm_clusters):
    print(f"Cluster {i + 1}: {cluster.name}")
    for chunk in cluster.chunks:
        print(f"  - {chunk.id}")
    print()

matching = compare_eval(graph_clusters, llm_clusters)
for a,b in matching:
    print("match: ")
    print(a)
    print(b)