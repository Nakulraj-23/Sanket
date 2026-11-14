"""Each data-quality check must fail on a corrupted copy of good data."""
import pandas as pd
import pytest

from sanket.pipeline.quality import DataQualityError, check_frame, check_splits
from sanket.taxonomy import INTENTS


def good_frame(per_class: int = 6, prefix: str = "a") -> pd.DataFrame:
    rows = [(f"{prefix}-{i}-{n}", f"my question number {n} about {i.lower()}", i) for i in INTENTS for n in range(per_class)]
    return pd.DataFrame(rows, columns=["row_id", "text", "intent"])


def test_good_frame_passes():
    check_frame(good_frame(), "good")


def test_null_fails():
    df = good_frame()
    df.loc[0, "text"] = None
    with pytest.raises(DataQualityError, match="null"):
        check_frame(df, "x")


def test_empty_text_fails():
    df = good_frame()
    df.loc[0, "text"] = "   "
    with pytest.raises(DataQualityError, match="empty"):
        check_frame(df, "x")


def test_unknown_intent_fails():
    df = good_frame()
    df.loc[0, "intent"] = "not_an_intent"
    with pytest.raises(DataQualityError, match="unknown"):
        check_frame(df, "x")


def test_duplicate_fails_unless_allowed():
    df = good_frame()
    df.loc[1, "text"] = df.loc[0, "text"]
    with pytest.raises(DataQualityError, match="duplicate"):
        check_frame(df, "x")
    check_frame(df, "x", allow_duplicates=True)


def test_length_bounds_fail():
    short, long_ = good_frame(), good_frame()
    short.loc[0, "text"] = "hi"
    long_.loc[0, "text"] = "a" * 2001
    for df in (short, long_):
        with pytest.raises(DataQualityError, match="length"):
            check_frame(df, "x")


def test_class_floor_fails():
    df = good_frame()
    df = df[df["intent"] != INTENTS[0]]
    with pytest.raises(DataQualityError, match="classes below"):
        check_frame(df, "x")


def test_split_overlap_fails():
    a, b = good_frame(), good_frame(prefix="b")
    b["text"] = b["text"] + " extra"
    check_splits({"a": a, "b": b})
    b.loc[0, "text"] = a.loc[0, "text"]
    with pytest.raises(DataQualityError, match="leak"):
        check_splits({"a": a, "b": b})


def test_uncleaned_text_fails():
    for bad in ("MY QUESTION number about x", "mail me at a@b.com about it", "<br> my question about x"):
        df = good_frame()
        df.loc[0, "text"] = bad
        with pytest.raises(DataQualityError):
            check_frame(df, "x")


def test_duplicate_row_id_fails():
    df = good_frame()
    df.loc[1, "row_id"] = df.loc[0, "row_id"]
    with pytest.raises(DataQualityError, match="row_id"):
        check_frame(df, "x")
