"""Serve the neural network with onnxruntime only (no torch)."""
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort

from sanket.config import get_settings
from sanket.models.nn.tokenizer import Tokenizer


class OnnxModel:
    """Implements Classifier: predict_proba(texts) -> (n, 77) probabilities."""

    def __init__(self, directory: Path | None = None):
        d = Path(directory) if directory else get_settings().artifacts_dir / "nn"
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(d / "model.onnx"), opts, providers=["CPUExecutionProvider"])
        self.tokenizer = Tokenizer.load(d / "vocab.json")
        card = d / "card.json"
        self.version = "nn-" + json.loads(card.read_text())["variant"] if card.exists() else "nn"

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Probabilities for already cleaned texts, columns in taxonomy.INTENTS order."""
        ids = np.array([self.tokenizer.encode(t) for t in texts], dtype=np.int64)
        return self.session.run(None, {"ids": ids})[0]
