"""The routing rule and the threshold choosers."""
import numpy as np

from sanket.routing.decide import Thresholds, decide, team_probabilities
from sanket.routing.thresholds import choose_tau_high, choose_tau_team, choose_thresholds
from sanket.taxonomy import INTENTS, team_of, urgency_of

TH = Thresholds(tau_team=0.5, tau_high=0.25, oov_max=0.2)


def peaked(intent: str, mass: float = 0.9) -> np.ndarray:
    """A probability row with `mass` on one intent and the rest spread evenly."""
    p = np.full(len(INTENTS), (1 - mass) / (len(INTENTS) - 1))
    p[INTENTS.index(intent)] = mass
    return p


def test_team_probabilities_sum_to_one() -> None:
    rng = np.random.default_rng(0)
    p = rng.random(len(INTENTS))
    p /= p.sum()
    assert abs(sum(team_probabilities(p).values()) - 1) < 1e-9


def test_confident_ticket_is_routed_automatically() -> None:
    d = decide(peaked("card_arrival"), 0.0, TH)
    assert (d.decision, d.reason, d.team, d.intent) == ("auto", "ok", "CARDS", "card_arrival")
    assert len(d.top_intents) == 5 and d.top_intents[0]["intent"] == "card_arrival"


def test_low_team_confidence_goes_to_human() -> None:
    d = decide(np.full(len(INTENTS), 1 / len(INTENTS)), 0.0, TH)
    assert d.team_conf < TH.tau_team
    assert (d.decision, d.reason) == ("human", "low_confidence")


def test_unfamiliar_words_go_to_human() -> None:
    d = decide(peaked("card_arrival"), 0.5, TH)
    assert (d.decision, d.reason) == ("human", "unfamiliar_words")


def test_low_confidence_wins_over_unfamiliar_words() -> None:
    d = decide(np.full(len(INTENTS), 1 / len(INTENTS)), 0.9, TH)
    assert d.reason == "low_confidence"


def test_high_urgency_rule() -> None:
    assert decide(peaked("lost_or_stolen_card"), 0.0, TH).urgency == "high"
    p = peaked("card_arrival", 0.9)
    p[INTENTS.index("lost_or_stolen_card")] = 0.4  # one more high intent above tau_high
    p /= p.sum()
    d = decide(p, 0.0, TH)
    assert d.p_high >= TH.tau_high and d.urgency == "high"


def test_medium_and_low_urgency() -> None:
    assert decide(peaked("card_arrival"), 0.0, TH).urgency == urgency_of("card_arrival")
    assert decide(peaked("exchange_rate"), 0.0, TH).urgency == "low"


def test_tau_team_is_smallest_step_meeting_target() -> None:
    labels = [INTENTS[i % len(INTENTS)] for i in range(200)]
    proba = np.stack([peaked(label, 0.9) for label in labels])
    assert choose_tau_team(proba, labels) == 0.05
    wrong = np.stack([peaked(INTENTS[(i + 1) % len(INTENTS)] if team_of(labels[i]) != "CARDS" else labels[i], 0.9)
                      for i in range(200)])
    assert choose_tau_team(wrong, labels) >= 0.05


def test_tau_high_is_largest_step_meeting_recall() -> None:
    labels = ["lost_or_stolen_card"] * 100
    proba = np.stack([peaked("lost_or_stolen_card", 0.62)] * 100)
    assert choose_tau_high(proba, labels) == 0.65  # p_high is 0.62 + 8 * 0.005 = 0.66


def test_choose_thresholds_uses_99th_percentile_for_oov() -> None:
    labels = ["card_arrival"] * 100
    proba = np.stack([peaked("card_arrival")] * 100)
    th = choose_thresholds(proba, np.linspace(0, 1, 100), labels)
    assert abs(th.oov_max - np.percentile(np.linspace(0, 1, 100), 99)) < 1e-9
