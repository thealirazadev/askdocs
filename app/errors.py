"""Consistent error types and FastAPI exception handlers.

Every error response uses the shape {"error": {"code", "message"}}. Application code raises
AppError (or a subclass) with the code and a safe, human-readable message; the handlers below
convert those, FastAPI's validation errors, and any unhandled exception into that shape.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("askdocs")


class AppError(Exception):
    """Base class for application errors mapped to the standard error JSON."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class UnsupportedFileTypeError(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "unsupported_file_type"


class FileTooLargeError(AppError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "file_too_large"


class EmptyDocumentError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "empty_document"


class ExtractionFailedError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "extraction_failed"


class EmbeddingFailedError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "embedding_failed"


class VectorStoreError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "vector_store_error"


class ModelApiError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "model_api_error"


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.info(
            "app_error",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "route": request.url.path,
            },
        )
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("validation_error", extra={"route": request.url.path, "errors": exc.errors()})
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", "The request body is invalid."
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == status.HTTP_404_NOT_FOUND else "internal_error"
        message = (
            str(exc.detail)
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else "An unexpected error occurred."
        )
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", extra={"route": request.url.path})
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred."
        )
