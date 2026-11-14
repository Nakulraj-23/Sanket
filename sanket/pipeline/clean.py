"""Validate and clean one ticket. The same code runs at training time and at serve time."""
import re
import unicodedata
from dataclasses import dataclass

from sanket.pipeline.pii import redact

MAX_CHARS = 2000
_PLACEHOLDER = re.compile(r"(\[(?:EMAIL|PHONE|CARD|ACCOUNT)\])")
_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass
class CleanResult:
    """Cleaned text, how many items of each kind were masked, and its size."""

    text: str
    pii: dict[str, int]
    n_chars: int
    n_tokens: int


def validate(text: str) -> list[str]:
    """List what is wrong with a raw ticket (empty, too_long, no_letters); empty list means ok."""
    problems = []
    if not text or not text.strip():
        problems.append("empty: the message has no text")
        return problems
    if len(text) > MAX_CHARS:
        problems.append(f"too_long: over {MAX_CHARS} characters")
    if not any(ch.isalpha() for ch in text):
        problems.append("no_letters: the message has no letters")
    return problems


def _lower_keep_placeholders(text: str) -> str:
    """Lower-case everything except the [EMAIL]-style placeholders."""
    parts = _PLACEHOLDER.split(text)
    return "".join(p if _PLACEHOLDER.fullmatch(p) else p.lower() for p in parts)


def clean(text: str) -> CleanResult:
    """Mask personal data, then normalise: NFKC, one space between words, lower-case.

    NFKC runs first so look-alike digits (full-width) cannot slip past the masks.
    Devanagari is kept as is. Running clean twice gives the same text.
    """
    text = unicodedata.normalize("NFKC", text)
    masked, pii = redact(text)
    masked = re.sub(r"\s+", " ", masked).strip()
    masked = _lower_keep_placeholders(masked)
    return CleanResult(masked, pii, len(masked), len(_WORD.findall(masked)))
