from typing import List, Dict
from pydantic import BaseModel, field_validator


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

class ChatResponse(BaseModel):
    chat: str