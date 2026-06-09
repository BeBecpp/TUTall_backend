import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai_engine import generate_assistant, generate_explanation, generate_quiz
from app.main import app
from app.providers import generate_with_providers

client = TestClient(app)


def test_ai_status_endpoint():
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    body = response.json()
    assert "openrouter_configured" in body
    assert "openrouter_enabled" in body
    assert "gemini_enabled" in body
    assert "groq_enabled" in body
    assert body["active_strategy"] == "openrouter -> accessstem_local"


def test_ai_status_does_not_expose_secrets():
    response = client.get("/api/ai/status")
    body_text = json.dumps(response.json()).lower()
    assert "api_key" not in body_text
    assert "openrouter_api" not in body_text
    assert "bearer" not in body_text
    assert "sk-" not in body_text


def test_openrouter_success_returns_openrouter_source():
    openrouter_json = json.dumps(
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

    with patch("app.providers.try_openrouter_text", return_value=openrouter_json):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "openrouter"
    assert "debug_reason" not in result
    assert "gravity" in result["explanation"].lower()


def test_openrouter_failure_returns_accessstem_local():
    with patch("app.providers.try_openrouter_text", return_value=None):
        result = generate_explanation("Gravity", "beginner", False)

    assert result["source"] == "accessstem_local"
    assert result["debug_reason"]
    assert result["source"] != "fallback"


def test_assistant_openrouter_plain_text_converted():
    openrouter_plain = (
        "Gravity pulls objects toward Earth. The more mass an object has, "
        "the stronger its gravitational pull."
    )

    with patch("app.providers.try_openrouter_text", return_value=openrouter_plain):
        result = generate_assistant(
            "Gravity",
            "Explain with an example",
            "beginner",
            "learning",
            "high school student",
        )

    assert result["source"] == "openrouter"
    assert result["answer"]
    assert len(result["key_points"]) >= 3
    assert result["suggested_questions"]


def test_quiz_openrouter_counts_3_5_7():
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

        with patch("app.providers.try_openrouter_text", return_value=payload):
            result = generate_quiz("Photosynthesis", "middle school", count)

        assert result["source"] == "openrouter"
        assert len(result["questions"]) == count
        for question in result["questions"]:
            assert question["correct_answer"] in question["options"]


def test_no_secrets_exposed_in_responses():
    with patch("app.providers.try_openrouter_text", return_value=None):
        result = generate_explanation("Chemistry", "beginner", False)

    response_text = json.dumps(result).lower()
    assert "api_key" not in response_text
    assert "openrouter_api" not in response_text
    assert "bearer" not in response_text
    assert "sk-" not in response_text


def test_generate_with_providers_parser_error_uses_local_engine():
    def parser(text: str, source: str) -> dict:
        data = json.loads(text)
        if "value" not in data:
            raise ValueError("unusable")
        return {"value": data["value"]}

    with patch("app.providers.try_openrouter_text", return_value='{"bad": "data"}'):
        result = generate_with_providers("prompt", parser, lambda: {"value": 0})

    assert result["source"] == "accessstem_local"
    assert result["debug_reason"] == "openrouter_output_unusable"
    assert result["value"] == 0


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
    ]

    for path, payload in endpoints:
        response = client.post(path, json=payload)
        assert response.status_code == 200
        assert response.json()["source"] != "fallback"
