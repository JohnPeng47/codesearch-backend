from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from fastapi.responses import HTMLResponse, JSONResponse

from src.exceptions import ClientActionException
from logging import getLogger

logger = getLogger(__name__)


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
            logger.exception(e)
            response = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": e.errors(), "error": True},
            )
        except ValueError as e:
            logger.exception(e)
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
            logger.exception(e)
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
