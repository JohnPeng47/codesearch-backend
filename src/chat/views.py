from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import re
import uuid
import json

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import User
from src.config import REPOS_ROOT, WALKTHROUGH_ROOT
from src.repo.models import RepoGetRequest

from .models import (
    Walkthrough, 
    WalkthroughResponse, 
    WalkthroughChat,
    ChatMessage,
    ChatType,
    ChatResponse,
    SrcMetadata
)

chat_router = APIRouter()

# main chat endpoint
@chat_router.post("/chat", response_model=ChatResponse)
async def chat(
    msg: ChatMessage,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user)
):
    walkthrough_path = WALKTHROUGH_ROOT / msg.repo_ident
    walkthrough_json = json.loads(open(walkthrough_path).read())
    if msg.type == ChatType.WALKTHROUGH_CHAT:
        # Flatten all chats from all walkthroughs into a single list
        all_chats = [chat for walkthrough in walkthrough_json for chat in walkthrough["walkthroughs"]]
        chat = next(filter(lambda chat: chat["id"] == msg.data.next_id, all_chats), None)
        if not chat:
            raise ValueError(f"Chat {msg.data.next_id} not found")
        
        return WalkthroughChat.from_json(chat)

@chat_router.post("/chat/walkthrough", response_model=WalkthroughResponse)
async def gen_walkthrough(
    repo_in: RepoGetRequest,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user)
):
    walkthrough_path = WALKTHROUGH_ROOT / repo_in.repo_ident
    walkthrough_json = json.loads(open(walkthrough_path).read())

    print([
            Walkthrough(
                name=walkthrough["name"], 
                chat_messages=[w["id"] for w in walkthrough["walkthroughs"]]
            ) for walkthrough in walkthrough_json
        ]
    )

    return WalkthroughResponse(
        walkthroughs = [
            Walkthrough(
                name=walkthrough["name"], 
                chat_messages=[w["id"] for w in walkthrough["walkthroughs"]]
            ) for walkthrough in walkthrough_json
        ]
    )