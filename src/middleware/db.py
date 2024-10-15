from typing import Optional, Final
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from sqlalchemy.orm import sessionmaker
from src.database.core import engine

import uuid


REQUEST_ID_CTX_KEY: Final[str] = "request_id"
_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar(
    REQUEST_ID_CTX_KEY, default=None
)


def get_request_id() -> Optional[str]:
    return _request_id_ctx_var.get()


class DBMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.token_registry = set()

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
            if not task_auth_token or not task_auth_token in self.token_registry:
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
