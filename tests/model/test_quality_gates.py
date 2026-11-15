"""Quality gates on the committed champion, and the retrain promote gate."""
import json
import shutil
import time

import numpy as np
import pandas as pd
import pytest

from sanket.config import ROOT, Settings
from sanket.models.baseline import BaselineModel
from sanket.models.evaluate import evaluate_frame, load_split, score_texts
from sanket.retrain import best_ever_problems, flip_labels, gate, label_sanity_problems, run_retrain
from sanket.routing.decide import decide
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


def test_all_wrong_reviews_are_rejected(scratch_artifacts) -> None:
    bad = flip_labels(load_split("stream").sample(200, random_state=8)[["text", "intent"]], 1.0)
    result = run_retrain(bad, min_new=50)
    assert result["promoted"] is False
    assert any("label sanity" in r for r in result["reasons"])
    assert json.loads((scratch_artifacts / "registry.json").read_text())["champion"] == "v1"


def human_routed_stream(champion: dict) -> pd.DataFrame:
    """The stream tickets the champion sends to a human, with their true labels: what reviewers really see."""
    stream = load_split("stream")
    proba, oov = score_texts(champion["model"], stream["text"].tolist())
    human = [decide(proba[i], oov[i], champion["th"]).decision == "human" for i in range(len(stream))]
    return stream[human][["text", "intent"]].reset_index(drop=True)


def test_label_sanity_accepts_true_labels_of_human_routed_tickets(champion: dict) -> None:
    rows = human_routed_stream(champion)
    assert len(rows) > 50
    assert label_sanity_problems(champion["model"], rows) == []


def test_label_sanity_accepts_true_labels_of_random_tickets(champion: dict) -> None:
    rows = load_split("stream").sample(200, random_state=1)[["text", "intent"]]
    assert label_sanity_problems(champion["model"], rows) == []


def test_label_sanity_rejects_all_wrong_labels(champion: dict) -> None:
    rows = load_split("stream").sample(200, random_state=8)[["text", "intent"]]
    assert label_sanity_problems(champion["model"], flip_labels(rows, 1.0))


def test_label_sanity_rejects_30_percent_label_noise(champion: dict) -> None:
    random_rows = load_split("stream").sample(200, random_state=1)[["text", "intent"]]
    for seed in range(3):
        assert label_sanity_problems(champion["model"], flip_labels(random_rows, 0.3, seed))
        assert label_sanity_problems(champion["model"], flip_labels(human_routed_stream(champion), 0.3, seed))


def test_best_ever_check_stops_the_slack_ratchet() -> None:
    reg = {"history": [{"decision": "promoted", "metrics": {"test": {"macro_f1": 0.90}}},
                       {"decision": "promoted", "metrics": {"test": {"macro_f1": 0.896}}}]}
    assert best_ever_problems(reg, {"intent_macro_f1": 0.895}) == []
    assert best_ever_problems(reg, {"intent_macro_f1": 0.885})


def test_calibration_in_card(champion: dict) -> None:
    card = champion["card"]
    assert 0.3 < card["temperature"] < 1.0 and card["calibration"]["test_ece"] < 0.03
    assert card["calibration"]["test_high_recall"] >= 0.97


def test_duplicate_reviews_do_not_count_as_new(scratch_artifacts) -> None:
    copies = load_split("train").head(60)[["text", "intent"]]
    assert run_retrain(copies, min_new=50)["status"] == "skipped"


def test_oov_conf_is_selected_on_val_typos_and_stored(champion: dict) -> None:
    sel = champion["card"]["oov_conf_selection"]
    assert sel["chosen"] == champion["th"].oov_conf and sel["val_typo_silent_wrong_team"] < 0.01
    cheaper = [r for r in sel["table"] if r["oov_conf"] < sel["chosen"]]
    assert all(r["silent_wrong_team"] >= 0.01 for r in cheaper)


def test_honest_human_routed_batch_is_promoted_end_to_end(scratch_artifacts, champion: dict) -> None:
    result = run_retrain(human_routed_stream(champion), min_new=50)
    assert result["promoted"] is True, result["reasons"]
