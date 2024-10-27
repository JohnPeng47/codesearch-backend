from .models import (
    CodeChunk, 
    LMClusteredTopicList, 
    ClusteredTopic,
    LMClusteredTopic
)
from src.chunk.models import ClusterInput

from typing import List, Callable, Set, Dict

class ClusterStrategy:
    def __init__(self, 
                 chunks: List[CodeChunk], 
                 *,
                 cluster_op: Callable[[List[ClusterInput]], List[LMClusteredTopic]],
                 # TODO: add recluster op
                 max_iters: int = 5):
        self.chunks = chunks
        self.cluster_op = cluster_op
        self.max_iters = max_iters
        
    def run(self,
            iterative: bool = True) -> List[ClusteredTopic]:
        cluster_inputs = self.chunks.copy()
        all_chunks = self.chunks.copy()
        name_to_cluster = {chunk.get_name(): i for i, chunk in enumerate(all_chunks)}
        
        generated_clusters = []
        
        for _ in range(1, self.max_iters + 1):
            # Check early stopping condition
            if len(cluster_inputs) < 0.3 * len(all_chunks):
                break
                                
            # Get clusters for current iteration
            new_clusters = self._cluster_iteration(
                cluster_inputs=cluster_inputs,
                all_chunks=all_chunks,
                name_to_cluster=name_to_cluster
            )
            
            generated_clusters.extend(new_clusters)
            if iterative:
                cluster_inputs = new_clusters
            
        return generated_clusters

    def _cluster_iteration(
        self,
        cluster_inputs: List[ClusterInput],
        all_chunks: List[ClusterInput],
        name_to_cluster: Dict[str, int]
    ) -> List[ClusteredTopic]:
        """
        Iterate through the output of the cluster operation and match the names of the LLM output
        to actual CodeChunk objects and update the stats
        """
        clusters = self.cluster_op(cluster_inputs)
        new_clusters = []
        unique_chunks = set()
        
        for cluster in clusters:
            chunks = []
            for chunk_name in cluster.chunks:
                chunk_index = name_to_cluster.get(chunk_name)
                if chunk_index is None:
                    print(f"Chunk Name: {chunk_name} hallucinated, skipping...")
                    continue
                
                matched_chunk = all_chunks[chunk_index]
                chunks.append(matched_chunk)
                
                # Remove clustered chunk from inputs
                try:
                    cluster_inputs.remove(matched_chunk)
                except ValueError:
                    pass

                # Update iteration statistics
                unique_chunks.add(matched_chunk)

            if chunks:  # Only create cluster if it has valid chunks
                new_clusters.append(
                    ClusteredTopic(
                        name=cluster.name,
                        chunks=[
                            {k: v for k, v in chunk.dict().items() 
                             if k != "metadata"} for chunk in chunks
                        ]
                    )
                )

        return new_clusters