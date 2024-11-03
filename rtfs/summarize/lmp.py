from typing import List
from pydantic import BaseModel

from llm import LLMModel

class CodeSummary(BaseModel):
    title: str
    summary: str
    key_variables: str


def summarize(model: LLMModel, child_content) -> CodeSummary:
    SUMMARY_PROMPT = """
The following chunks of code are grouped into the same feature.
I want you to respond with a structured output using the following steps: 
- first come up with a descriptive title that best captures the role that these chunks of code
play in the overall codebase. 
- next, write a short concise but descriptive summary of the chunks, thats 1-2 sentences long
- finally, take a list 4 of important functions/classes as key_variables (without any explanations!)

Here is the code:
{code}
""".format(code=child_content)

    try:
        response = model.invoke(SUMMARY_PROMPT, response_format=CodeSummary)
        return response
    except Exception as e:
        raise e


class CodeClusters(BaseModel):
    category: str
    children: List[str]


class ClusterList(BaseModel):
    clusters: List[CodeClusters]

    def __str__(self):
        return "\n".join(
            [f"Cluster: {cluster.category}, Cluster Children: {', '.join(cluster.children)}"
                for cluster in self.clusters]
        )


def categorize_clusters(model: LLMModel, clusters) -> ClusterList:
    REORGANIZE_CLUSTERS = """
You are given a following a set of ungrouped clusters that encapsulate different features in the codebase. Take these clusters
and group them into logical categories, then come up with a name for each category.

Here are some more precise instructions:
1. Carefully read through the entire list of features and functionalities.
2. The categories must be mutually exclusive and collectively exhaustive.
3. Place each feature or functionality under the most appropriate category
4. Each category should not have less than 2 children clusters
5. Make sure you generated name is different from any of the existing Cluster names

Your generated output should only contain the title of your created categories and their list of children titles, without
including any other information such as the children's summary

Return your output in a structured way.
Here are the ungrouped clusters:
{clusters}
    """.format(clusters=clusters)

    try:        
        response = model.invoke(REORGANIZE_CLUSTERS, response_format=ClusterList)
        return response
    except Exception as e:
        raise e


def categorize_missing(model: LLMModel, clusters, categories) -> ClusterList:
    categories = f"\n".join([f"{i}. {category}" for i, category in enumerate(categories, 1)])

    REORGANIZE_CLUSTERS = """
You are given a following a set of categories and a set of existing code functionalities. Assign each code functionality to an existing category
if it makes sense. Otherwise create a new category for the code functionality. 

Your generated output should only contain the title of categories along with the list of their children titles, added from the list
of code functionalities provided. Do not include any other information such as the children's summary

Here are the set of categories.
{categories}

Here are the set of code functionalities:
{clusters}

Remember, if:
1. None of the code categories fit
2. If creating a new category fits the code functionalities better, then create a new cateogry and add it to the list
    """.format(categories=categories, clusters=clusters)

    try:
        response = model.invoke(REORGANIZE_CLUSTERS, response_format=ClusterList)
        return response
    except Exception as e:
        raise e
