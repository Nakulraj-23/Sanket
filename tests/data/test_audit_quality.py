"""Q1 check 7: corrupt copies of the committed splits and see whether the quality checks notice.

Every corruption must be caught (FIXED = the ones the first version missed).
"""
import numpy as np
import pandas as pd
import pytest
from _audit_util import NAMES, read_split

from sanket.pipeline.quality import DataQualityError, check_frame, check_splits


def _run_checks(splits: dict[str, pd.DataFrame]) -> None:
    """The same checks `make data` runs."""
    for name, df in splits.items():
        check_frame(df, name, allow_duplicates=(name == "test"))
    check_splits(splits)


def _shuffle_labels(s):
    rng = np.random.default_rng(42)
    rows = rng.choice(len(s["train"]), 700, replace=False)
    s["train"].loc[rows, "intent"] = rng.permutation(s["train"].loc[rows, "intent"].to_numpy())


def _add(s, name, rows):
    s[name] = pd.concat([s[name], rows], ignore_index=True)


CAUGHT = {
    "class_dropped": lambda s: s.update(train=s["train"][s["train"]["intent"] != "card_arrival"]),
    "duplicate_rows": lambda s: _add(s, "train", s["train"].head(50)),
    "null_text": lambda s: s["val"].__setitem__("text", s["val"]["text"].where(s["val"].index != 3, None)),
    "columns_swapped": lambda s: s.update(val=s["val"].rename(columns={"text": "intent", "intent": "text"})),
    "text_cut_to_6_chars": lambda s: s["train"].__setitem__("text", s["train"]["text"].str.slice(0, 6)),
}
FIXED = {
    "10pct_labels_shuffled": _shuffle_labels,
    "test_paraphrase_in_train": lambda s: _add(s, "train", s["test"].head(100).assign(text=lambda d: d.text + " ?")),
    "html_and_mojibake": lambda s: s["train"].__setitem__("text", "<br>Ã© " + s["train"]["text"]),
    "raw_card_and_email": lambda s: s["train"].__setitem__("text", s["train"]["text"] + " 4111 1111 1111 1111 a@b.com"),
    "not_lower_cased": lambda s: s["train"].__setitem__("text", s["train"]["text"].str.upper()),
    "class_cut_to_5_rows": lambda s: s.update(train=s["train"].drop(
        s["train"][s["train"]["intent"] == "card_arrival"].index[5:])),
    "row_ids_identical": lambda s: s["train"].__setitem__("row_id", "tr-1"),
    "ten_test_rows_dropped": lambda s: s.update(test=s["test"].sample(3070, random_state=42)),
}


@pytest.fixture(scope="module")
def splits():
    return {n: read_split(n) for n in NAMES}


@pytest.mark.parametrize("name", list(CAUGHT))
def test_corruption_is_caught(splits, name):
    copy = {k: v.copy() for k, v in splits.items()}
    CAUGHT[name](copy)
    with pytest.raises(DataQualityError):
        _run_checks(copy)


@pytest.mark.parametrize("name", list(FIXED))
def test_corruption_caught_after_fix(splits, name):
    copy = {k: v.copy() for k, v in splits.items()}
    FIXED[name](copy)
    with pytest.raises(DataQualityError):
        _run_checks(copy)
