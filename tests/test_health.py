from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "TUTall" in response.json()["message"]


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "TUTall Backend"
    assert body["version"] == "1.0.0"
    assert "ai_configured" in body
    assert "gemini_configured" in body
    assert "groq_configured" in body
    assert "database_configured" in body


def test_meta():
    response = client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["core_engine"] == "AccessSTEM AI"
    assert "STEM explanation" in body["features"]


def test_security_headers():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
    assert response.headers.get("X-Request-ID")


def test_cors_allows_github_pages_and_localhost():
    from app.config import get_settings

    origins = get_settings().cors_origins
    assert "https://ajays22-orgs.github.io" in origins
    assert "https://ajays22-orgs.github.io/TUTall" in origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:5500" in origins
