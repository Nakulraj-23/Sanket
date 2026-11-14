"""Q1 check 1: leakage across splits (exact, normalised, near-duplicate) and the frozen test set."""
import itertools
import re

import pytest
from _audit_util import NAMES, near_duplicate_rows, read_split

from sanket.pipeline.clean import clean
from sanket.pipeline.load import load_raw

# Measured by Q1 on 2026-11-14. Near-duplicates are paraphrases inside Banking77 itself.
MAX_NEAR_DUP_ROWS = {("train", "test"): 95, ("train", "val"): 35, ("train", "stream"): 40}


def _norm(text: str) -> str:
    """Letters and digits only, single spaces: punctuation and hyphen variants collapse."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def test_no_exact_overlap_and_few_normalised():
    splits = {n: read_split(n) for n in NAMES}
    for a, b in itertools.combinations(NAMES, 2):
        assert not set(splits[a]["text"]) & set(splits[b]["text"]), (a, b)
        shared = set(map(_norm, splits[a]["text"])) & set(map(_norm, splits[b]["text"]))
        assert len(shared) <= 15, (a, b, len(shared))


@pytest.mark.parametrize("pair", list(MAX_NEAR_DUP_ROWS))
def test_near_duplicates_stay_below_measured_level(pair):
    a, b = (read_split(n) for n in pair)
    rows = near_duplicate_rows(list(a["text"]), list(b["text"]))
    assert len(rows) <= MAX_NEAR_DUP_ROWS[pair], len(rows)


def test_test_split_is_complete_and_only_cleaned():
    _, raw = load_raw()
    test = read_split("test").set_index("row_id")
    assert len(test) == 3080 and test.index.is_unique
    for row in raw.itertuples():
        stored = test.loc[f"te-{row.row_id}"]
        assert stored["intent"] == row.intent
        assert stored["text"] == clean(row.text).text
