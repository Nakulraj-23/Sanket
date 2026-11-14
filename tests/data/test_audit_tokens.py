"""Q1 check 3: label-pure tokens (support >= 30, one intent only) and digit shortcuts."""
import re
from collections import Counter, defaultdict

from _audit_util import read_split


def _support_by_intent() -> dict[str, Counter]:
    """For every word: how many train rows of each intent contain it."""
    train = read_split("train")
    counts: dict[str, Counter] = defaultdict(Counter)
    for text, intent in zip(train["text"], train["intent"]):
        for word in set(re.findall(r"\w+", text)):
            counts[word][intent] += 1
    return counts


def test_label_pure_tokens_are_only_legitimate_words():
    counts = _support_by_intent()
    pure = {w for w, c in counts.items() if len(c) == 1 and sum(c.values()) >= 30}
    assert pure == {"auto"}  # "auto top-up": a real word, not an id or template marker


def test_only_known_digit_shortcut():
    counts = _support_by_intent()
    digits = {w for w, c in counts.items() if any(ch.isdigit() for ch in w) and sum(c.values()) >= 30}
    assert digits == {"1"}  # "$1 / £1 charge": 60 of 62 rows are extra_charge_on_statement
