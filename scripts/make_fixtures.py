"""Write fixtures/*.json by instantiating the Pydantic schemas.

Run: .venv/bin/python scripts/make_fixtures.py
Values are realistic but invented; no real customer data.
"""
import json
from datetime import datetime
from pathlib import Path

from sanket import schemas as s
from sanket.taxonomy import taxonomy_payload

OUT = Path(__file__).resolve().parent.parent / "fixtures"
T0 = datetime(2026, 11, 14, 9, 30, 0)


def write(name: str, obj) -> None:
    """Dump a model, a list of models or a dict to fixtures/<name>.json."""
    if isinstance(obj, list):
        data = [o.model_dump(mode="json") for o in obj]
    elif hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    else:
        data = obj
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def prediction(intent: str, team: str, urgency: str, conf: float, team_conf: float,
               decision: str, reason: str, p_high: float) -> s.PredictionOut:
    """Build a prediction with plausible runners-up and terms."""
    return s.PredictionOut(
        intent=intent, intent_conf=conf,
        top_intents=[s.TopIntent(intent=intent, prob=conf),
                     s.TopIntent(intent="card_arrival", prob=round((1 - conf) * 0.5, 3)),
                     s.TopIntent(intent="card_delivery_estimate", prob=round((1 - conf) * 0.3, 3)),
                     s.TopIntent(intent="order_physical_card", prob=round((1 - conf) * 0.1, 3)),
                     s.TopIntent(intent="get_physical_card", prob=round((1 - conf) * 0.1, 3))],
        team=team, team_conf=team_conf,
        team_probs={team: team_conf, "CARDS": round(1 - team_conf, 3)} if team != "CARDS"
        else {"CARDS": team_conf, "ACCOUNT_KYC": round(1 - team_conf, 3)},
        urgency=urgency, p_high=p_high, decision=decision, reason=reason,
        model_version="v1",
        top_terms=[s.Term(term="stolen", weight=1.82), s.Term(term="card", weight=0.74),
                   s.Term(term="my", weight=0.12)],
        latency_ms=3.4)


def trace(before: str, after: str, pii: dict, pred: s.PredictionOut) -> list[s.TraceStep]:
    """Five trace steps for one ticket."""
    return [
        s.TraceStep(stage="ingest", ms=0.1, summary="Accepted, 1 problems checked",
                    detail={"problems": []}),
        s.TraceStep(stage="clean", ms=0.4, summary=f"Masked {sum(pii.values())} personal item(s)",
                    detail={"before_masked": before, "after": after, "pii": pii}),
        s.TraceStep(stage="classify", ms=2.9, summary=f"Top intent {pred.intent}",
                    detail={"top_intents": [t.model_dump() for t in pred.top_intents]}),
        s.TraceStep(stage="explain", ms=0.3, summary="3 terms drove the answer",
                    detail={"terms": [t.model_dump() for t in pred.top_terms]}),
        s.TraceStep(stage="route", ms=0.05, summary=f"{pred.decision}: {pred.reason}",
                    detail={"team_probs": pred.team_probs, "p_high": pred.p_high,
                            "thresholds": {"tau_team": 0.6, "tau_high": 0.3, "oov_max": 0.4},
                            "rule": "human if team_conf < tau_team or oov_rate > oov_max"}),
    ]


def summary_of(r: s.TicketResult) -> s.TicketSummary:
    """Reduce a TicketResult to a list row."""
    p = r.prediction
    return s.TicketSummary(
        ticket_id=r.ticket_id, created_at=r.created_at, status=r.status,
        text_redacted=r.text_redacted, intent=p.intent, team=p.team, urgency=p.urgency,
        intent_conf=p.intent_conf, team_conf=p.team_conf, decision=p.decision, reason=p.reason)


def drift(status: str, psi_val: float, ks_d: float, n: int, msg: str) -> s.DriftReportOut:
    """Build a drift report with three indicators of the same status."""
    ind = [s.DriftIndicator(name="n_tokens", kind="ks", value=ks_d, p_value=0.001 if ks_d > 0.1 else 0.4, status=status),
           s.DriftIndicator(name="oov_rate", kind="ks", value=ks_d, p_value=0.001 if ks_d > 0.1 else 0.5, status=status),
           s.DriftIndicator(name="team_mix", kind="psi", value=psi_val, status=status)]
    return s.DriftReportOut(
        created_at=T0, status=status, n_tickets=n, model_version="v1", indicators=ind,
        team_mix={"CARDS": {"reference": 0.25, "live": 0.24 if status == "green" else 0.1},
                  "FRAUD_SECURITY": {"reference": 0.08, "live": 0.08 if status == "green" else 0.3}},
        message=msg)


def main() -> None:
    """Write every fixture file."""
    OUT.mkdir(exist_ok=True)
    auto_text = "My card was stolen yesterday, please block it"
    auto_pred = prediction("lost_or_stolen_card", "FRAUD_SECURITY", "high", 0.91, 0.97, "auto", "ok", 0.95)
    auto = s.TicketResult(ticket_id=101, created_at=T0, status="auto_routed", text_redacted=auto_text,
                          prediction=auto_pred, trace=trace(auto_text, auto_text, {}, auto_pred))
    rev_text = "Mera card [CARD] kaam nahi kar raha, mail me at [EMAIL]"
    rev_pred = prediction("card_not_working", "CARDS", "medium", 0.38, 0.52, "human", "low_confidence", 0.04)
    review = s.Review(ticket_id=102, reviewer="asha", action="override", final_intent="card_not_working",
                      final_team="CARDS", final_urgency="medium", note="customer wrote in Hinglish", created_at=T0)
    needs = s.TicketResult(
        ticket_id=102, created_at=T0, status="needs_review", text_redacted=rev_text, prediction=rev_pred,
        trace=trace("Mera card 4111 1111 1111 1111 kaam nahi kar raha, mail me at ****@****.com",
                    rev_text, {"CARD": 1, "EMAIL": 1}, rev_pred))
    write("health", s.Health(status="ok", model_version="v1", tickets=412))
    write("ticket_result", auto)
    write("ticket_result_review", needs)
    write("ticket_list", [summary_of(needs), summary_of(auto)])
    write("review", review)
    write("stages", [s.Stage(
        id="clean", title="Clean", what="Masks emails, phones, card and account numbers, then lowercases.",
        why="Masks card, phone, email, Aadhaar, PAN and UPI patterns (not names or addresses); train and serve text match.",
        file="sanket/pipeline/clean.py", function="clean", code="def clean(text): ...")])
    write("taxonomy", s.Taxonomy(**taxonomy_payload()))
    write("compare", s.CompareOut(baseline=s.ModelAnswer(intent="lost_or_stolen_card", conf=0.91, ms=2.1),
                                  nn=s.ModelAnswer(intent="lost_or_stolen_card", conf=0.88, ms=1.4)))
    write("drift_report", drift("green", 0.03, 0.05, 500, "No meaningful change against the reference."))
    write("drift_report_red", drift("red", 0.41, 0.34, 500, "Ticket mix and wording moved a lot; review and consider retraining."))
    write("metrics", s.Metrics(
        override_rate_by_team={"CARDS": 0.08, "FRAUD_SECURITY": 0.03},
        auto_share_by_day=[{"day": "2026-11-13", "auto_share": 0.84, "n": 120}],
        latency_by_model={"baseline": {"p50_ms": 2.1, "p95_ms": 4.0}, "nn": {"p50_ms": 1.4, "p95_ms": 2.6}}))
    write("model", s.ModelInfo(
        champion={"version": "v1", "date": "2026-11-14", "metrics": {"val": {"macro_f1": 0.9}, "test": {"macro_f1": 0.89}}},
        registry={"champion": "v1", "history": [{"version": "v1", "created_at": "2026-11-14T09:00:00",
                                                  "decision": "promoted", "reasons": [], "metrics": {}}]},
        bench={"baseline": {"p50_ms": 2.1}, "nn": {"p50_ms": 1.4}}))


if __name__ == "__main__":
    main()
