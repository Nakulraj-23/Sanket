"""Train the PyTorch challenger (make train-nn). CPU only, seed 42, three variants at most.

Each variant is trained with early stopping on validation macro-F1. The best variant by
validation score is exported to artifacts/nn/. The test split is not touched here.
"""
import json
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
from torch import nn

from sanket.config import get_settings
from sanket.models.nn.export_onnx import export, torch_proba
from sanket.models.nn.net import IntentNet
from sanket.models.nn.tokenizer import Tokenizer
from sanket.taxonomy import INTENTS

VARIANTS = {
    "words_d64": {"dim": 64, "trigram_buckets": 0},
    "words_trigrams_d64": {"dim": 64, "trigram_buckets": 8192},
    "words_trigrams_d128": {"dim": 128, "trigram_buckets": 8192},
}
torch.set_num_threads(1)  # tiny matrices: extra threads only add overhead
MAX_EPOCHS, PATIENCE, BATCH, LR = 60, 6, 64, 2e-3


def load_split(name: str) -> tuple[list[str], np.ndarray]:
    """Texts and class indices (position in INTENTS) of one split."""
    df = pd.read_csv(get_settings().data_dir / "splits" / f"{name}.csv")
    index = {n: i for i, n in enumerate(INTENTS)}
    return df["text"].astype(str).tolist(), df["intent"].map(index).to_numpy()


def macro_f1(net: nn.Module, ids: torch.Tensor, y: np.ndarray) -> float:
    """Macro-F1 of the net on encoded texts."""
    net.eval()
    with torch.no_grad():
        pred = net(ids).argmax(dim=1).numpy()
    return float(f1_score(y, pred, average="macro", labels=range(len(INTENTS)), zero_division=0))


def train_variant(name: str, cfg: dict, data: dict) -> dict:
    """Train one variant; return its best validation score and the net with the best weights."""
    torch.manual_seed(42)
    tok = Tokenizer.fit(data["train"][0], min_count=2, trigram_buckets=cfg["trigram_buckets"])
    x = torch.tensor([tok.encode(t) for t in data["train"][0]], dtype=torch.long)
    y = torch.tensor(data["train"][1], dtype=torch.long)
    xv = torch.tensor([tok.encode(t) for t in data["val"][0]], dtype=torch.long)
    net = IntentNet(tok.size, cfg["dim"], len(INTENTS))
    opt, loss_fn = torch.optim.Adam(net.parameters(), lr=LR), nn.CrossEntropyLoss()
    best, best_state, bad, epochs, gen = -1.0, None, 0, 0, torch.Generator().manual_seed(42)
    for epoch in range(MAX_EPOCHS):
        net.train()
        order = torch.randperm(len(x), generator=gen)
        for s in range(0, len(x), BATCH):
            b = order[s:s + BATCH]
            opt.zero_grad()
            loss_fn(net(x[b]), y[b]).backward()
            opt.step()
        score = macro_f1(net, xv, data["val"][1])
        epochs = epoch + 1
        if score > best:
            best, bad = score, 0
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    net.load_state_dict(best_state)
    return {"name": name, "cfg": cfg, "val_macro_f1": best, "epochs": epochs, "net": net, "tok": tok}


def save_best(result: dict, val_texts: list[str], log: dict) -> None:
    """Write model.onnx, vocab.json, model.pt, expected.json and the variant record."""
    out = get_settings().artifacts_dir / "nn"
    out.mkdir(parents=True, exist_ok=True)
    tok, net = result["tok"], result["net"]
    tok.save(out / "vocab.json")
    torch.save(net.state_dict(), out / "model.pt")
    export(net, tok.seq_len, out / "model.onnx")
    texts = val_texts[::70][:20]
    ids = np.array([tok.encode(t) for t in texts], dtype=np.int64)
    expected = {"texts": texts, "proba": torch_proba(net, ids).round(7).tolist()}
    (out / "expected.json").write_text(json.dumps(expected), encoding="utf-8")
    info = {"variant": result["name"], "cfg": result["cfg"], "vocab_size": tok.size,
            "val_macro_f1": result["val_macro_f1"], "epochs": result["epochs"], "all_variants": log}
    (out / "variant.json").write_text(json.dumps(info, indent=2), encoding="utf-8")


def main() -> None:
    """Train all variants, keep the best by validation macro-F1, export it."""
    data = {s: load_split(s) for s in ("train", "val")}
    results, log = [], {}
    for name, cfg in VARIANTS.items():
        t0 = time.time()
        r = train_variant(name, cfg, data)
        log[name] = {"val_macro_f1": round(r["val_macro_f1"], 4), "epochs": r["epochs"],
                     "seconds": round(time.time() - t0, 1)}
        print(name, log[name], flush=True)
        results.append(r)
    best = max(results, key=lambda r: r["val_macro_f1"])
    save_best(best, data["val"][0], log)
    print("best:", best["name"], json.dumps(log))


if __name__ == "__main__":
    main()
