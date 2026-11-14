"""Pydantic models for every API request and response (see CONTRACTS)."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Urgency = Literal["high", "medium", "low"]
DriftStatus = Literal["green", "amber", "red", "insufficient_data"]


class Health(BaseModel):
    """GET /health."""

    status: str
    model_version: str
    tickets: int


class TicketCreate(BaseModel):
    """POST /tickets body."""

    text: str
    channel: Literal["web", "seed", "scenario"] = "web"


class TopIntent(BaseModel):
    """One of the five most likely intents."""

    intent: str
    prob: float


class Term(BaseModel):
    """A word that pushed the model towards its answer."""

    term: str
    weight: float


class PredictionOut(BaseModel):
    """The routing decision plus model bookkeeping."""

    intent: str
    intent_conf: float
    top_intents: list[TopIntent]
    team: str
    team_conf: float
    team_probs: dict[str, float]
    urgency: Urgency
    p_high: float
    decision: Literal["auto", "human"]
    reason: Literal["ok", "low_confidence", "unfamiliar_words"]
    model_version: str
    top_terms: list[Term]
    latency_ms: float


class TraceStep(BaseModel):
    """One pipeline stage as it ran for this ticket."""

    stage: Literal["ingest", "clean", "classify", "explain", "route"]
    ms: float
    summary: str
    detail: dict[str, Any]


class ReviewIn(BaseModel):
    """POST /tickets/{id}/review body."""

    reviewer: str
    action: Literal["confirm", "override"]
    final_intent: str | None = None
    final_urgency: Urgency | None = None
    note: str | None = None


class Review(BaseModel):
    """A stored review."""

    ticket_id: int
    reviewer: str
    action: Literal["confirm", "override"]
    final_intent: str
    final_team: str
    final_urgency: Urgency
    note: str | None = None
    created_at: datetime


class TicketResult(BaseModel):
    """Full view of one ticket."""

    ticket_id: int
    created_at: datetime
    status: Literal["auto_routed", "needs_review", "reviewed"]
    text_redacted: str
    prediction: PredictionOut
    trace: list[TraceStep]
    review: Review | None = None


class TicketSummary(BaseModel):
    """One row of the ticket list."""

    ticket_id: int
    created_at: datetime
    status: Literal["auto_routed", "needs_review", "reviewed"]
    text_redacted: str
    intent: str
    team: str
    urgency: Urgency
    intent_conf: float
    team_conf: float
    decision: Literal["auto", "human"]
    reason: Literal["ok", "low_confidence", "unfamiliar_words"]


class Stage(BaseModel):
    """GET /stages item: a pipeline stage explained next to its code."""

    id: str
    title: str
    what: str
    why: str
    file: str
    function: str
    code: str


class Taxonomy(BaseModel):
    """GET /taxonomy."""

    teams: dict[str, list[str]]
    urgency: dict[str, Urgency]


class CompareIn(BaseModel):
    """POST /compare body."""

    text: str


class ModelAnswer(BaseModel):
    """One model's answer in /compare."""

    intent: str
    conf: float
    ms: float


class CompareOut(BaseModel):
    """POST /compare response."""

    baseline: ModelAnswer
    nn: ModelAnswer


class DriftIndicator(BaseModel):
    """One drift measure. kind is psi or ks; p_value only for ks."""

    name: str
    kind: Literal["psi", "ks"]
    value: float
    p_value: float | None = None
    status: DriftStatus


class DriftReportOut(BaseModel):
    """Drift check of live tickets against the reference from val."""

    created_at: datetime
    status: DriftStatus
    n_tickets: int
    model_version: str
    indicators: list[DriftIndicator]
    team_mix: dict[str, dict[str, float]] = Field(description="reference and live share per team")
    message: str


class Metrics(BaseModel):
    """GET /metrics."""

    override_rate_by_team: dict[str, float]
    auto_share_by_day: list[dict[str, Any]]
    latency_by_model: dict[str, dict[str, float]]


class ModelInfo(BaseModel):
    """GET /model."""

    champion: dict[str, Any]
    registry: dict[str, Any]
    bench: dict[str, Any]


class Inserted(BaseModel):
    """POST /demo/scenario response."""

    inserted: int


class ScenarioIn(BaseModel):
    """POST /demo/scenario body."""

    name: Literal["hinglish_surge", "reset"]
