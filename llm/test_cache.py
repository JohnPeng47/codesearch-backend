from llm import LLMModel

def func():
    model = LLMModel(provider="openai")
    return model.invoke("hello world!")