"""Shared helpers for the Q1 data-audit tests: read splits, token sets, near-duplicate search."""
import re

import pandas as pd

from sanket.config import Settings

NAMES = ["train", "val", "stream", "test"]


def read_split(name: str) -> pd.DataFrame:
    """Read one committed split CSV."""
    return pd.read_csv(Settings().data_dir / "splits" / f"{name}.csv", keep_default_na=False)


def token_set(text: str) -> frozenset:
    """Lower-case word tokens of a text, as a set (for Jaccard similarity)."""
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def near_duplicate_rows(a: list[str], b: list[str], threshold: float = 0.9) -> set[int]:
    """Indexes of texts in `b` that have a different text in `a` with token-set Jaccard >= threshold.

    An inverted index keeps this fast: only pairs that share a word are compared.
    """
    sets_a = [token_set(t) for t in a]
    index: dict[str, list[int]] = {}
    for i, words in enumerate(sets_a):
        for w in words:
            index.setdefault(w, []).append(i)
    hits = set()
    for j, words in enumerate(token_set(t) for t in b):
        shared: dict[int, int] = {}
        for w in words:
            for i in index.get(w, ()):
                shared[i] = shared.get(i, 0) + 1
        for i, inter in shared.items():
            union = len(words) + len(sets_a[i]) - inter
            if inter / union >= threshold and a[i] != b[j]:
                hits.add(j)
                break
    return hits
