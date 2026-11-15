"""Q3 system audit checks. Strict xfails are open findings (docs/handoffs/Q3.md); they flip when fixed."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from sanket.api.app import create_app


def db_dump(client) -> str:
    """Every cell of every table, as one lower-case string."""
    rt = client.app.state.runtime
    with rt.engine.connect() as conn:
        names = [t[0] for t in conn.execute(text("select name from sqlite_master where type='table'"))]
        rows = [[str(c) for c in row] for n in names for row in conn.execute(text(f"select * from {n}"))]
    return json.dumps(rows, ensure_ascii=False).lower()


def new_ticket(client, body: str = "my card was stolen yesterday") -> int:
    """Post one ticket and return its id."""
    r = client.post("/api/tickets", json={"text": body})
    assert r.status_code == 201
    return r.json()["ticket_id"]


# Formats that are masked today: they must stay masked.
MASKED = [
    ("card 5500-0000-0000-0004 charged twice", "5500000000000004"),
    ("card ４１１１ １１１１ １１１１ １１１１ lost", "4111 1111 1111 1111"),
    ("कार्ड ४१११ ११११ ११११ ११११ खो गया", "4111 1111 1111 1111"),
    ("mail Rahul.Sharma+bank@Gmail.COM", "rahul.sharma+bank"),
    ("call +91-98765-43210 now", "98765"),
    ("iban GB82 WEST 1234 5698 7654 32 failed", "gb82 west"),
    ("contact amit (at) outlook.com", "amit"),
]


@pytest.mark.parametrize("raw,secret", MASKED)
def test_masked_formats_never_stored(client, raw, secret):
    new_ticket(client, raw)
    assert secret not in db_dump(client)


@pytest.mark.parametrize("sep", ["\n", "\t", "\r\n"])
def test_card_split_by_line_breaks_is_masked(client, sep):
    new_ticket(client, f"card 4012{sep}8888{sep}8888{sep}1881 was stolen")
    assert "4012 8888 8888 1881" not in db_dump(client)



@pytest.mark.parametrize("sep", ["_", "\u2013", ",", " , "])
def test_card_split_by_punctuation_is_masked(client, sep):
    new_ticket(client, f"card 4012{sep}8888{sep}8888{sep}1881 was stolen")
    assert "4012" + sep.lower() + "8888" not in db_dump(client)


def test_review_note_is_redacted(client):
    tid = new_ticket(client)
    note = "customer card 4111 1111 1111 1111, mail zara.khan@example.org"
    r = client.post(f"/api/tickets/{tid}/review", json={"reviewer": "q3", "action": "confirm", "note": note})
    assert r.status_code == 200
    dump = db_dump(client)
    assert "4111 1111 1111 1111" not in dump and "zara.khan" not in dump


def test_empty_reviewer_refused(client):
    tid = new_ticket(client)
    r = client.post(f"/api/tickets/{tid}/review", json={"reviewer": " ", "action": "confirm"})
    assert r.status_code == 422


def test_lone_surrogate_is_a_clean_error(client):
    r = client.post("/api/tickets", content=b'{"text": "card lost \\ud800 now"}',
                    headers={"content-type": "application/json"})
    assert r.status_code in (201, 422)


def test_ten_reviewers_one_ticket_exactly_one_wins(client):
    tid = new_ticket(client, "i am not sure what this charge is")
    barrier = Barrier(10)

    def go(k: int) -> int:
        barrier.wait()
        body = {"reviewer": f"r{k}", "action": "override", "final_intent": "card_arrival"}
        return client.post(f"/api/tickets/{tid}/review", json=body).status_code

    with ThreadPoolExecutor(10) as pool:
        codes = sorted(pool.map(go, range(10)))
    assert codes == [200] + [409] * 9
    assert client.get(f"/api/tickets/{tid}").json()["review"]["reviewer"].startswith("r")


def test_no_route_edits_reviews_or_trains(client):
    tid = new_ticket(client)
    for method in ("PUT", "PATCH", "DELETE"):
        assert client.request(method, f"/api/tickets/{tid}/review").status_code == 405
        assert client.request(method, f"/api/tickets/{tid}").status_code == 405
    for path in ("/api/retrain", "/api/train", "/api/model/promote"):
        assert client.post(path).status_code == 404


def test_cors_refuses_unknown_origin(client):
    r = client.options("/api/tickets", headers={"Origin": "https://evil.example",
                                                "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


@pytest.fixture
def capped(tmp_path, monkeypatch):
    """An app whose ticket cap is 10."""
    monkeypatch.setenv("SANKET_DB_URL", f"sqlite:///{tmp_path / 'cap.db'}")
    monkeypatch.setenv("SANKET_MAX_TICKETS", "10")
    with TestClient(create_app()) as c:
        yield c


def test_cap_keeps_reviews(capped):
    tid = new_ticket(capped)
    capped.post(f"/api/tickets/{tid}/review", json={"reviewer": "alice", "action": "confirm"})
    for _ in range(12):
        new_ticket(capped)
    assert "alice" in db_dump(capped)


def test_client_cannot_escape_cap_with_seed_channel(capped):
    for _ in range(15):
        capped.post("/api/tickets", json={"text": "my card has not arrived", "channel": "seed"})
    assert capped.get("/api/health").json()["tickets"] <= 10
