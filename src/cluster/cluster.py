from .models import (
    CodeChunk, 
    LMClusteredTopicList, 
    ClusteredTopic,
    LMClusteredTopic
)
from src.chunk.models import ClusterInput
from src.llm.lmp_base import LMP

from typing import List, Callable, Set, Dict

class LMChunk(ClusterInput):
    def __init__(self, chunk: CodeChunk):
        self._id = chunk.id
        self._content = chunk.content
        self._summary = chunk.summary

    def get_chunkinfo(self) -> str:
        return self._id
    
    def get_content(self) -> str:
        return self._content
    
    def get_name(self) -> str:
        return self._id

    def set_content(self, content: str):
        self._content = content

    def get_summary(self) -> str:
        return self._summary

class ClusterStrategy:
    """
    Generates clusters from a list of CodeChunks
    """
    def __init__(self, 
                 chunks: List[CodeChunk],
                 *,
                 cluster_op: Callable[[List[ClusterInput]], List[LMClusteredTopic]],
                 enrich_ops: Callable = []):
        self.chunks = chunks
        self.name_to_chunk = {
            chunk.get_name(): chunk for i, chunk in enumerate(self.chunks)
        }

        self.cluster_op = cluster_op
        self.enrich_ops = enrich_ops
    
    def run(self,
            remove_classified: bool = True,
            iters: int = 1):
        # create chunks that we can manipulate the representation of
        cluster_inputs = [LMChunk(chunk) for chunk in self.chunks]
        generated_clusters = []
        
        for _ in range(1, iters + 1):
            # Check early stopping condition
            if len(cluster_inputs) < 0.3 * len(self.chunks):
                break
                                
            # Get clusters for current iteration
            new_clusters = self._cluster_iteration(cluster_inputs)
            # apply gather ops
            for enrich_op in self.enrich_ops:
                new_clusters = enrich_op(new_clusters, cluster_inputs)

            generated_clusters.extend(new_clusters)
            if remove_classified:
                new_chunks = [new_chunk.get_name() for cluster in new_clusters for new_chunk in cluster.chunks]
                cluster_inputs = [chunk for chunk in cluster_inputs if chunk.get_name() not in new_chunks]

            print(f"Chunks clustered this round: { len(new_chunks)}/{len(self.chunks)}" )
            print(f"New inputs: {len(cluster_inputs)}")

        return generated_clusters
            
    def _cluster_iteration(
        self,
        cluster_inputs: List[ClusterInput]
    ) -> List[ClusteredTopic]:
        """
        Iterate through the output of the cluster operation and match the names of the LLM output
        to actual CodeChunk objects and update the stats
        """
        clusters, perplexity = self.cluster_op(cluster_inputs)
        all_inputs = [chunk.get_name() for chunk in cluster_inputs]
        new_clusters = []
        
        for cluster in clusters:
            chunks = []
            for chunk_name in cluster.chunks:
                matched_chunk = self.name_to_chunk.get(chunk_name)
                if not matched_chunk or matched_chunk.get_name() not in all_inputs:
                    print(f"Chunk Name: {chunk_name} hallucinated, skipping...")
                    continue
                
                # here matched_chunk is a real chunk
                chunks.append(matched_chunk)
            if chunks:
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