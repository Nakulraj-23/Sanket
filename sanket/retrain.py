"""Retrain from human-reviewed tickets and promote only if the candidate is not worse (`make retrain`).

Flow: read reviewed rows, check the data, train a candidate on train + reviewed rows, measure
champion and candidate on the frozen test set, apply the promote gate, update the registry.
No web endpoint calls this; a person runs it.
"""
import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from sanket.config import Settings
from sanket.db import Review, Ticket, make_engine, session_factory
from sanket.models.baseline import BaselineParams
from sanket.models.evaluate import load_split
from sanket.models.train_baseline import package_version, write_registry
from sanket.pipeline.clean import clean
from sanket.pipeline.quality import DataQualityError, check_frame, check_splits
from sanket.taxonomy import INTENTS

MACRO_F1_SLACK = 0.005
HIGH_RECALL_SLACK = 0.01
MAX_FILE_MB = 10.0
MAX_TOTAL_MB = 40.0


def gate(champion: dict, candidate: dict) -> tuple[bool, list[str]]:
    """Promote rule on test metrics: macro-F1 within 0.005 and high-urgency recall within 0.01.

    Each argument has `intent_macro_f1` and `high_recall`. Returns (promote, reasons for refusal).
    """
    reasons = []
    if candidate["intent_macro_f1"] < champion["intent_macro_f1"] - MACRO_F1_SLACK:
        reasons.append(
            f"macro-F1 {candidate['intent_macro_f1']:.4f} is more than {MACRO_F1_SLACK} below "
            f"champion {champion['intent_macro_f1']:.4f}")
    if candidate["high_recall"] < champion["high_recall"] - HIGH_RECALL_SLACK:
        reasons.append(
            f"high-urgency recall {candidate['high_recall']:.4f} is more than {HIGH_RECALL_SLACK} below "
            f"champion {champion['high_recall']:.4f}")
    return (not reasons), reasons


def size_problems(candidate_dir: Path) -> list[str]:
    """Check that the candidate fits the repository size limits."""
    problems = []
    for f in candidate_dir.iterdir():
        if f.stat().st_size / 1e6 >= MAX_FILE_MB:
            problems.append(f"{f.name} is {f.stat().st_size / 1e6:.1f} MB (limit {MAX_FILE_MB})")
    total = sum(f.stat().st_size for f in Settings().artifacts_dir.rglob("*") if f.is_file()) / 1e6
    if total >= MAX_TOTAL_MB:
        problems.append(f"artifacts total {total:.1f} MB (limit {MAX_TOTAL_MB})")
    return problems


def read_reviewed_from_db() -> pd.DataFrame:
    """Reviewed tickets as (text, intent); the intent is the reviewer's final_intent."""
    session = session_factory(make_engine())()
    with session:
        rows = session.query(Ticket.text_redacted, Review.final_intent).join(
            Review, Review.ticket_id == Ticket.id).all()
    return pd.DataFrame(rows, columns=["text", "intent"])


def flip_labels(df: pd.DataFrame, share: float, seed: int = 42) -> pd.DataFrame:
    """Give `share` of the rows a wrong intent (used only to prove the gate catches bad data)."""
    rng = np.random.default_rng(seed)
    out = df.copy().reset_index(drop=True)
    for i in rng.choice(len(out), size=int(len(out) * share), replace=False):
        out.loc[i, "intent"] = rng.choice([x for x in INTENTS if x != out.loc[i, "intent"]])
    return out


def build_training_frame(train: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Train rows plus new reviewed rows (cleaned, unknown intents dropped, texts already seen dropped)."""
    new = new.copy()
    new["text"] = [clean(t).text for t in new["text"]]
    new = new[new["intent"].isin(INTENTS) & ~new["text"].isin(set(train["text"]))]
    new = new.drop_duplicates("text").reset_index(drop=True)
    new["row_id"] = [f"rv-{i}" for i in range(len(new))]
    return pd.concat([train[["row_id", "text", "intent"]], new], ignore_index=True)


def quality_problems(frame: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> list[str]:
    """Run the data-quality checks on the combined training data; return a message if one fails."""
    stream = load_split("stream")
    stream = stream[~stream["text"].isin(set(frame["text"]))]  # reviewed stream rows now live in train
    try:
        check_frame(frame, "train")
        check_splits({"train": frame, "val": val, "stream": stream, "test": test})
    except DataQualityError as err:
        return [f"data quality: {err}"]
    return []


def next_version(registry: dict) -> str:
    """v1 -> v2 -> v3 by counting what is in the registry history."""
    numbers = [int(h["version"][1:]) for h in registry["history"]]
    return f"v{max(numbers) + 1}"


def run_retrain(new: pd.DataFrame, min_new: int = 50, sabotage: float = 0.0) -> dict:
    """Do one retrain attempt. Returns {status, version, promoted, reasons, ...}."""
    art = Settings().artifacts_dir
    registry = json.loads((art / "registry.json").read_text())
    if len(new) < min_new:
        return {"status": "skipped", "reasons": [f"only {len(new)} reviewed tickets, need {min_new}"]}
    train, val, test = load_split("train"), load_split("val"), load_split("test")
    if sabotage:
        new, train = flip_labels(new, sabotage), flip_labels(train, sabotage)
    frame = build_training_frame(train, new)
    reasons = quality_problems(frame, val, test)
    champ_card = json.loads((art / "models" / registry["champion"] / "card.json").read_text())
    params = BaselineParams(**champ_card["params"])
    version = next_version(registry)
    card = package_version(frame, val, params, version, art / "models" / version,
                           {"retrained_on": {"new_reviewed_rows": len(frame) - len(train)}})
    reasons += size_problems(art / "models" / version)
    ok, gate_reasons = gate(champ_card["metrics"]["test"], card["metrics"]["test"])
    reasons += gate_reasons
    promoted = ok and not reasons
    now = datetime.now(UTC).isoformat(timespec="seconds")
    write_registry({"version": version, "created_at": now, "decision": "promoted" if promoted else "rejected",
                    "reasons": reasons, "metrics": {"test": {
                        "macro_f1": card["metrics"]["test"]["intent_macro_f1"],
                        "high_recall": card["metrics"]["test"]["high_recall"]}}},
                   version if promoted else None)
    return {"status": "done", "version": version, "promoted": promoted, "reasons": reasons,
            "champion_test": champ_card["metrics"]["test"], "candidate_test": card["metrics"]["test"]}


def main(argv: list[str] | None = None) -> int:
    """Command line: reads reviewed tickets from the database, or a CSV with --from-csv."""
    ap = argparse.ArgumentParser(description="Retrain from reviewed tickets and apply the promote gate.")
    ap.add_argument("--min-new", type=int, default=50)
    ap.add_argument("--sabotage", type=float, default=0.0, help="share of labels to flip (gate demo)")
    ap.add_argument("--from-csv", type=Path, default=None, help="CSV with text,intent instead of the database")
    args = ap.parse_args(argv)
    new = pd.read_csv(args.from_csv) if args.from_csv else read_reviewed_from_db()
    result = run_retrain(new, args.min_new, args.sabotage)
    print(json.dumps({k: v for k, v in result.items() if "test" not in k}, indent=2))
    for key in ("champion_test", "candidate_test"):
        if key in result:
            m = result[key]
            print(f"{key}: macro-F1 {m['intent_macro_f1']:.4f} high-recall {m['high_recall']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
