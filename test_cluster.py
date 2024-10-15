from src.cluster.cluster import (
    generate_full_code_clusters, 
    generate_graph_clusters, 
    generate_summarized_clusters
)
from src.llm.evals import eval_clusters_similarity

from pathlib import Path

repo_name = "CrashOffsetFinder"
repo_path = Path("src/cluster/repos") / repo_name

# Generate clusters
full_code_clusters = generate_full_code_clusters(repo_path)
graph_clusters = generate_graph_clusters(repo_path)

# Evaluate similarity between full_code and summary clusters
for i in range(1, 7):
    try:
        print(f"Clustering run {i}")
        summary_clusters = generate_summarized_clusters(repo_path)
        full_code_summary_sim = eval_clusters_similarity(full_code_clusters, summary_clusters)
        for metric, score in full_code_summary_sim.items():
            print(f"{metric}: {score}")
    except Exception as e:
        print("Run failed!")
        continue

print("\n");  # Add a blank line for readability

# Evaluate similarity between full_code and graph clusters
full_code_graph_sim = eval_clusters_similarity(full_code_clusters, graph_clusters)
print("Similarity between full code and graph clusters:")
for metric, score in full_code_graph_sim.items():
    print(f"{metric}: {score}")




# # print(graph_clusters)

# matching = compare_eval(graph_clusters, llm_clusters, "Graph", "LLM")
