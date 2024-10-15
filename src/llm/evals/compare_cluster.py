import ell
from pydantic import BaseModel, field_validator
from typing import List, Tuple

from ...cluster.types import ClusteredTopic

class BinaryChoice(BaseModel):
    choice: str

    @field_validator('choice')
    def validate_choice(cls, v):
        if v not in ["A", "B"]:
            raise ValueError("Choice must be 'A' or 'B'")
        return v

# TODO: Make this generic for number of compares
# TODO: Use dspy to auto-tune a list of topics
@ell.complex(model="gpt-4o-2024-08-06", response_format=BinaryChoice)
def compare_cluster(cluster_a: ClusteredTopic, cluster_b: ClusteredTopic) -> BinaryChoice:
    print(cluster_a)
    code_str = "\n".join([str(chunk) for chunk in set(cluster_a) | set(cluster_b)])

    print("Codestr: \n", code_str)
#     EVAL_PROMPT = """
# You are a software engineer.
# You are given a piece of source code and two sets clusters of the source, A and B.
# Your task is to evaluate which cluster best encapsulates a functional component of the source
# All the chunks in the cluster should make sense together, and be internally cohesive without overreaching

# Here is the source code:
# {code_chunks}

# Cluster Set A:
# {cluster_a}

# Cluster Set B:
# {cluster_b}

# Based on your analysis, output only one of the following responses:
# "A" if Cluster Set A is preferable
# "B" if Cluster Set B is preferable

# Do not provide any additional explanation or text in your response.
# """
#     return EVAL_PROMPT.format(code_chunks=code_str, cluster_a=cluster_a, cluster_b=cluster_b)
    return ""


def compare_eval(cluster_a: List[ClusteredTopic], 
                 cluster_b: List[ClusteredTopic],
                 a_label: str,
                 b_label: str) -> List[int]:
    """
    Loops through all clusters to find the best match for each cluster in the other set.
    """
    min_match = 0
    matched_clusters = []
    for a in cluster_a:
        best_match = None
        best_score = -1
        for b in cluster_b:
            score = len(set(a.chunks) & set(b.chunks))
            if score > best_score:
                best_score = score
                best_match = b
        if best_score >= min_match:
            matched_clusters.append((a, best_match))

    results = []
    for a, b in matched_clusters:
        print(f"Comparing {a.name} and {b.name}")
        result = compare_cluster(a, b).parsed
        results.append(result.choice)
    
    total_a = results.count("A")
    total_b = results.count("B")

    print(f"Total A: {total_a}, Total B: {total_b}, Total Matches: {len(matched_clusters)}")
    return total_a, total_b