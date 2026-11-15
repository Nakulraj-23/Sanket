# Architecture

SANKET has six components and two surfaces. This page shows how they connect, what is stored,
and why each part was built the way it was. Words in **bold** on first use are defined in
[GLOSSARY.md](GLOSSARY.md). Every number comes from the model card
(`artifacts/models/v1/card.json`), `docs/bench.md`, a handoff note or `docs/AUDIT_LOG.md`.

## The picture

```
 complaint text (raw, only in memory)
      |
 [1 INTAKE + CLEAN]  validate -> redact PII -> normalise            sanket/pipeline/
      |
 [2 CLASSIFY]        TF-IDF + logistic regression -> 77 intent probabilities   sanket/models/
      |              (PyTorch IntentNet -> ONNX: benchmarked "second opinion")
 [3 EXPLAIN + ROUTE] top words; sum probabilities per team and per urgency;
      |              low confidence or unfamiliar words -> human     sanket/routing/
      |
   auto-routed ------------------------> team
   needs review -> [4 REVIEW] person confirms or overrides; logged   sanket/review.py
      |
 [5 MONITOR]   live tickets vs validation reference: PSI, KS, override rate   sanket/monitoring/
      |
 [6 RETRAIN GATE] train on corrections; promote only if not worse    sanket/retrain.py
      '-------------------------------> new champion -> [2]

 Surfaces: REST API (FastAPI + SQLite, sanket/api/) and a one-page React dashboard (web/).
```

## The six components

| # | Component | Main file | Input | Output |
|---|---|---|---|---|
| 1 | Intake and clean | `sanket/pipeline/clean.py`, `pii.py`, `quality.py` | raw text | cleaned text, PII counts, or a 422 with the problems |
| 2 | Classify | `sanket/models/baseline.py` (challenger `sanket/models/nn/`) | cleaned text | 77 probabilities that sum to 1 |
| 3 | Explain and route | `baseline.py: explain`, `sanket/routing/decide.py`, `sanket/taxonomy.yaml` | probabilities, unfamiliar-word rate | top terms, team, urgency, auto or human, reason |
| 4 | Review | `sanket/review.py`, table `reviews` | a person's confirm or override | one stored review per ticket, or 409 |
| 5 | Monitor | `sanket/monitoring/drift.py` | latest 500 tickets vs `reference.json` | green / amber / red / insufficient_data |
| 6 | Retrain gate | `sanket/retrain.py`, `artifacts/registry.json` | reviewed tickets | a new champion, or a rejected candidate with reasons |

The orchestration of 1 to 3 for one request lives in `sanket/service.py: process_ticket`.
It times each stage with `time.perf_counter` and returns a **trace** of five steps.

## Data flow for one ticket

1. The browser sends `POST /api/tickets` with `{"text": "..."}`.
2. `api/app.py` refuses a body over 20 kB (413). `tickets.py` refuses a channel other than `web` (422).
3. `service.validate_text` checks the text: not empty, at most 2,000 characters, has letters, can be encoded. Problems give 422 and nothing is stored.
4. `clean` masks PII first, then normalises. The raw text is dropped when the function returns.
5. `BaselineModel.predict_proba` gives 77 probabilities; `oov_rate` gives the share of unknown words.
6. `explain` picks the five terms that pushed hardest; `decide` produces team, urgency and auto-or-human.
7. The ticket and the prediction are written in **one transaction**. If more than 5,000 tickets exist,
   the oldest unreviewed, non-seed tickets are deleted in the same transaction.
8. The API answers 201 with the full result and the trace.

## Database schema (SQLite, `sanket/db.py`)

| Table | Key columns | Rules |
|---|---|---|
| `tickets` | id, created_at, channel, text_redacted, pii_json, n_chars, n_tokens, oov_rate, status | index on (status, created_at); only redacted text |
| `predictions` | id, ticket_id → tickets, model_version, intent, intent_conf, team, team_conf, urgency, p_high, top_terms_json, decision, reason, latency_ms | index on ticket_id |
| `reviews` | id, ticket_id → tickets **UNIQUE**, reviewer, action, final_intent, final_team, final_urgency, note | reviewer and note are redacted too |
| `drift_reports` | id, created_at, status, n_tickets, report_json | one row per drift run |

Foreign keys are switched on (`PRAGMA foreign_keys=ON`) and the database runs in **WAL** mode.
No raw text and no ground-truth label is stored.

## Models and files on disk

| Path | What | Size |
|---|---|---|
| `artifacts/models/v1/model.joblib` | vectorisers, float32 weights, intercepts, temperature | 4.93 MB |
| `artifacts/models/v1/thresholds.json` | tau_team 0.70, tau_high 0.20, oov_max 0.20, oov_conf 0.97 | |
| `artifacts/models/v1/reference.json` | validation n_tokens, oov_rate, team_conf, team mix (for drift) | |
| `artifacts/models/v1/card.json` | model card: data, metrics, stress results, limits | |
| `artifacts/nn/model.onnx` + `vocab.json` | the neural challenger, run with onnxruntime | 2.51 MB |
| `artifacts/registry.json` | champion name and history of promoted/rejected versions | |

All committed artifacts together are 9.7 MB (B3 handoff). A test enforces 10 MB per file and 40 MB total.

## Design decisions and the alternative we rejected

**1. One model predicts the intent; team and urgency come from a table.**
Banking77 has 77 real intent labels and no team or urgency labels. Inventing a learned urgency label would be dishonest.
So `taxonomy.yaml` maps each intent to a team and an urgency, and P(team) is the sum of its intents' probabilities.
*Rejected:* a separate learned team model. Measured in an **ablation**: summing gave test team accuracy 0.9708, a direct 7-team model 0.9636.
*Bonus:* a reorganisation is a YAML edit, not a retrain.

**2. The linear model serves; the neural network is a benchmarked challenger.**
The linear model's explanation is exact: contribution = weight × TF-IDF value.
*Rejected:* serving the network. It scored test macro-F1 0.8865 against 0.9003, and its explanations would be approximate.
It is about 15× faster (ONNX p50 0.055 ms against 0.82 ms), but both are far under one millisecond, so speed does not decide it.

**3. Urgency errs on the safe side.**
A ticket is "high" when the summed probability of the 9 high-urgency intents reaches tau_high (0.20), not when "high" is merely the most likely.
*Rejected:* "pick the most likely urgency". That misses fraud reports that are 30% likely. On test, high-urgency recall is 0.983 and precision 0.915.

**4. Unsure tickets go to a person; unknown words alone do not.**
A ticket goes to a person if team confidence is under 0.70, or if over 20% of its words are unknown **and** team confidence is under 0.97.
*Rejected:* "unknown words always go to a person". Q2 measured that this sent 65% of typo tickets to a person, most of them needlessly.

**5. Personal data is masked with readable patterns, not a learned detector.**
*Rejected:* an ML entity recogniser. It is heavier, harder to test line by line, and card, phone and email formats are regular.
Cards must pass the **Luhn** check, so order numbers are not masked by mistake.

**6. The frozen test set never enters the live system.**
Live demo tickets come from a separate `stream` split. Corrections used for retraining therefore cannot leak test rows.
*Rejected:* using test rows in the demo; it would make the gate's score meaningless.

**7. Retraining is a command a person runs, never an endpoint.**
*Rejected:* automatic retraining from the web. Anyone could poison it. The gate checks label sanity, the frozen test, the frozen val, the best model so far, and file sizes.

**8. Drift maths in plain NumPy.**
*Rejected:* a monitoring library. PSI is about 10 lines and KS about 15; writing them shows understanding, and the KS result is checked against SciPy in a test.

**9. SQLite, one file.**
*Rejected:* PostgreSQL. Free hosting has no managed database, and SQLite still gives real SQL, foreign keys, unique constraints and transactions.
The cost: one writer at a time, and the free host wipes the disk on restart.

**10. A replay fallback for the dashboard.**
The free API host sleeps. The page waits 4 seconds for `/api/health`; if there is no answer it shows recorded real answers from `web/public/replay.json` with an amber "Replay" badge, and keeps retrying.
*Rejected:* a fake "mock mode". Replay uses only recorded output of the real pipeline.

## The two surfaces

**REST API (`sanket/api/`).** 13 endpoints under `/api` (see `docs/plan/CONTRACTS.md`). Resources are nouns,
methods are verbs, and status codes mean something: 201 created, 404 missing, 409 already reviewed, 413 too large, 422 bad input.
Errors are always `{"detail": "..."}`. There is no endpoint that trains or promotes a model.

**Dashboard (`web/src/`).** React 18 and Vite, plain JavaScript, one CSS file, 52.6 kB of JavaScript gzipped (B5 handoff).
Seven cards in a row (ingest, clean, classify, explain, route, review, monitor). Clicking a card opens a drawer with
four tabs: what it does, why this way, the real code (read from the running function with `inspect.getsource`, so it cannot go stale),
and this ticket's data. Below the strip: review queue, monitor panel, model panel.

## What production would need (not built)

Authentication and roles for reviewers; PostgreSQL or another server database; a queue between intake and the model
for bursts; a byte limit for chunked request bodies; more PII kinds (UPI ids, Aadhaar, PAN); a second test set so the gate
does not wear out the first; real ticket data with real team and urgency labels; alerting on drift instead of a button.
