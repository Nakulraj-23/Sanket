"""The baseline classifier: TF-IDF word and character n-grams into multinomial logistic regression.

After training only the vectorisers and two small arrays (coefficients, intercepts) are kept,
as float32, so the saved file stays small and every prediction is plain arithmetic we can show.
"""
import heapq
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from sanket.taxonomy import INTENTS

MAX_WORD_FEATURES = 8000
MAX_CHAR_FEATURES = 15000


@dataclass
class BaselineParams:
    """Settings for one training run."""

    C: float = 10.0
    use_char: bool = True
    max_word: int = MAX_WORD_FEATURES
    max_char: int = MAX_CHAR_FEATURES
    seed: int = 42


def _softmax(scores: np.ndarray) -> np.ndarray:
    """Row-wise softmax in float64 so rows sum to 1."""
    shifted = scores - scores.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def fit_temperature(scores: np.ndarray, y_intent: list[str]) -> float:
    """The single number T that minimises log-loss of softmax(scores / T) on validation data."""
    from scipy.optimize import minimize_scalar

    y = np.array([INTENTS.index(label) for label in y_intent])

    def loss(t: float) -> float:
        p = _softmax(scores / t)
        return float(-np.log(p[np.arange(len(y)), y] + 1e-12).mean())

    return float(minimize_scalar(loss, bounds=(0.2, 3.0), method="bounded").x)


def _make_vectorizers(p: BaselineParams) -> tuple[TfidfVectorizer, TfidfVectorizer | None]:
    """Word 1-2 grams, and optionally character 2-5 grams inside word edges; both sublinear tf."""
    word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=p.max_word,
                           dtype=np.float32)
    char = None
    if p.use_char:
        char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2,
                               max_features=p.max_char, dtype=np.float32)
    return word, char


class BaselineModel:
    """Implements Classifier. Build one with `BaselineModel.fit`, or load a saved one."""

    def __init__(self, version: str, word, char, coef: np.ndarray, intercept: np.ndarray,
                 dtype=np.float32, temperature: float = 1.0) -> None:
        self.version = version
        self.word = word
        self.char = char
        self.coef = coef.astype(dtype)
        self.intercept = intercept.astype(dtype)
        self.temperature = temperature  # one number fitted on val; below 1 sharpens the probabilities
        self._weights = np.ascontiguousarray(self.coef.T.astype(np.float64))  # built once, not per call
        self._unigrams = {t for t in word.vocabulary_ if " " not in t}
        self._tokenize = word.build_tokenizer()
        self._names = self._feature_names()

    @classmethod
    def fit(cls, texts: list[str], labels: list[str], params: BaselineParams, version: str = "dev",
            dtype=np.float32) -> "BaselineModel":
        """Train on cleaned texts and intent names; coefficients are cast to float32 at the end."""
        word, char = _make_vectorizers(params)
        blocks = [word.fit_transform(texts)]
        if char is not None:
            blocks.append(char.fit_transform(texts))
        x = sp.hstack(blocks, format="csr")
        y = np.array([INTENTS.index(label) for label in labels])
        lr = LogisticRegression(C=params.C, max_iter=300, random_state=params.seed)
        lr.fit(x, y)
        coef = np.zeros((len(INTENTS), x.shape[1]), dtype=np.float64)
        intercept = np.full(len(INTENTS), -30.0, dtype=np.float64)  # classes absent from training
        coef[lr.classes_] = lr.coef_
        intercept[lr.classes_] = lr.intercept_
        for vec in (word, char):
            if vec is not None and hasattr(vec, "stop_words_"):
                del vec.stop_words_  # large and only used for inspection
        return cls(version, word, char, coef, intercept, dtype)

    def _feature_names(self) -> list[str]:
        """Names for every column, word terms first then character terms."""
        names = list(self.word.get_feature_names_out())
        if self.char is not None:
            names += [f"~{n}" for n in self.char.get_feature_names_out()]
        return names

    def _features(self, texts: list[str]):
        """The sparse TF-IDF matrix, words and characters side by side."""
        blocks = [self.word.transform(texts)]
        if self.char is not None:
            blocks.append(self.char.transform(texts))
        return sp.hstack(blocks, format="csr")

    def scores(self, texts: list[str]) -> np.ndarray:
        """Raw (pre-softmax) scores, shape (n, 77), float64."""
        return np.asarray(self._features(texts) @ self._weights + self.intercept, dtype=np.float64)

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Return shape (n, 77) probabilities in taxonomy.INTENTS order, scores divided by the temperature."""
        return _softmax(self.scores(texts) / self.temperature)

    def explain(self, text: str, intent: str, k: int = 5) -> list[dict]:
        """The k terms that pushed hardest towards `intent`: weight = coefficient x TF-IDF value.

        Character pieces are shown with a leading "~". Weights plus the intercept add up
        to the intent's raw score before softmax, so nothing is hidden.
        """
        row = self._features([text])
        coef = self.coef[INTENTS.index(intent)]
        pairs = [(float(coef[j] * v), j) for j, v in zip(row.indices, row.data)]
        best = heapq.nlargest(k, pairs)
        return [{"term": self._names[j], "weight": w} for w, j in best]

    def raw_score(self, text: str, intent: str) -> float:
        """Raw (pre-softmax) score of one intent; used by the explain test."""
        row = self._features([text])
        i = INTENTS.index(intent)
        return float((row @ self.coef[i].astype(np.float64))[0] + self.intercept[i])

    def oov_rate(self, text: str) -> float:
        """Share of word tokens that are not in the word vocabulary (0.0 if there are none)."""
        tokens = self._tokenize(text.lower())
        if not tokens:
            return 0.0
        return sum(t not in self._unigrams for t in tokens) / len(tokens)

    def save(self, dir: Path) -> None:
        """Write model.joblib into `dir`."""
        dir.mkdir(parents=True, exist_ok=True)
        state = {"version": self.version, "word": self.word, "char": self.char,
                 "coef": self.coef, "intercept": self.intercept, "temperature": self.temperature}
        joblib.dump(state, dir / "model.joblib", compress=3)

    @classmethod
    def load(cls, dir: Path) -> "BaselineModel":
        """Read model.joblib from a directory under artifacts/ (never from anywhere else)."""
        s = joblib.load(dir / "model.joblib")
        return cls(s["version"], s["word"], s["char"], s["coef"], s["intercept"],
                   temperature=s.get("temperature", 1.0))
