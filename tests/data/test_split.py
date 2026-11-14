"""The committed splits: sizes, no overlap, stratified, deterministic, and a fresh build matches."""
import pandas as pd

from sanket.config import Settings
from sanket.pipeline.load import load_raw
from sanket.pipeline.quality import check_frame, check_splits
from sanket.pipeline.split import build_splits
from sanket.taxonomy import INTENTS

NAMES = ["train", "val", "stream", "test"]


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(Settings().data_dir / "splits" / f"{name}.csv", keep_default_na=False)


def test_columns_and_quality():
    splits = {n: read(n) for n in NAMES}
    for name, df in splits.items():
        assert list(df.columns) == ["row_id", "text", "intent"]
        check_frame(df, name, allow_duplicates=(name == "test"))
    check_splits(splits)


def test_row_counts_add_up():
    raw_train, raw_test = load_raw()
    splits = {n: read(n) for n in NAMES}
    assert len(splits["test"]) == len(raw_test)
    _, removed = build_splits()
    used = sum(len(splits[n]) for n in ("train", "val", "stream"))
    assert used + removed["train_test_overlap"] + removed["train_internal_duplicates"] == len(raw_train)


def test_ratios_and_every_class_everywhere():
    sizes = {n: len(read(n)) for n in ("train", "val", "stream")}
    total = sum(sizes.values())
    assert abs(sizes["train"] / total - 0.70) < 0.01
    assert abs(sizes["val"] / total - 0.15) < 0.01
    assert abs(sizes["stream"] / total - 0.15) < 0.01
    for name in NAMES:
        assert set(read(name)["intent"]) == set(INTENTS)


def test_build_is_deterministic_and_matches_files():
    first, _ = build_splits(42)
    second, _ = build_splits(42)
    for name in NAMES:
        assert first[name].equals(second[name])
        assert first[name].equals(read(name))
