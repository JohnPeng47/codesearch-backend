from fastapi import status, HTTPException
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
        # TODO: figure out why this needs to be here or else CORs errors ...        
        try:
            response = await call_next(request)
        
        except HTTPException as e:
            response = JSONResponse(
                status_code=e.status_code,
                content={"detail": [{"msg": e.detail}]},
            )

        # handles all retryable client errors
        except ClientActionException as e:
            response = JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                headers={"Access-Control-Allow-Origin": "*"},
                # mimic pydantic error message format
                content={
                    "detail" : [
                        {"msg": e.message, "type": "ClientError"},
                    ]
                }
            )

        except Exception as e:
            logger.exception(e)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": [
                        {"msg": "Unknown server error", "type": "ServerError"},
                    ],
                    "error": True,
                },
            )

        return response
