from typing import Optional, Final
from contextvars import ContextVar
import os

from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import ValidationError

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
from src.database.core import engine

from src.extensions import init_sentry
from src.config import PORT, REPOS_ROOT

import uuid

log = getLogger(__name__)

STATIC_DIR = "build"

async def not_found(request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": [{"msg": "Not Found."}]},
    )


exception_handlers = {404: not_found}


app = FastAPI(exception_handlers=exception_handlers, openapi_url="/docs/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static", StaticFiles(directory=os.path.join(STATIC_DIR, "static")))

@app.get("/")
def read_root():
    with open(os.path.join(STATIC_DIR, "index.html"), 'r') as f:
        content = f.read()
        return HTMLResponse(content=content)

# def get_path_params_from_request(request: Request) -> str:
#     path_params = {}
#     for r in api_router.routes:
#         path_regex, path_format, param_converters = compile_path(r.path)
#         path = request["path"].removeprefix(
#             "/api/v1"
#         )  # remove the /api/v1 for matching
#         match = path_regex.match(path)
#         if match:
#             path_params = match.groupdict()
#     return path_params


def get_path_template(request: Request) -> str:
    if hasattr(request, "path"):
        return ",".join(request.path.split("/")[1:])
    return ".".join(request.url.path.split("/")[1:])


REQUEST_ID_CTX_KEY: Final[str] = "request_id"
_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar(
    REQUEST_ID_CTX_KEY, default=None
)


def get_request_id() -> Optional[str]:
    return _request_id_ctx_var.get()


# these paths do not require DB
NO_DB_PATHS = ["/task/get"]


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
                session = sessionmaker(bind=engine)
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


# class LogfireLogUser(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         try:
#             # we have to skip requests with x-task-auth or else logfire will log an exception for this
#             # request when it tries to acces request.state.db
#             if not request.headers.get("x-task-auth", None):
#                 with logfire.span("request"):
#                     user = get_current_user(request)
#                     logfire.info("{user}", user=user.email)
#         except AttributeError as e:
#             pass
#         finally:
#             response = await call_next(request)
#             return response


task_queue = TaskQueue()


class AddTaskQueueMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.task_queue = task_queue
        response = await call_next(request)
        return response


# app.add_middleware(LogfireLogUser)
app.add_middleware(ExceptionMiddleware)
app.add_middleware(DBMiddleware)
app.add_middleware(AddTaskQueueMiddleware)

app.include_router(auth_router)
app.include_router(repo_router)
app.include_router(task_queue_router)
# app.include_router(search_router)
app.include_router(health_router)
# logfire.configure(console=False)
# logfire.instrument_fastapi(app, excluded_urls=["/task/get"])


def calculate_workers(num_threads_per_core=2):
    """
    Calculate the number of workers based on the formula:
    number_of_workers = number_of_cores x num_of_threads_per_core + 1

    :param num_threads_per_core: Number of threads per core (default is 2)
    :return: Calculated number of workers
    """
    num_cores = multiprocessing.cpu_count()
    number_of_workers = (num_cores * num_threads_per_core) + 1
    return number_of_workers


if __name__ == "__main__":
    # start the repo sync thread
    # Session = sessionmaker(bind=engine)
    # db_session = Session()
    # start_sync_thread(db_session, task_queue)

    # logfire.configure()

    uvicorn.run(
        "main:app",
        host="localhost",
        port=PORT,
        # workers=2,
        # workers=calculate_workers(),
        reload=True,
        reload_excludes=["./data"],
        # log_config=config,
    )
