"""The one interface every classifier implements."""
from typing import Protocol

import numpy as np


class Classifier(Protocol):
    """Anything that turns cleaned texts into intent probabilities."""

    version: str

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Return shape (n, 77); columns follow taxonomy.INTENTS; rows sum to 1."""
        ...
