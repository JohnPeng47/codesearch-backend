from pathlib import Path
from .lmp import generate_clusters
from .chunk_repo import chunk_repo

EXCLUSIONS = [
    "**/tests/**",
    "**/examples/**"
]

class LLMException(Exception):
    pass

# NOTE: maybe we can run the clustering algorithm beforehand to seed the order
# of the chunks, reducing the "distance" penalty in classification
def _calculate_clustered_range(matched_indices, length):
    """Measures how wide the range of the clustered chunks are"""
    pass

# Should track how good we are at tracking faraway chunks
def generate_full_code(repo_path: Path, tries: int = 1):
    cluster_inputs = chunk_repo(repo_path, exclusions=EXCLUSIONS)
    free_chunks = [chunk.sensible_id() for chunk in cluster_inputs]

    for _ in range(tries):
        clusters = generate_clusters(cluster_inputs).parsed.topics
        if not isinstance(clusters, list):
            raise LLMException(f"Failed to generate list: {clusters}")
        
        # calculate the clustered range
        # NOTE: chunk_name != chunk.id, former is for LLM, later is for us
        matched_indices = [i for cluster in clusters for i, chunk in enumerate(free_chunks) if chunk in cluster.chunk_ids]
        _calculate_clustered_range(matched_indices, len(free_chunks))

        for cluster in clusters:
            print(cluster)

        # calculate new inputs and run again until empty or no chunks to classify
        cluster_inputs = [chunk_name for i, chunk_name in 
                          enumerate(cluster_inputs) if i not in matched_indices]
        free_chunks = [chunk_name for chunk_name in cluster_inputs]

        print("Unclassified chunks: ", len(free_chunks))
