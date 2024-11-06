from pydantic import BaseModel
import ell

from src.llm.lmp_base import LogProbLMP
from src.cluster.models import ClusteredTopic

class OneToSixteenScale(BaseModel):
    rating: float

@ell.complex(model="gpt-4o-2024-08-06", return_metadata=True)
def eval_coherence_single_lmp(cluster: ClusteredTopic):
    DELIMITER = "\n\n================="
    cluster_code = "\n".join([chunk.get_content() + DELIMITER for chunk in cluster.chunks])

    EVAL_COHERENCE = """
You are given a cluster that is the output of a clustering algorithm designed to group together code from related features. Your task is to evaluate how well the code in this cluster works together as a cohesive functional unit in the wider codebase. Output your score on a scale of 1 to 16, where:
1-3 indicates the cluster contains entirely unrelated code snippets with no functional relationship whatsoever. The grouping appears random and the code pieces actively conflict in their purposes or dependencies.
4-7 indicates the cluster has only superficial relationships (like sharing common utility functions). Most code snippets would work better in different clusters, and the code lacks any meaningful architectural or functional cohesion.
8-10 indicates the cluster contains moderately related code with a somewhat discernible shared purpose, but with significant irrelevant or misplaced elements. While there's a recognizable theme, 40-60% of the code belongs elsewhere.
11-13 indicates the cluster has closely related code forming a mostly cohesive functional unit. At least 80% of the code clearly belongs together, with only minor inconsistencies or outliers. The code has strong functional dependencies and shared purpose.
14-16 indicates the cluster represents a perfect or near-perfect functional unit. Virtually all code (>95%) is strongly related and necessary for the feature. The cluster captures complete functionality with no missing pieces and clear, strong functional dependencies between all components. Removing any piece would break the functionality.
Here is the code in the cluster:
{code}

Evaluate the coherence and output your rating. Your output format should be in the following form:
Score: <YOU_SCORE>

For example, here are some valid outputs:
Score: 4.333
Here is another one:
Score: 5.0
Here is yet another one:
Score: 6.0

Now output your score:
"""
    return EVAL_COHERENCE.format(code=cluster_code)


def eval_coherence_single(cluster: ClusteredTopic):
    lmp_func = LogProbLMP(eval_coherence_single_lmp)
    lmp_func2 = LogProbLMP(eval_coherence_single_lmp)

    result1 = lmp_func.call(cluster, output_rgx="")
    result2 = lmp_func2.call(cluster, output_rgx=r"Score\s*:\s*(\d+\.?\d*)")

    perp1 = lmp_func.logprobs().perplexity()
    perp2 = lmp_func2.logprobs().perplexity()

    return (result1, perp1), (result2, perp2)


    
