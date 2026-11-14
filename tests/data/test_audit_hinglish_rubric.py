"""Q1 checks 5, 8, 9: class balance per team and urgency, the Hinglish set, byte-identical splits."""
import re

import pandas as pd
from _audit_util import NAMES, read_split, token_set

from sanket.config import Settings
from sanket.pipeline.clean import clean
from sanket.pipeline.split import build_splits
from sanket.taxonomy import TEAM_NAMES, team_of, urgency_of

DEVANAGARI = re.compile("[ऀ-ॿ]")


def _hinglish() -> pd.DataFrame:
    """The hand-written Hinglish stress set."""
    return pd.read_csv(Settings().data_dir / "stress" / "hinglish.csv", keep_default_na=False)


def test_team_and_urgency_balance_in_every_split():
    shares = {n: read_split(n)["intent"].map(team_of).value_counts(normalize=True) for n in NAMES}
    for name in NAMES:
        assert set(shares[name].index) == set(TEAM_NAMES)
        assert shares[name].min() >= 0.05, name
        assert (read_split(name)["intent"].map(urgency_of) == "high").mean() >= 0.10, name
    for name in ("val", "stream"):
        assert (shares[name] - shares["train"]).abs().max() < 0.01, name


def test_hinglish_not_copied_and_clean_is_safe():
    df = _hinglish()
    dataset = [token_set(t) for n in NAMES for t in read_split(n)["text"]]
    for text in df["text"]:
        words = token_set(text)
        assert max(len(words & d) / len(words | d) for d in dataset if d) < 0.6, text
        once = clean(text).text
        assert clean(once).text == once
        assert DEVANAGARI.findall(once) == DEVANAGARI.findall(text)
    assert df["text"].is_unique


def test_hinglish_script_column_matches_characters():
    for text, script in zip(_hinglish()["text"], _hinglish()["script"]):
        has_dev, has_lat = bool(DEVANAGARI.search(text)), bool(re.search("[A-Za-z]", text))
        actual = "mixed" if has_dev and has_lat else "devanagari" if has_dev else "roman"
        assert actual == script, text


def test_splits_are_byte_identical_to_a_fresh_build(tmp_path):
    for attempt in ("a", "b"):
        splits, _ = build_splits(42)
        for name, df in splits.items():
            df.to_csv(tmp_path / f"{name}_{attempt}.csv", index=False)
    for name in NAMES:
        committed = (Settings().data_dir / "splits" / f"{name}.csv").read_bytes()
        assert (tmp_path / f"{name}_a.csv").read_bytes() == committed
        assert (tmp_path / f"{name}_b.csv").read_bytes() == committed
