"""The routing rule: from intent probabilities to team, urgency and auto-or-human.

A pure function. No files, no model, no database, so every rule can be tested alone.
"""
from dataclasses import dataclass

import numpy as np

from sanket.taxonomy import INTENTS, TEAM_NAMES, team_of, urgency_of

TEAM_INDEX = {t: [i for i, name in enumerate(INTENTS) if team_of(name) == t] for t in TEAM_NAMES}
HIGH_INDEX = [i for i, name in enumerate(INTENTS) if urgency_of(name) == "high"]
MEDIUM_INDEX = [i for i, name in enumerate(INTENTS) if urgency_of(name) == "medium"]
LOW_INDEX = [i for i, name in enumerate(INTENTS) if urgency_of(name) == "low"]


@dataclass
class Thresholds:
    """The three numbers that decide when a human must look."""

    tau_team: float  # below this team confidence, a human looks
    tau_high: float  # at or above this chance of "high urgency", the ticket is high
    oov_max: float  # above this share of unknown words, a human looks


@dataclass
class Decision:
    """What the system concluded about one ticket."""

    intent: str
    intent_conf: float
    top_intents: list[dict]
    team: str
    team_conf: float
    team_probs: dict[str, float]
    urgency: str
    p_high: float
    decision: str
    reason: str


def team_probabilities(proba: np.ndarray) -> dict[str, float]:
    """Add up the intent probabilities inside each team."""
    return {t: float(proba[idx].sum()) for t, idx in TEAM_INDEX.items()}


def decide(proba: np.ndarray, oov_rate: float, th: Thresholds) -> Decision:
    """Turn one row of 77 probabilities into a Decision using the thresholds.

    Why teams are summed: a ticket can be confusing between two card intents yet clearly a
    card ticket, so the team is often safe to route even when the intent is not.
    """
    order = np.argsort(-proba)
    top = [{"intent": INTENTS[i], "prob": float(proba[i])} for i in order[:5]]
    team_probs = team_probabilities(proba)
    team = max(team_probs, key=lambda t: team_probs[t])
    p_high = float(proba[HIGH_INDEX].sum())
    if p_high >= th.tau_high:
        urgency = "high"
    else:
        urgency = "medium" if proba[MEDIUM_INDEX].sum() >= proba[LOW_INDEX].sum() else "low"
    team_conf = team_probs[team]
    if team_conf < th.tau_team:
        decision, reason = "human", "low_confidence"
    elif oov_rate > th.oov_max:
        decision, reason = "human", "unfamiliar_words"
    else:
        decision, reason = "auto", "ok"
    return Decision(
        intent=INTENTS[order[0]], intent_conf=float(proba[order[0]]), top_intents=top,
        team=team, team_conf=team_conf, team_probs=team_probs, urgency=urgency,
        p_high=p_high, decision=decision, reason=reason,
    )
