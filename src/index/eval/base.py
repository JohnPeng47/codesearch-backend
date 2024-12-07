from pydantic import BaseModel, Field
from typing import List, Optional
from dataclasses import dataclass
import functools

from src.models import CHUNK_ID, MetadataType
from ..stores import VectorStore
from ..core import IndexStrat

class QuestionFileOnly(BaseModel):
    question: str
    files: List[str]

    def ans(self, files: List[str]) -> float:
        return len(set(files).intersection(self.files)) / len(self.files)

class EvalFileOnly:
    def __init__(self, vec_store: VectorStore):
        # if vec_store.name() != IndexStrat.CLUSTER:
        #     raise ValueError(f"Invalid vector store type {vec_store.name()}")
        self._vec_store = vec_store

    def evaluate(self, question_set: List[QuestionFileOnly]) -> float:
        total_score = 0.0

        for question in question_set:
            print("Evaluating question: ", question.question)
            results = self._vec_store.query(question.question)
            files = list(set(functools.reduce(lambda a,b: a + b, [r.files for r in results])))
            score = question.ans(files)
            total_score += score
            
        return total_score / len(question_set)
