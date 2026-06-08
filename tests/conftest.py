import pytest

from app.storage import reset_storage


@pytest.fixture(autouse=True)
def isolated_storage():
    reset_storage(force_memory=True)
    yield
    reset_storage(force_memory=True)
