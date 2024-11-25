from pydantic import BaseModel, Field
from typing import List, Optional

from src.models import CHUNK_ID

class Answer(BaseModel):
    answer: str

class Question(BaseModel):
    question: str
    files: List[str] = Field(default_factory=list)
    answer: Optional[Answer] = None
    chunk_ids: Optional[List[CHUNK_ID]] = Field(default_factory=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.files:
            self.files = list(set([chunk_id.split("::")[0] for chunk_id in self.chunk_ids]))
            print("Initializing with files: ", self.files)

class QuestionSetFileOnly(BaseModel):
    question_set: List[str]
    files: List[str] = Field(default_factory=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.files:
            self.files = list(set([chunk_id.split("::")[0] for chunk_id in self.chunk_ids]))
            print("Initializing with files: ", self.files)

    def ans(self, files: List[str]) -> float:
        return len(set(files).intersection(self.files)) / len(self.files)