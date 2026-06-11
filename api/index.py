"""Vercel serverless entrypoint — stdlib fallback if FastAPI cannot load."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler

logger = logging.getLogger(__name__)

_SECRET_MARKERS = ("api_key", "secret", "password", "token", "bearer", "database_url")


def _safe_error_message(exc: BaseException) -> str:
    message = " ".join(str(exc).split())
    lowered = message.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
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


class handler(BaseHTTPRequestHandler):
    """Stdlib fallback used only when FastAPI `app` is unavailable."""

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in {"/health", "/health/"}:
            self._send_json(
                200,
                {
                    "status": "degraded",
                    "service": "TUTall Backend",
                    "error": "startup_import_failed",
                    "message": "Backend emergency health is running",
                },
            )
            return
        if path in {"/api/debug/startup", "/api/debug/startup/"}:
            self._send_json(
                200,
                _startup_debug_payload(
                    RuntimeError("FastAPI application could not be imported in serverless runtime.")
                ),
            )
            return
        if path in {"/", ""}:
            self._send_json(
                200,
                {
                    "message": "TUTall Backend emergency stdlib handler",
                    "health": "/health",
                    "startup_debug": "/api/debug/startup",
                },
            )
            return
        self._send_json(
            503,
            {
                "error": "Backend boot failed",
                "error_code": "BOOT_FAILED",
                "path": path,
                "startup_ok": False,
            },
        )

    def log_message(self, format: str, *args) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _emergency_fastapi_app(startup_error: BaseException) -> object:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

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


app = None

try:
    from app.application import app as _loaded_app

    app = _loaded_app
except Exception as exc:
    logger.exception("Failed to load TUTall application")
    try:
        app = _emergency_fastapi_app(exc)
    except Exception:
        logger.exception("FastAPI emergency boot failed; stdlib handler remains active")
        app = None

if app is not None:
    handler = app

__all__ = ["app", "handler"]
