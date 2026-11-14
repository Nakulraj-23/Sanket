"""Data-quality checks that stop the pipeline with a clear message instead of training on bad data."""
import pandas as pd

from sanket.taxonomy import INTENTS

MIN_CHARS = 5
MAX_CHARS = 2000
MIN_PER_CLASS = 5


class DataQualityError(ValueError):
    """Raised when a check fails; the message names the frame and the problem."""


def check_frame(
    df: pd.DataFrame, name: str, allow_duplicates: bool = False, min_per_class: int = MIN_PER_CLASS
) -> None:
    """Check one frame: nulls, empty text, unknown intent, duplicate text, length bounds, class floor.

    `allow_duplicates` is only for the frozen official test set, which we may not edit.
    """
    for col in ("text", "intent"):
        if df[col].isna().any():
            raise DataQualityError(f"{name}: {int(df[col].isna().sum())} null values in '{col}'")
    text = df["text"].astype(str)
    empty = int((text.str.strip() == "").sum())
    if empty:
        raise DataQualityError(f"{name}: {empty} rows with empty text")
    unknown = sorted(set(df["intent"]) - set(INTENTS))
    if unknown:
        raise DataQualityError(f"{name}: unknown intents {unknown[:5]}")
    dupes = int(text.duplicated().sum())
    if dupes and not allow_duplicates:
        raise DataQualityError(f"{name}: {dupes} duplicate texts")
    lengths = text.str.len()
    if lengths.min() < MIN_CHARS or lengths.max() > MAX_CHARS:
        raise DataQualityError(
            f"{name}: text length outside {MIN_CHARS}..{MAX_CHARS} (min {lengths.min()}, max {lengths.max()})"
        )
    counts = df["intent"].value_counts().reindex(INTENTS, fill_value=0)
    thin = counts[counts < min_per_class]
    if len(thin):
        raise DataQualityError(f"{name}: classes below {min_per_class} rows: {thin.to_dict()}")


def check_splits(splits: dict[str, pd.DataFrame]) -> None:
    """Check that no cleaned text is shared between any two splits (no leakage)."""
    names = list(splits)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = set(splits[a]["text"]) & set(splits[b]["text"])
            if shared:
                raise DataQualityError(f"leak: {len(shared)} texts appear in both {a} and {b}")
