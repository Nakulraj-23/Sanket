"""Benchmark baseline vs neural network (make bench): test quality, latency, throughput, size."""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from sanket.config import get_settings
from sanket.pipeline.clean import clean
from sanket.taxonomy import INTENTS, team_of

TEAM_OF_IDX = np.array([team_of(i) for i in INTENTS])


def load_test() -> tuple[list[str], np.ndarray]:
    """Test texts and class indices."""
    df = pd.read_csv(get_settings().data_dir / "splits" / "test.csv")
    index = {n: i for i, n in enumerate(INTENTS)}
    return df["text"].astype(str).tolist(), df["intent"].map(index).to_numpy()


def quality(proba: np.ndarray, y: np.ndarray) -> dict:
    """Intent accuracy, intent macro-F1 and team accuracy from probabilities."""
    pred = proba.argmax(axis=1)
    return {"intent_accuracy": float(accuracy_score(y, pred)),
            "intent_macro_f1": float(f1_score(y, pred, average="macro", labels=range(len(INTENTS)),
                                              zero_division=0)),
            "team_accuracy": float(np.mean(TEAM_OF_IDX[pred] == TEAM_OF_IDX[y]))}


def latency(model, texts: list[str], n: int = 1000, warm: int = 50) -> dict:
    """p50 and p95 in ms of one call: clean the text, then predict one ticket."""
    for t in texts[:warm]:
        model.predict_proba([clean(t).text])
    times = []
    for k in range(n):
        t0 = time.perf_counter()
        model.predict_proba([clean(texts[k % len(texts)]).text])
        times.append((time.perf_counter() - t0) * 1000)
    return {"p50_ms": float(np.percentile(times, 50)), "p95_ms": float(np.percentile(times, 95))}


def throughput(model, texts: list[str], batch: int = 64, rounds: int = 20) -> float:
    """Tickets per second when predicting 64 at a time."""
    chunk = texts[:batch]
    model.predict_proba(chunk)
    t0 = time.perf_counter()
    for _ in range(rounds):
        model.predict_proba(chunk)
    return batch * rounds / (time.perf_counter() - t0)


def measure(name: str, model, size_bytes: int, texts, y) -> dict:
    """All numbers for one model."""
    cleaned = [clean(t).text for t in texts]
    row = {"model": name, "size_mb": round(size_bytes / 1e6, 3)}
    row.update(quality(model.predict_proba(cleaned), y))
    row.update(latency(model, texts))
    row["throughput_per_s"] = throughput(model, cleaned)
    return row


def load_torch_model(nn_dir: Path):
    """The torch version of the net behind the Classifier interface, or None if torch is missing."""
    try:
        import torch
    except ImportError:
        return None
    from sanket.models.nn.net import IntentNet
    from sanket.models.nn.tokenizer import Tokenizer
    torch.set_num_threads(1)
    tok = Tokenizer.load(nn_dir / "vocab.json")
    cfg = json.loads((nn_dir / "variant.json").read_text())["cfg"]
    net = IntentNet(tok.size, cfg["dim"], len(INTENTS))
    net.load_state_dict(torch.load(nn_dir / "model.pt", weights_only=True))
    net.eval()

    class TorchModel:
        version = "nn-torch"

        def predict_proba(self, texts: list[str]) -> np.ndarray:
            ids = torch.tensor([tok.encode(t) for t in texts], dtype=torch.long)
            with torch.no_grad():
                return torch.softmax(net(ids), dim=-1).numpy()

    return TorchModel()


def load_baseline(art: Path):
    """Champion baseline and its file size, or (None, 0) when B2 has not produced one."""
    reg = art / "registry.json"
    if not reg.exists():
        return None, 0
    from sanket.models.baseline import BaselineModel
    version = json.loads(reg.read_text())["champion"]
    path = art / "models" / version
    return BaselineModel.load(path), (path / "model.joblib").stat().st_size


def write_docs(rows: list[dict], variants: dict) -> None:
    """Write docs/bench.md and artifacts/nn/card.json."""
    cols = ["model", "intent_accuracy", "intent_macro_f1", "team_accuracy", "p50_ms", "p95_ms",
            "throughput_per_s", "size_mb"]
    lines = ["# Benchmark (test split, 1 CPU thread)", "", "| " + " | ".join(cols) + " |",
             "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(f"{r[c]:.4f}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    lines += ["", "Latency: 1,000 single-ticket calls after 50 warm-up calls, including `clean`. "
              "Throughput: batch of 64. Variants (val macro-F1): " + json.dumps(variants)]
    root = get_settings().artifacts_dir.parent
    (root / "docs" / "bench.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    info = json.loads((get_settings().artifacts_dir / "nn" / "variant.json").read_text())
    card = {**info, "test": next(r for r in rows if r["model"] == "nn_onnx"), "bench": rows}
    (get_settings().artifacts_dir / "nn" / "card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")


def main() -> None:
    """Measure every available model and write the reports."""
    from sanket.models.nn.onnx_model import OnnxModel
    art = get_settings().artifacts_dir
    nn_dir = art / "nn"
    texts, y = load_test()
    rows = []
    base, base_size = load_baseline(art)
    if base is None:
        print("baseline artifact missing: run make train first; skipping baseline")
    else:
        rows.append(measure("baseline", base, base_size, texts, y))
    torch_model = load_torch_model(nn_dir)
    if torch_model is not None:
        rows.append(measure("nn_torch", torch_model, (nn_dir / "model.pt").stat().st_size, texts, y))
    rows.append(measure("nn_onnx", OnnxModel(nn_dir), (nn_dir / "model.onnx").stat().st_size, texts, y))
    variants = json.loads((nn_dir / "variant.json").read_text())
    write_docs(rows, {"chosen": variants["variant"], "val_macro_f1": round(variants["val_macro_f1"], 4)})
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
