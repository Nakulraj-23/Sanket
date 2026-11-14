"""Text similarity helpers for the data checks: near-duplicates and label agreement.

Both use TF-IDF word vectors and cosine similarity. Nothing here is a model we ship.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

CHUNK = 500


def _best_match(vec_a, vec_b) -> tuple[np.ndarray, np.ndarray]:
    """For each row of `vec_b`, return the highest cosine to any row of `vec_a` and that row's index."""
    scores = np.zeros(vec_b.shape[0], dtype=np.float32)
    index = np.zeros(vec_b.shape[0], dtype=np.int64)
    for start in range(0, vec_b.shape[0], CHUNK):
        sims = (vec_b[start:start + CHUNK] @ vec_a.T).toarray()
        index[start:start + CHUNK] = sims.argmax(axis=1)
        scores[start:start + CHUNK] = sims.max(axis=1)
    return scores, index


def near_duplicates(
    a_texts: list[str], b_texts: list[str], threshold: float = 0.9
) -> tuple[np.ndarray, np.ndarray]:
    """Return (positions in b, positions in a) of pairs whose TF-IDF cosine is above `threshold`."""
    vectorizer = TfidfVectorizer().fit(list(a_texts) + list(b_texts))
    scores, index = _best_match(vectorizer.transform(a_texts), vectorizer.transform(b_texts))
    hit = np.where(scores > threshold)[0]
    return hit, index[hit]


def nearest_label_agreement(
    ref_texts: list[str], ref_labels: list[str], texts: list[str], labels: list[str]
) -> float:
    """Share of `texts` whose single most similar reference text has the same label.

    Shuffled labels in the reference set make this number fall, so it is a label sanity check.
    """
    vectorizer = TfidfVectorizer().fit(list(ref_texts) + list(texts))
    _, index = _best_match(vectorizer.transform(ref_texts), vectorizer.transform(texts))
    ref = np.asarray(ref_labels)
    return float((ref[index] == np.asarray(labels)).mean())
