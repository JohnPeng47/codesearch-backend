from typing import Dict, Optional, NewType
from enum import Enum
from dataclasses import dataclass, field

from rtfs.graph import Node
from rtfs.utils import TextRange

from pydantic import Field


class NodeKind(str, Enum):
    SCOPE = "LocalScope"
    DEFINITION = "LocalDef"
    IMPORT = "Import"
    REFERENCE = "Reference"
    CALL = "Call"


class EdgeKind(str, Enum):
    ScopeToScope = "ScopeToScope"
    DefToScope = "DefToScope"
    ImportToScope = "ImportToScope"
    RefToDef = "RefToDef"
    RefToOrigin = "RefToOrigin"
    RefToImport = "RefToImport"
    CallToRef = "CallToRef"


@dataclass(kw_only=True)
class ScopeNode(Node):
    kind: str = "ScopeNode"
    range: TextRange
    type: NodeKind
    name: Optional[str] = ""
    data: Optional[Dict] = field(default_factory=dict)


ScopeID = NewType("ScopeID", int)
