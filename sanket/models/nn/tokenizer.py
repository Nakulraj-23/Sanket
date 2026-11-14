"""Turn cleaned text into a fixed-length list of integer ids. Plain Python, no torch.

Ids: 0 = padding, 1 = unknown word. The vocabulary comes from the training split only.
Optional extra ids: every character trigram of every word is hashed into a fixed number of
buckets, which helps with spelling mistakes and unseen word forms.
"""
import json
import re
import zlib
from collections import Counter
from pathlib import Path

PAD, UNK = 0, 1
MAX_LEN = 48
TRIGRAM_SLOTS = 96
_WORD = re.compile(r"\w+", re.UNICODE)


def words(text: str) -> list[str]:
    """Lower-case word tokens of an already cleaned text."""
    return _WORD.findall(text.lower())


class Tokenizer:
    """Maps text to ids using a saved vocabulary."""

    def __init__(self, vocab: dict[str, int], trigram_buckets: int = 0, max_len: int = MAX_LEN):
        self.vocab = vocab
        self.trigram_buckets = trigram_buckets
        self.max_len = max_len

    @property
    def size(self) -> int:
        """Number of rows the embedding table needs: words plus trigram buckets."""
        return len(self.vocab) + 2 + self.trigram_buckets

    @property
    def seq_len(self) -> int:
        """Length of every id list this tokenizer returns."""
        return self.max_len + (TRIGRAM_SLOTS if self.trigram_buckets else 0)

    @classmethod
    def fit(cls, texts: list[str], min_count: int = 2, trigram_buckets: int = 0) -> "Tokenizer":
        """Build the vocabulary from training texts; words seen fewer than min_count times are dropped."""
        counts = Counter(w for t in texts for w in words(t))
        kept = sorted(w for w, c in counts.items() if c >= min_count)
        return cls({w: i + 2 for i, w in enumerate(kept)}, trigram_buckets)

    def _trigram_ids(self, tokens: list[str]) -> list[int]:
        """Hash each character trigram of each word to a bucket id placed after the word ids."""
        base = len(self.vocab) + 2
        ids = []
        for w in tokens:
            padded = f"<{w}>"
            for k in range(len(padded) - 2):
                ids.append(base + zlib.crc32(padded[k:k + 3].encode()) % self.trigram_buckets)
        return ids[:TRIGRAM_SLOTS]

    def encode(self, text: str) -> list[int]:
        """Ids for one text, cut or padded to seq_len."""
        tokens = words(text)[: self.max_len]
        ids = [self.vocab.get(w, UNK) for w in tokens]
        ids += [PAD] * (self.max_len - len(ids))
        if self.trigram_buckets:
            tri = self._trigram_ids(tokens)
            ids += tri + [PAD] * (TRIGRAM_SLOTS - len(tri))
        return ids

    def save(self, path: Path) -> None:
        """Write vocab.json."""
        data = {"vocab": self.vocab, "trigram_buckets": self.trigram_buckets, "max_len": self.max_len}
        path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Tokenizer":
        """Read vocab.json."""
        d = json.loads(path.read_text(encoding="utf-8"))
        return cls(d["vocab"], d["trigram_buckets"], d["max_len"])
