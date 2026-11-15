"""Q2 model audit: checks that hold (pass) and known findings (strict xfail; they flip when fixed)."""
import json
import random
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pytest

from sanket.config import ROOT, Settings
from sanket.models.baseline import BaselineModel, _softmax
from sanket.models.evaluate import expected_calibration_error, load_split, score_texts
from sanket.monitoring.drift import drift_report, ks_2samp, psi
from sanket.pipeline.clean import clean
from sanket.pipeline.perturb import hinglishify
from sanket.retrain import flip_labels, gate, main, run_retrain
from sanket.routing.thresholds import choose_thresholds, load_thresholds, team_matrix
from sanket.taxonomy import INTENTS, TEAM_NAMES

V1 = ROOT / "artifacts" / "models" / "v1"


@pytest.fixture(scope="module")
def model() -> BaselineModel:
    return BaselineModel.load(V1)


@pytest.fixture(scope="module")
def reference() -> dict:
    return json.loads((V1 / "reference.json").read_text())


def live_signals(model: BaselineModel, texts: list[str]) -> dict:
    """Build the `live` dict for drift_report the same way reference.json is built."""
    cleaned = [clean(t) for t in texts]
    tm = team_matrix(model.predict_proba([c.text for c in cleaned]))
    mix = pd.Series(np.array(TEAM_NAMES)[tm.argmax(axis=1)]).value_counts(normalize=True)
    return {"n_tokens": [c.n_tokens for c in cleaned], "oov_rate": [model.oov_rate(c.text) for c in cleaned],
            "team_conf": list(tm.max(axis=1)), "team_mix": {t: float(mix.get(t, 0.0)) for t in TEAM_NAMES}}


def test_explain_contributions_plus_intercept_equal_raw_score(model) -> None:
    test = load_split("test")
    for i in random.Random(42).sample(range(len(test)), 20):
        text = test["text"][i]
        intent = INTENTS[int(model.predict_proba([text]).argmax())]
        parts = model.explain(text, intent, k=100_000)
        total = sum(p["weight"] for p in parts) + float(model.intercept[INTENTS.index(intent)])
        assert total == pytest.approx(model.raw_score(text, intent), abs=1e-5)


def test_thresholds_follow_contract_rules_on_val(model) -> None:
    val = load_split("val")
    proba, oov = score_texts(model, val["text"].tolist())
    assert np.allclose(team_matrix(proba).sum(axis=1), 1.0)
    chosen, saved = choose_thresholds(proba, oov, val["intent"].tolist()), load_thresholds(V1)
    # oov_conf is picked separately, on a val typo set (see train_baseline.choose_oov_conf)
    assert (chosen.tau_team, chosen.tau_high, chosen.oov_max) == (saved.tau_team, saved.tau_high, saved.oov_max)


def test_ece_matches_hand_computation() -> None:
    conf = np.array([0.95, 0.95, 0.55, 0.55])
    correct = np.array([1.0, 1.0, 1.0, 0.0])
    # bin (0.9,1]: |1.0-0.95| * 0.5 ; bin (0.5,0.6]: |0.5-0.55| * 0.5
    assert expected_calibration_error(conf, correct) == pytest.approx(0.05)


def test_oov_rule_rarely_escalates_clean_english(model) -> None:
    test = load_split("test")
    _, oov = score_texts(model, test["text"].tolist())
    assert (oov > load_thresholds(V1).oov_max).mean() < 0.01  # measured 13 / 3080


def test_reference_json_is_built_from_val(reference) -> None:
    val = load_split("val")
    assert len(reference["n_tokens"]) == len(val)
    assert reference["n_tokens"] == [clean(t).n_tokens for t in val["text"]]


def test_drift_green_on_shuffled_clean_stream(model, reference) -> None:
    stream = load_split("stream").sample(500, random_state=42)["text"].tolist()
    assert drift_report(reference, live_signals(model, stream))["status"] == "green"


def test_drift_red_on_hinglish_surge(model, reference) -> None:
    stream = load_split("stream").sample(frac=1.0, random_state=42)["text"].tolist()
    surge = stream[:200] + [hinglishify(t, i) for i, t in enumerate(stream[200:500])]
    report = drift_report(reference, live_signals(model, surge))
    assert report["status"] == "red"
    assert {i["name"]: i["status"] for i in report["indicators"]}["oov_rate"] == "red"


def test_drift_green_on_stream_in_file_order(model, reference) -> None:
    stream = load_split("stream")["text"].tolist()[:500]
    assert drift_report(reference, live_signals(model, stream))["status"] == "green"


def test_ks_edge_cases_match_scipy() -> None:
    stats = pytest.importorskip("scipy.stats")
    cases = [(np.array([1.0]), np.array([2.0])), (np.arange(10.0), np.arange(10.0)),
             (np.ones(50), np.ones(50)), (np.ones(50), np.zeros(50)),
             (np.repeat([0.0, 1, 2], 30), np.repeat([0.0, 1, 2], [20, 30, 40]))]
    for a, b in cases:
        d, p = ks_2samp(a, b)
        ref = stats.ks_2samp(a, b)
        assert d == pytest.approx(ref.statistic, abs=1e-9) and p == pytest.approx(ref.pvalue, abs=1e-3)


def test_psi_edge_cases() -> None:
    assert psi(np.arange(100.0), np.arange(100.0)) == pytest.approx(0.0)
    assert psi(np.ones(100), np.ones(100)) == pytest.approx(0.0)
    assert psi(np.arange(100.0), np.full(100, 200.0)) > 0.25  # everything in one (top) bin
    assert np.isfinite(psi(np.arange(100.0), np.array([5.0])))


@pytest.mark.xfail(strict=True, reason="Q2 LOW: a constant reference gives one bin, so any live data scores 0")
def test_psi_constant_reference_detects_change() -> None:
    assert psi(np.ones(100), np.zeros(100)) > 0.25


def test_gate_accepts_equal_candidate_and_has_no_skip_flag(capsys) -> None:
    champ = {"intent_macro_f1": 0.90, "high_recall": 0.97}
    assert gate(champ, dict(champ)) == (True, [])
    with pytest.raises(SystemExit):
        main(["--help"])
    help_text = capsys.readouterr().out
    assert "--force" not in help_text and "--skip" not in help_text


@pytest.fixture()
def scratch(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "artifacts", tmp_path / "artifacts")
    monkeypatch.setenv("SANKET_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    return tmp_path / "artifacts"


def test_retrain_with_50_correct_labels_end_to_end(scratch) -> None:
    new = load_split("stream").sample(50, random_state=42)[["text", "intent"]]
    result = run_retrain(new, min_new=50)
    assert result["promoted"] is True, result["reasons"]
    entry = json.loads((scratch / "registry.json").read_text())["history"][-1]
    assert set(entry) == {"version", "created_at", "decision", "reasons", "metrics"}
    assert Settings().artifacts_dir == scratch


def test_retrain_rejects_poisoned_reviews(scratch) -> None:
    bad = flip_labels(load_split("stream").sample(200, random_state=8)[["text", "intent"]], 1.0)
    assert run_retrain(bad, min_new=50)["promoted"] is False


def test_serving_loads_without_torch() -> None:
    code = ("import sys; from sanket.models.baseline import BaselineModel; from sanket.config import ROOT;"
            "from sanket.models.nn.onnx_model import OnnxModel; BaselineModel.load(ROOT/'artifacts/models/v1');"
            "OnnxModel(); assert 'torch' not in sys.modules")
    subprocess.run([sys.executable, "-c", code], check=True, cwd=ROOT)


def test_nn_stopped_early_not_at_epoch_cap() -> None:
    info = json.loads((ROOT / "artifacts" / "nn" / "variant.json").read_text())
    assert all(v["epochs"] < 60 for v in info["all_variants"].values())


def _median_ms(fn, texts: list[str]) -> float:
    times = []
    for t in texts:
        start = time.perf_counter()
        fn([t])
        times.append(time.perf_counter() - start)
    return float(np.median(times)) * 1000


def test_baseline_predict_has_no_per_call_matrix_copy(model) -> None:
    weights = np.ascontiguousarray(model.coef.T.astype(np.float64))

    def fast(texts):
        return _softmax(np.asarray(model._features(texts) @ weights + model.intercept))

    texts = load_split("test")["text"].tolist()[:300]
    _median_ms(model.predict_proba, texts[:30])
    assert _median_ms(model.predict_proba, texts) < 1.5 * _median_ms(fast, texts)
