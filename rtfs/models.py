import logging
import asyncio
import os
import yaml

from anthropic import Anthropic, RateLimitError
from dataclasses import dataclass, fields
from openai import BadRequestError, OpenAI, AzureOpenAI
from simple_parsing.helpers import FrozenSerializable, Serializable
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_not_exception_type,
)
import tiktoken
import yaml

# from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger("test_results")


@dataclass
class ModelArguments(Serializable):
    model_name: str
    api_key: str
    per_instance_cost_limit: float = 0.0
    total_cost_limit: float = 0.0
    temperature: float = 1.0
    top_p: float = 1.0
    replay_path: str = None
    host_url: str = "localhost:11434"


@dataclass
class APIStats(Serializable):
    total_cost: float = 0
    instance_cost: float = 0
    tokens_sent: int = 0
    tokens_received: int = 0
    api_calls: int = 0

    def __add__(self, other):
        if not isinstance(other, APIStats):
            raise TypeError("Can only add APIStats with APIStats")

        return APIStats(
            **{
                field.name: getattr(self, field.name) + getattr(other, field.name)
                for field in fields(self)
            }
        )

    def replace(self, other):
        if not isinstance(other, APIStats):
            raise TypeError("Can only replace APIStats with APIStats")

        return APIStats(
            **{field.name: getattr(other, field.name) for field in fields(self)}
        )

    def __str__(self):
        return f"total_cost={self.total_cost:.2f}, instance_cost={self.instance_cost:.2f}, tokens_sent={self.tokens_sent:_}, tokens_received={self.tokens_received:_}, api_calls={self.api_calls:_}"


class ContextWindowExceededError(Exception):
    pass


class CostLimitExceededError(Exception):
    pass


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


class BaseModel:
    MODELS = {}
    SHORTCUTS = {}

    def __init__(self, args: ModelArguments = None):
        self.args = args
        self.model_metadata = {}
        self.stats = APIStats()

        # Map `model_name` to API-compatible name `api_model`
        self.api_model = (
            self.SHORTCUTS[self.args.model_name]
            if self.args.model_name in self.SHORTCUTS
            else self.args.model_name
        )

        # Map model name to metadata (cost, context info)
        MODELS = {
            **{dest: self.MODELS[src] for dest, src in self.SHORTCUTS.items()},
            **self.MODELS,
        }
        if args.model_name in MODELS:
            self.model_metadata = MODELS[args.model_name]
        else:
            raise ValueError(
                f"Unregistered model ({args.model_name}). Add model name to MODELS metadata to {self.__class__}"
            )

    def reset_stats(self, other: APIStats = None):
        if other is None:
            self.stats = APIStats(total_cost=self.stats.total_cost)
        else:
            self.stats = other

    def input_cost(self, input_tokens: int) -> int:
        """
        Calculate the cost of the input prompt in tokens
        """
        return self.model_metadata["cost_per_input_token"] * input_tokens

    def output_cost(self, output_tokens: int) -> int:
        """
        Calculate the cost of the output response in tokens
        """
        return self.model_metadata["cost_per_output_token"] * output_tokens

    def update_stats(self, input_tokens, output_tokens):
        """
        Calculates the cost of a response from the openai API.

        Args:
        input_tokens (int): The number of tokens in the prompt.
        output_tokens (int): The number of tokens in the response.

        Returns:
        float: The cost of the response.
        """
        # Calculate cost and update cost related fields
        cost = self.input_cost(input_tokens) + self.output_cost(output_tokens)
        self.stats.total_cost += cost
        self.stats.instance_cost += cost
        self.stats.tokens_sent += input_tokens
        self.stats.tokens_received += output_tokens
        self.stats.api_calls += 1

        # Log updated cost values to std. out.
        # logger.info(
        #     f"input_tokens={input_tokens:_}, "
        #     f"output_tokens={output_tokens:_}, "
        #     f"instance_cost={self.stats.instance_cost:.2f}, "
        #     f"cost={cost:.2f}"
        # )
        # logger.info(
        #     f"total_tokens_sent={self.stats.tokens_sent:_}, "
        #     f"total_tokens_received={self.stats.tokens_received:_}, "
        #     f"total_cost={self.stats.total_cost:.2f}, "
        #     f"total_api_calls={self.stats.api_calls:_}"
        # )

        # Check whether total cost or instance cost limits have been exceeded
        # if (
        #     self.args.total_cost_limit > 0
        #     and self.stats.total_cost >= self.args.total_cost_limit
        # ):
        #     logger.warning(
        #         f"Cost {self.stats.total_cost:.2f} exceeds limit {self.args.total_cost_limit:.2f}"
        #     )
        #     raise CostLimitExceededError("Total cost limit exceeded")

        # if (
        #     self.args.per_instance_cost_limit > 0
        #     and self.stats.instance_cost >= self.args.per_instance_cost_limit
        # ):
        #     logger.warning(
        #         f"Cost {self.stats.instance_cost:.2f} exceeds limit {self.args.per_instance_cost_limit:.2f}"
        #     )
        #     raise CostLimitExceededError("Instance cost limit exceeded")
        return cost

    async def query(self, prompt: str) -> str:
        raise NotImplementedError("Use a subclass of BaseModel")


class AnthropicModel(BaseModel):
    MODELS = {
        "claude-instant": {
            "max_context": 100_000,
            "cost_per_input_token": 1.63e-06,
            "cost_per_output_token": 5.51e-06,
        },
        "claude-2.0": {
            "max_context": 100_000,
            "cost_per_input_token": 1.102e-05,
            "cost_per_output_token": 3.268e-05,
        },
        "claude-2.1": {
            "max_context": 100_000,
            "cost_per_input_token": 1.102e-05,
            "cost_per_output_token": 3.268e-05,
        },
        "claude-3-opus-20240229": {
            "max_context": 200_000,
            "max_tokens": 4096,  # Max tokens to generate for Claude 3 models
            "cost_per_input_token": 1.5e-05,
            "cost_per_output_token": 7.5e-05,
        },
        "claude-3-sonnet-20240229": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 3e-06,
            "cost_per_output_token": 1.5e-05,
        },
        "claude-3-5-sonnet-20240620": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 3e-06,
            "cost_per_output_token": 1.5e-05,
        },
        "claude-3-haiku-20240307": {
            "max_context": 200_000,
            "max_tokens": 4096,
            "cost_per_input_token": 2.5e-07,
            "cost_per_output_token": 1.25e-06,
        },
    }

    SHORTCUTS = {
        "claude-2": "claude-2.1",
        "claude-opus": "claude-3-opus-20240229",
        "claude-sonnet": "claude-3-sonnet-20240229",
        "claude-haiku": "claude-3-haiku-20240307",
        "claude-sonnet-3.5": "claude-3-5-sonnet-20240620",
    }

    def __init__(self, args: ModelArguments = None):
        if not args:
            # Set Anthropic key
            args = ModelArguments(
                model_name="claude-sonnet-3.5", api_key=os.getenv("ANTHROPIC_API_KEY")
            )

        super().__init__(args)

        self.api = Anthropic(api_key=self.args.api_key)

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(15),
        retry=retry_if_not_exception_type((RateLimitError,)),
    )
    def query(self, prompt: str) -> str:
        """
        Query the Anthropic API with the given `history` and return the response.
        """
        return anthropic_query(self, prompt)

    def query_sync(self, prompt: str) -> str:
        return self.query(prompt)


def anthropic_query(model: AnthropicModel, message) -> str:
    """
    Query the Anthropic API with the given `history` and return the response.
    """

    message = {"role": "user", "content": message}

    # Perform Anthropic API call
    response = model.api.messages.create(
        messages=[message],
        max_tokens=model.model_metadata["max_tokens"],
        model=model.api_model,
        temperature=model.args.temperature,
        top_p=model.args.top_p,
    )

    # Calculate + update costs, return response
    model.update_stats(response.usage.input_tokens, response.usage.output_tokens)
    return "\n".join([x.text for x in response.content])


class OpenAIModel(BaseModel):
    MODELS = {
        "gpt-3.5-turbo-0125": {
            "max_context": 16_385,
            "cost_per_input_token": 5e-07,
            "cost_per_output_token": 1.5e-06,
        },
        "gpt-3.5-turbo-1106": {
            "max_context": 16_385,
            "cost_per_input_token": 1.5e-06,
            "cost_per_output_token": 2e-06,
        },
        "gpt-3.5-turbo-16k-0613": {
            "max_context": 16_385,
            "cost_per_input_token": 1.5e-06,
            "cost_per_output_token": 2e-06,
        },
        "gpt-4-32k-0613": {
            "max_context": 32_768,
            "cost_per_input_token": 6e-05,
            "cost_per_output_token": 0.00012,
        },
        "gpt-4-0613": {
            "max_context": 8_192,
            "cost_per_input_token": 3e-05,
            "cost_per_output_token": 6e-05,
        },
        "gpt-4-1106-preview": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
        "gpt-4-0125-preview": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
        # TODO: double check
        "gpt-4o": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-06,
            "cost_per_output_token": 2e-06,
        },
        # TODO: correct this
        "deepseek-chat": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
    }

    SHORTCUTS = {
        "gpt3": "gpt-3.5-turbo-1106",
        "gpt3-legacy": "gpt-3.5-turbo-16k-0613",
        "gpt4": "gpt-4-1106-preview",
        "gpt-4o": "gpt-4o",
        "gpt4-legacy": "gpt-4-0613",
        "gpt4-0125": "gpt-4-0125-preview",
        "gpt3-0125": "gpt-3.5-turbo-0125",
        # deepseek, same API
        "deepseek-chat": "deepseek-chat",
    }

    def __init__(self, args: ModelArguments = None):
        if not args:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("env OPENAI_API_KEY not set")

            args = ModelArguments(
                model_name="gpt-4o",
                api_key=os.getenv("OPENAI_API_KEY"),
            )

        super().__init__(args)

        self.async_client = AsyncOpenAI(api_key=args.api_key)
        self.client = OpenAI(api_key=args.api_key)

        # deepseek specific settings
        if args.model_name == "deepseek-chat":
            print(args.api_key)
            print("Setting deepseek specific settings .....")
            self.client.base_url = "https://api.deepseek.com"
            # https://platform.deepseek.com/api-docs/#the-temperature-parameter
            self.args.temperature = 0.0

    def history_to_messages(
        self, history: list[dict[str, str]], is_demonstration: bool = False
    ) -> list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
            return "\n".join([entry["content"] for entry in history])
        # Return history components with just role, content fields
        return [
            {k: v for k, v in entry.items() if k in ["role", "content"]}
            for entry in history
        ]

    def calc_input_cost(self, prompt: str) -> int:
        """
        Calculate the cost of the input prompt in tokens
        """
        num_tokens = num_tokens_from_string(prompt)

        return num_tokens, self.input_cost(num_tokens)

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query(self, prompt: str) -> str:
        """
        Query the OpenAI API with the given `history` and return the response.
        """

        try:
            # Perform OpenAI API call
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}], model=self.api_model
            )

            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            self.update_stats(input_tokens, output_tokens)
            return response.choices[0].message.content

        except BadRequestError as e:
            raise CostLimitExceededError(
                f"Context window ({self.model_metadata['max_context']} tokens) exceeded"
            )

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    async def query_async(self, prompt: str) -> str:
        """
        Query the OpenAI API with the given `history` and return the response.
        """

        try:
            # Perform OpenAI API call
            response = await self.async_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}], model=self.api_model
            )

            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            self.update_stats(input_tokens, output_tokens)
            return response.choices[0].message.content

        except BadRequestError as e:
            raise CostLimitExceededError(
                f"Context window ({self.model_metadata['max_context']} tokens) exceeded"
            )

    @retry(
        wait=wait_random_exponential(min=2, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    def query_yaml(self, prompt):
        response = self.query(prompt)
        yaml_content = response.split("```yaml")[1].split("```")[0].strip()

        return yaml.safe_load(yaml_content)


### UTILS
def extract_yaml(response: str):
    yaml_content = response.split("```yaml")[1].split("```")[0].strip()
    return yaml.safe_load(yaml_content)


if __name__ == "__main__":
    from starlette.config import Config

    env = Config(".env")

    async def run_query():
        # Create an instance of ModelArguments
        args = ModelArguments(
            model_name="gpt3",
            api_key=env.get("OPENAI_API_KEY"),
            per_instance_cost_limit=0.05,
            total_cost_limit=1.0,
            temperature=0.7,
            top_p=0.9,
            replay_path=None,
            host_url="localhost:11434",
        )

        # Create an instance of BaseModel
        model = OpenAIModel(args)

        # Define the prompt
        prompt = "What is the capital of France?"

        # Query the model
        response = await model.query(prompt)

    # Run the async function
    asyncio.run(run_query())
