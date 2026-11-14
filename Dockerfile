FROM python:3.11-slim

RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Runtime dependencies only: no torch, no dev tools.
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
CMD ["sh", "-c", "python scripts/seed.py && uvicorn sanket.api.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
