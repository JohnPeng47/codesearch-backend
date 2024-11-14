from llm import LLMModel
from uuid import uuid4

class UserQuery:
    pass

class ChatResponse:
    """
    Main chat response class that supports:
    - normal code queries
    - walkthrough queries
    """

    def __init__(self, model: LLMModel, query: str):
        self._id = str(uuid4())
        self._model = model