from fastapi.testclient import TestClient

from app.application import app

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
    assert "cohere_configured" in body
    assert "openrouter_configured" in body
    assert "database_configured" in body
    assert "environment" in body
    assert "COHERE_API_KEY" not in str(body)
    assert "api_key" not in str(body).lower()


def test_ai_status():
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    body = response.json()
    assert body["active_strategy"] == "cohere -> openrouter -> gemini -> groq -> accessstem_local"
    assert "cohere_enabled" in body
    assert "gemini_configured" in body
    assert "groq_configured" in body
    assert "cohere_model" not in body


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


def test_cors_allows_frontend_origins():
    from app.config import get_settings

    origins = get_settings().cors_origins
    assert "https://tutall.vercel.app" in origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:3000" in origins


def test_api_index_import():
    from api.index import app as api_app

    assert api_app is not None


def test_app_application_import():
    from app.application import app as application_app

    assert application_app is not None


def test_app_main_shim_import():
    from app.main import app as shim_app

    assert shim_app is not None


def test_startup_debug_endpoint():
    response = client.get("/api/debug/startup")
    assert response.status_code == 200
    body = response.json()
    assert body["startup_ok"] is True
    assert "api_key" not in str(body).lower()
