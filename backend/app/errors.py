import logging
from typing import Literal

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app.shared.errors import AppError

logger = logging.getLogger(__name__)

STATUS_CODES = {
    400: "VALIDATION_ERROR",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    409: "STATE_CONFLICT",
    422: "VALIDATION_ERROR",
}
STABLE_CODES = set(STATUS_CODES.values()) | {"SERVICE_ERROR", "ROLE_REQUIRED", "INVALID_DATE_RANGE"}


class ErrorDetail(BaseModel):
    code: Literal[
        "AUTH_REQUIRED",
        "FORBIDDEN",
        "RESOURCE_NOT_FOUND",
        "STATE_CONFLICT",
        "VALIDATION_ERROR",
        "SERVICE_ERROR",
        "ROLE_REQUIRED",
        "INVALID_DATE_RANGE",
    ]
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail


def error_payload(code: str, message: str) -> dict:
    return {"detail": {"code": code, "message": message}}


def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or STATUS_CODES.get(exc.status_code, "SERVICE_ERROR"))
        message = str(detail.get("message") or code)
    else:
        message = str(detail)
        code = message if message in STABLE_CODES else STATUS_CODES.get(exc.status_code, "SERVICE_ERROR")
    return JSONResponse(status_code=exc.status_code, content=error_payload(code, message), headers=exc.headers)


def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_payload(exc.code, exc.message))


def validation_exception_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content=error_payload("VALIDATION_ERROR", "请求参数无效"))


def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    route = request.scope.get("route")
    logger.error(
        "Unhandled API error method=%s route=%s type=%s",
        request.method,
        getattr(route, "path", "unknown"),
        type(exc).__name__,
    )
    return JSONResponse(status_code=500, content=error_payload("SERVICE_ERROR", "服务暂时不可用"))
