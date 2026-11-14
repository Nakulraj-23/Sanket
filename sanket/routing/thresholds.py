"""Choose the three routing thresholds from validation data only, then save and load them."""
import json
from pathlib import Path

import numpy as np

from sanket.routing.decide import HIGH_INDEX, TEAM_INDEX, Thresholds
from sanket.taxonomy import INTENTS, TEAM_NAMES, team_of, urgency_of

TARGET_TEAM_ACC = 0.985
TARGET_HIGH_RECALL = 0.97
STEPS = [round(0.05 * k, 2) for k in range(1, 20)]  # 0.05 .. 0.95


def team_matrix(proba: np.ndarray) -> np.ndarray:
    """Shape (n, 7): summed probability per team, columns in TEAM_NAMES order."""
    return np.stack([proba[:, TEAM_INDEX[t]].sum(axis=1) for t in TEAM_NAMES], axis=1)


def choose_tau_team(proba: np.ndarray, y_intent: list[str]) -> float:
    """Smallest step where the tickets with team confidence >= step have team accuracy >= 0.985."""
    tm = team_matrix(proba)
    pred = np.array(TEAM_NAMES)[tm.argmax(axis=1)]
    true = np.array([team_of(i) for i in y_intent])
    conf = tm.max(axis=1)
    for step in STEPS:
        keep = conf >= step
        if keep.sum() and (pred[keep] == true[keep]).mean() >= TARGET_TEAM_ACC:
            return step
    return STEPS[-1]


def choose_tau_high(proba: np.ndarray, y_intent: list[str]) -> float:
    """Largest step where at least 97% of truly high-urgency tickets have p_high >= step."""
    p_high = proba[:, HIGH_INDEX].sum(axis=1)
    is_high = np.array([urgency_of(i) == "high" for i in y_intent])
    if not is_high.any():
        return STEPS[0]
    for step in reversed(STEPS):
        if (p_high[is_high] >= step).mean() >= TARGET_HIGH_RECALL:
            return step
    return STEPS[0]


def choose_thresholds(proba: np.ndarray, oov: np.ndarray, y_intent: list[str]) -> Thresholds:
    """Apply the three rules in CONTRACTS to validation probabilities, oov rates and true intents."""
    assert proba.shape[1] == len(INTENTS)
    return Thresholds(
        tau_team=choose_tau_team(proba, y_intent),
        tau_high=choose_tau_high(proba, y_intent),
        oov_max=float(np.percentile(oov, 99)),
    )


def save_thresholds(th: Thresholds, directory: Path) -> None:
    """Write thresholds.json next to the model."""
    payload = {"tau_team": th.tau_team, "tau_high": th.tau_high, "oov_max": th.oov_max,
               "oov_conf": th.oov_conf}
    (directory / "thresholds.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_thresholds(directory: Path) -> Thresholds:
    """Read thresholds.json from a model directory."""
    data = json.loads((directory / "thresholds.json").read_text(encoding="utf-8"))
    return Thresholds(data["tau_team"], data["tau_high"], data["oov_max"], data.get("oov_conf", 0.98))
