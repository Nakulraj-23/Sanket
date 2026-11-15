"""Write dist/space/, a folder that can be pushed as a Hugging Face Space (make space-bundle).

It holds only what the image needs: the package, the champion model, the NN files, the stream
split (the seed and the Hinglish scenario read it) and the seed script. Training data, tests,
torch weights and the web app stay out.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "space"
NN_FILES = ["model.onnx", "vocab.json", "card.json", "variant.json"]

README = """---
title: SANKET
emoji: "\U0001F3E6"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

SANKET reads a bank support message, masks card numbers, phone numbers and emails by pattern (not names or addresses), predicts intent, team and urgency,
and sends unsure tickets to a person. This Space runs the API only (`/api/health`, `/api/docs`).
Set the Space variable `SANKET_CORS_ORIGINS` to the address of the web app.
"""

DOCKERFILE = """FROM python:3.11-slim
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY pyproject.toml ./
COPY sanket/ sanket/
RUN pip install --no-cache-dir .
COPY artifacts/ artifacts/
COPY data/ data/
COPY scripts/ scripts/
RUN chown -R app:app /app
USER app
ENV SANKET_DB_URL=sqlite:////app/sanket.db
EXPOSE 7860
CMD ["sh", "-c", "python scripts/seed.py && uvicorn sanket.api.app:app --host 0.0.0.0 --port 7860"]
"""


def copy_files(champion: str) -> None:
    """Copy the package, champion model, NN files, stream split and seed script."""
    shutil.copy(ROOT / "pyproject.toml", OUT / "pyproject.toml")
    shutil.copytree(ROOT / "sanket", OUT / "sanket", ignore=shutil.ignore_patterns("__pycache__"))
    art = OUT / "artifacts"
    (art / "nn").mkdir(parents=True)
    shutil.copy(ROOT / "artifacts" / "registry.json", art / "registry.json")
    shutil.copytree(ROOT / "artifacts" / "models" / champion, art / "models" / champion)
    for name in NN_FILES:
        shutil.copy(ROOT / "artifacts" / "nn" / name, art / "nn" / name)
    (OUT / "data" / "splits").mkdir(parents=True)
    shutil.copy(ROOT / "data" / "splits" / "stream.csv", OUT / "data" / "splits" / "stream.csv")
    (OUT / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "seed.py", OUT / "scripts" / "seed.py")


def main() -> None:
    """Rebuild dist/space from scratch."""
    champion = json.loads((ROOT / "artifacts" / "registry.json").read_text())["champion"]
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    copy_files(champion)
    (OUT / "README.md").write_text(README, encoding="utf-8")
    (OUT / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e6
    print(f"wrote {OUT} ({size:.1f} MB, champion {champion})")


if __name__ == "__main__":
    main()
