from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Tuple, Optional, NewType, Any
from enum import Enum
import uuid

from src.models import UUID

class WikiPage(BaseModel):
    title: str
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

class ChatResType(str, Enum):
    CHAT = "chat"
    WALKTHROUGH_CHAT = "walkthrough_chat"

class ChatResponse(BaseModel):
    content: str
    type: ChatResType
    id: UUID = Field(default=str(uuid.uuid4()))
    title: Optional[str] = Field(default="")
    metadata: Optional[Any] = Field(default=None)

class WalkthroughChat(ChatResponse):
    next_chat: Optional[UUID] = Field(default=None) 
    type: ChatResType = ChatResType.WALKTHROUGH_CHAT
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
# TODO: add cluster count
class Walkthrough(BaseModel):
    name: str
    chat_list: List[UUID]

class WalkthroughResponse(BaseModel):
    walkthroughs: List[Walkthrough]