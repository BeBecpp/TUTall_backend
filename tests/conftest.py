import pytest

from app.providers import ProviderCallResult
from app.storage import reset_storage


@pytest.fixture(autouse=True)
def isolated_storage():
    reset_storage(force_memory=True)
    yield
    reset_storage(force_memory=True)


@pytest.fixture(autouse=True)
def disable_live_ai_providers(monkeypatch):
    """Integration tests use local engine unless a test mocks providers explicitly."""

    def _disabled(_provider: str, _prompt: str) -> ProviderCallResult:
        return ProviderCallResult(error_code="NOT_CONFIGURED")

    monkeypatch.setattr("app.providers.try_provider_text", _disabled)
