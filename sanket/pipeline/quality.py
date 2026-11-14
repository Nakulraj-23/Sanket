"""Data-quality checks that stop the pipeline with a clear message instead of training on bad data."""
import re

import pandas as pd

from sanket.pipeline.clean import clean
from sanket.pipeline.similarity import near_duplicates, nearest_label_agreement
from sanket.taxonomy import INTENTS

MIN_CHARS = 5
MAX_CHARS = 2000
MIN_PER_CLASS = 5
CLASS_FLOOR = {"train": 20}  # val and stream are small, so they use MIN_PER_CLASS
EXPECTED_TEST_ROWS = 3080  # the official Banking77 test set, frozen
LEAK_COSINE = 0.99  # a train and a test text this similar are the same sentence
MIN_LABEL_AGREEMENT = 0.72  # 1-nearest-neighbour label agreement, val and stream against train
_MARKUP = re.compile(r"<[a-zA-Z/][^>]*>|&[a-z]+;|Ã.|â€|\ufffd")


class DataQualityError(ValueError):
    """Raised when a check fails; the message names the frame and the problem."""


def check_frame(
    df: pd.DataFrame, name: str, allow_duplicates: bool = False, min_per_class: int | None = None
) -> None:
    """Check one frame: nulls, empty text, unknown intent, duplicates, length, class floor, cleaning.

    Cleaning means the text equals clean(text): lower-cased, normalised, no raw card, email or phone.

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
    if df["row_id"].duplicated().any():
        raise DataQualityError(f"{name}: row_id values are not unique")
    if text.str.contains(_MARKUP).any():
        raise DataQualityError(f"{name}: {int(text.str.contains(_MARKUP).sum())} rows with HTML or mojibake")
    uncleaned = [t for t in text if clean(t).text != t]
    if uncleaned:
        raise DataQualityError(f"{name}: {len(uncleaned)} rows are not clean (raw PII or not normalised)")
    lengths = text.str.len()
    if lengths.min() < MIN_CHARS or lengths.max() > MAX_CHARS:
        raise DataQualityError(
            f"{name}: text length outside {MIN_CHARS}..{MAX_CHARS} (min {lengths.min()}, max {lengths.max()})"
        )
    min_per_class = min_per_class or CLASS_FLOOR.get(name, MIN_PER_CLASS)
    counts = df["intent"].value_counts().reindex(INTENTS, fill_value=0)
    thin = counts[counts < min_per_class]
    if len(thin):
        raise DataQualityError(f"{name}: classes below {min_per_class} rows: {thin.to_dict()}")


def check_splits(splits: dict[str, pd.DataFrame]) -> None:
    """Check the splits together: ids, test size, no shared text, no test leak, labels look right."""
    names = list(splits)
    all_ids = pd.concat([splits[n]["row_id"] for n in names])
    if all_ids.duplicated().any():
        raise DataQualityError("row_id values repeat across splits")
    if "test" in splits and len(splits["test"]) != EXPECTED_TEST_ROWS:
        raise DataQualityError(f"test has {len(splits['test'])} rows, expected {EXPECTED_TEST_ROWS}")
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = set(splits[a]["text"]) & set(splits[b]["text"])
            if shared:
                raise DataQualityError(f"leak: {len(shared)} texts appear in both {a} and {b}")
    if "train" in splits and "test" in splits:
        hits, _ = near_duplicates(splits["test"]["text"].tolist(), splits["train"]["text"].tolist(), LEAK_COSINE)
        if len(hits):
            raise DataQualityError(f"leak: {len(hits)} train texts are near copies of a test text")
    _check_label_agreement(splits)


def _check_label_agreement(splits: dict[str, pd.DataFrame]) -> None:
    """Shuffled or wrong labels make the most-similar-text label agreement drop below the floor."""
    if not {"train", "val", "stream"} <= set(splits):
        return
    train = splits["train"]
    scores = [
        nearest_label_agreement(
            train["text"].tolist(), train["intent"].tolist(), splits[n]["text"].tolist(), splits[n]["intent"].tolist()
        )
        for n in ("val", "stream")
    ]
    if sum(scores) / 2 < MIN_LABEL_AGREEMENT:
        raise DataQualityError(
            f"labels look inconsistent: nearest-text agreement {sum(scores) / 2:.3f} < {MIN_LABEL_AGREEMENT}"
        )
