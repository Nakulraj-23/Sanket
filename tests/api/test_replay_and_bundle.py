"""The recorded replay file matches the schemas and the champion."""
import json
from pathlib import Path

from sanket import schemas as s

ROOT = Path(__file__).resolve().parents[2]


def test_replay_validates_and_matches_champion():
    doc = json.loads((ROOT / "web/public/replay.json").read_text())
    champion = json.loads((ROOT / "artifacts/registry.json").read_text())["champion"]
    assert doc["model_version"] == champion == doc["health"]["model_version"]
    assert doc["health"]["status"] == "ok"
    assert [x["chip"] for x in doc["samples"][:6]] == [
        "Clear", "Urgent fraud", "Ambiguous", "Fake PII", "Hinglish", "Gibberish"]
    for sample in doc["samples"]:
        s.TicketResult(**sample)
        assert len(sample["trace"]) == 5 and all(t["detail"] for t in sample["trace"])
    assert [x["id"] for x in doc["stages"]] == [
        "ingest", "clean", "classify", "explain", "route", "review", "monitor"]
    assert "real code arrives" not in json.dumps(doc["stages"])
    [s.TicketSummary(**q) for q in doc["queue"]]
    s.DriftReportOut(**doc["drift"])
    assert s.DriftReportOut(**doc["drift_after_scenario"]).status == "red"
    s.Metrics(**doc["metrics"])
    s.ModelInfo(**doc["model"])
    s.Taxonomy(**doc["taxonomy"])
    for key, value in doc["compare"].items():
        assert int(key) < len(doc["samples"]) and s.CompareOut(**value)
