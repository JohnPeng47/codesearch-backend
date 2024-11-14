from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import re
import uuid
import json

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import User
from src.chunk.chunk import chunk_repo, ChunkStrat
from src.config import REPOS_ROOT, WALKTHROUGH_ROOT
from src.repo.models import RepoGetRequest

from .models import Walkthrough, WalkthroughResponse, ChatResponse

chat_router = APIRouter()

# main chat endpoint
# @chat_router.post("/chat")
# async def chat(
#     chat_id: int,
#     db_session: Session = Depends(get_db),
#     curr_user: User = Depends(get_current_user)
# ):
#     chat = CHATS[chat_id]
#     print("Getting chat: ", chat["nextWiki"])
#     return ChatResponse(
#         id=str(uuid.uuid4()), 
#         content=chat["content"], 
#         nextWiki=chat["nextWiki"], 
#         title=chat["content"][12:24])


@chat_router.post("/chat/walkthrough", response_model=WalkthroughResponse)
async def gen_walkthrough(
    repo_in: RepoGetRequest,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user)
):
    walkthrough_path = WALKTHROUGH_ROOT / repo_in.repo_ident
    walkthrough_json = json.loads(open(walkthrough_path).read())

    return WalkthroughResponse(
        walkthroughs = [
            Walkthrough(
                name=walkthrough["name"], 
                chat_list=[w["id"] for w in walkthrough["walkthroughs"]]
            ) for walkthrough in walkthrough_json
        ]
    )