"""FastAPI application factory: routers, exception handlers, logging middleware, static web UI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"

if _WEB_DIR.is_dir():
    app.mount("/web", StaticFiles(directory=_WEB_DIR), name="web")

    @app.get("/", include_in_schema=False)
    def serve_index() -> FileResponse:
        return FileResponse(_WEB_DIR / "index.html")
