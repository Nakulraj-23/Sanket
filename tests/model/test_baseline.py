"""BaselineModel on a small training set: shapes, explanation arithmetic, save and load."""
import numpy as np
import pandas as pd
import pytest

from sanket.config import Settings
from sanket.models.baseline import BaselineModel, BaselineParams
from sanket.taxonomy import INTENTS


@pytest.fixture(scope="module")
def small_model() -> BaselineModel:
    df = pd.read_csv(Settings().data_dir / "splits" / "train.csv").groupby("intent").head(8)
    return BaselineModel.fit(df["text"].tolist(), df["intent"].tolist(), BaselineParams(C=10), "t")


def test_predict_proba_shape_and_sums(small_model: BaselineModel) -> None:
    p = small_model.predict_proba(["my card has not arrived", "what is the exchange rate"])
    assert p.shape == (2, len(INTENTS))
    assert np.allclose(p.sum(axis=1), 1.0)


def test_explain_contributions_plus_intercept_equal_raw_score(small_model: BaselineModel) -> None:
    text = "i lost my card yesterday and someone used it abroad"
    intent = "lost_or_stolen_card"
    terms = small_model.explain(text, intent, k=100000)
    intercept = float(small_model.intercept[INTENTS.index(intent)])
    assert abs(sum(t["weight"] for t in terms) + intercept - small_model.raw_score(text, intent)) < 1e-5


def test_explain_returns_k_sorted_terms(small_model: BaselineModel) -> None:
    terms = small_model.explain("my card payment was declined", "declined_card_payment", k=3)
    weights = [t["weight"] for t in terms]
    assert len(terms) == 3 and weights == sorted(weights, reverse=True)


def test_oov_rate(small_model: BaselineModel) -> None:
    assert small_model.oov_rate("") == 0.0
    assert small_model.oov_rate("zzzqqq xxyyzz") == 1.0
    assert small_model.oov_rate("my card") < 0.5


def test_save_load_roundtrip(small_model: BaselineModel, tmp_path) -> None:
    small_model.save(tmp_path)
    again = BaselineModel.load(tmp_path)
    texts = ["card not working", "top up failed"]
    assert np.allclose(small_model.predict_proba(texts), again.predict_proba(texts))
    assert again.coef.dtype == np.float32
