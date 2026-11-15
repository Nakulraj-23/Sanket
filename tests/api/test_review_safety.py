"""Free-text fields are redacted, reserved channels refused, reviewed tickets survive the cap."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from sanket.api.app import create_app

SECRETS = ("4111 1111 1111 1111", "zara.khan", "98123")


def ticket(c) -> int:
    """Post a ticket, return its id."""
    return c.post("/api/tickets", json={"text": "my card was stolen"}).json()["ticket_id"]


def test_note_and_reviewer_are_redacted_everywhere(client, tmp_path):
    tid = ticket(client)
    body = {"reviewer": "zara.khan@example.org", "action": "confirm",
            "note": "card 4111 1111 1111 1111,\n+91 98123 45679"}
    r = client.post(f"/api/tickets/{tid}/review", json=body)
    assert r.status_code == 200
    shown = r.text + client.get(f"/api/tickets/{tid}").text
    with client.app.state.runtime.engine.connect() as conn:
        conn.execute(text("PRAGMA wal_checkpoint(PASSIVE)"))
        rows = str(list(conn.execute(text("select reviewer, note from reviews"))))
    files = ""
    db_file = client.app.state.runtime.engine.url.database
    for suffix in ("", "-wal", "-shm"):
        path = Path(db_file + suffix)
        files += path.read_bytes().decode("latin-1") if path.exists() else ""
    for secret in SECRETS:
        assert secret not in shown and secret not in rows and secret not in files
    assert "[CARD]" in shown and "[EMAIL]" in shown


@pytest.mark.parametrize("reviewer", ["", "   ", "x" * 65])
def test_bad_reviewer_is_422(client, reviewer):
    tid = ticket(client)
    r = client.post(f"/api/tickets/{tid}/review", json={"reviewer": reviewer, "action": "confirm"})
    assert r.status_code == 422


def test_long_note_is_422(client):
    tid = ticket(client)
    body = {"reviewer": "a", "action": "confirm", "note": "n" * 1001}
    assert client.post(f"/api/tickets/{tid}/review", json=body).status_code == 422


@pytest.mark.parametrize("channel", ["seed", "scenario"])
def test_reserved_channels_refused(client, channel):
    r = client.post("/api/tickets", json={"text": "hello card", "channel": channel})
    assert r.status_code == 422


def test_cap_never_deletes_reviewed_tickets(tmp_path, monkeypatch):
    monkeypatch.setenv("SANKET_DB_URL", f"sqlite:///{tmp_path / 'cap.db'}")
    monkeypatch.setenv("SANKET_MAX_TICKETS", "10")
    with TestClient(create_app()) as c:
        first = ticket(c)
        c.post(f"/api/tickets/{first}/review", json={"reviewer": "alice", "action": "confirm"})
        for _ in range(15):
            ticket(c)
        assert c.get(f"/api/tickets/{first}").json()["review"]["reviewer"] == "alice"
        assert c.get("/api/health").json()["tickets"] <= 11
