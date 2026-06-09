import pytest

from app.storage import reset_storage


@pytest.fixture(autouse=True)
def isolated_storage():
    reset_storage(force_memory=True)
    yield
    reset_storage(force_memory=True)


@pytest.fixture(autouse=True)
def disable_live_ai_providers(monkeypatch):
    """Integration tests use local engine unless a test mocks OpenRouter explicitly."""
    monkeypatch.setattr("app.providers.try_openrouter_text", lambda prompt: None)
