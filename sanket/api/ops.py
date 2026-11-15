"""The other endpoints: health, stages, taxonomy, compare, monitor, scenario, metrics, model."""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func, select

from sanket.api import queries
from sanket.db import Ticket
from sanket.pipeline.clean import clean
from sanket.schemas import (
    CompareIn,
    CompareOut,
    DriftReportOut,
    Health,
    Inserted,
    Metrics,
    ModelAnswer,
    ModelInfo,
    ScenarioIn,
    Stage,
    Taxonomy,
)
from sanket.service import timed, validate_text
from sanket.stages import build_stages
from sanket.taxonomy import INTENTS, taxonomy_payload

router = APIRouter()


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    """Liveness check: status ok, champion version and ticket count."""
    rt = request.app.state.runtime
    with rt.sessions() as session:
        count = session.scalar(select(func.count()).select_from(Ticket)) or 0
    return Health(status="ok", model_version=rt.model_version, tickets=count)


@router.get("/stages", response_model=list[Stage])
def stages(request: Request) -> list[Stage]:
    """The seven stages with their real code."""
    rt = request.app.state.runtime
    return build_stages(rt.card, asdict(rt.thresholds), rt.bench)


@router.get("/taxonomy", response_model=Taxonomy)
def taxonomy() -> dict:
    """Teams with their intents, and the urgency of each intent."""
    return taxonomy_payload()


@router.post("/compare", response_model=CompareOut)
def compare(body: CompareIn, request: Request) -> CompareOut:
    """Run both models on the cleaned text. Nothing is stored."""
    rt = request.app.state.runtime
    problems = validate_text(body.text)
    if problems:
        raise HTTPException(status_code=422, detail="; ".join(problems))
    text = clean(body.text).text
    answers = {}
    for name, model in (("baseline", rt.baseline), ("nn", rt.nn)):
        proba, ms = timed(lambda m=model: m.predict_proba([text])[0])
        best = int(proba.argmax())
        answers[name] = ModelAnswer(intent=INTENTS[best], conf=float(proba[best]), ms=round(ms, 3))
    return CompareOut(**answers)


@router.get("/monitor/drift", response_model=DriftReportOut)
def drift(request: Request) -> DriftReportOut:
    """The latest stored drift report (or a fresh one if none exists yet)."""
    return queries.latest_drift(request.app.state.runtime)


@router.post("/monitor/drift/run", response_model=DriftReportOut)
def drift_run(request: Request) -> DriftReportOut:
    """Compute drift over the latest 500 tickets, store it and return it."""
    return queries.run_drift(request.app.state.runtime)


@router.post("/demo/scenario", response_model=Inserted)
def scenario(body: ScenarioIn, request: Request) -> Inserted:
    """hinglish_surge pushes up to 300 prepared tickets through the pipeline; reset removes them."""
    return Inserted(inserted=queries.run_scenario(request.app.state.runtime, body.name))


@router.get("/metrics", response_model=Metrics)
def metrics(request: Request) -> dict:
    """Override rate by team, auto-routed share by day and latency by model, from sql/metrics.sql."""
    return queries.metrics(request.app.state.runtime)


@router.get("/model", response_model=ModelInfo)
def model(request: Request) -> ModelInfo:
    """The champion's model card, the registry and the benchmark."""
    rt = request.app.state.runtime
    return ModelInfo(champion=rt.card, registry=rt.registry, bench=rt.bench)
