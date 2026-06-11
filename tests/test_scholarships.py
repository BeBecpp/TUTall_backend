from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ALLOWED_SOURCES

client = TestClient(app)


def test_scholarship_match_frontend_fields():
    response = client.post(
        "/api/scholarships/match",
        json={
            "gpa": 3.7,
            "country": "USA",
            "intended_major": "Computer Science",
            "major": "cs",
            "first_generation": True,
            "financial_need": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] in ALLOWED_SOURCES
    assert body["source"] != "fallback"
    assert body["fit_score"] == body["readiness_score"]
    assert body["summary"]
    assert body["strengths"]
    assert body["improvements"]
    assert len(body["recommended_scholarships"]) >= 1
    assert body["recommended_scholarships"][0]["name"]
    assert body["recommended_scholarships"][0]["fit"] in {"High", "Medium", "Low"}
    assert body["required_documents"]
    assert body["next_steps"]
    assert "guarantee" in body["disclaimer"].lower()
    assert "COHERE_API_KEY" not in str(body)


def test_scholarship_match_legacy_fields():
    response = client.post(
        "/api/scholarships/match",
        json={
            "grade_level": "11",
            "gpa": 3.8,
            "country": "Mongolia",
            "intended_major": "Computer Science",
            "english_level": "B2",
            "financial_need": "high",
            "activities": "Hackathons, coding club",
            "has_essay": False,
            "has_english_test": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["readiness_score"] >= 0
    assert body["fit_score"] >= 0
