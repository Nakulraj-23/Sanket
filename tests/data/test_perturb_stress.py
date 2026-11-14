"""Perturbation helpers and the hand-written stress files."""
import pandas as pd

from sanket.config import Settings
from sanket.pipeline.perturb import PHRASES, WORDS, add_typos, hinglishify
from sanket.taxonomy import INTENTS, team_of, urgency_of

TEXT = "my card is not working and i want to know why my money was charged twice"


def test_deterministic():
    assert add_typos(TEXT, 0.2, 1) == add_typos(TEXT, 0.2, 1)
    assert hinglishify(TEXT, 1) == hinglishify(TEXT, 1)


def test_typos_change_text_only_with_rate():
    assert add_typos(TEXT, 0.0, 1) == TEXT
    assert add_typos(TEXT, 0.3, 1) != TEXT


def test_hinglish_changes_text_and_dictionary_size():
    assert len(PHRASES) + len(WORDS) >= 80
    assert "kaam nahi kar raha" in hinglishify("my card is not working", 1)


def test_hinglish_stress_file():
    df = pd.read_csv(Settings().data_dir / "stress" / "hinglish.csv", keep_default_na=False)
    assert len(df) == 60
    assert df["script"].value_counts().to_dict() == {"roman": 46, "devanagari": 10, "mixed": 4}
    assert set(df["intent"]) <= set(INTENTS)
    assert len({team_of(i) for i in df["intent"]}) == 7
    assert (df["urgency"] == "high").sum() >= 15
    assert all(urgency_of(i) == u for i, u in zip(df["intent"], df["urgency"]))
    assert (df["note"].str.len() > 0).all()
