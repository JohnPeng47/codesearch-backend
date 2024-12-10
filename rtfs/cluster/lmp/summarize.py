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

def summarizev3(model: LLMModel, cluster: Cluster) -> ClusterSummary:
    SUMMARY_PROMPT = """
The following chunks of code are grouped into the same feature.
I want you to respond with a structured output using the following steps: 
- first come up with a descriptive title that best captures the role that these chunks of code
play in the overall codebase. 
- next, write a extremely detailed summary of the code chunks, paying special attention to include:
--> reference specific source code symbols much as you can
--> make inferences to how its used in the wider codebase
--> include a list of bullet points that describe how the included chunks might interact together to accomplish the overall goal of this cluster

Here is an example of the length and style that I want you to replicate:

The code implements a state machine for automated code manipulation through "Agentic States." The system consists of an abstract AgenticState base class and specialized state classes for editing, searching, and analyzing code. A Transitions class manages state changes, while an AgenticLoop orchestrates execution. States handle specific tasks like code editing, searching, and relevance assessment, with transitions triggered by actions and conditions. The system maintains context through trajectory tracking and comprehensive logging, enabling automated workflows for code modification and analysis.
The key components are:

State management through AgenticState and specialized state classes
Transition handling via Transitions and AgenticLoop
Code manipulation capabilities (editing, searching, planning)
Context tracking and logging for workflow management

Here is the code, now generate a summary using instructions and the example above:
{code}
    """.format(code=cluster.to_str(return_content=True))
    return model.invoke(SUMMARY_PROMPT, 
                        model_name="gpt-4o", 
                        response_format=ClusterSummary)
