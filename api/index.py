"""Vercel serverless entrypoint — must never crash at import time."""

import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def _emergency_app() -> FastAPI:
    emergency = FastAPI(title="TUTall Backend")

    @emergency.get("/health")
    def emergency_health() -> dict:
        return {
            "status": "ok",
            "service": "TUTall Backend",
            "environment": os.getenv("APP_ENV", "production"),
            "ai_configured": False,
            "cohere_configured": False,
            "openrouter_configured": False,
            "database_configured": bool(os.getenv("DATABASE_URL", "").strip()),
            "version": "1.0.0",
        }

    @emergency.api_route("/{path:path}", methods=["GET", "POST", "DELETE", "OPTIONS"])
    def emergency_handler(path: str) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Backend boot failed",
                "error_code": "BOOT_FAILED",
                "path": f"/{path}",
            },
        )

    return emergency


try:
    from app.main import app as app
except Exception:
    logger.exception("Failed to load TUTall app; serving emergency endpoints")
    app = _emergency_app()

__all__ = ["app"]
