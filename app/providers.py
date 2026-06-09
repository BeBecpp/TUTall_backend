"""AI provider layer: OpenRouter -> Gemini -> Groq -> AccessSTEM Local Engine."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from google import genai

from app.config import get_settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = "You are AccessSTEM AI, a helpful STEM learning assistant for students."
OPENROUTER_HTTP_REFERER = "https://bebecpp.github.io/TUTall_frontend/"
OPENROUTER_APP_TITLE = "TUTall AccessSTEM AI"
REQUEST_TIMEOUT = 45.0
PROVIDER_ORDER = ("openrouter", "gemini", "groq")
PROVIDER_TEST_PROMPT = "Say only: provider works"

SOURCE_OPENROUTER = "openrouter"
SOURCE_GEMINI = "gemini"
SOURCE_GROQ = "groq"
SOURCE_LOCAL = "accessstem_local"


@dataclass
class ProviderCallResult:
    text: str | None = None
    error_code: str | None = None


def _safe_error_code(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in {401, 403, 429, 500, 502, 503}:
            return "RESTRICTED_OR_HTTP_ERROR"
        return "RESTRICTED_OR_HTTP_ERROR"
    message = str(exc).lower()
    if "empty" in message:
        return "EMPTY_RESPONSE"
    if "not configured" in message:
        return "NOT_CONFIGURED"
    return "SAFE_CODE_ONLY"


def _provider_enabled(provider: str) -> bool:
    settings = get_settings()
    if provider == "openrouter":
        return settings.openrouter_enabled
    if provider == "gemini":
        return settings.gemini_enabled
    if provider == "groq":
        return settings.groq_enabled
    return False


def _provider_configured(provider: str) -> bool:
    settings = get_settings()
    if provider == "openrouter":
        return settings.openrouter_configured
    if provider == "gemini":
        return settings.gemini_configured
    if provider == "groq":
        return settings.groq_configured
    return False


def call_openrouter_text(prompt: str) -> str:
    settings = get_settings()
    if not settings.openrouter_configured:
        raise RuntimeError("OpenRouter is not configured")

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
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


def call_gemini_text(prompt: str) -> str:
    settings = get_settings()
    if not settings.gemini_configured:
        raise RuntimeError("Gemini is not configured")

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Empty Gemini response")
    return text


def call_groq_text(prompt: str) -> str:
    settings = get_settings()
    if not settings.groq_configured:
        raise RuntimeError("Groq is not configured")

    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Empty Groq response")

    text = str(choices[0].get("message", {}).get("content", "")).strip()
    if not text:
        raise RuntimeError("Empty Groq response text")
    return text


def try_provider_text(provider: str, prompt: str) -> ProviderCallResult:
    if not _provider_enabled(provider):
        return ProviderCallResult(error_code="NOT_ENABLED")

    if not _provider_configured(provider):
        return ProviderCallResult(error_code="NOT_CONFIGURED")

    try:
        if provider == "openrouter":
            return ProviderCallResult(text=call_openrouter_text(prompt))
        if provider == "gemini":
            return ProviderCallResult(text=call_gemini_text(prompt))
        if provider == "groq":
            return ProviderCallResult(text=call_groq_text(prompt))
        return ProviderCallResult(error_code="NOT_CONFIGURED")
    except Exception as exc:
        logger.warning("%s call failed: %s", provider.capitalize(), type(exc).__name__)
        return ProviderCallResult(error_code=_safe_error_code(exc))


def _apply_local_result(
    local_fn: Callable[[], dict[str, Any]],
    provider_attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    result = local_fn()
    result["source"] = SOURCE_LOCAL
    result["debug_reason"] = "ALL_PROVIDERS_FAILED"
    result["provider_attempts"] = provider_attempts
    return result


def generate_with_providers(
    prompt: str,
    parser: Callable[[str, str], dict[str, Any]],
    local_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Try OpenRouter, Gemini, Groq, then AccessSTEM Local Engine."""
    provider_attempts: list[dict[str, Any]] = []

    for provider in PROVIDER_ORDER:
        if not _provider_enabled(provider):
            provider_attempts.append(
                {"provider": provider, "ok": False, "error_code": "NOT_ENABLED"}
            )
            continue

        if not _provider_configured(provider):
            provider_attempts.append(
                {"provider": provider, "ok": False, "error_code": "NOT_CONFIGURED"}
            )
            continue

        call_result = try_provider_text(provider, prompt)
        if not call_result.text:
            provider_attempts.append(
                {
                    "provider": provider,
                    "ok": False,
                    "error_code": call_result.error_code or "SAFE_CODE_ONLY",
                }
            )
            continue

        try:
            result = parser(call_result.text, provider)
            result["source"] = provider
            result.pop("debug_reason", None)
            result.pop("provider_attempts", None)
            return result
        except Exception as exc:
            logger.warning("%s output unusable: %s", provider.capitalize(), type(exc).__name__)
            provider_attempts.append(
                {"provider": provider, "ok": False, "error_code": "OUTPUT_UNUSABLE"}
            )

    return _apply_local_result(local_fn, provider_attempts)


def generate_text_with_providers(
    prompt: str,
    parser: Callable[[str, str], dict[str, Any]],
    local_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    return generate_with_providers(prompt, parser, local_fn)


def diagnose_provider(provider: str, prompt: str = PROVIDER_TEST_PROMPT) -> dict[str, Any]:
    enabled = _provider_enabled(provider)
    configured = _provider_configured(provider)

    if not enabled:
        return {
            "enabled": False,
            "configured": configured,
            "ok": False,
            "error_code": "NOT_ENABLED",
        }

    if not configured:
        return {
            "enabled": True,
            "configured": False,
            "ok": False,
            "error_code": "NOT_CONFIGURED",
        }

    call_result = try_provider_text(provider, prompt)
    if call_result.text and "provider works" in call_result.text.lower():
        return {
            "enabled": True,
            "configured": True,
            "ok": True,
            "error_code": None,
        }

    return {
        "enabled": True,
        "configured": True,
        "ok": False,
        "error_code": call_result.error_code or "SAFE_CODE_ONLY",
    }


def run_provider_diagnostics() -> dict[str, dict[str, Any]]:
    return {
        "openrouter": diagnose_provider("openrouter"),
        "gemini": diagnose_provider("gemini"),
        "groq": diagnose_provider("groq"),
    }
