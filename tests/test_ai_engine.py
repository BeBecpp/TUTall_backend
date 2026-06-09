import json

import pytest

from app.ai_engine import (
    _build_quiz_response,
    _ensure_no_guarantee,
    _extract_json,
    _hint_reveals_answer,
    _is_generic_explanation,
    _resolve_correct_answer,
)


def test_extract_json_plain():
    data = _extract_json('{"topic": "Physics", "level": "beginner"}')
    assert data["topic"] == "Physics"


def test_extract_json_with_markdown_fence():
    raw = """Here is the quiz:
```json
{"topic": "Math", "questions": []}
```
Hope that helps."""
    data = _extract_json(raw)
    assert data["topic"] == "Math"


def test_extract_json_with_extra_text():
    raw = 'Sure! {"topic": "Biology", "level": "high school", "source": "gemini"} Done.'
    data = _extract_json(raw)
    assert data["topic"] == "Biology"


def test_extract_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        _extract_json("No JSON here at all.")


def test_resolve_correct_answer_exact_and_fuzzy():
    options = [
        "Understand the main idea",
        "Memorize random facts",
        "Skip examples",
        "Avoid practice",
    ]
    assert _resolve_correct_answer("Understand the main idea", options) == options[0]
    assert _resolve_correct_answer("A) Understand the main idea", options) == options[0]
    assert _resolve_correct_answer("understand the main idea", options) == options[0]


def test_build_quiz_response_exact_count():
    payload = {
        "topic": "Chemistry",
        "level": "beginner",
        "questions": [
            {
                "id": "q1",
                "question": "What is H2O?",
                "options": ["Water", "Oxygen", "Hydrogen", "Salt"],
                "correct_answer": "Water",
                "explanation": "H2O is water.",
                "concept": "Chemistry basics",
            },
            {
                "id": "q2",
                "question": "What is NaCl?",
                "options": ["Salt", "Sugar", "Water", "Iron"],
                "correct_answer": "Salt",
                "explanation": "NaCl is table salt.",
                "concept": "Chemistry basics",
            },
            {
                "id": "q3",
                "question": "What is CO2?",
                "options": ["Carbon dioxide", "Water", "Oxygen", "Helium"],
                "correct_answer": "Carbon dioxide",
                "explanation": "CO2 is carbon dioxide.",
                "concept": "Chemistry basics",
            },
        ],
    }
    result = _build_quiz_response(payload, "Chemistry", "beginner", 3, "openrouter")
    assert len(result["questions"]) == 3
    assert result["source"] == "openrouter"
    for question in result["questions"]:
        assert len(question["options"]) == 4
        assert question["correct_answer"] in question["options"]


def test_build_quiz_response_repairs_short_count():
    payload = {
        "topic": "Chemistry",
        "level": "beginner",
        "questions": [
            {
                "id": "q1",
                "question": "What is H2O?",
                "options": ["Water", "Oxygen", "Hydrogen", "Salt"],
                "correct_answer": "Water",
                "explanation": "H2O is water.",
                "concept": "Chemistry basics",
            }
        ],
    }
    result = _build_quiz_response(payload, "Chemistry", "beginner", 3, "accessstem_local")
    assert len(result["questions"]) == 3
    assert result["source"] == "accessstem_local"


def test_is_generic_explanation_detects_generic_text():
    assert _is_generic_explanation(
        "Gravity",
        "This can be learned step by step by understanding the main idea.",
    )


def test_hint_reveals_answer_detection():
    assert _hint_reveals_answer(
        "Think about objects staying at rest unless acted on by force",
        "Objects stay at rest or in motion unless acted on by force",
    )


def test_ensure_no_guarantee_sanitizes_risky_text():
    safe = _ensure_no_guarantee("You are guaranteed acceptance to this scholarship.")
    assert "does not guarantee" in safe.lower()
