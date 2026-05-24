"""Exception handlers for the FastAPI application.

centralises error handling logic
"""

from typing import Any
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger("uvicorn.error")


def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error at %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": str(exc) or "Undefined error"})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, handle_unexpected_error)
