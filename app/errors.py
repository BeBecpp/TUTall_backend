from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_payload(code: str, message: str, request_id: str) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorDetail(code=code, message=message, request_id=request_id)
    ).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = _get_request_id(request)
        detail = exc.detail

        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            message = str(detail["message"])
            code = str(detail["code"])
        elif isinstance(detail, str):
            message = detail
            code = _status_to_code(exc.status_code)
        else:
            message = "Request could not be processed."
            code = _status_to_code(exc.status_code)

        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code, message, request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(
                "VALIDATION_ERROR",
                "Invalid request data. Please check your input and try again.",
                request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        _ = exc
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                "INTERNAL_ERROR",
                "An unexpected error occurred. Please try again later.",
                request_id,
            ),
        )


def _status_to_code(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        429: "RATE_LIMITED",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
    }
    return mapping.get(status_code, "ERROR")
