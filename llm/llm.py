from typing import Any, Dict, Optional, Type, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.llms import BaseLLM
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from pydantic import BaseModel
import tiktoken

def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string, disallowed_special=()))
    return num_tokens

class LLMModel:
    """
    A flexible wrapper class for LangChain language models that supports arbitrary configuration.
    
    Example usage:
    ```python
    # OpenAI with response format
    model = LLMModel(
        provider="openai",
        model_name="gpt-4-0125-preview",
        temperature=0
    )
    
    # Anthropic with specific temperature
    model = LLMModel(
        provider="anthropic",
        model_name="claude-3-opus-20240229", 
        temperature=0.7
    )
    ```
    """
    
    # Mapping of provider names to their corresponding LangChain model classes
    PROVIDER_MAP = {
        "openai": ChatOpenAI,
        "anthropic": ChatAnthropic,
    }
    
    def __init__(
        self,
        provider: str,
    ) -> None:
        """
        Initialize the LLM model with the specified provider and configuration.
        
        Args:
            provider: The name of the model provider (e.g., "openai", "anthropic")
            model_name: The specific model name to use
            **kwargs: Additional arguments to pass to the model constructor
        
        Raises:
            ValueError: If the provider is not supported
        """
        if provider not in self.PROVIDER_MAP:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers are: {list(self.PROVIDER_MAP.keys())}"
            )
        
        self.provider = provider
        
    def use_model(self, model_name: str, temperature: int = 0, **kwargs: Any):
        model_class = self.PROVIDER_MAP[self.provider]

        return model_class(
            model=model_name,
            **kwargs
        )
        
    # TODO: Defining 
    def invoke(
        self,
        prompt: str,
        temperature: int = 0,
        *,
        model_name: str,
        response_format: Optional[Type[BaseModel]] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke the model with the given prompt and configuration.
        
        Args:
            prompt: The input prompt to send to the model
            response_format: Optional Pydantic model to format the response (OpenAI only)
            **kwargs: Additional configuration parameters
            
        Returns:
            The model's response
            
        Raises:
            ValueError: If response_format is provided for a non-OpenAI provider
        """
        lm = self.use_model(model_name, temperature=temperature, **kwargs)
        if response_format is not None:
            if self.provider != "openai":
                raise ValueError(
                    f"response_format is only supported for OpenAI models, "
                    f"but was provided for {self.provider}"
                )
            lm = lm.with_structured_output(response_format, strict=True)

        # TODO: build adapter here to support other models
        res = lm.invoke(prompt)        
        if isinstance(res, BaseModel):
            return res
        else:
            return res.content