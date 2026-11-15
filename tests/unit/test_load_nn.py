"""The neural network is optional: a missing or unreadable model file must not stop the API."""
from sanket.service import load_nn


def test_load_nn_returns_none_when_model_file_is_missing(tmp_path):
    assert load_nn(tmp_path) is None


def test_load_nn_returns_none_when_model_file_is_garbage(tmp_path):
    (tmp_path / "model.onnx").write_bytes(b"not an onnx file")
    assert load_nn(tmp_path) is None
