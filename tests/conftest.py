import pytest

from app.storage import reset_storage


@pytest.fixture(autouse=True)
def isolated_storage():
    reset_storage(force_memory=True)
    yield
    reset_storage(force_memory=True)


@pytest.fixture(autouse=True)
def disable_live_ai_providers(monkeypatch):
    """Integration tests use fallback unless a test mocks providers explicitly."""
    monkeypatch.setattr("app.providers.try_provider_text", lambda provider, prompt: None)
