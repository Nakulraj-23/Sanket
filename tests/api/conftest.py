"""Shared fixtures: one app with a temporary database per test module."""
import pytest
from fastapi.testclient import TestClient

from sanket.api.app import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """A TestClient on a fresh temporary SQLite file (models load once per module)."""
    db = tmp_path_factory.mktemp("db") / "t.db"
    mp = pytest.MonkeyPatch()
    mp.setenv("SANKET_DB_URL", f"sqlite:///{db}")
    with TestClient(create_app()) as c:
        yield c
    mp.undo()
