from .base import LMP
from typing import List

import re
import numpy as np
from dataclasses import dataclass, field

@dataclass
class LogProbs:
    tokens: List[str] = field(default_factory=list)
    logprobs: List[float] = field(default_factory=list)
 
    def __add__(self, other: "LogProbs"):
        self.tokens += other.tokens
        self.logprobs += other.logprobs
        return self
    
    def __radd__(self, other: "LogProbs"):
        if other == 0:
            return self
        return self.__add__(other)

    def perplexity(self):
        """
        Calculate perplexity from a list of TokenProb objects using raw logprobs.
        Perplexity = exp(-average(log_probabilities))
        Lower perplexity indicates better prediction/higher confidence.
        """
        avg_log_prob = np.mean([lp for lp in self.logprobs])
        return np.exp(-avg_log_prob)

class LogProbLMP(LMP):
    """
    Wraps a LMP that has return_metadata enabled for logprobs
    """
    def call(self, *args, output_rgx: str = "", **kwargs):
        # if not self._check_lmp_returns_metadata():
        #     raise ValueError("LMP must have return_metadata enabled")

        result, metadata = self._lmp(*args, **kwargs)
        self._logprobs = self._calc_logprobs(metadata, output_rgx)
        if output_rgx:
            try:
                print("Result: ", result)
                print("Result: ", result.content[0].text)
                return re.match(output_rgx, result.content[0].text).group(1)
            except AttributeError:
                raise ValueError(f"Output regex pattern '{output_rgx}' did not match any tokens in the response: {str(result)}")

        return result
        
    def _calc_logprobs(self, metadata, output_rgx: str = ""):
        logprobs = LogProbs()
        
        # Get all tokens and their logprobs
        tokens = []
        token_logprobs = []
        for lp in metadata["choices"][0]["logprobs"]["content"]:
            tokens.append(lp["token"])
            token_logprobs.append(lp["logprob"])
            
        # If regex pattern specified, only keep tokens in capturing groups
        if output_rgx:
            text = "".join(tokens)
            matches = re.finditer(output_rgx, text)
            
            for match in matches:
                # Get start and end indices of captured group
                start, end = match.span(1) # Use first capturing group
                
                # Find tokens that fall within the captured span
                curr_pos = 0
                for i, token in enumerate(tokens):
                    token_len = len(token)
                    if curr_pos + token_len > start and curr_pos < end:
                        logprobs.tokens.append(token)
                        logprobs.logprobs.append(token_logprobs[i])
                    curr_pos += token_len
        else:
            logprobs.tokens = tokens
            logprobs.logprobs = token_logprobs
            
        return logprobs
    
    def logprobs(self):
        return self._logprobs

    # TODO: doesn't work, idk
    def _check_lmp_returns_metadata(self):
        return hasattr(self._lmp, "__ell_return_metadata__")