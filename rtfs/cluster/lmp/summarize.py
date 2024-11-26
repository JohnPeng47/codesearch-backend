from llm import LLMModel

from ..graph import Cluster, ClusterSummary

def summarize(model: LLMModel, cluster: Cluster) -> ClusterSummary:
    SUMMARY_PROMPT = """
The following chunks of code are grouped into the same feature.
I want you to respond with a structured output using the following steps: 
- first come up with a descriptive title that best captures the role that these chunks of code
play in the overall codebase. 
- next, write a short concise but descriptive summary of the chunks, thats 1-2 sentences long

Here is the code:
{code}
""".format(code=cluster.to_str(return_content=True))
    return model.invoke(SUMMARY_PROMPT, 
                        model_name="gpt-4o", 
                        response_format=ClusterSummary)

def summarizev2(model: LLMModel, cluster: Cluster) -> ClusterSummary:
    SUMMARY_PROMPT = """
The following chunks of code are grouped into the same feature.
I want you to respond with a structured output using the following steps: 
- first come up with a descriptive title that best captures the role that these chunks of code
play in the overall codebase. 
- next, write a extremely detailed summary of the code chunks, paying special attention to include:
--> reference specific source code symbols much as you can
--> make inferences to how its used in the wider codebase
--> include a list of bullet points that describe how the included chunks might interact together to accomplish the overall goal of this cluster

Here is the code:
{code}
""".format(code=cluster.to_str(return_content=True))
    return model.invoke(SUMMARY_PROMPT, 
                        model_name="gpt-4o", 
                        response_format=ClusterSummary)

    