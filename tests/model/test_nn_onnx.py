"""NN challenger: tokenizer, ONNX model against saved expected output, torch parity."""
import json

import numpy as np
import pytest

from sanket.config import get_settings
from sanket.models.nn.onnx_model import OnnxModel
from sanket.models.nn.tokenizer import MAX_LEN, Tokenizer
from sanket.taxonomy import INTENTS

NN_DIR = get_settings().artifacts_dir / "nn"
needs_artifact = pytest.mark.skipif(not (NN_DIR / "model.onnx").exists(), reason="run make train-nn")


def test_tokenizer_basics():
    tok = Tokenizer.fit(["my card is lost", "my card is old", "zebra"], min_count=2)
    ids = tok.encode("my card zzz")
    assert len(ids) == MAX_LEN and ids[2] == 1 and ids[3] == 0
    assert "zebra" not in tok.vocab
    tri = Tokenizer.fit(["my card"], min_count=1, trigram_buckets=64)
    assert len(tri.encode("card")) == tri.seq_len


@needs_artifact
def test_onnx_matches_expected_without_torch():
    exp = json.loads((NN_DIR / "expected.json").read_text())
    proba = OnnxModel(NN_DIR).predict_proba(exp["texts"])
    assert proba.shape == (20, len(INTENTS))
    assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-5)
    assert np.abs(proba - np.array(exp["proba"])).max() < 1e-4


@needs_artifact
def test_torch_onnx_parity_200_texts():
    pytest.importorskip("torch")
    import pandas as pd

    from sanket.bench import load_torch_model
    texts = pd.read_csv(get_settings().data_dir / "splits" / "val.csv")["text"].astype(str).tolist()[:200]
    a = load_torch_model(NN_DIR).predict_proba(texts)
    b = OnnxModel(NN_DIR).predict_proba(texts)
    assert np.abs(a - b).max() < 1e-4


@needs_artifact
def test_nn_artifact_size():
    assert (NN_DIR / "model.onnx").stat().st_size < 10_000_000
