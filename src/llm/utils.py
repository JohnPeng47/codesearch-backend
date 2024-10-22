from ell.api import get_invocations_by_session_id
from typing import Tuple

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
        "cost_per_output_token": 6e-07,
    },
    "gpt-4o-mini-2024-07-18": {
        "max_context": 128_000, # cap??? swear its 8192
        "prompt_token_cost": 1.5e-07,
        "cached_token_cost": 7.5e-08,
        "cost_per_output_token": 6e-07,
    }
}

def get_session_cost(model_name: str) -> Tuple[float, float]:
    prompt_tokens, completion_tokens, cached_tokens = 0, 0, 0
    invocations = get_invocations_by_session_id()
    for invocation in invocations:
        prompt_tokens += invocation.prompt_tokens
        completion_tokens += invocation.completion_tokens
        cached_tokens += invocation.cached_tokens
    
    input_cost = (prompt_tokens - cached_tokens) * OPENAI_MODELS[model_name]["prompt_token_cost"] \
                + cached_tokens * OPENAI_MODELS[model_name]["cached_token_cost"]
    output_cost = completion_tokens * OPENAI_MODELS[model_name]["completion_token_cost"]
    return input_cost, output_cost
