"""Record real API answers into web/public/replay.json (make replay).

Uses a throw-away database, seeds it, then calls the app through TestClient for the six
sample chips (clear, urgent fraud, ambiguous, fake PII, Hinglish, gibberish), six more
tickets, the queue, drift before and after the Hinglish surge, metrics, model, stages and
taxonomy. Every number in the file is a real output of the pipeline.
"""
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

CHIPS = [
    ("Clear", "How do I order a physical card?"),
    ("Urgent fraud", "Someone used my card abroad, I did not make this payment"),
    ("Ambiguous", "I tried to pay and it did not work"),
    ("Fake PII", "Mera card 4111 1111 1111 1111 kaam nahi kar raha, mail me at test@example.com"),
    ("Hinglish", "Mera paisa transfer nahi hua, jaldi batao"),
    ("Gibberish", "asdf qwer zxcv"),
]
EXTRA = [
    ("Lost phone", "I lost my phone and I think someone can open my banking app"),
    ("Exchange rate", "What exchange rate do you use when I pay abroad?"),
    ("Pending transfer", "My transfer to my landlord has been pending for three days"),
    ("Card swallowed", "The ATM kept my card and gave nothing back"),
    ("Double charge", "I was charged twice for the same coffee shop payment"),
    ("Fake email", "Please update my details, my email is anna.k@example.org"),
]


def get(client, path: str):
    """GET a path and fail loudly if it is not 200."""
    res = client.get("/api" + path)
    res.raise_for_status()
    return res.json()


def post(client, path: str, body: dict, ok: int = 200):
    """POST JSON and fail loudly unless the expected status comes back."""
    res = client.post("/api" + path, json=body)
    assert res.status_code == ok, (path, res.status_code, res.text)
    return res.json()


def build(client) -> dict:
    """Call the running app and assemble the replay document."""
    samples, compare = [], {}
    for i, (label, text) in enumerate(CHIPS + EXTRA):
        result = post(client, "/tickets", {"text": text, "channel": "web"}, 201)
        result["chip"] = label
        samples.append(result)
        compare[str(i)] = post(client, "/compare", {"text": text})
    queue = get(client, "/tickets?status=needs_review&limit=50")
    drift = post(client, "/monitor/drift/run", {})
    metrics = get(client, "/metrics")
    post(client, "/demo/scenario", {"name": "hinglish_surge"})
    after = post(client, "/monitor/drift/run", {})
    post(client, "/demo/scenario", {"name": "reset"})
    health = get(client, "/health")
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model_version": health["model_version"], "health": health,
        "stages": get(client, "/stages"), "taxonomy": get(client, "/taxonomy"),
        "samples": samples, "compare": compare, "queue": queue, "drift": drift,
        "drift_after_scenario": after, "metrics": metrics, "model": get(client, "/model"),
    }


def main() -> None:
    """Seed a temporary database, record the answers and write web/public/replay.json."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["SANKET_DB_URL"] = f"sqlite:///{tmp}/replay.db"
        import seed
        from fastapi.testclient import TestClient

        from sanket.api.app import create_app

        seed.main()
        with TestClient(create_app()) as client:
            doc = build(client)
    out = ROOT / "web" / "public" / "replay.json"
    out.write_text(json.dumps(doc), encoding="utf-8")
    print(f"wrote {out} (model {doc['model_version']}, drift {doc['drift']['status']} -> "
          f"{doc['drift_after_scenario']['status']})")


if __name__ == "__main__":
    main()
