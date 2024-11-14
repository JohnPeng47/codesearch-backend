from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Tuple, Optional, NewType, Any
from enum import Enum
import uuid

from src.repo.models import RepoGetRequest
from src.models import UUID, NameStr

class WikiPage(BaseModel):
    title: NameStr
    content: str
    metadata: Dict

class WikiPageResponse(BaseModel):
    pages: List[WikiPage]
    start: int

    @field_validator('start')
    @classmethod
    def validate_start(cls, v: int, info) -> int:
        if not info.data.get('pages'):
            return v
        if v < 0 or v >= len(info.data['pages']):
            raise ValueError(f"Start index {v} is out of range for pages list with length {len(info.data['pages'])}")
        return v
    
class SrcMetadata(BaseModel):
    filepath: str
    start_line: int
    end_line: int

class ChatType(str, Enum):
    CHAT = "chat"
    WALKTHROUGH_CHAT = "walkthrough_chat"


# TODO: kinda weird to extend repoGetRequest ...
class ChatMessage(RepoGetRequest):
    query: str
    id: UUID
    type: ChatType = ChatType.CHAT
    data: Optional[Any] = Field(default=None)

    # Add model validator to handle ChatMessage subclasses
    @model_validator(mode='before')
    @classmethod
    def validate_data(cls, values):
        if isinstance(values, dict):
            if values.get('type') == ChatType.WALKTHROUGH_CHAT and values.get('data'):
                values['data'] = WalkThroughData(**values['data'])
        return values

class WalkThroughData(BaseModel):
    walkthrough: NameStr
    next_id: UUID

class WalkthroughMessage(RepoGetRequest):
    type: ChatType = ChatType.WALKTHROUGH_CHAT
    data: WalkThroughData

class ChatResponse(BaseModel):
    content: str
    type: ChatType
    id: UUID = Field(default=str(uuid.uuid4()))
    title: Optional[NameStr] = Field(default="")
    metadata: Optional[Any] = Field(default=None)

class WalkthroughChat(ChatResponse):
    next_chat: Optional[UUID] = Field(default=None) 
    type: ChatType = ChatType.WALKTHROUGH_CHAT
    metadata: Dict[str, SrcMetadata] = Field(...)

    # NOTE: need custom validator here for the dict
    @model_validator(mode='before')
    def validate_metadata(cls, values):
        if 'metadata' in values:
            metadata = values['metadata']
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    # NOTE: confirm that python 
                    if value.__class__.__name__ != 'SrcMetadata':
                        raise ValueError(f"Value for key {key} must be SrcMetadata")
        return values

    @classmethod
    def from_json(cls, dict) -> 'WalkthroughChat':        
        return WalkthroughChat(
            content=dict["content"],
            metadata={fp: SrcMetadata(**src_data) for fp, src_data in dict["metadata"].items()}
        )

# TODO: create a db model for this associated a with Repo
# TODO: add cluster count to this
class Walkthrough(BaseModel):
    name: NameStr
    chat_list: List[UUID]

class WalkthroughResponse(BaseModel):
    walkthroughs: List[Walkthrough]