"""Sanitized startup diagnostics — never expose secrets."""

from __future__ import annotations

import re

_SECRET_PATTERNS = (
    r"api[_-]?key",
    r"secret",
    r"password",
    r"token",
    r"bearer",
    r"authorization",
    r"database_url",
    r"postgres",
    r"supabase",
)


def sanitize_error_message(message: str, *, max_length: int = 180) -> str:
    cleaned = " ".join(message.split())
    lowered = cleaned.lower()
    for pattern in _SECRET_PATTERNS:
        if re.search(pattern, lowered):
            return "Startup failed due to a configuration or import error."
    if len(cleaned) > max_length:
        return cleaned[: max_length - 3] + "..."
    return cleaned or "Unknown startup error."


def startup_debug_payload(
    *,
    startup_ok: bool,
    error: BaseException | None = None,
) -> dict[str, object]:
    if startup_ok:
        return {"startup_ok": True}

    error_type = type(error).__name__ if error else "RuntimeError"
    if error_type not in {"ImportError", "ModuleNotFoundError", "RuntimeError", "ValidationError"}:
        error_type = "RuntimeError"

    message = sanitize_error_message(str(error)) if error else "Application import failed."
    return {
        "startup_ok": False,
        "error_type": error_type,
        "error_message": message,
    }
