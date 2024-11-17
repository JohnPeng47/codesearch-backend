from pydantic import BaseModel
from abc import ABC, abstractmethod

# TODO:
# this is not enough
# we essentially want sosmthing like
# struct -> invoke (lm_struct) -> lm_struct : struct
# need to map lm_struct back to struct automatically after the invoke
# need for SELECT/UPDATE/DELETE operations on an existing set of structs


class LMStruct(BaseModel, ABC):
    """
    Used for structs used inside of LM text prompts, that implements a simplified
    """

    @abstractmethod
    def to_lmstr(self) -> str:
        raise NotImplementedError