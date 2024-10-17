from pathlib import Path
from src.cluster.cluster import (
    generate_full_code_clusters, 
    generate_summarized_clusters,
    generate_graph_clusters
)

from src.cluster.types import (
    CodeChunk,
    SummaryChunk,
    ClusterInput,
    ClusteredTopic,
    ClusterInputType,
    LMClusteredTopicList
)


repo_name = "ell"
repo_path = Path("../../src/cluster/repos") / repo_name

from src.llm.evals.eval_cluster import eval_coherence_cluster


full_code_clusters = generate_full_code_clusters(repo_path)
graph_clusters = generate_graph_clusters(repo_path)

full_code_cohere = eval_coherence_cluster(full_code_clusters, iters=5)
graph_cohere = eval_coherence_cluster(graph_clusters, iters=5)

print("Full code coherence score: ", full_code_cohere)
print("Graph coherence score: ", graph_cohere)