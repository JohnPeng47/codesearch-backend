from pydantic import BaseModel
from ell.api import get_invocations_by_session_id
from typing import Tuple, List, Dict
from enum import Enum

OPENAI_MODELS = {
    "gpt-4o": {
        "max_context": 128_000,
        "prompt_token_cost": 2.5e-06,
        "cached_token_cost": 1.25e-06,
        "completion_token_cost": 1e-5,
    },
    "gpt-4o-2024-08-06" : {
        "max_context": 128_000,
        "prompt_token_cost": 2.5e-06,
        "cached_token_cost": 1.25e-06,
        "completion_token_cost": 1e-5,
    },
    "gpt-4o-mini": {
        "max_context": 128_000, # cap??? swear its 8192
        "prompt_token_cost": 1.5e-07,
        "cached_token_cost": 7.5e-08,
        "completion_token_cost": 6e-07,
    },
    "gpt-4o-mini-2024-07-18": {
        "max_context": 128_000, # cap??? swear its 8192
        "prompt_token_cost": 1.5e-07,
        "cached_token_cost": 7.5e-08,
        "completion_token_cost": 6e-07,
    }
}

class TokenType(str, Enum):
    PROMPT = "prompt"
    CACHED = "cached"
    COMPLETION = "completion"

class TokenUsage(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int

    @property
    def prt_token_cost(self) -> float:
        return OPENAI_MODELS[self.model]["prompt_token_cost"]
    
    @property
    def cch_token_cost(self) -> float:
        return OPENAI_MODELS[self.model]["cached_token_cost"]
    
    @property
    def cpt_token_cost(self) -> float:
        return OPENAI_MODELS[self.model]["completion_token_cost"]

    # THIS IS WRONGNNNGGG
    def total_cost(self) -> int:
        return (self.prompt_tokens - self.cached_tokens) * self.prt_token_cost \
                + self.cached_tokens * self.cch_token_cost \
                + self.completion_tokens * self.cpt_token_cost

    def cached_savings(self) -> float:
        savings = self.cached_tokens * self.prt_token_cost - self.cached_tokens * self.cch_token_cost
        return savings

class LLMMetrics(BaseModel):
    token_costs: List[TokenUsage]
    exec_time: float
    
    def total_cost(self) -> float:
        return sum([cost.total_cost() for cost in self.token_costs])
    
    def cached_savings(self) -> float:
        return sum([cost.cached_savings() for cost in self.token_costs]) / self.total_cost() * 100
    
    def __str__(self) -> str:
        return (
            f"Total Cost: {self.total_cost()}\n"
            f"Cached Savings: {self.cached_savings()} %\n"
            f"Execution Time: {self.exec_time / 1000} s"
        )

def get_session_cost() -> LLMMetrics:
    invocations = get_invocations_by_session_id()
    token_usages: List[TokenUsage] = []
    ex_time = 0

    for invocation in invocations:
        ex_time += invocation.latency_ms
        token_usage = TokenUsage(
            model=invocation.model,
            prompt_tokens=invocation.prompt_tokens,
            completion_tokens=invocation.completion_tokens,
            cached_tokens=invocation.cached_tokens
        )
        token_usages.append(token_usage)

    return LLMMetrics(token_costs=token_usages, exec_time=ex_time)
