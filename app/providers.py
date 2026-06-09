"""AI provider layer: OpenRouter -> AccessSTEM Local Engine."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_SYSTEM_PROMPT = (
    "You are AccessSTEM AI, a helpful STEM learning assistant for students."
)
OPENROUTER_HTTP_REFERER = "https://bebecpp.github.io/TUTall_frontend/"
OPENROUTER_APP_TITLE = "TUTall AccessSTEM AI"
REQUEST_TIMEOUT = 45.0

SOURCE_OPENROUTER = "openrouter"
SOURCE_LOCAL = "accessstem_local"


def call_openrouter_text(prompt: str) -> str:
    settings = get_settings()
    if not settings.openrouter_configured:
        raise RuntimeError("OpenRouter is not configured")

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": OPENROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_HTTP_REFERER,
        "X-Title": OPENROUTER_APP_TITLE,
    }

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.post(OPENROUTER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Empty OpenRouter response")

    text = str(choices[0].get("message", {}).get("content", "")).strip()
    if not text:
        raise RuntimeError("Empty OpenRouter response text")
    return text


def try_openrouter_text(prompt: str) -> str | None:
    settings = get_settings()
    if not settings.openrouter_configured:
        return None

    try:
        return call_openrouter_text(prompt)
    except Exception as exc:
        logger.warning("OpenRouter call failed: %s", type(exc).__name__)
        return None


def _local_debug_reason(settings_reason: str | None = None) -> str:
    settings = get_settings()
    if not settings.enable_ai:
        return "ai_disabled"
    if settings.demo_mode:
        return "demo_mode"
    if not settings.enable_openrouter:
        return "openrouter_disabled"
    if not settings.openrouter_api_key.strip():
        return "openrouter_not_configured"
    return settings_reason or "openrouter_unavailable"


def _apply_local_result(local_fn: Callable[[], dict[str, Any]], debug_reason: str) -> dict[str, Any]:
    result = local_fn()
    result["source"] = SOURCE_LOCAL
    result["debug_reason"] = debug_reason
    return result


def generate_with_providers(
    prompt: str,
    parser: Callable[[str, str], dict[str, Any]],
    local_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Try OpenRouter first, then AccessSTEM Local Engine. Parser receives (text, source)."""
    text = try_openrouter_text(prompt)
    if text:
        try:
            result = parser(text, SOURCE_OPENROUTER)
            result["source"] = SOURCE_OPENROUTER
            result.pop("debug_reason", None)
            return result
        except Exception as exc:
            logger.warning("OpenRouter output unusable: %s", type(exc).__name__)
            return _apply_local_result(local_fn, "openrouter_output_unusable")

    return _apply_local_result(local_fn, _local_debug_reason())


def generate_text_with_providers(
    prompt: str,
    parser: Callable[[str, str], dict[str, Any]],
    local_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Alias for plain-text endpoints like hint."""
    return generate_with_providers(prompt, parser, local_fn)
