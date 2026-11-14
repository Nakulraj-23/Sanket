"""The small neural network: average the word vectors, then two linear layers."""
import torch
from torch import nn


class IntentNet(nn.Module):
    """Embedding, mean over real tokens, dropout, Linear(dim, 128), ReLU, Linear(128, n_classes)."""

    def __init__(self, vocab_size: int, dim: int = 64, n_classes: int = 77, dropout: float = 0.3):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, dim, padding_idx=0)  # one vector per id; pad stays zero
        self.drop = nn.Dropout(dropout)  # randomly hides parts of the average while training
        self.hidden = nn.Linear(dim, 128)  # mixes the dimensions of the averaged vector
        self.out = nn.Linear(128, n_classes)  # one score (logit) per intent

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """Return logits of shape (batch, n_classes) for ids of shape (batch, length)."""
        mask = (ids != 0).unsqueeze(-1).float()  # 1 for real tokens, 0 for padding
        vectors = self.embed(ids) * mask  # look up vectors, zero out padding
        mean = vectors.sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)  # average over real tokens only
        hidden = torch.relu(self.hidden(self.drop(mean)))  # dropout, linear layer, ReLU
        return self.out(hidden)  # final scores
