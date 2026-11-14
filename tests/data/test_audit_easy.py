"""Q1 check 2: the task is not too easy. Trivial baselines stay far below TF-IDF + LR on val."""
import numpy as np
from _audit_util import read_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.tree import DecisionTreeClassifier


def _macro_f1(y_true, y_pred) -> float:
    """Intent macro-F1, the project's headline metric."""
    return f1_score(y_true, y_pred, average="macro")


def test_trivial_baselines_are_weak_and_lr_is_in_band():
    train, val = read_split("train"), read_split("val")
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)
    x_train, x_val = vec.fit_transform(train["text"]), vec.transform(val["text"])
    majority = train["intent"].value_counts().idxmax()
    scores = {"majority": _macro_f1(val["intent"], [majority] * len(val))}
    tree = DecisionTreeClassifier(max_depth=3, random_state=42).fit(x_train, train["intent"])
    scores["tree_depth3"] = _macro_f1(val["intent"], tree.predict(x_val))

    def lengths(df):
        return np.c_[df["text"].str.len(), df["text"].str.split().str.len()]

    by_length = DecisionTreeClassifier(max_depth=6, random_state=42).fit(lengths(train), train["intent"])
    scores["length_only"] = _macro_f1(val["intent"], by_length.predict(lengths(val)))
    lr = LogisticRegression(C=10, max_iter=2000).fit(x_train, train["intent"])
    scores["tfidf_lr"] = _macro_f1(val["intent"], lr.predict(x_val))
    assert max(v for k, v in scores.items() if k != "tfidf_lr") < 0.5, scores
    assert 0.85 <= scores["tfidf_lr"] <= 0.93, scores
