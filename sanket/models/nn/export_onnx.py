"""Export the trained torch network to ONNX with a dynamic batch size (softmax included)."""
from pathlib import Path

import numpy as np
import torch
from torch import nn


class _WithSoftmax(nn.Module):
    """Wrap the net so the ONNX file outputs probabilities, not logits."""

    def __init__(self, net: nn.Module):
        super().__init__()
        self.net = net

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """Probabilities for a batch of id lists."""
        return torch.softmax(self.net(ids), dim=-1)


def export(net: nn.Module, seq_len: int, path: Path) -> None:
    """Write model.onnx; input `ids` (batch, seq_len) int64, output `proba` (batch, 77)."""
    net.eval()
    dummy = torch.zeros(2, seq_len, dtype=torch.long)
    torch.onnx.export(_WithSoftmax(net), (dummy,), str(path), input_names=["ids"],
                      output_names=["proba"], dynamic_axes={"ids": {0: "batch"}, "proba": {0: "batch"}},
                      opset_version=17, dynamo=False)


def torch_proba(net: nn.Module, ids: np.ndarray) -> np.ndarray:
    """Probabilities from the torch model, for the parity test."""
    net.eval()
    with torch.no_grad():
        return torch.softmax(net(torch.tensor(ids, dtype=torch.long)), dim=-1).numpy()
