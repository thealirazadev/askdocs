"""Pydantic models for the standard error response shape, used for OpenAPI documentation."""

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
