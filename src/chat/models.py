from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Tuple, Optional, NewType, Any
from enum import Enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Table, Index, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from src.database.core import Base
from src.repo.models import RepoGetRequest, Repo
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

class WalkthroughData(BaseModel):
    next_chat: Optional[UUID] = Field(default=None) 
    metadata: Dict[str, SrcMetadata] = Field(...)

    @model_validator(mode='before')
    def validate_metadata(cls, values):
        if 'metadata' in values:
            metadata = values['metadata']
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    if not isinstance(value, SrcMetadata):
                        raise ValueError(f"Value for key {key} must be SrcMetadata")
        return values

class WalkthroughChat(ChatResponse): 
    type: ChatType = ChatType.WALKTHROUGH_CHAT
    metadata: WalkthroughData

    @classmethod
    def from_json(cls, dict) -> 'WalkthroughChat':      
        print("Chat dict: ", dict)          
        metadata = WalkthroughData(
            next_chat=dict["metadata"]["next_chat"],
            metadata={fp: SrcMetadata(**src_data) for fp, src_data in dict["metadata"]["metadata"].items()}
        )
        return WalkthroughChat(
            content=dict["content"],
            metadata=metadata
        )

# walkthrough_chat_messages = Table(
#     'walkthrough_chat_messages',
#     Base.metadata,
#     Column('walkthrough_id', PGUUID(as_uuid=True), ForeignKey('walkthroughs.id')),
#     Column('chat_message_id', PGUUID(as_uuid=True), ForeignKey('chat_messages.id')),
# )


# class ChatMessage(Base):
#     __tablename__ = 'chat_messages'

#     id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     query = Column(String, nullable=False)
#     type = Column(String(ChatType), nullable=False, default=ChatType.CHAT)
#     data = Column(JSON, nullable=True)  # Stores WalkThroughData as JSON
#     created_at = Column(DateTime, default=datetime.utcnow)
    
#     # Foreign key for repository relationship
#     repo_id = Column(PGUUID(as_uuid=True), ForeignKey('repositories.id'), nullable=False)
    
#     # Relationships
#     repository = relationship("Repository", back_populates="chat_messages")
#     response = relationship("ChatResponse", uselist=False, back_populates="message", cascade="all, delete-orphan")
#     walkthroughs = relationship(
#         "Walkthrough",
#         secondary=walkthrough_chat_messages,
#         back_populates="chat_messages"
#     )

#     # Define separate indices for different chat types
#     __table_args__ = (
#         # Index for regular chats - includes repo_id for filtering and created_at for sorting
#         Index(
#             'idx_regular_chats',
#             repo_id,
#             created_at.desc(),
#             postgresql_where=(type == ChatType.CHAT)
#         ),
#         # Index for walkthrough chats - optimized for frequent access
#         Index(
#             'idx_walkthrough_chats',
#             repo_id,
#             type,
#             created_at.desc(),
#             postgresql_where=(type == ChatType.WALKTHROUGH_CHAT)
#         ),
#         # Compound index for type-based queries with repository filtering
#         Index('idx_chat_type_repo', type, repo_id)
#     )


# class Walkthrough(Base):
#     __tablename__ = 'walkthroughs'
#     id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String, nullable=False)
    
#     # Relationships
#     chat_messages = relationship(
#         "ChatMessage",
#         secondary=walkthrough_chat_messages,
#         back_populates="walkthroughs",
#         order_by="ChatMessage.id"
#     )
    
#     # Foreign key for repository relationship
#     repo_id = Column(PGUUID(as_uuid=True), ForeignKey(Repo.id), nullable=False)
#     repository = relationship(Repo, back_populates="walkthroughs")


# TODO: create a db model for this associated a with Repo
# TODO: add cluster count to this
class Walkthrough(BaseModel):
    name: NameStr
    chat_messages: List[UUID]

class WalkthroughResponse(BaseModel):
    walkthroughs: List[Walkthrough]