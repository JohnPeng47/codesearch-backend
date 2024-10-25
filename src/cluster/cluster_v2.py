from .models import (
    CodeChunk, 
    LMClusteredTopicList, 
    ClusteredTopic,
    LMClusteredTopic
)
from src.chunk.models import ClusterInput

from typing import List, Callable, Set, Dict
from pydantic import BaseModel
from typing import Set

# TODO: change this to keep track of every successive cluster stat
# so we can see the change in perf as the iterations go on
class ClusterIterationStat(BaseModel):
    unique_chunks: Set = set()
    total_chunks: int = 0
    unclassified_chunks: int = 0
    total_input_chunks: int = 0
    current_iteration: int = 0
    
    def __add__(self, other: 'ClusterIterationStat') -> 'ClusterIterationStat':
        return ClusterIterationStat(
            unique_chunks=self.unique_chunks.union(other.unique_chunks),
            total_chunks=self.total_chunks + other.total_chunks,
            unclassified_chunks=other.unclassified_chunks,  # Take the most recent
            total_input_chunks=other.total_input_chunks,    # Take the most recent
            current_iteration=max(self.current_iteration, other.current_iteration)
        )
    
    def __str__(self):
        return (f"Iteration {self.current_iteration} statistics:\n"
                f"Unclassified chunks: {self.unclassified_chunks} / {self.total_input_chunks}\n"
                f"Unique chunks: {len(self.unique_chunks)}\n"
                f"Total clustered chunks: {self.total_chunks}")

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
        self.stats = ClusterIterationStat()
        
    def run(self) -> List[ClusteredTopic]:
        cluster_inputs = self.chunks.copy()
        all_chunks = self.chunks.copy()
        name_to_cluster = {chunk.get_name(): i for i, chunk in enumerate(all_chunks)}
        
        generated_clusters = []
        
        for iteration in range(1, self.max_iters + 1):
            # Check early stopping condition
            if len(cluster_inputs) < 0.3 * len(all_chunks):
                break
                
            # Update iteration stats
            self.stats.current_iteration = iteration
            self.stats.unclassified_chunks = len(cluster_inputs)
            self.stats.total_input_chunks = len(all_chunks)
                
            # Get clusters for current iteration
            new_clusters = self._cluster_iteration(
                cluster_inputs=cluster_inputs,
                all_chunks=all_chunks,
                name_to_cluster=name_to_cluster
            )
            
            generated_clusters.extend(new_clusters)
            # Log current iteration statistics
            print(self.stats)
            
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
        clusters = self.cluster_op(self.chunks)
        new_clusters = []
        iteration_stat = ClusterIterationStat()
        
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
                iteration_stat.unique_chunks.add(matched_chunk)
                iteration_stat.total_chunks += 1

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
        
        # Accumulate statistics
        self.stats += iteration_stat
        return new_clusters