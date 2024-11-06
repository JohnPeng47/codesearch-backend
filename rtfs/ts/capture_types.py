from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from rtfs.scope_resolution import Scoping

@dataclass
class LocalCallCapture:
    index: int
    name: str
    parameters: List[str] = field(default_factory=list)

    def add_parameter(self, value: str):
        self.parameters.append(value)

@dataclass
class LocalDefCapture:
    index: int
    symbol: Optional[str]
    scoping: Scoping

@dataclass
class LocalRefCapture:
    index: int
    symbol: Optional[str]

class ImportPartType(str, Enum):
    MODULE = "module"
    ALIAS = "alias"
    NAME = "name"

@dataclass
class LocalImportPartCapture:
    index: int
    part: str
