"""Measure a classifier on val, test and the two stress sets. Numbers only, no plotting."""
from collections import Counter
from itertools import pairwise

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from sanket.config import Settings
from sanket.models.base import Classifier
from sanket.pipeline.clean import clean
from sanket.pipeline.perturb import add_typos
from sanket.routing.decide import Thresholds, decide
from sanket.taxonomy import INTENTS, team_of, urgency_of

COVERAGE_STEPS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]


def load_split(name: str) -> pd.DataFrame:
    """Read data/splits/<name>.csv (columns row_id, text, intent)."""
    return pd.read_csv(Settings().data_dir / "splits" / f"{name}.csv")


def score_texts(model, texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Probabilities (n, 77) and OOV rates (n,) for cleaned texts."""
    proba = model.predict_proba(texts)
    oov = np.array([model.oov_rate(t) for t in texts]) if hasattr(model, "oov_rate") else np.zeros(len(texts))
    return proba, oov


def expected_calibration_error(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    """Average gap between stated confidence and actual accuracy, over 10 equal-width bins."""
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in pairwise(edges):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            total += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(total)


def confused_pairs(true: list[str], pred: list[str], n: int = 10) -> list[dict]:
    """The n most common (true, predicted) mistakes."""
    counts = Counter((t, p) for t, p in zip(true, pred) if t != p)
    return [{"true": t, "pred": p, "count": c} for (t, p), c in counts.most_common(n)]


def coverage_table(team_conf: np.ndarray, team_ok: np.ndarray) -> list[dict]:
    """For several team-confidence cut-offs: share of tickets kept and their team accuracy."""
    rows = []
    for cut in COVERAGE_STEPS:
        keep = team_conf >= cut
        acc = float(team_ok[keep].mean()) if keep.any() else None
        rows.append({"cutoff": cut, "coverage": float(keep.mean()), "team_accuracy": acc})
    return rows


def _decisions(proba: np.ndarray, oov: np.ndarray, th: Thresholds) -> list:
    """Run the routing rule on every row."""
    return [decide(proba[i], float(oov[i]), th) for i in range(len(proba))]


def metrics_from_scores(proba: np.ndarray, oov: np.ndarray, y_intent: list[str], th: Thresholds) -> dict:
    """All headline metrics for one set of tickets, given probabilities and true intents."""
    decs = _decisions(proba, oov, th)
    pred_intent = [d.intent for d in decs]
    true_team = np.array([team_of(i) for i in y_intent])
    pred_team = np.array([d.team for d in decs])
    true_urg = [urgency_of(i) for i in y_intent]
    pred_urg = [d.urgency for d in decs]
    auto = np.array([d.decision == "auto" for d in decs])
    team_ok = pred_team == true_team
    conf = np.array([d.intent_conf for d in decs])
    intent_ok = np.array(pred_intent) == np.array(y_intent)
    is_high = np.array([u == "high" for u in true_urg])
    flagged = np.array([u == "high" for u in pred_urg])
    return {
        "n": len(y_intent),
        "intent_accuracy": float(intent_ok.mean()),
        "intent_macro_f1": float(f1_score(y_intent, pred_intent, labels=INTENTS, average="macro", zero_division=0)),
        "team_accuracy": float(team_ok.mean()),
        "urgency_macro_f1": float(f1_score(true_urg, pred_urg, average="macro", zero_division=0)),
        "high_recall": float(flagged[is_high].mean()),
        "high_precision": float(is_high[flagged].mean()) if flagged.any() else None,
        "auto_share": float(auto.mean()),
        "auto_team_accuracy": float(team_ok[auto].mean()) if auto.any() else None,
        "auto_intent_accuracy": float(intent_ok[auto].mean()) if auto.any() else None,
        "ece": expected_calibration_error(conf, intent_ok),
        "coverage_table": coverage_table(np.array([d.team_conf for d in decs]), team_ok),
        "confused_pairs": confused_pairs(y_intent, pred_intent),
    }


def evaluate_frame(model: Classifier, df: pd.DataFrame, th: Thresholds) -> dict:
    """Metrics for a split frame with columns text and intent."""
    proba, oov = score_texts(model, df["text"].tolist())
    return metrics_from_scores(proba, oov, df["intent"].tolist(), th)


def stress_metrics(model: Classifier, texts: list[str], y_intent: list[str], th: Thresholds) -> dict:
    """Accuracy, share sent to a human, and silent failures (wrong AND auto-routed) on a stress set."""
    proba, oov = score_texts(model, texts)
    return stress_from_scores(proba, oov, y_intent, th)


def stress_from_scores(proba: np.ndarray, oov: np.ndarray, y_intent: list[str], th: Thresholds) -> dict:
    """Same numbers as stress_metrics, from probabilities that were already computed."""
    decs = _decisions(proba, oov, th)
    auto = np.array([d.decision == "auto" for d in decs])
    intent_ok = np.array([d.intent == y for d, y in zip(decs, y_intent)])
    team_ok = np.array([d.team == team_of(y) for d, y in zip(decs, y_intent)])
    return {
        "n": len(y_intent),
        "intent_accuracy": float(intent_ok.mean()),
        "team_accuracy": float(team_ok.mean()),
        "human_share": float(1 - auto.mean()),
        "silent_wrong_team": float((~team_ok & auto).mean()),
        "silent_wrong_intent": float((~intent_ok & auto).mean()),
    }


def typo_texts(texts: list[str], seed: int) -> list[str]:
    """Copies of `texts` with 10% character noise, one seed per row (seed + row number)."""
    return [clean(add_typos(t, 0.1, seed + i)).text for i, t in enumerate(texts)]


def evaluate_stress(model: Classifier, th: Thresholds, test: pd.DataFrame) -> dict:
    """Typo test set (10% character noise, seed 42) and the Hinglish stress file."""
    typo_texts_test = typo_texts(test["text"].tolist(), 42)
    hing = pd.read_csv(Settings().data_dir / "stress" / "hinglish.csv")
    hing_texts = [clean(t).text for t in hing["text"]]
    return {
        "typos_10pct": stress_metrics(model, typo_texts_test, test["intent"].tolist(), th),
        "hinglish": stress_metrics(model, hing_texts, hing["intent"].tolist(), th),
    }


def evaluate_all(model: Classifier, th: Thresholds) -> dict:
    """Metrics on val and test plus the stress sets; the dict stored in card.json."""
    val, test = load_split("val"), load_split("test")
    return {"val": evaluate_frame(model, val, th), "test": evaluate_frame(model, test, th),
            "stress": evaluate_stress(model, th, test)}
