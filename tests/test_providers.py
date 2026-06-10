import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai_engine import generate_assistant, generate_explanation, generate_quiz
from app.main import app
from app.providers import ProviderCallResult, generate_with_providers, run_provider_diagnostics

client = TestClient(app)

EXPLAIN_JSON = {
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


def _provider_side_effect(mapping: dict[str, str | None]):
    def _side_effect(provider: str, prompt: str) -> ProviderCallResult:
        if provider not in mapping:
            return ProviderCallResult(error_code="NOT_CONFIGURED")
        text = mapping[provider]
        if text is None:
            return ProviderCallResult(error_code="SAFE_CODE_ONLY")
        return ProviderCallResult(text=text)

    return _side_effect


def test_ai_status_endpoint():
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    body = response.json()
    assert body["active_strategy"] == "cohere -> openrouter -> gemini -> groq -> accessstem_local"
    assert "cohere_enabled" in body
    assert "cohere_configured" in body
    assert "cohere_model" in body


def test_ai_status_does_not_expose_secrets():
    response = client.get("/api/ai/status")
    body_text = json.dumps(response.json()).lower()
    assert "api_key" not in body_text
    assert "cohere_api" not in body_text
    assert "bearer" not in body_text


def test_provider_test_returns_safe_diagnostics():
    response = client.get("/api/ai/provider-test")
    assert response.status_code == 200
    body = response.json()
    for provider in ("cohere", "openrouter", "gemini", "groq"):
        assert "enabled" in body[provider]
        assert "configured" in body[provider]
        assert "ok" in body[provider]
        assert "error_code" in body[provider]
    body_text = json.dumps(body).lower()
    assert "api_key" not in body_text
    assert "bearer" not in body_text


def test_cohere_provider_test_success():
    with patch(
        "app.providers.try_provider_text",
        return_value=ProviderCallResult(text="provider works"),
    ):
        diagnostics = run_provider_diagnostics()

    assert diagnostics["cohere"]["ok"] is True
    assert diagnostics["cohere"]["error_code"] is None


def test_cohere_success_returns_cohere_source():
    with patch(
        "app.providers.try_provider_text",
        side_effect=_provider_side_effect({"cohere": json.dumps(EXPLAIN_JSON)}),
    ):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "cohere"
    assert "provider_attempts" not in result


def test_cohere_fail_openrouter_success_returns_openrouter_source():
    with patch(
        "app.providers.try_provider_text",
        side_effect=_provider_side_effect(
            {"cohere": None, "openrouter": json.dumps(EXPLAIN_JSON)}
        ),
    ):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "openrouter"


def test_openrouter_fail_gemini_success_returns_gemini_source():
    gemini_json = dict(EXPLAIN_JSON)
    gemini_json["explanation"] = "Gravity pulls objects toward Earth's center."

    with patch(
        "app.providers.try_provider_text",
        side_effect=_provider_side_effect(
            {"cohere": None, "openrouter": None, "gemini": json.dumps(gemini_json)}
        ),
    ):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "gemini"


def test_openrouter_gemini_fail_groq_success_returns_groq_source():
    groq_json = dict(EXPLAIN_JSON)
    groq_json["explanation"] = "Gravity is the force that attracts objects with mass."

    with patch(
        "app.providers.try_provider_text",
        side_effect=_provider_side_effect(
            {
                "cohere": None,
                "openrouter": None,
                "gemini": None,
                "groq": json.dumps(groq_json),
            }
        ),
    ):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "groq"


def test_all_providers_fail_returns_accessstem_local_with_attempts():
    with patch(
        "app.providers.try_provider_text",
        side_effect=_provider_side_effect(
            {"cohere": None, "openrouter": None, "gemini": None, "groq": None}
        ),
    ):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "accessstem_local"
    assert result["debug_reason"] == "ALL_PROVIDERS_FAILED"
    assert len(result["provider_attempts"]) == 4
    assert result["source"] != "fallback"


def test_quiz_cohere_counts_3_5_7():
    for count in (3, 5, 7):
        questions = []
        for index in range(count):
            questions.append(
                {
                    "id": f"q{index + 1}",
                    "question": f"What is part {index + 1} of Photosynthesis?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "Review photosynthesis.",
                    "concept": "Photosynthesis",
                }
            )
        payload = json.dumps(
            {
                "topic": "Photosynthesis",
                "level": "middle school",
                "questions": questions,
            }
        )

        with patch(
            "app.providers.try_provider_text",
            side_effect=_provider_side_effect({"cohere": payload}),
        ):
            result = generate_quiz("Photosynthesis", "middle school", count)

        assert result["source"] == "cohere"
        assert len(result["questions"]) == count
        for question in result["questions"]:
            assert question["correct_answer"] in question["options"]


def test_quiz_malformed_json_keeps_cohere_source():
    malformed = """```json
{
  "topic": "Photosynthesis",
  "level": "middle school",
  "questions": [
    {
      "id": "q1",
      "question": "What is Photosynthesis?",
      "options": ["Light energy", "Heat only", "Sound", "Magnetism"],
      "correct_answer": "Light energy",
      "explanation": "Plants use light.",
      "concept": "Photosynthesis"
    },
  ]
}
```"""

    with patch(
        "app.providers.try_provider_text",
        side_effect=_provider_side_effect({"cohere": malformed}),
    ):
        result = generate_quiz("Photosynthesis", "middle school", 3)

    assert result["source"] == "cohere"
    assert len(result["questions"]) == 3


def test_no_secrets_exposed_in_responses():
    with patch(
        "app.providers.try_provider_text",
        side_effect=_provider_side_effect(
            {"cohere": None, "openrouter": None, "gemini": None, "groq": None}
        ),
    ):
        result = generate_explanation("Chemistry", "beginner", False)

    response_text = json.dumps(result).lower()
    assert "api_key" not in response_text
    assert "cohere_api" not in response_text
    assert "bearer" not in response_text


def test_generate_with_providers_parser_error_tries_next_provider():
    calls: list[str] = []

    def fake_try(provider: str, prompt: str) -> ProviderCallResult:
        calls.append(provider)
        if provider == "cohere":
            return ProviderCallResult(text='{"bad": "data"}')
        if provider == "openrouter":
            return ProviderCallResult(text='{"value": 1}')
        return ProviderCallResult(error_code="SAFE_CODE_ONLY")

    def parser(text: str, source: str) -> dict:
        data = json.loads(text)
        if "value" not in data:
            raise ValueError("unusable")
        return {"value": data["value"]}

    with patch("app.providers.try_provider_text", side_effect=fake_try):
        result = generate_with_providers("prompt", parser, lambda: {"value": 0})

    assert result["source"] == "openrouter"
    assert calls[:2] == ["cohere", "openrouter"]


def test_no_endpoint_returns_fallback_source():
    endpoints = [
        (
            "/api/accessstem/explain",
            {"topic": "Algebra basics", "difficulty": "beginner", "low_bandwidth": False},
        ),
        (
            "/api/accessstem/quiz",
            {"topic": "Photosynthesis", "difficulty": "middle school", "question_count": 5},
        ),
        (
            "/api/accessstem/assistant",
            {
                "topic": "Newton's Laws",
                "question": "Explain with an example",
                "difficulty": "beginner",
                "mode": "learning",
                "student_context": "",
            },
        ),
        (
            "/api/accessstem/review-quiz",
            {
                "topic": "Photosynthesis",
                "difficulty": "beginner",
                "score": 3,
                "total": 5,
                "weak_concepts": ["chlorophyll"],
            },
        ),
        (
            "/api/accessstem/recommend-next",
            {
                "topic": "Photosynthesis",
                "difficulty": "beginner",
                "completed_topics": ["Cells"],
                "score": 4,
                "total": 5,
            },
        ),
    ]

    for path, payload in endpoints:
        response = client.post(path, json=payload)
        assert response.status_code == 200
        assert response.json()["source"] != "fallback"
