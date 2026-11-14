"""SQLite tables (SQLAlchemy). No raw text and no ground-truth label is stored."""
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from sanket.config import get_settings


def utcnow() -> datetime:
    """Current UTC time (naive, stored as UTC)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base class for all tables."""


class Ticket(Base):
    """One support message after cleaning."""

    __tablename__ = "tickets"
    __table_args__ = (Index("ix_tickets_status_created", "status", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    channel: Mapped[str] = mapped_column(String(16))
    text_redacted: Mapped[str] = mapped_column(Text)
    pii_json: Mapped[dict] = mapped_column(JSON, default=dict)
    n_chars: Mapped[int] = mapped_column(Integer)
    n_tokens: Mapped[int] = mapped_column(Integer)
    oov_rate: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="auto_routed")


class Prediction(Base):
    """The model's answer for a ticket."""

    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_ticket", "ticket_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    model_version: Mapped[str] = mapped_column(String(32))
    intent: Mapped[str] = mapped_column(String(64))
    intent_conf: Mapped[float] = mapped_column(Float)
    team: Mapped[str] = mapped_column(String(32))
    team_conf: Mapped[float] = mapped_column(Float)
    urgency: Mapped[str] = mapped_column(String(8))
    p_high: Mapped[float] = mapped_column(Float)
    top_terms_json: Mapped[list] = mapped_column(JSON, default=list)
    decision: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str] = mapped_column(String(24))
    latency_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Review(Base):
    """A human's confirm or override. One per ticket."""

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("ticket_id", name="uq_reviews_ticket"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    reviewer: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(8))
    final_intent: Mapped[str] = mapped_column(String(64))
    final_team: Mapped[str] = mapped_column(String(32))
    final_urgency: Mapped[str] = mapped_column(String(8))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class DriftReport(Base):
    """A stored drift check."""

    __tablename__ = "drift_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    status: Mapped[str] = mapped_column(String(24))
    n_tickets: Mapped[int] = mapped_column(Integer)
    report_json: Mapped[dict] = mapped_column(JSON)


def _set_pragmas(dbapi_conn, _record) -> None:
    """Turn on foreign keys and WAL for every new SQLite connection."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


def make_engine(db_url: str | None = None) -> Engine:
    """Create an engine; SQLite connections get foreign keys and WAL."""
    url = db_url or get_settings().db_url
    engine = create_engine(url, connect_args={"check_same_thread": False})
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _set_pragmas)
    return engine


def init_db(engine: Engine | None = None) -> Engine:
    """Create all tables if missing and return the engine."""
    engine = engine or make_engine()
    Base.metadata.create_all(engine)
    return engine


def session_factory(engine: Engine) -> sessionmaker:
    """Return a session maker bound to an engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)
