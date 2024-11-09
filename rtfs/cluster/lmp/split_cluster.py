from llm import LLMModel, LMClusteredTopicList
from rtfs.cluster.graph import Cluster

def split_cluster(model: LLMModel, cluster: Cluster) -> LMClusteredTopicList:
    cluster_str = cluster.to_str(return_content=True)

    COMPARE_PAIRWISE = """
Here is a large cluster generated from a clustering algorithm. It is too big. I want you to break it up into smaller clusters.
Each cluster should represent a cohesive set of code chunks that work together to implement a common feature.
Your output should be a list of new clusters with titles and the names of the chunks that belong to each cluster.

Here is the cluster:
{cluster}
"""
    return model.invoke(
        COMPARE_PAIRWISE.format(cluster=cluster_str), 
        model_name="gpt-4o",
        response_format=LMClusteredTopicList
    )

