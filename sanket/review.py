"""The human review step: save a decision exactly once per ticket, and list the waiting queue.

Two reviewers can open the same ticket. The conditional UPDATE below lets only the first one
change the status; the second finds no row to change and gets a conflict. The UNIQUE constraint
on reviews.ticket_id is a second lock behind it.
"""
from datetime import datetime

from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from sanket.db import Prediction, Ticket, utcnow
from sanket.db import Review as ReviewRow
from sanket.schemas import Review, ReviewIn, TicketSummary
from sanket.taxonomy import INTENTS, team_of, urgency_of


class TicketNotFound(LookupError):
    """No ticket has this id."""


class AlreadyReviewed(RuntimeError):
    """Somebody has already reviewed this ticket."""


class BadReview(ValueError):
    """The review request is not valid (unknown intent, missing intent on override)."""


def _final_values(body: ReviewIn, pred: Prediction) -> tuple[str, str]:
    """Work out the final intent and urgency; urgency comes from the taxonomy unless given."""
    if body.action == "confirm":
        intent = pred.intent
        urgency = body.final_urgency or pred.urgency
        return intent, urgency
    if not body.final_intent:
        raise BadReview("override needs final_intent")
    if body.final_intent not in INTENTS:
        raise BadReview(f"unknown intent: {body.final_intent}")
    return body.final_intent, body.final_urgency or urgency_of(body.final_intent)


def review_to_schema(row: ReviewRow) -> Review:
    """Convert a stored row to the API shape."""
    return Review(ticket_id=row.ticket_id, reviewer=row.reviewer, action=row.action,
                  final_intent=row.final_intent, final_team=row.final_team,
                  final_urgency=row.final_urgency, note=row.note, created_at=row.created_at)


def save_review(sessions: sessionmaker, ticket_id: int, body: ReviewIn,
                created_at: datetime | None = None) -> Review:
    """Store one review and mark the ticket reviewed, all or nothing.

    Raises TicketNotFound (404), BadReview (422) or AlreadyReviewed (409).
    """
    if body.action == "override" and body.final_intent is not None and body.final_intent not in INTENTS:
        raise BadReview(f"unknown intent: {body.final_intent}")
    with sessions() as session:
        pred = session.scalars(select(Prediction).where(Prediction.ticket_id == ticket_id)).first()
    if pred is None:
        raise TicketNotFound(f"ticket {ticket_id} not found")
    intent, urgency = _final_values(body, pred)
    try:
        with sessions() as session, session.begin():
            _claim_and_insert(session, ticket_id, body, intent, urgency, created_at)
    except (AlreadyReviewed, IntegrityError):
        raise AlreadyReviewed(f"ticket {ticket_id} was already reviewed") from None
    with sessions() as session:
        row = session.scalars(select(ReviewRow).where(ReviewRow.ticket_id == ticket_id)).one()
        return review_to_schema(row)


def _claim_and_insert(session: Session, ticket_id: int, body: ReviewIn, intent: str,
                      urgency: str, created_at: datetime | None) -> None:
    """Flip the ticket to reviewed only if it is not yet, then insert the review row."""
    claimed = session.execute(
        update(Ticket).where(Ticket.id == ticket_id, Ticket.status != "reviewed")
        .values(status="reviewed"))
    if claimed.rowcount == 0:
        raise AlreadyReviewed()
    session.add(ReviewRow(
        ticket_id=ticket_id, reviewer=body.reviewer, action=body.action, final_intent=intent,
        final_team=team_of(intent), final_urgency=urgency, note=body.note,
        created_at=created_at or utcnow()))


def summary_from_rows(t: Ticket, p: Prediction) -> TicketSummary:
    """One list row built from a ticket and its prediction."""
    return TicketSummary(
        ticket_id=t.id, created_at=t.created_at, status=t.status, text_redacted=t.text_redacted,
        intent=p.intent, team=p.team, urgency=p.urgency, intent_conf=p.intent_conf,
        team_conf=p.team_conf, decision=p.decision, reason=p.reason)


def list_tickets(sessions: sessionmaker, status: str | None, limit: int = 50) -> list[TicketSummary]:
    """List tickets. The review queue is urgent first, then oldest; other lists are newest first."""
    query = select(Ticket, Prediction).join(Prediction, Prediction.ticket_id == Ticket.id)
    if status:
        query = query.where(Ticket.status == status)
    if status == "needs_review":
        rank = case((Prediction.urgency == "high", 0), (Prediction.urgency == "medium", 1), else_=2)
        query = query.order_by(rank, Ticket.created_at, Ticket.id)
    else:
        query = query.order_by(Ticket.created_at.desc(), Ticket.id.desc())
    with sessions() as session:
        return [summary_from_rows(t, p) for t, p in session.execute(query.limit(limit))]


def queue(sessions: sessionmaker, limit: int = 50) -> list[TicketSummary]:
    """The review queue: urgent first, then oldest."""
    return list_tickets(sessions, "needs_review", limit)
