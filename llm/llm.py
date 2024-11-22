from typing import Any, Dict, Optional, Type, Union
import inspect
from pathlib import Path
import yaml
import sqlite3
import hashlib
import json

from langchain_core.messages.base import BaseMessage
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
        use_cache: bool = True,
        configpath: Path = Path(__file__).parent / "cache.yaml",
        dbpath: Path = Path(__file__).parent / "llm_cache.db"
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
        self.use_cache = use_cache
        self.config = self._read_config(configpath)
        
        # Initialize cache-related attributes
        self.cache_enabled_functions = self._get_cache_enabled_functions()
        print("Enabled functions: ", "\n".join([f for f, enabled in self.cache_enabled_functions.items() if enabled]))
        self.db_connection = None
        
        if use_cache:
            self._initialize_cache(dbpath)
        
        # Add call chain tracking
        self.call_chain = []

    def _read_config(self, fp: Path):
        with open(fp, "r") as f:
            config = yaml.safe_load(f)
        return config

    def _get_caller_info(self):
        frame = inspect.currentframe()
        caller_frame = frame.f_back.f_back  # Go back one more frame
        caller_function = caller_frame.f_code.co_name
        caller_filename = caller_frame.f_code.co_filename

        return caller_filename, caller_function

    def use_model(self, 
                  model_name: str, 
                  temperature: int = 0,
                  provider: str = None,
                  **kwargs: Any):
        provider = provider if provider else self.provider    
        model_class = self.PROVIDER_MAP[provider]

        return model_class(
            model=model_name,
            **kwargs
        )
        
    def _get_cache_enabled_functions(self) -> Dict[str, bool]:
        """Extract function names and their cache states from config."""
        cache_states = {}
        for func_name, settings in self.config.items():
            # Look for cache setting in the list of dictionaries
            cache_setting = next((item.get('cache') 
                                for item in settings 
                                if isinstance(item, dict) and 'cache' in item), 
                               False)
            cache_states[func_name] = cache_setting
        return cache_states

    def _initialize_cache(self, dbpath: Path) -> None:
        """Initialize SQLite connection and create cache table if it doesn't exist."""
        self.db_connection = sqlite3.connect(dbpath)
        cursor = self.db_connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                function_name TEXT,
                model_name TEXT,
                prompt_hash TEXT,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (function_name, model_name, prompt_hash)
            )
        """)
        self.db_connection.commit()

    def _hash_prompt(self, prompt: str) -> str:
        """Create a consistent hash of the prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def _get_cached_response(self, function_name: str, model_name: str, prompt_hash: str) -> Optional[str]:
        """Retrieve cached response if it exists."""
        if not self.db_connection:
            return None
            
        cursor = self.db_connection.cursor()
        cursor.execute(
            "SELECT response FROM llm_cache WHERE function_name = ? AND model_name = ? AND prompt_hash = ?",
            (function_name, model_name, prompt_hash)
        )
        result = cursor.fetchone()
        return json.loads(result[0]) if result else None

    def _cache_response(self, function_name: str, model_name: str, prompt_hash: str, response: Any) -> None:
        """Store response in cache."""
        if not self.db_connection:
            return
            
        cursor = self.db_connection.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO llm_cache (function_name, model_name, prompt_hash, response) VALUES (?, ?, ?, ?)",
            (function_name, model_name, prompt_hash, json.dumps(response))
        )
        self.db_connection.commit()

    def invoke(
        self,
        prompt: str,
        temperature: int = 0,
        *,
        model_name: str,
        response_format: Optional[Type[BaseModel]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Any:
        """Modified invoke method with caching and timeout support."""
        # Track the call
        caller_filename, caller_function = self._get_caller_info()
        self.call_chain.append((caller_filename, caller_function))
        
        # Check if caching is enabled for this function
        if (self.use_cache and 
            caller_function in self.cache_enabled_functions and 
            self.cache_enabled_functions[caller_function]):

            # Check cache for existing response
            prompt_hash = self._hash_prompt(prompt)
            cached_response = self._get_cached_response(caller_function, model_name, prompt_hash)
            
            print(f"Retrieving from cache for {caller_function} using {model_name}")
            
            if cached_response is not None:
                # If response is a Pydantic model, reconstruct it
                if response_format is not None:
                    return response_format.model_validate(cached_response)
                return cached_response

        # If no cache hit, proceed with normal invocation
        lm = self.use_model(
            model_name, 
            temperature=temperature,
            timeout=timeout,
            max_retries=0,
            **kwargs
        )
        
        if response_format is not None:
            if self.provider != "openai":
                raise ValueError(
                    f"response_format is only supported for OpenAI models, "
                    f"but was provided for {self.provider}"
                )
            lm = lm.with_structured_output(response_format, strict=True)

        try:
            res = lm.invoke(prompt)
        except Exception as e:
            if "timeout" in str(e).lower():
                raise TimeoutError(f"LLM request timed out after {timeout} seconds") from e
            raise

        # Extract content from response and convert to response to string for caching
        if isinstance(res, BaseMessage):
            cached_response = res.content
        elif isinstance(res, BaseModel):
            cached_response = res.model_dump()
        else:
            raise Exception(f"Unsupported return type: {type(res)}")

        # Cache the response if caching is enabled for this function
        if (self.use_cache and 
            caller_function in self.cache_enabled_functions and 
            self.cache_enabled_functions[caller_function]):

            print("Caching response: ", cached_response)
            self._cache_response(caller_function, model_name, prompt_hash, cached_response)

        # If original response was a Pydantic model, return it as is
        if isinstance(res, BaseMessage):
            final_response = res.content
        elif isinstance(res, BaseModel):
            final_response = res
            
        return final_response

    def __del__(self):
        """Cleanup database connection on object destruction."""
        if self.db_connection:
            self.db_connection.close()

    def get_callchain(self) -> None:
        """Prints the sequence of calls made to the invoke method."""
        print("\nCall Chain:")
        for idx, (file, func) in enumerate(self.call_chain, 1):
            print(f"{idx}. File: {file}")
            print(f"   Function: {func}")
            if idx < len(self.call_chain):
                print("   ↓")
