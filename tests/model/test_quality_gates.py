"""Quality gates on the committed champion, and the retrain promote gate."""
import json
import shutil
import time

import numpy as np
import pandas as pd
import pytest

from sanket.config import ROOT, Settings
from sanket.models.baseline import BaselineModel
from sanket.models.evaluate import evaluate_frame, load_split
from sanket.retrain import gate, run_retrain
from sanket.routing.thresholds import load_thresholds

ART = ROOT / "artifacts"


@pytest.fixture(scope="module")
def champion() -> dict:
    version = json.loads((ART / "registry.json").read_text())["champion"]
    directory = ART / "models" / version
    model = BaselineModel.load(directory)
    th = load_thresholds(directory)
    return {"dir": directory, "model": model, "th": th, "card": json.loads((directory / "card.json").read_text()),
            "test": evaluate_frame(model, load_split("test"), th)}


def test_intent_macro_f1_has_not_regressed(champion: dict) -> None:
    measured = champion["card"]["metrics"]["test"]["intent_macro_f1"]
    assert champion["test"]["intent_macro_f1"] >= max(measured - 0.02, 0.85)


def test_team_accuracy(champion: dict) -> None:
    assert champion["test"]["team_accuracy"] >= 0.95


def test_high_urgency_recall(champion: dict) -> None:
    assert champion["test"]["high_recall"] >= 0.95


def test_auto_routed_accuracy(champion: dict) -> None:
    assert champion["test"]["auto_team_accuracy"] >= 0.98


def test_single_ticket_latency_p95_under_20ms(champion: dict) -> None:
    model, th = champion["model"], champion["th"]
    texts = load_split("val")["text"].tolist()[:200]
    times = []
    for t in texts:
        start = time.perf_counter()
        proba = model.predict_proba([t])
        model.oov_rate(t)
        model.explain(t, "card_arrival", 5)
        times.append((time.perf_counter() - start) * 1000)
        assert proba.shape == (1, 77) and th.tau_team > 0
    assert np.percentile(times, 95) < 20


def test_artifact_size_limits() -> None:
    files = [f for f in ART.rglob("*") if f.is_file()]
    assert all(f.stat().st_size < 10e6 for f in files)
    assert sum(f.stat().st_size for f in files) < 40e6


def test_gate_rules() -> None:
    champ = {"intent_macro_f1": 0.90, "high_recall": 0.97}
    assert gate(champ, {"intent_macro_f1": 0.896, "high_recall": 0.962})[0]
    ok, reasons = gate(champ, {"intent_macro_f1": 0.89, "high_recall": 0.97})
    assert not ok and "macro-F1" in reasons[0]
    ok, reasons = gate(champ, {"intent_macro_f1": 0.90, "high_recall": 0.95})
    assert not ok and "recall" in reasons[0]


@pytest.fixture()
def scratch_artifacts(tmp_path, monkeypatch):
    """A copy of artifacts/ so a retrain test never touches the committed champion."""
    shutil.copytree(ART, tmp_path / "artifacts")
    monkeypatch.setenv("SANKET_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    assert Settings().artifacts_dir == tmp_path / "artifacts"
    return tmp_path / "artifacts"


def reviewed_rows(n: int = 60) -> pd.DataFrame:
    return load_split("stream").head(n)[["text", "intent"]]


def test_sabotaged_retrain_is_rejected(scratch_artifacts) -> None:
    result = run_retrain(reviewed_rows(), min_new=50, sabotage=0.3)
    assert result["promoted"] is False and result["reasons"]
    assert json.loads((scratch_artifacts / "registry.json").read_text())["champion"] == "v1"


def test_clean_retrain_is_not_rejected(scratch_artifacts) -> None:
    result = run_retrain(reviewed_rows(), min_new=50)
    assert result["promoted"] is True, result["reasons"]
    assert json.loads((scratch_artifacts / "registry.json").read_text())["champion"] == result["version"]


def test_retrain_needs_enough_reviewed_tickets(scratch_artifacts) -> None:
    assert run_retrain(reviewed_rows(10), min_new=50)["status"] == "skipped"
