from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ALLOWED_SOURCES

client = TestClient(app)


def _assert_no_fallback_source(body: dict) -> None:
    assert body.get("source") != "fallback"
    assert body.get("source") in ALLOWED_SOURCES


def test_explain_frontend_fields():
    response = client.post(
        "/api/accessstem/explain",
        json={"topic": "Photosynthesis", "difficulty": "beginner", "low_bandwidth": False},
    )
    assert response.status_code == 200
    body = response.json()
    _assert_no_fallback_source(body)
    assert body["topic"] == "Photosynthesis"
    assert body["explanation"]
    assert len(body["key_concepts"]) >= 3
    assert len(body["key_points"]) >= 3
    assert body["example"]
    assert body["quote"]
    assert body["check_question"]
    assert len(body["next_topics"]) >= 1


def test_quiz_frontend_shape_and_counts():
    for count in (3, 5, 7):
        response = client.post(
            "/api/accessstem/quiz",
            json={
                "topic": "Photosynthesis",
                "difficulty": "middle school",
                "question_count": count,
            },
        )
        assert response.status_code == 200
        body = response.json()
        _assert_no_fallback_source(body)
        assert body["topic"] == "Photosynthesis"
        assert body["difficulty"] == "middle school"
        assert len(body["questions"]) == count
        for question in body["questions"]:
            assert isinstance(question["id"], int)
            assert len(question["options"]) == 4
            assert question["correct_answer"] in question["options"]
            assert question["options"][question["correct"]] == question["correct_answer"]
            assert question["explanation"]
            assert question["concept"]


def test_assistant_frontend_shape():
    response = client.post(
        "/api/accessstem/assistant",
        json={
            "topic": "Photosynthesis",
            "question": "Why do plants need sunlight?",
            "difficulty": "middle school",
            "mode": "learning",
            "student_context": "FGLI STEM student",
        },
    )
    assert response.status_code == 200
    body = response.json()
    _assert_no_fallback_source(body)
    assert body["answer"]
    assert len(body["key_points"]) >= 3
    assert body["example"]
    assert len(body["next_steps"]) >= 2
    assert len(body["suggested_questions"]) >= 3


def test_hint_local_engine():
    response = client.post(
        "/api/accessstem/hint",
        json={
            "topic": "Newton's Laws",
            "question": "What does Newton's First Law describe?",
            "student_answer": "Gravity",
            "correct_answer": "Objects stay at rest or in motion unless acted on by force",
        },
    )
    assert response.status_code == 200
    body = response.json()
    _assert_no_fallback_source(body)
    assert body["reveals_answer"] is False


def test_check_answer_correct():
    response = client.post(
        "/api/accessstem/check-answer",
        json={
            "question": "What is 2+2?",
            "student_answer": "4",
            "correct_answer": "4",
            "explanation": "Basic addition.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["score_delta"] == 1


def test_progress_save_and_dashboard():
    student_id = "demo-user-test"

    client.delete(f"/api/progress?student_id={student_id}")

    save_response = client.post(
        "/api/progress",
        json={
            "student_id": student_id,
            "topic": "Photosynthesis",
            "score": 4,
            "total": 5,
        },
    )
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["saved"] is True
    assert saved["student_id"] == student_id
    assert saved["topic"] == "Photosynthesis"
    assert saved["score"] == 4
    assert saved["total"] == 5
    assert saved["percentage"] == 80

    dashboard_response = client.get(f"/api/progress/dashboard?student_id={student_id}")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["student_id"] == student_id
    assert dashboard["quizzes_taken"] >= 1
    assert dashboard["last_topic"] == "Photosynthesis"
    assert dashboard["source"] == "backend"
    assert len(dashboard["recent_scores"]) >= 1
    assert dashboard["recommended_next_topic"]

    client.delete(f"/api/progress?student_id={student_id}")
