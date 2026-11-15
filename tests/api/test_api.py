"""API tests: shapes against fixtures, status codes, PII never stored, races, no torch."""
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import text

from sanket import schemas as s
from sanket.stages import build_stages

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "fixtures"


def keys(name: str) -> set:
    """Top-level keys of a fixture (first element for lists)."""
    data = json.loads((FIX / f"{name}.json").read_text())
    return set(data[0] if isinstance(data, list) else data)


def post_ticket(client, body: str):
    """POST one ticket."""
    return client.post("/api/tickets", json={"text": body})


def test_health_and_shapes(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and keys("health") == set(h)
    r = post_ticket(client, "How do I order a physical card?")
    assert r.status_code == 201
    body = s.TicketResult(**r.json())
    assert [t.stage for t in body.trace] == ["ingest", "clean", "classify", "explain", "route"]
    assert keys("ticket_result") == set(r.json())
    assert set(r.json()["prediction"]) == set(json.loads((FIX / "ticket_result.json").read_text())["prediction"])
    got = client.get(f"/api/tickets/{body.ticket_id}")
    assert got.status_code == 200 and s.TicketResult(**got.json())


def test_list_compare_taxonomy_stages_model_metrics(client):
    post_ticket(client, "I tried to pay and it did not work")
    rows = client.get("/api/tickets?limit=5").json()
    assert rows and keys("ticket_list") == set(rows[0])
    assert s.CompareOut(**client.post("/api/compare", json={"text": "lost my card"}).json())
    assert s.Taxonomy(**client.get("/api/taxonomy").json())
    stages = [s.Stage(**x) for x in client.get("/api/stages").json()]
    assert [x.id for x in stages] == ["ingest", "clean", "classify", "explain", "route", "review", "monitor"]
    assert s.ModelInfo(**client.get("/api/model").json())
    m = client.get("/api/metrics").json()
    assert s.Metrics(**m) and set(m) == keys("metrics")
    assert s.DriftReportOut(**client.get("/api/monitor/drift").json())


def test_stage_files_exist_and_code_not_empty(client):
    card = json.loads((ROOT / "artifacts/models/v1/card.json").read_text())
    th = json.loads((ROOT / "artifacts/models/v1/thresholds.json").read_text())
    for st in build_stages(card, th, {}):
        assert (ROOT / st.file).exists() and st.code.strip() and st.function in st.code


def test_compare_stores_nothing(client):
    before = client.get("/api/health").json()["tickets"]
    client.post("/api/compare", json={"text": "my card was swallowed"})
    assert client.get("/api/health").json()["tickets"] == before


@pytest.mark.parametrize("body", ["", "   ", "1234 5678", "x" * 2001])
def test_422_on_bad_text(client, body):
    r = post_ticket(client, body)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_404_and_review_errors(client):
    assert client.get("/api/tickets/999999").status_code == 404
    ok = {"reviewer": "a", "action": "confirm"}
    assert client.post("/api/tickets/999999/review", json=ok).status_code == 404
    tid = post_ticket(client, "I tried to pay and it did not work").json()["ticket_id"]
    bad = {"reviewer": "a", "action": "override", "final_intent": "nope"}
    assert client.post(f"/api/tickets/{tid}/review", json=bad).status_code == 422
    good = {"reviewer": "a", "action": "override", "final_intent": "failed_transfer"}
    r = client.post(f"/api/tickets/{tid}/review", json=good)
    assert r.status_code == 200 and r.json()["final_team"] == "TRANSFERS_TOPUPS"
    assert keys("review") == set(r.json())
    assert client.post(f"/api/tickets/{tid}/review", json=ok).status_code == 409
    assert client.get(f"/api/tickets/{tid}").json()["status"] == "reviewed"


def test_review_race_gives_one_200_one_409(client):
    tid = post_ticket(client, "I tried to pay and it did not work").json()["ticket_id"]
    barrier = threading.Barrier(2)

    def go(name):
        barrier.wait()
        body = {"reviewer": name, "action": "confirm"}
        return client.post(f"/api/tickets/{tid}/review", json=body).status_code

    with ThreadPoolExecutor(2) as pool:
        codes = sorted(pool.map(go, ["a", "b"]))
    assert codes == [200, 409]


def test_pii_never_stored(client):
    raw = ("my card 4111 1111 1111 1111, mail jane.doe@example.com, call +44 7700 900123, "
           "lost it")
    r = post_ticket(client, raw)
    assert r.status_code == 201
    assert "•" in r.json()["trace"][1]["detail"]["before_masked"]
    rt = client.app.state.runtime
    with rt.engine.connect() as conn:
        tables = [t[0] for t in conn.execute(text("select name from sqlite_master where type='table'"))]
        dump = ""
        for t in tables:
            dump += json.dumps([[str(c) for c in row] for row in conn.execute(text(f"select * from {t}"))])
    for secret in ("4111", "jane.doe", "example.com", "7700"):
        assert secret not in dump


def test_parallel_posts(client):
    with ThreadPoolExecutor(10) as pool:
        codes = list(pool.map(lambda i: post_ticket(client, f"my transfer {i} is pending").status_code,
                              range(20)))
    assert codes == [201] * 20


def test_scenario_and_drift(client):
    r = client.post("/api/demo/scenario", json={"name": "hinglish_surge"})
    assert r.status_code == 200 and 0 < r.json()["inserted"] <= 300
    assert client.post("/api/monitor/drift/run").json()["n_tickets"] >= 200
    client.post("/api/demo/scenario", json={"name": "reset"})
    with client.app.state.runtime.engine.connect() as conn:
        n = conn.execute(text("select count(*) from tickets where channel='scenario'")).scalar()
    assert n == 0


def test_no_torch_and_cap(client):
    assert "torch" not in sys.modules
    assert client.post("/api/demo/scenario", json={"name": "bogus"}).status_code == 422
