"""Train the baseline and write artifacts/models/<version>/ (run with `make train`).

Steps: small grid on val, refit the winner, choose thresholds on val, measure on val and test,
write model, thresholds, reference, card, and the registry.
"""
import json
import subprocess
import time
from datetime import UTC, date, datetime
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from sanket.config import Settings
from sanket.models.baseline import BaselineModel, BaselineParams, fit_temperature
from sanket.models.evaluate import (
    evaluate_all,
    expected_calibration_error,
    load_split,
    score_texts,
    stress_from_scores,
    typo_texts,
)
from sanket.pipeline.clean import clean
from sanket.routing.decide import Thresholds
from sanket.routing.thresholds import choose_thresholds, save_thresholds, team_matrix
from sanket.taxonomy import INTENTS, TEAM_NAMES

GRID_C = [5, 10, 20]
GRID_CHAR = [False, True]


def val_macro_f1(model: BaselineModel, val: pd.DataFrame) -> float:
    """Intent macro-F1 of a model on a frame."""
    pred = np.array(INTENTS)[model.predict_proba(val["text"].tolist()).argmax(axis=1)]
    return float(f1_score(val["intent"], pred, labels=INTENTS, average="macro", zero_division=0))


def run_grid(train: pd.DataFrame, val: pd.DataFrame) -> list[dict]:
    """Fit every grid cell on train and score it on val only (test is never touched here)."""
    rows = []
    for c, use_char in product(GRID_C, GRID_CHAR):
        start = time.time()
        params = BaselineParams(C=c, use_char=use_char)
        model = BaselineModel.fit(train["text"].tolist(), train["intent"].tolist(), params)
        rows.append({"C": c, "use_char": use_char, "val_macro_f1": val_macro_f1(model, val),
                     "seconds": round(time.time() - start, 1)})
    return rows


def float32_cost(train: pd.DataFrame, val: pd.DataFrame, params: BaselineParams) -> dict:
    """Val macro-F1 with float64 versus float32 coefficients, same training run."""
    texts, labels = train["text"].tolist(), train["intent"].tolist()
    f64 = BaselineModel.fit(texts, labels, params, dtype=np.float64)
    f32 = BaselineModel(f64.version, f64.word, f64.char, f64.coef, f64.intercept, np.float32)
    return {"float64_macro_f1": val_macro_f1(f64, val), "float32_macro_f1": val_macro_f1(f32, val)}


def reference_from_val(model: BaselineModel, val: pd.DataFrame, proba: np.ndarray, oov: np.ndarray) -> dict:
    """Raw validation values the drift monitor compares live traffic against."""
    tm = team_matrix(proba)
    mix = pd.Series(np.array(TEAM_NAMES)[tm.argmax(axis=1)]).value_counts(normalize=True)
    return {
        "n_tokens": [clean(t).n_tokens for t in val["text"]],
        "oov_rate": [float(x) for x in oov],
        "team_conf": [float(x) for x in tm.max(axis=1)],
        "team_mix": {t: float(mix.get(t, 0.0)) for t in TEAM_NAMES},
    }


OOV_CONF_CANDIDATES = [round(0.80 + 0.01 * k, 2) for k in range(21)]  # 0.80 .. 1.00; 1.00 = always escalate
TYPO_SEED = 1042  # fixed so the choice is reproducible; the test typo set uses seed 42


def choose_oov_conf(model: BaselineModel, val: pd.DataFrame, th: Thresholds) -> dict:
    """Pick oov_conf on a typo copy of val: lowest human share with silent wrong-team under 1%.

    Larger values send more noisy tickets to a human, so human share only falls as the value
    falls; the first (smallest) value meeting the 1% limit is therefore the cheapest safe one.
    If none meets it, take the value with the fewest silent wrong-team tickets.
    """
    texts = typo_texts(val["text"].tolist(), TYPO_SEED)
    proba, oov = score_texts(model, texts)
    rows = []
    for c in OOV_CONF_CANDIDATES:
        trial = Thresholds(th.tau_team, th.tau_high, th.oov_max, c)
        m = stress_from_scores(proba, oov, val["intent"].tolist(), trial)
        rows.append({"oov_conf": c, "human_share": m["human_share"], "silent_wrong_team": m["silent_wrong_team"]})
    ok = [r for r in rows if r["silent_wrong_team"] < 0.01]
    best = min(ok, key=lambda r: (r["human_share"], r["oov_conf"])) if ok else min(
        rows, key=lambda r: r["silent_wrong_team"])
    return {"chosen": best["oov_conf"], "val_typo_human_share": best["human_share"],
            "val_typo_silent_wrong_team": best["silent_wrong_team"],
            "rule": "silent wrong-team < 1%, lowest human share", "typo_seed": TYPO_SEED, "table": rows}


def code_version() -> str:
    """Short git hash of the code, or 'unknown' outside a git checkout."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                             cwd=Settings().artifacts_dir.parent, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def package_version(train: pd.DataFrame, val: pd.DataFrame, params: BaselineParams, version: str,
                    out_dir: Path, extra_card: dict | None = None) -> dict:
    """Fit on `train`, choose thresholds on `val`, evaluate, write the directory; return the card."""
    model = BaselineModel.fit(train["text"].tolist(), train["intent"].tolist(), params, version)
    val_y = val["intent"].tolist()
    model.temperature = fit_temperature(model.scores(val["text"].tolist()), val_y)
    proba, oov = score_texts(model, val["text"].tolist())
    th = choose_thresholds(proba, oov, val["intent"].tolist())
    oov_choice = choose_oov_conf(model, val, th)
    th.oov_conf = oov_choice["chosen"]
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save(out_dir)
    save_thresholds(th, out_dir)
    ref = reference_from_val(model, val, proba, oov)
    (out_dir / "reference.json").write_text(json.dumps(ref), encoding="utf-8")
    card = {
        "version": version, "date": date.today().isoformat(), "code_version": code_version(),
        "model": "TF-IDF word 1-2 grams + char_wb 2-5 grams, multinomial logistic regression, float32",
        "params": {"C": params.C, "use_char": params.use_char}, "n_train": len(train),
        "temperature": model.temperature,
        "thresholds": {"tau_team": th.tau_team, "tau_high": th.tau_high, "oov_max": th.oov_max,
                       "oov_conf": th.oov_conf},
        "metrics": evaluate_all(model, th),
        "limits": [
            "Team and urgency come from this project's rubric, not from the dataset.",
            "Banking77 labels contain noise; about 8% of sampled train labels were disputed in the data audit.",
            "English only. On the 60-row Hinglish stress set (n=60, a small sample) 26 went to a human, none were silently misrouted to the wrong team, 1 was silently given a wrong intent in the right team, and intent accuracy was 0.65.",
            "Confidence is not perfectly calibrated (see ece in the metrics).",
        ],
        "model_file_mb": round((out_dir / "model.joblib").stat().st_size / 1e6, 2),
    }
    card["oov_conf_selection"] = oov_choice
    card["calibration"] = calibration_summary(model, val, card["metrics"])
    card.update(extra_card or {})
    (out_dir / "card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    return card


def calibration_summary(model: BaselineModel, val: pd.DataFrame, metrics: dict) -> dict:
    """ECE on val before (T=1) and after temperature scaling, and the headline test numbers after it."""
    texts, y = val["text"].tolist(), np.array([INTENTS.index(i) for i in val["intent"]])
    raw = model.scores(texts)
    out = {"temperature": model.temperature, "fitted_on": "val (log-loss)"}
    for name, t in (("val_ece_before", 1.0), ("val_ece_after", model.temperature)):
        p = np.exp((raw / t) - (raw / t).max(axis=1, keepdims=True))
        p /= p.sum(axis=1, keepdims=True)
        out[name] = expected_calibration_error(p.max(axis=1), p.argmax(axis=1) == y)
    t = metrics["test"]
    out.update({f"test_{k}": t[k] for k in ("ece", "auto_share", "high_recall", "auto_team_accuracy")})
    return out


def write_registry(entry: dict, champion: str | None) -> None:
    """Append an entry to registry.json; set the champion when one is given."""
    path = Settings().artifacts_dir / "registry.json"
    reg = json.loads(path.read_text()) if path.exists() else {"champion": None, "history": []}
    reg["history"].append(entry)
    if champion:
        reg["champion"] = champion
    path.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def main() -> None:
    """Grid, train v1, print the headline numbers."""
    start = time.time()
    train, val = load_split("train"), load_split("val")
    grid = run_grid(train, val)
    best = max(grid, key=lambda r: r["val_macro_f1"])
    params = BaselineParams(C=best["C"], use_char=best["use_char"])
    cost = float32_cost(train, val, params)
    out = Settings().artifacts_dir
    (out / "registry.json").unlink(missing_ok=True)
    card = package_version(train, val, params, "v1", out / "models" / "v1",
                           {"grid_on_val": grid, "float32_cost": cost})
    now = datetime.now(UTC).isoformat(timespec="seconds")
    write_registry({"version": "v1", "created_at": now, "decision": "promoted", "reasons": ["first model"],
                    "metrics": {"test": {"macro_f1": card["metrics"]["test"]["intent_macro_f1"]}}}, "v1")
    m = card["metrics"]
    print("grid:", grid)
    print("float32 cost:", cost)
    print("thresholds:", card["thresholds"], "file MB:", card["model_file_mb"])
    print(f"val macro-F1 {m['val']['intent_macro_f1']:.4f}  test macro-F1 {m['test']['intent_macro_f1']:.4f}")
    print(f"done in {time.time() - start:.0f}s")


if __name__ == "__main__":
    main()
