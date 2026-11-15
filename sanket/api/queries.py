"""Database reads for the API: rebuilt tickets, live drift inputs, metrics and the scenario."""
from collections import Counter
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select, text

from sanket.db import DriftReport, Prediction, Ticket, utcnow
from sanket.db import Review as ReviewRow
from sanket.monitoring.drift import drift_report
from sanket.pipeline.perturb import hinglishify
from sanket.review import review_to_schema
from sanket.schemas import DriftReportOut, PredictionOut, TicketResult
from sanket.service import InvalidTicket, Runtime, analyse, build_trace, process_ticket

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "metrics.sql"
DRIFT_WINDOW = 500
SURGE_START, SURGE_SIZE = 400, 300  # stream rows 400..699; the seed script uses rows 0..399


def get_ticket_result(rt: Runtime, ticket_id: int) -> TicketResult | None:
    """Rebuild a ticket's result from stored rows; the trace is re-run on the stored cleaned text.

    The raw text is gone by design, so ingest and clean show what was stored, and the stage
    times are fresh measurements of the re-run, not the original ones.
    """
    with rt.sessions() as session:
        ticket = session.get(Ticket, ticket_id)
        pred = session.scalars(select(Prediction).where(Prediction.ticket_id == ticket_id)).first()
        review = session.scalars(select(ReviewRow).where(ReviewRow.ticket_id == ticket_id)).first()
    if ticket is None or pred is None:
        return None
    an = analyse(rt, ticket.text_redacted)
    detail = {"before_masked": ticket.text_redacted, "after": ticket.text_redacted,
              "pii": ticket.pii_json}
    trace = build_trace(rt, an, (0.0, {"problems": []}), (0.0, detail))
    stored = PredictionOut(
        intent=pred.intent, intent_conf=pred.intent_conf, top_intents=an.decision.top_intents,
        team=pred.team, team_conf=pred.team_conf, team_probs=an.decision.team_probs,
        urgency=pred.urgency, p_high=pred.p_high, decision=pred.decision, reason=pred.reason,
        model_version=pred.model_version, top_terms=pred.top_terms_json, latency_ms=pred.latency_ms)
    return TicketResult(
        ticket_id=ticket.id, created_at=ticket.created_at, status=ticket.status,
        text_redacted=ticket.text_redacted, prediction=stored, trace=trace,
        review=review_to_schema(review) if review else None)


def live_inputs(rt: Runtime, window: int = DRIFT_WINDOW) -> dict:
    """The same four things reference.json holds, taken from the latest `window` tickets."""
    query = (select(Ticket.n_tokens, Ticket.oov_rate, Prediction.team_conf, Prediction.team)
             .join(Prediction, Prediction.ticket_id == Ticket.id)
             .order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(window))
    with rt.sessions() as session:
        rows = session.execute(query).all()
    teams = Counter(r.team for r in rows)
    n = max(len(rows), 1)
    return {"n_tokens": [r.n_tokens for r in rows], "oov_rate": [r.oov_rate for r in rows],
            "team_conf": [r.team_conf for r in rows], "team_mix": {t: c / n for t, c in teams.items()}}


def compute_drift(rt: Runtime) -> dict:
    """A drift report over the latest tickets (not stored)."""
    return drift_report(rt.reference, live_inputs(rt), rt.model_version)


def run_drift(rt: Runtime) -> DriftReportOut:
    """Compute a drift report, store it and return it."""
    report = compute_drift(rt)
    with rt.sessions() as session, session.begin():
        session.add(DriftReport(created_at=utcnow(), status=report["status"],
                                n_tickets=report["n_tickets"], report_json=report))
    return DriftReportOut(**report)


def latest_drift(rt: Runtime) -> DriftReportOut:
    """The newest stored report, or a fresh unsaved one if none has been stored yet."""
    with rt.sessions() as session:
        row = session.scalars(select(DriftReport).order_by(DriftReport.id.desc())).first()
        report = row.report_json if row else None
    return DriftReportOut(**(report or compute_drift(rt)))


def _named_queries() -> dict[str, str]:
    """Split metrics.sql into its named queries."""
    parts, name = {}, None
    for line in SQL_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- name:"):
            name = line.split(":", 1)[1].strip()
            parts[name] = ""
        elif name:
            parts[name] += line + "\n"
    return parts


def metrics(rt: Runtime) -> dict:
    """Run the three queries in sql/metrics.sql and shape the result like fixtures/metrics.json."""
    q = _named_queries()
    with rt.engine.connect() as conn:
        by_team = conn.execute(text(q["override_rate_by_team"])).all()
        by_day = conn.execute(text(q["auto_share_by_day"])).all()
        by_model = conn.execute(text(q["latency_by_model"])).all()
    return {
        "override_rate_by_team": {r.team: round(r.rate, 4) for r in by_team},
        "auto_share_by_day": [{"day": r.day, "auto_share": round(r.auto_share, 4), "n": r.n}
                              for r in by_day],
        "latency_by_model": {r.model_version: {"avg_ms": round(r.avg_ms, 3), "n": float(r.n)}
                             for r in by_model},
    }


def run_scenario(rt: Runtime, name: str) -> int:
    """hinglish_surge: push up to 300 Hinglish-ified stream rows through the pipeline. reset: remove them."""
    if name == "reset":
        return reset_scenario(rt)
    stream = pd.read_csv(rt.settings.data_dir / "splits" / "stream.csv")
    rows = stream["text"].astype(str).tolist()[SURGE_START:SURGE_START + SURGE_SIZE]
    inserted = 0
    for i, text_ in enumerate(rows):
        try:
            process_ticket(hinglishify(text_, rt.settings.seed + i), "scenario", rt)
            inserted += 1
        except InvalidTicket:
            continue
    return inserted


def reset_scenario(rt: Runtime) -> int:
    """Delete every ticket made by a scenario, with its prediction and review."""
    with rt.sessions() as session, session.begin():
        ids = list(session.scalars(select(Ticket.id).where(Ticket.channel == "scenario")))
        for table in (ReviewRow, Prediction):
            session.execute(delete(table).where(table.ticket_id.in_(ids)))
        session.execute(delete(Ticket).where(Ticket.id.in_(ids)))
    return 0
