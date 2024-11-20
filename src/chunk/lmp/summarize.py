from typing import List
from pydantic import BaseModel
from llm import LLMModel

from src.models import CodeSummary

def summarize_chunk(model: LLMModel, code: str, context: str = "") -> str:
    SUMMARY_PROMPT_1 = """
Generate a summary of this source code. 
First generate a description of the source code, and its intended purpose. This should cover its most salient features. Features that are novel shud be explained but generic features can be noted without too much detail. Avoid the use of conditionals in describing the logic if you can. Can resort to internet english for the sake of brevity
Next, generate a concise description of the code
Follow this by, if there is some uncertainty about the code given the context provided, raise this as a list of questions. These questions should be unambiguous as possible, and can be resolved by looking at somewhere in the codebase. Generate only 2-3

Write your summaries using sentence fragments and omit a passive subject
"""
    CONTEXT = """
Here are some additional context to guide your response:
{context}
""".format(context=context) if context else ""
    
    SUMMARY_PROMPT_2 = """
Here is the code:
{code}

Provide your response in a structured format.
""".format(code=code)
        
    SUMMARY_PROMPT = SUMMARY_PROMPT_1 + CONTEXT + SUMMARY_PROMPT_2
    return model.invoke(SUMMARY_PROMPT, model_name="gpt-4o-mini")

def convert(model: LLMModel, summary_raw: str) -> CodeSummary:
    SUMMARY_PROMPT = """
Convert the following summary into the 3 sections:
- a long description
- a short description
- a list of questions

Here is the summary:
{summary_raw}
"""
    return model.invoke(
        SUMMARY_PROMPT.format(summary_raw=summary_raw), 
        model_name="gpt-4o-mini",
        response_format=CodeSummary
    )

def summarize_lmp(model: LLMModel, code) -> CodeSummary:
    print("generating summary")
    raw_summary = summarize_chunk(model, code)    
    return convert(model, raw_summary)

def func():
    model = LLMModel(provider="openai")
    print(model.invoke("hello?", model_name="gpt-4o-mini"))