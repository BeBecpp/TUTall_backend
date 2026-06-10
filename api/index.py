"""Vercel serverless entrypoint — exposes the FastAPI ASGI app."""

import logging

logger = logging.getLogger(__name__)

try:
    from app.main import app as app
except Exception as exc:
    logger.exception("Failed to load TUTall app")

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="TUTall Backend")

    @app.get("/health")
    def boot_error_health() -> dict:
        return {
            "status": "error",
            "message": "Backend boot failed",
            "error_code": "BOOT_FAILED",
        }

    @app.api_route("/{path:path}", methods=["GET", "POST", "DELETE", "OPTIONS"])
    def boot_error(path: str) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Backend boot failed",
                "error_code": "BOOT_FAILED",
                "path": f"/{path}",
            },
        )

__all__ = ["app"]
