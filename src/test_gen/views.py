from fastapi import APIRouter, Depends

from src.database.core import get_db
from src.models import HTTPSuccess
from src.auth.service import get_current_user
from src.queue.core import get_queue

from .models import AugmentTestRequest, AugmentTestResponse
from .service import augment_test

test_gen_router = APIRouter()


@test_gen_router.post("/test-gen/augment")
async def augment_test_route(
    request: AugmentTestRequest,
    db_session=Depends(get_db),
    curr_user=Depends(get_current_user),
    task_queue=Depends(get_queue),
):
    merge_url = await augment_test(
        task_queue=task_queue,
        db_session=db_session,
        curr_user=curr_user,
        tm_name=request.tm_name,
        repo_name=request.repo_name,
    )

    return AugmentTestResponse(merge_url=merge_url)
