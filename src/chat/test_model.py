from llm import LLMModel

model = LLMModel(provider="openai")
model.invoke("hello?", model_name="gpt-4o-mini")