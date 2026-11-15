"""The ticket pipeline: validate, clean, classify, explain, route, store.

One call to `process_ticket` runs every stage, times each one with `time.perf_counter`, writes
the cleaned ticket and the prediction in a single transaction and returns the full trace.
The raw text only exists in memory for the length of the call. It is never stored or logged.
"""
import json
import re
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from sanket.config import Settings, get_settings
from sanket.db import Prediction, Review, Ticket, init_db, make_engine, session_factory, utcnow
from sanket.models.baseline import BaselineModel
from sanket.pipeline.clean import clean, validate
from sanket.pipeline.pii import ascii_digits, redact, unify_spaces
from sanket.routing.decide import Decision, Thresholds, decide
from sanket.schemas import PredictionOut, TicketResult, TraceStep
from sanket.taxonomy import INTENTS

PLACEHOLDER = re.compile(r"\[(?:EMAIL|UPI|PHONE|CARD|AADHAAR|PAN|ACCOUNT)\]")
ROUTE_RULE = ("human if team_conf < tau_team; also human if oov_rate > oov_max "
              "and team_conf < oov_conf; otherwise auto")


class InvalidTicket(ValueError):
    """The raw text failed `validate`; the message lists the problems."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass
class Runtime:
    """Everything loaded once at start-up: models, thresholds, reference, database."""

    baseline: BaselineModel
    nn: object | None
    thresholds: Thresholds
    reference: dict
    card: dict
    registry: dict
    bench: dict
    engine: object
    sessions: object
    settings: Settings

    @property
    def model_version(self) -> str:
        """Version name of the champion baseline model."""
        return self.baseline.version


def _read_json(path: Path) -> dict:
    """Read one JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_nn(directory: Path):
    """The ONNX network, or None when onnxruntime or its files are missing (e.g. on Vercel).

    The network is only a benchmarked second opinion; the baseline serves every ticket.
    """
    if not (Path(directory) / "model.onnx").exists():
        return None
    try:
        from sanket.models.nn.onnx_model import OnnxModel

        return OnnxModel(directory)
    except Exception:  # noqa: BLE001 - optional component: onnxruntime raises its own error types
        return None


def load_runtime(settings: Settings | None = None) -> Runtime:
    """Load the champion from artifacts/registry.json plus the NN, and open the database."""
    st = settings or get_settings()
    registry = _read_json(st.artifacts_dir / "registry.json")
    mdir = st.artifacts_dir / "models" / registry["champion"]
    nn_card = _read_json(st.artifacts_dir / "nn" / "card.json")
    rows = {r["model"]: r for r in nn_card.get("bench", [])}
    engine = init_db(make_engine(st.db_url))
    return Runtime(
        baseline=BaselineModel.load(mdir), nn=load_nn(st.artifacts_dir / "nn"),
        thresholds=Thresholds(**_read_json(mdir / "thresholds.json")),
        reference=_read_json(mdir / "reference.json"), card=_read_json(mdir / "card.json"),
        registry=registry, bench={"baseline": rows.get("baseline", {}), "nn": rows.get("nn_onnx", {})},
        engine=engine, sessions=session_factory(engine), settings=st)


_RUNTIME: Runtime | None = None


def get_runtime() -> Runtime:
    """The shared runtime, loaded on first use."""
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = load_runtime()
    return _RUNTIME


def mask_with_bullets(raw: str) -> str:
    """The input with every personal character replaced by a bullet, built in memory only.

    `redact` returns text with placeholders. We cut the masked text into the pieces between
    placeholders and find those same pieces in the original; what lies between them was masked.
    """
    norm = ascii_digits(unicodedata.normalize("NFKC", unify_spaces(raw)))
    masked, _ = redact(norm)
    pieces = PLACEHOLDER.split(masked)
    if len(pieces) == 1:
        return norm
    pattern = "^" + "(.+?)".join(re.escape(p) for p in pieces) + "$"
    match = re.match(pattern, norm, re.DOTALL)
    if match is None:
        return masked
    out, last = [], 0
    for i, piece in enumerate(pieces[:-1]):
        out.append(piece)
        out.append("•" * len(match.group(i + 1)))
        last = i + 1
    out.append(pieces[last])
    return "".join(out)


def timed(fn, *args):
    """Call fn(*args) and return (result, milliseconds)."""
    start = time.perf_counter()
    result = fn(*args)
    return result, (time.perf_counter() - start) * 1000


def shown_terms(model: BaselineModel, text: str, intent: str, k: int = 5) -> list[dict]:
    """The k strongest terms; a character piece is hidden when it only repeats a shown word."""
    pool = model.explain(text, intent, k=16)
    words = [t["term"] for t in pool if not t["term"].startswith("~")]
    keep = []
    for t in pool:
        piece = t["term"][1:].strip() if t["term"].startswith("~") else None
        if piece is not None and any(piece in w for w in words):
            continue
        keep.append(t)
    return keep[:k]


@dataclass
class Analysis:
    """Classify, explain and route output for one cleaned text, with the time of each stage."""

    proba: np.ndarray
    oov: float
    decision: Decision
    terms: list[dict]
    ms: dict[str, float]


def analyse(rt: Runtime, text: str) -> Analysis:
    """Run the model, explanation and routing rule on an already cleaned text."""
    (proba, oov), t_cls = timed(lambda: (rt.baseline.predict_proba([text])[0], rt.baseline.oov_rate(text)))
    best = INTENTS[int(np.argmax(proba))]
    terms, t_exp = timed(shown_terms, rt.baseline, text, best)
    decision, t_route = timed(decide, proba, oov, rt.thresholds)
    return Analysis(proba, oov, decision, terms, {"classify": t_cls, "explain": t_exp, "route": t_route})


def build_trace(rt: Runtime, an: Analysis, ingest: tuple, clean_part: tuple) -> list[TraceStep]:
    """Five trace steps. `ingest` and `clean_part` are (ms, detail) pairs made by the caller."""
    d = an.decision
    th = asdict(rt.thresholds)
    steps = [
        ("ingest", ingest[0], "Accepted: no problems found", ingest[1]),
        ("clean", clean_part[0], _clean_summary(clean_part[1]["pii"]), clean_part[1]),
        ("classify", an.ms["classify"], f"Top intent {d.intent} ({d.intent_conf:.0%})",
         {"top_intents": d.top_intents, "oov_rate": round(an.oov, 4)}),
        ("explain", an.ms["explain"], f"{len(an.terms)} terms drove the answer", {"terms": an.terms}),
        ("route", an.ms["route"], f"{d.decision}: {d.reason}",
         {"team_probs": d.team_probs, "p_high": d.p_high, "thresholds": th, "rule": ROUTE_RULE}),
    ]
    return [TraceStep(stage=s, ms=round(ms, 3), summary=sm, detail=dt) for s, ms, sm, dt in steps]


def _clean_summary(pii: dict) -> str:
    """One line saying how much personal data was masked."""
    n = sum(pii.values())
    return f"Masked {n} personal item(s)" if n else "No personal data found"


def prediction_out(rt: Runtime, an: Analysis, latency_ms: float) -> PredictionOut:
    """The Decision plus model bookkeeping, as the API returns it."""
    return PredictionOut(**asdict(an.decision), model_version=rt.model_version,
                         top_terms=an.terms, latency_ms=round(latency_ms, 3))


def _enforce_cap(session: Session, limit: int) -> None:
    """Keep at most `limit` tickets: delete the oldest unreviewed non-seed ones with their rows.

    A reviewed ticket is never deleted: its review is the override log and the retraining label.
    """
    total = session.scalar(select(func.count()).select_from(Ticket)) or 0
    if total <= limit:
        return
    old = select(Ticket.id).where(Ticket.channel != "seed", Ticket.status != "reviewed").order_by(Ticket.created_at, Ticket.id)
    ids = list(session.scalars(old.limit(total - limit)))
    for table in (Review, Prediction):
        session.execute(delete(table).where(table.ticket_id.in_(ids)))
    session.execute(delete(Ticket).where(Ticket.id.in_(ids)))


def store_ticket(rt: Runtime, channel: str, cleaned, an: Analysis, latency_ms: float,
                 created_at: datetime | None = None) -> tuple[int, datetime]:
    """Insert ticket and prediction in one transaction; return (ticket id, created_at)."""
    when = created_at or utcnow()
    d = an.decision
    status = "auto_routed" if d.decision == "auto" else "needs_review"
    with rt.sessions() as session, session.begin():
        ticket = Ticket(created_at=when, channel=channel, text_redacted=cleaned.text,
                        pii_json=cleaned.pii, n_chars=cleaned.n_chars, n_tokens=cleaned.n_tokens,
                        oov_rate=an.oov, status=status)
        session.add(ticket)
        session.flush()
        session.add(Prediction(
            ticket_id=ticket.id, model_version=rt.model_version, intent=d.intent,
            intent_conf=d.intent_conf, team=d.team, team_conf=d.team_conf, urgency=d.urgency,
            p_high=d.p_high, top_terms_json=an.terms, decision=d.decision, reason=d.reason,
            latency_ms=latency_ms, created_at=when))
        _enforce_cap(session, rt.settings.max_tickets)
        return ticket.id, when


def validate_text(text: str) -> list[str]:
    """`validate`, plus a refusal of text that cannot be stored (such as a lone surrogate)."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return ["bad_encoding: the message has characters that cannot be read"]
    return validate(text)


def process_ticket(text: str, channel: str = "web", rt: Runtime | None = None,
                   created_at: datetime | None = None) -> TicketResult:
    """Run every stage on one raw ticket, store it, and return the result with its trace.

    Raises InvalidTicket if the text fails validation (nothing is stored then).
    """
    rt = rt or get_runtime()
    problems, t_ingest = timed(validate_text, text)
    if problems:
        raise InvalidTicket(problems)
    cleaned, t_clean = timed(clean, text)
    detail = {"before_masked": mask_with_bullets(text), "after": cleaned.text, "pii": cleaned.pii}
    an = analyse(rt, cleaned.text)
    latency = t_clean + sum(an.ms.values())
    trace = build_trace(rt, an, (t_ingest, {"problems": problems}), (t_clean, detail))
    ticket_id, when = store_ticket(rt, channel, cleaned, an, latency, created_at)
    status = "auto_routed" if an.decision.decision == "auto" else "needs_review"
    return TicketResult(ticket_id=ticket_id, created_at=when, status=status,
                        text_redacted=cleaned.text, prediction=prediction_out(rt, an, latency),
                        trace=trace, review=None)
