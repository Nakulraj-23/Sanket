"""Scaffold tests: taxonomy, fixtures, database, artifact size limits."""
import json
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from sanket import schemas as s
from sanket import taxonomy as tx
from sanket.db import Review, Ticket, init_db, make_engine, session_factory

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "fixtures"

FIXTURE_SCHEMAS = {
    "health": s.Health, "ticket_result": s.TicketResult, "ticket_result_review": s.TicketResult,
    "ticket_list": list[s.TicketSummary], "review": s.Review, "stages": list[s.Stage],
    "taxonomy": s.Taxonomy, "compare": s.CompareOut, "drift_report": s.DriftReportOut,
    "drift_report_red": s.DriftReportOut, "metrics": s.Metrics, "model": s.ModelInfo,
}


def test_taxonomy_counts_and_uniqueness():
    assert len(tx.INTENTS) == 77
    assert len(set(tx.INTENTS)) == 77
    assert tx.INTENTS == sorted(tx.INTENTS)
    total = sum(len(v) for v in tx.TEAMS.values())
    assert total == 77
    assert len(tx.TEAMS) == 7
    assert {tx.urgency_of(i) for i in tx.INTENTS} == {"high", "medium", "low"}
    assert sum(tx.urgency_of(i) == "high" for i in tx.INTENTS) == 9


def test_taxonomy_matches_dataset_labels():
    for split in ("train", "test"):
        labels = set(pd.read_csv(ROOT / "data/raw" / f"banking77_{split}.csv").category)
        assert labels == set(tx.INTENTS)


def test_team_and_urgency_lookup():
    assert tx.team_of("lost_or_stolen_card") == "FRAUD_SECURITY"
    assert tx.urgency_of("lost_or_stolen_card") == "high"
    assert tx.urgency_of("exchange_rate") == "low"
    assert tx.urgency_of("pending_transfer") == "medium"


@pytest.mark.parametrize("name", sorted(FIXTURE_SCHEMAS))
def test_fixture_validates(name):
    from pydantic import TypeAdapter
    data = json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))
    TypeAdapter(FIXTURE_SCHEMAS[name]).validate_python(data)


def test_db_foreign_keys_wal_and_unique_review(tmp_path):
    engine = init_db(make_engine(f"sqlite:///{tmp_path / 't.db'}"))
    with engine.connect() as c:
        assert c.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert c.execute(text("PRAGMA journal_mode")).scalar().lower() == "wal"
    Session = session_factory(engine)
    with Session() as db:
        db.add(Ticket(channel="web", text_redacted="x", n_chars=1, n_tokens=1, oov_rate=0.0))
        db.commit()
        row = {"ticket_id": 1, "reviewer": "a", "action": "confirm",
               "final_intent": "exchange_rate", "final_team": "FEES_FX", "final_urgency": "low"}
        db.add(Review(**row))
        db.commit()
        db.add(Review(**row))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(Review(**{**row, "ticket_id": 999}))
        with pytest.raises(IntegrityError):
            db.commit()


def test_artifact_size_limits():
    art = ROOT / "artifacts"
    if not art.exists():
        return
    files = [p for p in art.rglob("*") if p.is_file()]
    assert all(p.stat().st_size < 10 * 1024 * 1024 for p in files)
    assert sum(p.stat().st_size for p in files) < 40 * 1024 * 1024
