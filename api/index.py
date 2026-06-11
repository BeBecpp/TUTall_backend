"""Vercel serverless entrypoint — must never crash at import time."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.startup_debug import startup_debug_payload

logger = logging.getLogger(__name__)

_STARTUP_ERROR: BaseException | None = None


def _emergency_app(startup_error: BaseException | None = None) -> FastAPI:
    emergency = FastAPI(title="TUTall Backend")
    debug_payload = startup_debug_payload(startup_ok=False, error=startup_error)

    @emergency.get("/")
    def emergency_root() -> dict:
        return {
            "message": "TUTall Backend emergency mode",
            "health": "/health",
            "startup_debug": "/api/debug/startup",
        }

    @emergency.get("/health")
    def emergency_health() -> dict:
        return {
            "status": "degraded",
            "service": "TUTall Backend",
            "error": "startup_import_failed",
            "message": "Backend emergency health is running",
        }

    @emergency.get("/api/debug/startup")
    def emergency_startup_debug() -> dict:
        return debug_payload

    @emergency.api_route("/{path:path}", methods=["GET", "POST", "DELETE", "OPTIONS"])
    def emergency_handler(path: str) -> JSONResponse:
        if path in {"health", "api/debug/startup"}:
            return JSONResponse(status_code=404, content={"error": "Not found"})
        return JSONResponse(
            status_code=503,
            content={
                "error": "Backend boot failed",
                "error_code": "BOOT_FAILED",
                "path": f"/{path}",
                "startup_ok": False,
            },
        )

    return emergency


try:
    from app.application import app as app
except Exception as exc:
    _STARTUP_ERROR = exc
    logger.exception("Failed to load TUTall application")
    app = _emergency_app(exc)

__all__ = ["app"]
