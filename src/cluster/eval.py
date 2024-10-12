import ell
from pydantic import BaseModel
from typing import List, Tuple

from .types import ClusteredTopic


class BinaryChoice(BaseModel):
    choice: str

# TODO: Make this generic for number of compares
# TODO: Use dspy to auto-tune a list of topics
@ell.complex(model="gpt-4o-2024-08-06", response_format=BinaryChoice)
def compare_cluster(cluster_a: List[ClusteredTopic], 
                 cluster_b: List[ClusteredTopic]) -> BinaryChoice:
    EVAL_PROMPT = """
You are given two sets of code clusters, A and B. Your task is to evaluate these clusters based on the principles of Single Responsibility Principle 
(SRP) and overall code organization, and determine which one is preferable. Consider the following criteria:

1. Cohesion: How well do the elements within each cluster relate to each other and serve a single purpose?
2. Separation of Concerns: How effectively does each clustering separate different functionalities or responsibilities?
3. Modularity: How well do the clusters promote modular design, allowing for easier maintenance and scalability?
4. Clarity: How clear and intuitive is the organization of code in each clustering?
5. Adherence to SRP: How well does each clustering adhere to the Single Responsibility Principle?

Cluster Set A:
{cluster_a}

Cluster Set B:
{cluster_b}

Based on your analysis, output only one of the following responses:
"A" if Cluster Set A is preferable
"B" if Cluster Set B is preferable

Do not provide any additional explanation or text in your response.
"""
    return EVAL_PROMPT.format(cluster_a=cluster_a, cluster_b=cluster_b)


def compare_eval(cluster_a: List[ClusteredTopic], 
                 cluster_b: List[ClusteredTopic]) -> List[int]:
    """
    Loops through all clusters to find the best match for each cluster in the other set.
    """
    min_match = 0

    matches = []
    for a in cluster_a:
        best_match = None
        best_score = -1
        for b in cluster_b:
            score = len(set(a.chunks) & set(b.chunks))
            if score > best_score:
                best_score = score
                best_match = b
        if best_score >= min_match:
            matches.append((a, best_match))

    return matches