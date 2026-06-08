import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai_engine import generate_assistant, generate_explanation
from app.main import app
from app.providers import generate_with_providers

client = TestClient(app)


def test_health_includes_provider_flags():
    response = client.get("/health")
    body = response.json()
    assert "gemini_configured" in body
    assert "groq_configured" in body
    assert "ai_configured" in body


def test_groq_used_when_gemini_fails():
    groq_json = json.dumps(
        {
            "topic": "Gravity",
            "level": "beginner",
            "explanation": "Gravity is a force that pulls objects toward Earth.",
            "example": "An apple falling from a tree shows gravity.",
            "key_points": [
                "Gravity pulls objects toward mass",
                "Earth's gravity keeps us on the ground",
                "Gravity depends on distance and mass",
            ],
            "check_question": "What does gravity do to objects?",
            "next_topics": ["Mass and weight", "Orbital motion"],
            "safety_note": "AI-generated learning support. Verify important information.",
        }
    )

    with patch("app.providers.try_provider_text") as mock_try:
        mock_try.side_effect = lambda provider, prompt: (
            None if provider == "gemini" else groq_json
        )
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "groq"
    assert "gravity" in result["explanation"].lower()


def test_fallback_when_both_providers_fail():
    with patch("app.providers.try_provider_text", return_value=None):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "fallback"


def test_assistant_groq_plain_text_converted():
    groq_plain = (
        "Gravity pulls objects toward Earth. The more mass an object has, "
        "the stronger its gravitational pull."
    )

    with patch("app.providers.try_provider_text") as mock_try:
        mock_try.side_effect = lambda provider, prompt: (
            None if provider == "gemini" else groq_plain
        )
        result = generate_assistant(
            "Gravity",
            "Explain with an example",
            "beginner",
            "learning",
            "high school student",
        )

    assert result["source"] == "groq"
    assert result["answer"]
    assert len(result["key_points"]) >= 3
    assert result["suggested_questions"]


def test_assistant_gemini_plain_text_converted():
    gemini_plain = "Newton's First Law says objects keep moving unless a force acts on them."

    with patch("app.providers.try_provider_text") as mock_try:
        mock_try.side_effect = lambda provider, prompt: (
            gemini_plain if provider == "gemini" else None
        )
        result = generate_assistant(
            "Newton's Laws",
            "What is inertia?",
            "beginner",
            "learning",
            "",
        )

    assert result["source"] == "gemini"
    assert "newton" in result["answer"].lower() or "inertia" in result["answer"].lower()


def test_no_secrets_exposed_in_responses():
    with patch("app.providers.try_provider_text", return_value=None):
        result = generate_explanation("Chemistry", "beginner", False)

    response_text = json.dumps(result).lower()
    assert "api_key" not in response_text
    assert "groq_api" not in response_text
    assert "gemini_api" not in response_text
    assert "bearer" not in response_text


def test_generate_with_providers_parser_error_tries_next():
    calls: list[str] = []

    def fake_try(provider: str, prompt: str) -> str | None:
        calls.append(provider)
        return '{"bad": "data"}' if provider == "gemini" else '{"topic": "ok", "value": 1}'

    def parser(text: str, source: str) -> dict:
        data = json.loads(text)
        if "value" not in data:
            raise ValueError("unusable")
        return {"value": data["value"]}

    with patch("app.providers.try_provider_text", side_effect=fake_try):
        result = generate_with_providers("prompt", parser, lambda: {"value": 0})

    assert result["source"] == "groq"
    assert calls == ["gemini", "groq"]
