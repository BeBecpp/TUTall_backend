from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_scholarship_match():
    response = client.post(
        "/api/scholarships/match",
        json={
            "grade_level": "11",
            "gpa": 3.8,
            "country": "Mongolia",
            "intended_major": "Computer Science",
            "english_level": "B2",
            "financial_need": "high",
            "activities": "Hackathons, coding club, volunteer teaching",
            "has_essay": False,
            "has_english_test": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["overall_readiness_score"] >= 0
    assert len(body["matches"]) >= 1
    assert body["advisor"]["warning"]
    assert body["source"] in {"accessstem_local", "openrouter"}
    assert "does not guarantee" in body["advisor"]["warning"].lower()
