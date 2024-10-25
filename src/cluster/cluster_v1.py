from pathlib import Path
from typing import List
import ell
import random
from openai import LengthFinishReasonError

from rtfs.aider_graph.aider_graph import AiderGraph
from rtfs.transforms.cluster import cluster as cluster_cg
from src.utils import num_tokens_from_string
from src.llm.utils import get_session_cost
from src.llm.invoke_mt import invoke_multithread
from src.chunk.models import CodeChunk, ClusterInput, ClusterInputType, SummaryChunk

from .models import (
    CodeChunk,
    ClusteredTopic,
    LMClusteredTopicList,
    LMClusteredTopic
)
from ..chunk.lmp.sum_chunks import summarize_chunk
from .chunk_repo import chunk_repo, temp_index_dir, ChunkStrat
from .utils import get_attrs_or_key

from .lmp.remove_chunks import remove_chunks
from .lmp.cluster_v1 import generate_clusters as gen_clusters_v1
from .lmp.cluster_v2 import generate_clusters as gen_structured_clusters
from .lmp.cluster_v3 import generate_clusters as gen_unstructured_clustersv1
from .lmp.cluster_v4 import generate_clusters as gen_unstructured_clustersv2, ChunkType
# from .lmp.cluster_basellm import generate_clusters

from src.config import GRAPH_ROOT

EXCLUSIONS = [
    "**/tests/**",
    "**/examples/**"
]

class LLMException(Exception):
    pass

def remove_chunks_from_cluster(clusters: List[ClusteredTopic]) -> List[ClusteredTopic]:
    modified_clusters = []
    removed_chunks = []
    for cluster, r in zip(clusters, invoke_multithread(clusters, remove_chunks)["results"]):
        print("Cluster: ", cluster)
        print("Remove: ", r.parsed.remove)

        removed_chunks.extend(r.parsed.remove)
        cluster.chunks = [chunk for chunk in cluster.chunks if chunk not in r.parsed.remove]
        modified_clusters.append(cluster)
    
    print("Total removed: ", len(removed_chunks))
    return modified_clusters

    # return [
    #     LMClusteredTopic(
    #         chunks=[chunk for chunk in cluster.chunks if chunk not in r.parsed.remove]) 
    #         for cluster, r in zip(clusters, invoke_multithread(clusters, remove_chunks)["results"])
    #     ]


# TODO: test how well LLM can select chunks using the short ID
# should prolly use this, to reduce code, if not increase token cost
# 2x more token usage ~ 5 tokens more per id
# 5 * 200 = 1000 tokens extra using this id ...
def _generate_llm_clusters(cluster_inputs: List[ClusterInput], tries: int = 4) -> List[ClusteredTopic]:
    new_clusters = []

    # need sensible name because its easier for LLm to track
    unsorted_names = [f"Chunk {i}" for i, _ in enumerate(cluster_inputs)]
    name_to_chunk = {f"Chunk {i}": chunk for i, chunk in enumerate(cluster_inputs)}

    for i in range(1, tries + 1):
        if len(unsorted_names) == 0:
            break
        
        output = gen_clusters_v1(cluster_inputs, unsorted_names)
        # TODO: add structured parsing support to ell
        parsed = get_attrs_or_key(output, "parsed")
        g_clusters = LMClusteredTopicList.parse_obj(parsed).topics # generated clusters
        if not isinstance(g_clusters, list):
            raise LLMException(f"Failed to generate list: {g_clusters}")
        
        # calculate the clustered range
        # NOTE: chunk_name != chunk.id, former is for LLM, later is for us
        matched_indices = [i for cluster in g_clusters for i, chunk in enumerate(unsorted_names) 
                           if chunk in cluster.chunks]

        # remove chunks that have already been clustered
        cluster_inputs = [chunk for i, chunk in enumerate(cluster_inputs) 
                          if i not in matched_indices]
        unsorted_names = [chunk_name for i, chunk_name in enumerate(unsorted_names)
                          if i not in matched_indices]

        # convert LMClusteredTopic to ClusteredTopic
        for g_cluster in g_clusters:
            chunks = []
            try:
                for g_chunk_name in g_cluster.chunks:
                    chunks.append(name_to_chunk[g_chunk_name])
            except KeyError as e:
                print(f"Chunk Name: {g_chunk_name} hallucinated, skipping...")
                continue
            
            new_cluster = ClusteredTopic(
                name=g_cluster.name, 
                # yep, gotta convert pydantic to dict before it accepts it
                # as a valid input ...
                chunks=[
                    # TODO: need to do this or else pydantic shits bed
                    # for empty {} validation for metadata field
                    {k:v for k,v in chunk.dict().items()
                        if k != "metadata"} for chunk in chunks]
            )
            new_clusters.append(new_cluster)            
        
        print(f"Unclassified chunks, iter:[{i}]: ", len(unsorted_names))

    return new_clusters

def _generate_llm_clusters_v2(cluster_inputs: List[ClusterInput], tries: int = 4, structured: bool = False) -> List[ClusteredTopic]:
    """
    Multi-step clustering, first indentify centroids, then generate cluster
    
    """
    
    new_clusters = []

    for i in range(1, tries + 1):
        if len(cluster_inputs) == 0:
            break
    
        g_clusters: LMClusteredTopicList = gen_unstructured_clustersv1(cluster_inputs).parsed if structured \
            else gen_structured_clusters(cluster_inputs).parsed 
        
        # with open(f"unstructured_output{i}.json", "w") as f:
        #     f.write(str(output))

        print(f"Writing to structured_output{i}.json")
        with open(f"structured_output{i}.json", "w") as f:
            for _, cluster in enumerate(g_clusters.topics):
                chunks = []
                for chunk in cluster.chunks:
                    try:
                        matching_chunk = next(filter(lambda c: c.get_name() == chunk, cluster_inputs))
                        chunks.append(matching_chunk)
                        cluster_inputs.remove(matching_chunk)
                    except StopIteration as e:
                        print(f"Chunk Name: {chunk} hallucinated, skipping...")
                        continue

                print("New Cluster: ", cluster)
                f.write(str(cluster) + "\n")
                new_clusters.append(
                    ClusteredTopic(
                        name=cluster.name, 
                        chunks=[
                            {k:v for k,v in chunk.dict().items()
                                if k != "metadata"} for chunk in chunks]
                    )
                )

        print(f"Unclassified chunks, iter:[{i}]: ", len(cluster_inputs))
        return

    cost = get_session_cost()
    print(f"Clustering cost\n: {cost}")

    return new_clusters

def _generate_llm_clusters_v3(cluster_inputs: List[ClusterInput], 
                              tries: int = 4) -> List[ClusteredTopic]:
    """
    Added support for identifying data structs and logic type chunks
    """
    new_clusters = []
    all_chunks = [chunk for chunk in cluster_inputs]
    name_to_cluster = {chunk.get_name():i for i, chunk in enumerate(all_chunks)}
    
    for i in range(1, tries + 1):
        if len(cluster_inputs) < 0.3 * len(all_chunks):
            break
        
        g_clusters = []
        for t in ChunkType:
            cluster: LMClusteredTopicList = gen_unstructured_clustersv2(cluster_inputs, 
                                                                      chunk_type = t.value).parsed
            g_clusters.extend(cluster.topics)
            print(f"Generated clusters for type {t}:", [c.name for c in cluster.topics])

        uniq_clustered_chunks = set()
        total_clustered_chunks = 0
        with open(f"structured_output{i}.json", "w") as f:
            for _, cluster in enumerate(g_clusters):
                chunks = []
                for c in cluster.chunks:
                    c_index = name_to_cluster.get(c, None)
                    if not c_index:
                        print(f"Chunk Name: {c} hallucinated, skipping...")
                        continue
                    
                    matched_chunk = all_chunks[c_index]
                    chunks.append(matched_chunk)
                    
                    # continuously remove chunks that have been clustered
                    try:
                        cluster_inputs.remove(matched_chunk)
                    except ValueError:
                        pass

                    # for tracking
                    uniq_clustered_chunks.add(matched_chunk)
                    total_clustered_chunks += 1

                f.write(str(cluster) + "\n")
                new_clusters.append(
                    ClusteredTopic(
                        name=cluster.name, 
                        chunks=[
                            {k:v for k,v in chunk.dict().items()
                                if k != "metadata"} for chunk in chunks]
                    )
                )
    
        print(f"Unclassified chunks, iter:{i}: {len(cluster_inputs)} / {len(all_chunks)}")
        print(f"Unique chunks: {len(uniq_clustered_chunks)}")
        print(f"Total clustered chunks: {total_clustered_chunks}")

    cost = get_session_cost()
    print(cost)
    return new_clusters

def _generate_llm_clusters_v4(cluster_inputs: List[ClusterInput], 
                              tries: int = 4) -> List[ClusteredTopic]:
    """
    Added support for identifying data structs and logic type chunks
    """
    generated_clusters = []
    all_chunks = [chunk for chunk in cluster_inputs]
    name_to_cluster = {chunk.get_name():i for i, chunk in enumerate(all_chunks)}
    
    for i in range(1, tries + 1):
        if len(cluster_inputs) < 0.3 * len(all_chunks):
            break
        
        g_clusters = []
        for t in ChunkType:
            clusters: LMClusteredTopicList = gen_unstructured_clustersv2(cluster_inputs, 
                                                                      chunk_type = t.value).parsed
            g_clusters.extend(clusters.topics)
            # print(f"Generated clusters for type {t}:", [c.name for c in clusters.topics])

        uniq_clustered_chunks = set()
        total_clustered_chunks = 0
        new_clusters = []
        for _, cluster in enumerate(g_clusters):
            chunks = []
            for c in cluster.chunks:
                c_index = name_to_cluster.get(c, None)
                if not c_index:
                    print(f"Chunk Name: {c} hallucinated, skipping...")
                    continue
                
                matched_chunk = all_chunks[c_index]
                chunks.append(matched_chunk)
                
                # continuously remove chunks that have been clustered
                try:
                    cluster_inputs.remove(matched_chunk)
                except ValueError:
                    pass

                # for tracking
                uniq_clustered_chunks.add(matched_chunk)
                total_clustered_chunks += 1

            new_clusters.append(
                ClusteredTopic(
                    name=cluster.name, 
                    chunks=[
                        {k:v for k,v in chunk.dict().items()
                            if k != "metadata"} for chunk in chunks]
                )
            )
    
        # TODO: remove chunks suck
        # print("HELLLO?? : ", new_clusters)
        # remove unnesscary chunks
        # modified_clusters = remove_chunks_from_cluster(new_clusters)
        # generated_clusters.extend(modified_clusters)
        generated_clusters.extend(new_clusters)

        print(f"Unclassified chunks, iter:{i}: {len(cluster_inputs)} / {len(all_chunks)}")
        print(f"Unique chunks: {len(uniq_clustered_chunks)}")
        print(f"Total clustered chunks: {total_clustered_chunks}")

    # TODO: currently broken because of session
    # cost = get_session_cost()
    # print(cost)
    return generated_clusters

def generate_full_code_clusters(repo_path: Path, 
                                chunk_strat: ChunkStrat = ChunkStrat.VANILLA,
                                summarize: bool = False) -> List[ClusteredTopic]:
    print("Generating full code clusters...")
    chunks = chunk_repo(repo_path, chunk_strat, mode="full", exclusions=EXCLUSIONS)
    return _generate_llm_clusters(chunks, tries=3)


def generate_full_code_clustersv2(repo_path: Path, 
                                chunk_strat: ChunkStrat = ChunkStrat.VANILLA,
                                summarize: bool = False) -> List[ClusteredTopic]:
    print("Generating full code clusters...")
    chunks = chunk_repo(repo_path, chunk_strat, mode="full", exclusions=EXCLUSIONS)
    if summarize:
        results = invoke_multithread(chunks, summarize_chunk)
        summed = results["results"]
        # TODO: handle context too long
        errors = results["errors"]
        summary_chunks  = [SummaryChunk.from_chunk(chunk, summed.parsed) for chunk, summed in 
                       zip(chunks, summed)]
        
        summary_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in summary_chunks]))
        code_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in chunks]))

        print(f"Summary tokens: {summary_tokens}, \
            Code tokens: {code_tokens}, \
            Ratio: {summary_tokens / code_tokens}")
        
        chunks = summary_chunks

    return _generate_llm_clusters_v4(chunks, tries=1)


def generate_summarized_clusters(repo_path: Path,
                                chunk_strat: ChunkStrat = ChunkStrat.VANILLA) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, chunk_strat, mode="full", exclusions=EXCLUSIONS)

    summary_chunks = []
    for chunk in chunks:
        try:
            summary = summarize_chunk(chunk).parsed
        except LengthFinishReasonError as e:
            print(f"[Summarize Chunk] Chunk too long: {len(chunk.content)}, continuing...")
            continue

        summary_chunk = SummaryChunk.from_chunk(chunk, summary)
        summary_chunks.append(summary_chunk)

    summary_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in summary_chunks]))
    code_tokens = num_tokens_from_string("".join([chunk.get_content() for chunk in chunks]))

    print(f"Summary tokens: {summary_tokens}, \
          Code tokens: {code_tokens}, \
          Ratio: {summary_tokens / code_tokens}")

    return _generate_llm_clusters(summary_chunks)

# NOTE: generated clusters are not named
def generate_graph_clusters(repo_path: Path) -> List[ClusteredTopic]:
    chunks = chunk_repo(repo_path, ChunkStrat.VANILLA, mode="full", exclusions=EXCLUSIONS)
    cg = AiderGraph.from_chunks(repo_path, chunks)

    cluster_cg(cg)

    return [
        ClusteredTopic(
            name="Graph Cluster",
            chunks=[
                CodeChunk(
                    id=chunk.og_id,
                    content=chunk.content,
                    filepath=chunk.file_path,
                    input_type=ClusterInputType.CHUNK,
                ).dict() for chunk in cluster.chunks
            ],
        ) 
        for cluster in cg.get_clusters()
    ]


def generate_random_clusters(repo_path: Path, size: int = 5, num_clusters: int = 4) -> List[ClusteredTopic]:
    rng = random.Random(42)
    chunks = chunk_repo(repo_path, ChunkStrat.VANILLA, mode="full", exclusions=EXCLUSIONS)

    return [
        ClusteredTopic(
            name=f"Random {i}",
            chunks=[
                chunk.dict() for chunk in rng.sample(chunks, size)
            ],
        )
        for i in range(num_clusters)
    ]