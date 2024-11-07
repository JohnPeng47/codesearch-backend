from llm import LLMModel
from ..models import ClassifiedFilesList, FILE_CLASSIFICATIONS_DICT

def classify_tree(model: LLMModel, file_tree: str) -> ClassifiedFilesList:
    categories = "".join([f"{category} : {description}\n" 
                          for category, description in FILE_CLASSIFICATIONS_DICT.items()])

    prompt = f"""
Given the directory tree, classify each filepath into the following categories:
{categories} 

Here is the directory tree:
{file_tree}
"""
    return model.invoke(prompt, response_format=ClassifiedFilesList)
