"""Fill a fresh database with demo data (make seed). Safe to run again: it starts from scratch.

400 stream tickets go through the real pipeline, a simulated reviewer handles the queue except
15 tickets, and one drift report is stored. The reviewer's true labels live only in memory.
"""
import random
import sys
import time
from datetime import timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from sanket.api.queries import run_drift
from sanket.config import get_settings
from sanket.db import Review, Ticket, utcnow
from sanket.review import queue, save_review
from sanket.schemas import ReviewIn
from sanket.service import Runtime, load_runtime, process_ticket

N_TICKETS = 400
LEFT_IN_QUEUE = 15
PII_SENTENCES = [
    "my card number is 4111 1111 1111 1111",
    "you can email me at jane.doe@example.com",
    "call me on +44 7700 900123",
    "my account number is 12345678",
]


def remove_old_database(db_url: str) -> None:
    """Delete the SQLite file (and its WAL files) so the seed starts clean."""
    if not db_url.startswith("sqlite:///"):
        return
    path = Path(db_url.replace("sqlite:///", "", 1))
    for suffix in ("", "-wal", "-shm"):
        Path(str(path) + suffix).unlink(missing_ok=True)


def push_tickets(rt: Runtime, rows: pd.DataFrame) -> dict[int, str]:
    """Send rows through the pipeline, spread over the last 7 days; return id -> true intent."""
    rng = random.Random(rt.settings.seed)
    truth, start = {}, utcnow() - timedelta(days=7)
    step = timedelta(days=7) / len(rows)
    for i, row in enumerate(rows.itertuples()):
        text = row.text
        if i % 10 == 0:
            text = f"{text} {rng.choice(PII_SENTENCES)}"
        result = process_ticket(text, "seed", rt, created_at=start + step * i)
        truth[result.ticket_id] = row.intent
    return truth


def simulate_reviewer(rt: Runtime, truth: dict[int, str]) -> int:
    """Review all queued tickets but 15, using the true label in memory. Returns reviews made."""
    waiting = queue(rt.sessions, limit=1000)
    skip = {t.ticket_id for t in random.Random(rt.settings.seed).sample(waiting, min(LEFT_IN_QUEUE, len(waiting) // 2))}
    done = 0
    for item in waiting:
        if item.ticket_id in skip:
            continue
        right = truth[item.ticket_id]
        if item.intent == right:
            body = ReviewIn(reviewer="sim-reviewer", action="confirm")
        else:
            body = ReviewIn(reviewer="sim-reviewer", action="override", final_intent=right,
                            note="simulated reviewer")
        save_review(rt.sessions, item.ticket_id, body)
        done += 1
    return done


def count(rt: Runtime, model, *conditions) -> int:
    """Number of rows of a table matching the conditions."""
    with rt.sessions() as s:
        return s.scalar(select(func.count()).select_from(model).where(*conditions))


def main(n_tickets: int = N_TICKETS, rt: Runtime | None = None) -> None:
    """Build the demo database and print the counts. A passed `rt` must already own an empty database."""
    start = time.perf_counter()
    st = get_settings()
    if rt is None:
        remove_old_database(st.db_url)
        rt = load_runtime(st)
    stream = pd.read_csv(st.data_dir / "splits" / "stream.csv").head(n_tickets)
    truth = push_tickets(rt, stream)
    simulate_reviewer(rt, truth)
    report = run_drift(rt)
    print(f"seeded {n_tickets} tickets: auto {count(rt, Ticket, Ticket.status == 'auto_routed')}, "
          f"queued {count(rt, Ticket, Ticket.status == 'needs_review')}, "
          f"reviewed {count(rt, Review)}, "
          f"overrides {count(rt, Review, Review.action == 'override')}, drift {report.status}, "
          f"{time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
