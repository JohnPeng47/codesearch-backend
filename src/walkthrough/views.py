from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import re

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import User
from src.chunk.chunk import chunk_repo, ChunkStrat
from src.config import REPOS_ROOT

from .data import CHATS, WIKIS
from .models import WikiPageResponse, ChatResponse, WikiPage

walkthrough_router = APIRouter()

@walkthrough_router.post("/walkthrough/wiki")
async def start_walkthrough(
    wikiRequest: WikiPage,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user)
):
    # HARDCODED
    MOATLESS_PATH = REPOS_ROOT / "aorwall_moatless-tools"
    chunk_files = re.findall("\[\[(.*)\]\]", WIKIS[wikiRequest.title])
    chunks = chunk_repo(MOATLESS_PATH, ChunkStrat.VANILLA)
    chunk_dict = {}
    for f in chunk_files:
        chunk = next(filter(lambda c: c.id == f, chunks), None)
        if not chunk:
            raise Exception(f"{f} not found")
        chunk_dict[f] = {"start_line": chunk.metadata.start_line, "end_line": chunk.metadata.end_line}

    print("CHunkfiuc: ", chunk_dict)
    wiki = WikiPage(title=wikiRequest.title, content=WIKIS[wikiRequest.title], metadata=chunk_dict)
    return WikiPageResponse(pages=[wiki], start=0)

@walkthrough_router.get("/walkthrough/chat/{chat_id}")
async def start_walkthrough(
    chat_id: int,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user)
):
    chat = CHATS[chat_id]
    return ChatResponse(content=chat)
