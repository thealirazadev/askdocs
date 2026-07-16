"""FastAPI application factory: routers, exception handlers, logging middleware."""

from fastapi import FastAPI

from app.config import get_settings
from app.errors import register_exception_handlers
from app.logging import RequestIdMiddleware, configure_logging
from app.routers import ask, documents, health

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="askdocs")
app.add_middleware(RequestIdMiddleware)
register_exception_handlers(app)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(ask.router)
