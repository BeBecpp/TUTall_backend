"""Vercel serverless entrypoint — must never crash at import time."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_SECRET_PATTERNS = (
    "api_key",
    "secret",
    "password",
    "token",
    "bearer",
    "database_url",
)


def _safe_error_message(exc: BaseException) -> str:
    message = " ".join(str(exc).split())
    lowered = message.lower()
    if any(pattern in lowered for pattern in _SECRET_PATTERNS):
        return "Application import failed due to a configuration or dependency error."
    return message[:180] if message else "Application import failed."


def _startup_debug_payload(exc: BaseException | None) -> dict[str, object]:
    if exc is None:
        return {"startup_ok": True}
    error_type = type(exc).__name__
    if error_type not in {"ImportError", "ModuleNotFoundError", "RuntimeError", "ValidationError"}:
        error_type = "RuntimeError"
    return {
        "startup_ok": False,
        "error_type": error_type,
        "error_message": _safe_error_message(exc),
    }


def _emergency_app(startup_error: BaseException | None = None) -> FastAPI:
    emergency = FastAPI(title="TUTall Backend")
    debug_payload = _startup_debug_payload(startup_error)

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
    logger.exception("Failed to load TUTall application")
    app = _emergency_app(exc)

handler = app

__all__ = ["app", "handler"]
