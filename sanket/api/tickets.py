"""Ticket endpoints: create, list, read, review."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from sanket import review as review_mod
from sanket.api.queries import get_ticket_result
from sanket.schemas import Review, ReviewIn, TicketCreate, TicketResult, TicketSummary
from sanket.service import InvalidTicket, process_ticket

router = APIRouter()


@router.post("/tickets", response_model=TicketResult, status_code=201)
def create_ticket(body: TicketCreate, request: Request) -> TicketResult:
    """Run the full pipeline on one message and return every stage's output."""
    try:
        return process_ticket(body.text, body.channel, request.app.state.runtime)
    except InvalidTicket as err:
        raise HTTPException(status_code=422, detail=str(err)) from None


@router.get("/tickets", response_model=list[TicketSummary])
def list_tickets(
    request: Request,
    status: Literal["auto_routed", "needs_review", "reviewed"] | None = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[TicketSummary]:
    """List tickets; needs_review comes urgent first, then oldest."""
    return review_mod.list_tickets(request.app.state.runtime.sessions, status, limit)


@router.get("/tickets/{ticket_id}", response_model=TicketResult)
def read_ticket(ticket_id: int, request: Request) -> TicketResult:
    """One ticket with its trace rebuilt from stored rows."""
    result = get_ticket_result(request.app.state.runtime, ticket_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")
    return result


@router.post("/tickets/{ticket_id}/review", response_model=Review)
def review_ticket(ticket_id: int, body: ReviewIn, request: Request) -> Review:
    """Confirm or override the prediction. A second review of the same ticket gets 409."""
    try:
        return review_mod.save_review(request.app.state.runtime.sessions, ticket_id, body)
    except review_mod.TicketNotFound as err:
        raise HTTPException(status_code=404, detail=str(err)) from None
    except review_mod.AlreadyReviewed as err:
        raise HTTPException(status_code=409, detail=str(err)) from None
    except review_mod.BadReview as err:
        raise HTTPException(status_code=422, detail=str(err)) from None
