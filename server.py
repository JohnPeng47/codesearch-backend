from typing import Optional, Final
from contextvars import ContextVar
import os

from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from sqlalchemy import Engine
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from sqlalchemy.orm import sessionmaker

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

import uvicorn
from logging import getLogger
import multiprocessing

# from src.logger import configure_uvicorn_logger
# from src.auth.service import get_current_user

from src.queue.core import TaskQueue
from src.auth.views import auth_router
from src.repo.views import repo_router

# from src.search.views import search_router
from src.queue.views import task_queue_router
from src.health.views import health_router
from src.exceptions import ClientActionException

from src.extensions import init_sentry
from src.config import PORT, REPOS_ROOT

import uuid

log = getLogger(__name__)

STATIC_DIR = "out"


async def not_found(request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": [{"msg": "Not Found."}]},
    )


def create_app(sql_engine: Engine):
    exception_handlers = {404: not_found}

    REQUEST_ID_CTX_KEY: Final[str] = "request_id"
    _request_id_ctx_var: ContextVar[Optional[str]] = ContextVar(
        REQUEST_ID_CTX_KEY, default=None
    )

    # TODO: ideally this should have some sort of contract with our front-end
    class ExceptionMiddleware(BaseHTTPMiddleware):
        async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
        ) -> StreamingResponse:
            try:
                response = await call_next(request)

            # this is an interface with client
            except ClientActionException as e:
                response = JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": e.message, "type": e.type},
                )

            except ValidationError as e:
                log.exception(e)
                response = JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": e.errors(), "error": True},
                )
            except ValueError as e:
                log.exception(e)
                response = JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": [
                            {"msg": "Unknown", "loc": ["Unknown"], "type": "Unknown"}
                        ],
                        "error": True,
                    },
                )
            except Exception as e:
                log.exception(e)
                response = JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "detail": [
                            {"msg": "Unknown", "loc": ["Unknown"], "type": "Unknown"}
                        ],
                        "error": True,
                    },
                )

            return response

    token_registry = set()

    class DBMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # request_id = str(uuid1())

            # we create a per-request id such that we can ensure that our session is scoped for a particular request.
            # see: https://github.com/tiangolo/fastapi/issues/726
            # ctx_token = _request_id_ctx_var.set(request_id)
            # path_params = get_path_params_from_request(request)

            # # if this call is organization specific set the correct search path
            # organization_slug = path_params.get("organization", "default")
            # request.state.organization = organization_slug

            # # Find out more about
            # schema = f"dispatch_organization_{organization_slug}"
            # # validate slug exists
            # schema_names = inspect(engine).get_schema_names()
            # if schema in schema_names:
            #     # add correct schema mapping depending on the request
            #     schema_engine = engine.execution_options(
            #         schema_translate_map={
            #             None: schema,
            #         }
            #     )
            # else:
            #     return JSONResponse(
            #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            #         content={"detail": [{"msg": f"Unknown database schema name: {schema}"}]},
            #     )

            try:
                request.state.session_id = str(uuid.uuid4())
                # this is a very janky implementation to handle the fact that assigning a db session
                # to every request blows up our db connection pool
                task_auth_token = request.headers.get("x-task-auth", None)
                if not task_auth_token or not task_auth_token in token_registry:
                    session = sessionmaker(bind=sql_engine)
                    request.state.db = session()
                    request.state.db.id = str(uuid.uuid4())

                response = await call_next(request)
            except Exception as e:
                raise e from None
            finally:
                db = getattr(request.state, "db", None)
                if db:
                    db.close()

            # _request_id_ctx_var.reset(ctx_token)
            return response

    task_queue = TaskQueue()

    class AddTaskQueueMiddleware(BaseHTTPMiddleware):
        async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
        ) -> Response:
            request.state.task_queue = task_queue
            response = await call_next(request)
            return response

    app = FastAPI(
        exception_handlers=exception_handlers, openapi_url="/docs/openapi.json"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # configure serving static folders
    app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR, "static")))

    @app.get("/")
    def read_root():
        with open(os.path.join(STATIC_DIR, "index.html"), "r") as f:
            content = f.read()
            return HTMLResponse(content=content)

    app.add_middleware(ExceptionMiddleware)
    app.add_middleware(DBMiddleware)
    app.add_middleware(AddTaskQueueMiddleware)

    app.include_router(auth_router)
    app.include_router(repo_router)
    app.include_router(task_queue_router)
    app.include_router(health_router)
