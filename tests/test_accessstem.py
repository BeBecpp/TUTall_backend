from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_explain_local_engine():
    response = client.post(
        "/api/accessstem/explain",
        json={"topic": "Algebra basics", "difficulty": "beginner", "low_bandwidth": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "Algebra basics"
    assert body["source"] == "accessstem_local"
    assert body.get("debug_reason")
    assert body.get("provider_attempts")
    assert len(body["key_points"]) >= 3
    assert body["safety_note"]


def test_quiz_local_engine_respects_question_count():
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
        assert body["source"] == "accessstem_local"
        assert body.get("debug_reason")
        assert body.get("provider_attempts")
        assert len(body["questions"]) == count
        for question in body["questions"]:
            assert len(question["options"]) == 4
            assert question["correct_answer"] in question["options"]
            assert "Photosynthesis" in question["question"] or question["concept"]


def test_assistant_local_engine_shape():
    response = client.post(
        "/api/accessstem/assistant",
        json={
            "topic": "Newton's Laws",
            "question": "Can you explain this with an example?",
            "difficulty": "beginner",
            "mode": "learning",
            "student_context": "high school student preparing for quiz",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "Newton's Laws"
    assert body["source"] == "accessstem_local"
    assert body.get("debug_reason")
    assert body.get("provider_attempts")
    assert body["answer"]
    assert len(body["key_points"]) >= 3
    assert body["example"]
    assert len(body["next_steps"]) >= 2
    assert len(body["suggested_questions"]) >= 3
    assert body["safety_note"]


def test_newton_explain_local_engine_is_topic_specific():
    response = client.post(
        "/api/accessstem/explain",
        json={"topic": "Newton's Laws", "difficulty": "beginner", "low_bandwidth": False},
    )
    body = response.json()
    assert "inertia" in body["explanation"].lower() or "newton" in body["explanation"].lower()


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
    assert body["source"] == "accessstem_local"
    assert body.get("debug_reason")
    assert body.get("provider_attempts")
    assert body["reveals_answer"] is False
    assert "hint" in body
    assert "encouragement" in body


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


def test_check_answer_incorrect():
    response = client.post(
        "/api/accessstem/check-answer",
        json={
            "question": "What is 2+2?",
            "student_answer": "5",
            "correct_answer": "4",
            "explanation": "Try counting again.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is False
    assert body["score_delta"] == 0


def test_study_plan_local_engine():
    response = client.post(
        "/api/accessstem/study-plan",
        json={
            "goal": "Improve algebra and physics",
            "grade_level": "high school",
            "available_days": 3,
            "weak_topics": ["linear equations", "forces"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "accessstem_local"
    assert body.get("debug_reason")
    assert body.get("provider_attempts")
    assert len(body["days"]) == 3
    assert body["days"][0]["tasks"]
    assert "linear equations" in body["days"][0]["focus"].lower() or "forces" in body["days"][1]["focus"].lower()


def test_progress_save_list_delete():
    student_id = "demo-user-test"

    client.delete(f"/api/progress?student_id={student_id}")

    save_response = client.post(
        "/api/progress",
        json={
            "student_id": student_id,
            "topic": "Newton's Laws",
            "score": 4,
            "total": 5,
        },
    )
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["saved"] is True
    assert saved["item"]["percentage"] == 80

    list_response = client.get(f"/api/progress?student_id={student_id}")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed["items"]) >= 1
    assert listed["average_percentage"] == 80

    delete_response = client.delete(f"/api/progress?student_id={student_id}")
    assert delete_response.json()["deleted"] is True
