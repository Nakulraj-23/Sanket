"""The seven pipeline stages explained next to their real code (GET /stages).

`code` is read from the source file with `inspect.getsource`, so the page can never show
code that is not the code that runs. Numbers in the text come from the model card.
"""
import inspect
import textwrap

from sanket.models.baseline import BaselineModel
from sanket.monitoring.drift import psi
from sanket.pipeline.clean import clean, validate
from sanket.review import save_review
from sanket.routing.decide import decide
from sanket.schemas import Stage

# id, title, file, function, object to read the code from
SOURCES = [
    ("ingest", "Ingest", "sanket/pipeline/clean.py", "validate", validate),
    ("clean", "Clean", "sanket/pipeline/clean.py", "clean", clean),
    ("classify", "Classify", "sanket/models/baseline.py", "predict_proba", BaselineModel.predict_proba),
    ("explain", "Explain", "sanket/models/baseline.py", "explain", BaselineModel.explain),
    ("route", "Route", "sanket/routing/decide.py", "decide", decide),
    ("review", "Review", "sanket/review.py", "save_review", save_review),
    ("monitor", "Monitor", "sanket/monitoring/drift.py", "psi", psi),
]


def _texts(card: dict, th: dict, bench: dict) -> dict[str, tuple[str, str]]:
    """What and why for each stage; the numbers come from the champion card and the benchmark."""
    test = card["metrics"]["test"]
    nn_f1 = bench.get("nn", {}).get("intent_macro_f1", 0.0)
    return {
        "ingest": (
            ("Before the model sees a complaint, we check it is usable. It must not be empty, "
            "must not be over 2,000 characters, and must contain letters. A bad message is "
            "refused with a clear reason and nothing is stored."),
            ("Refusing bad input at the door keeps every later step simple. The answer tells the "
            "sender exactly what to fix. Nothing about a refused message is kept.")),
        "clean": (
            ("Emails, phone numbers, card numbers and account numbers become placeholders such as "
            "[CARD]. A 16-digit number counts as a card only if it passes the Luhn check, the "
            "checksum banks use, so an order number is not hidden by mistake. Then the text is "
            "lower-cased and spaces are tidied, and only this cleaned text is stored."),
            ("Personal data never reaches the model or the database. Regular patterns can be "
            "read and tested line by line, which a learned detector cannot offer. The same "
            "function cleans the training text and the live text, so the model sees the same kind "
            "of text in both places.")),
        "classify": (
            ("TF-IDF gives each word and short group of letters a score: high if it is frequent "
            "in this message and rare overall. Logistic regression holds one weight per term "
            "per intent, adds up score times weight, and softmax turns the 77 totals into "
            "probabilities that sum to one. The scores are divided by one number fitted on "
            f"validation data (temperature {card['temperature']:.2f}) so a 90% answer is right about 90% of the time."),
            (f"On the held-out test set this model scores macro-F1 {test['intent_macro_f1']:.3f}; the "
            f"small neural network in the Compare tab scores {nn_f1:.3f}. The linear model is "
            "slightly better and fully explainable, so it serves. Both are reported.")),
        "explain": (
            ("For a linear model the explanation is exact. The score of an intent is a sum of "
            "weight times TF-IDF value, one term per word, so we show the five largest terms. "
            "Terms starting with ~ are groups of letters; they are hidden when they only repeat "
            "a word already shown."),
            ("A reviewer can see why the model answered, not only what it answered. If the "
            "terms look wrong the reviewer can tell at a glance. The terms plus a fixed offset "
            "add up to the real score, so nothing is hidden.")),
        "route": (
            ("A table maps each of the 77 intents to one of 7 teams and to an urgency. The "
            "probability of a team is the sum of the probabilities of its intents. If the best "
            f"team has less than {th['tau_team']:.2f} probability, or many words are unknown and the "
            f"team is not clear (above {th['oov_max']:.2f} unknown, team under {th['oov_conf']:.2f}), a person looks. "
            f"A ticket is urgent when the chance of the high-urgency intents reaches {th['tau_high']:.2f}."),
            ("Two cards intents can be confusing and still be one team, so summing is safer than "
            "trusting one intent. The urgent cut-off was chosen on validation data to catch at "
            f"least 97% of urgent tickets ({card['metrics']['test']['high_recall']:.1%} on test), accepting some "
            "false alarms, because missing a fraud report costs more than a wasted look. Team "
            "and urgency come from this project's own table, not from the dataset.")),
        "review": (
            ("Tickets the model is unsure about wait in a queue, urgent first, then oldest. A "
            "person confirms the answer or picks the right intent, and the decision is saved "
            "with who, when and a note. A unique rule in the database and a transaction make "
            "sure two people cannot both decide the same ticket; the second gets a clear "
            "'already reviewed' reply."),
            ("These rows are the override log and the training data for the next model. Only "
            "uncertain tickets are reviewed, so they are a biased sample and say little about "
            "the whole stream. Nothing here trains or promotes a model; a person runs that "
            "step and a frozen test decides.")),
        "monitor": (
            ("A model is trained on yesterday's messages. We compare the latest 500 live tickets "
            "with the validation tickets on things we can measure now: message length, share of "
            "unknown words, the model's confidence and the mix of teams. PSI sums "
            "(live share - reference share) x ln(live share / reference share) over bins; under "
            "0.1 is stable and over 0.25 is a real shift."),
            ("True labels arrive late, so these signals warn early. Drift is a reason to look, "
            "not proof the model is wrong. With fewer than 200 live tickets the page says "
            "there is not enough data instead of guessing.")),
    }


def build_stages(card: dict, thresholds: dict, bench: dict) -> list[Stage]:
    """The seven stages with text from EXPLAINABILITY and code read from the real functions."""
    texts = _texts(card, thresholds, bench)
    out = []
    for stage_id, title, file, function, obj in SOURCES:
        what, why = texts[stage_id]
        out.append(Stage(id=stage_id, title=title, what=what, why=why, file=file,
                         function=function, code=textwrap.dedent(inspect.getsource(obj))))
    return out
