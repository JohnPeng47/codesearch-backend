import os
import uvicorn
from logging import getLogger
import multiprocessing
import ell

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from src.middleware import DBMiddleware, AddTaskQueueMiddleware, ExceptionMiddleware
from src.auth.views import auth_router
from src.repo.views import repo_router
from src.queue.views import task_queue_router
from src.health.views import health_router
from src.chat.views import chat_router
from src.config import PORT, REPOS_ROOT, ELL_STORAGE


os.environ["PYDANTIC_WARNINGS"] = "none"  # Set this before importing pydantic

log = getLogger(__name__)

STATIC_DIR = "out"

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

app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR, "static")))

@app.get("/")
def read_root():
    with open(os.path.join(STATIC_DIR, "index.html"), "r") as f:
        content = f.read()
        return HTMLResponse(content=content)


# these paths do not require DB
NO_DB_PATHS = ["/task/get"]

# Add this middleware to your FastAPI app
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

app.add_middleware(ExceptionMiddleware)
app.add_middleware(DBMiddleware)
app.add_middleware(AddTaskQueueMiddleware)

# app.include_router(auth_router, prefix="/api")
# app.include_router(repo_router, prefix="/api")
# app.include_router(task_queue_router, prefix="/api")
# app.include_router(health_router, prefix="/api")
# app.include_router(chat_router, prefix="/api")

app.include_router(auth_router)
app.include_router(repo_router)
app.include_router(task_queue_router)
app.include_router(health_router)
app.include_router(chat_router)

# app.include_router(search_router)
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
    import socket

    def is_port_open(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return True
            except socket.error:
                return False

    if not is_port_open(PORT):
        raise RuntimeError(
            f"Port {PORT} is not available. Please choose a different port."
        )

    uvicorn.run(
        "main:app",
        host="localhost",
        port=PORT,
        workers=2,
        reload=True,
        # reload_excludes=["data"],
        # log_config=config,
    )
