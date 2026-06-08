"""AI provider layer: Gemini (primary) -> Groq (secondary) -> fallback."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
from google import genai

from app.config import get_settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_SYSTEM_PROMPT = "You are AccessSTEM AI, a helpful STEM learning assistant."
REQUEST_TIMEOUT = 45.0


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
            {"role": "system", "content": GROQ_SYSTEM_PROMPT},
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


def try_provider_text(provider: str, prompt: str) -> str | None:
    settings = get_settings()
    if provider == "gemini" and not settings.gemini_configured:
        return None
    if provider == "groq" and not settings.groq_configured:
        return None

    try:
        if provider == "gemini":
            return call_gemini_text(prompt)
        return call_groq_text(prompt)
    except Exception as exc:
        logger.warning("%s call failed: %s", provider.capitalize(), type(exc).__name__)
        return None


def generate_with_providers(
    prompt: str,
    parser: Callable[[str, str], dict[str, Any]],
    fallback_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Try Gemini, then Groq, then fallback. Parser receives (text, source)."""
    for source in ("gemini", "groq"):
        text = try_provider_text(source, prompt)
        if not text:
            continue
        try:
            result = parser(text, source)
            result["source"] = source
            return result
        except Exception as exc:
            logger.warning("%s output unusable: %s", source.capitalize(), type(exc).__name__)

    fallback = fallback_fn()
    fallback["source"] = "fallback"
    return fallback


def generate_text_with_providers(
    prompt: str,
    parser: Callable[[str, str], dict[str, Any]],
    fallback_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Alias for plain-text endpoints like hint."""
    return generate_with_providers(prompt, parser, fallback_fn)
