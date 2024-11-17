from llm import LLMModel

def func():
    model = LLMModel(provider="openai")
    print(model.invoke("hello?", model_name="gpt-4o-mini"))