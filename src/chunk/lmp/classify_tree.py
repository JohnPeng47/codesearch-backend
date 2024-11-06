from typing import List, Tuple
import ell
from ..models import ClassifiedFilesList, FILE_CLASSIFICATIONS_DICT

@ell.complex(model="gpt-4o-2024-08-06", response_format=ClassifiedFilesList)
def classify_tree(file_tree: str) -> ClassifiedFilesList:
    categories = "".join([f"{category} : {description}\n" 
                          for category, description in FILE_CLASSIFICATIONS_DICT.items()])

    CLASSIFY_TREE = """
Given the directory tree, classify each filepath into the following categories:
{categories} 

Here is the directory tree:
{tree}
"""
    return CLASSIFY_TREE.format(tree=file_tree, categories=categories)
