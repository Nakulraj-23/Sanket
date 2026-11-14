# CONTRACTS — shared by every agent

Every agent reads this file and its own brief, nothing else from `docs/plan/` unless the brief says so.
If a contract must change, do not change it silently: write the proposed change in your handoff note.

## Repo layout and ownership

```
sanket/                                    (repo root: /home/user/sanket)
  pyproject.toml  Makefile  Dockerfile  .dockerignore  .gitignore  .github/workflows/ci.yml   # B0
  data/raw/        banking77_train.csv  banking77_test.csv  SOURCE.md        # B0 (committed)
  data/splits/     train.csv  val.csv  stream.csv  test.csv                   # B1 (committed)
  data/stress/     hinglish.csv  pii_probe.csv                                # B1 (committed)
  sanket/
    config.py  db.py  schemas.py  taxonomy.py  taxonomy.yaml                  # B0
    pipeline/      load.py  quality.py  clean.py  pii.py  split.py  perturb.py   # B1
    models/        base.py (B0)  baseline.py  evaluate.py  train_baseline.py  # B2
    models/nn/     tokenizer.py  net.py  train.py  export_onnx.py  onnx_model.py   # B3
    routing/       decide.py  explain.py  thresholds.py                       # B2
    retrain.py                                                                # B2
    monitoring/    drift.py                                                   # B3
    bench.py                                                                  # B3
    service.py  review.py  stages.py  sql/metrics.sql  api/                   # B4
  scripts/         seed.py  make_replay.py  space_bundle.py                   # B4
  artifacts/       registry.json  models/<version>/  nn/                      # B2, B3 (rules below)
  fixtures/        one JSON per API response                                  # B0
  web/             React + Vite app, e2e/                                     # B5
  tests/           unit/ data/ model/ api/     # builders add tests for their own code; Q-agents add more
  docs/            handoffs/ (all)  EXPERIMENTS.md  AUDIT_LOG.md (append-only, all)  rest: D1
```

Write only inside what you own. `schemas.py`, `db.py`, `taxonomy.yaml`, `fixtures/` change only through B0 or the orchestrator.

## Conventions

- Python 3.11, `ruff` clean, type hints, a docstring on every public function that says what and why in
  plain words. The candidate must be able to read every file: no clever one-liners, no metaclasses, no
  decorators beyond FastAPI's, functions under 40 lines, files under 250 lines.
- Seed 42 everywhere. Config via `sanket.config.Settings` (env prefix `SANKET_`). No hard-coded paths.
- No LLM calls, no network at run time, no pickle loaded from outside `artifacts/`.
- Do not `pip install torch`. Training code imports torch lazily; serving code never imports it.
  In this sandbox `make link-torch` exposes torch 2.15 from `/home/user/prahari/.venv`.
- Do not download browsers. Playwright `@playwright/test` 1.47.2 with `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`
  (copy the `executablePath` logic from `/home/user/prahari/web/playwright.config.js`).
- Make targets that must keep working: `setup link-torch data seed train train-nn bench retrain serve web test lint replay space-bundle`.
- Real measured numbers only. Failed approaches go in `docs/EXPERIMENTS.md` (date, tried, result, change).
- Do not run `git commit` or `git push`; the orchestrator commits.
- Finish with `docs/handoffs/<ID>.md`, 30 lines at most: what exists, how to run, measured numbers, known gaps, contract changes requested.
- Committed artifacts: each file under 10 MB, `artifacts/` under 40 MB total (a test enforces this).

## Data and labels

Source: Banking77, CC-BY-4.0, columns `text,category`. In this project `category` is called **intent**.
Splits (B1, stratified by intent, seed 42): official train minus rows whose normalised text appears in the
official test, then `train` 70% / `val` 15% / `stream` 15%. `test` = official test, frozen.
Rules: `test` is never shown to the live system and never used for training or threshold choice.
`stream` feeds the live demo and may be absorbed by retraining. Thresholds are chosen on `val`.
Split CSV columns: `row_id,text,intent`. Stress sets: `hinglish.csv` = `text,intent,urgency,script,note`;
`pii_probe.csv` = `text,expected_redacted,kinds`.

`taxonomy.yaml` (B0 writes it from these lists; `taxonomy.py` loads it and exposes `INTENTS` (sorted, fixed order), `team_of`, `urgency_of`):

- **CARDS**: activate_my_card card_about_to_expire card_acceptance card_arrival card_delivery_estimate card_linking card_not_working change_pin contactless_not_working get_disposable_virtual_card get_physical_card getting_spare_card getting_virtual_card order_physical_card pin_blocked virtual_card_not_working visa_or_mastercard disposable_card_limits apple_pay_or_google_pay
- **FRAUD_SECURITY**: card_payment_not_recognised cash_withdrawal_not_recognised compromised_card direct_debit_payment_not_recognised lost_or_stolen_card lost_or_stolen_phone
- **CARD_PAYMENTS**: Refund_not_showing_up request_refund reverted_card_payment? transaction_charged_twice declined_card_payment pending_card_payment
- **TRANSFERS_TOPUPS**: balance_not_updated_after_bank_transfer balance_not_updated_after_cheque_or_cash_deposit beneficiary_not_allowed cancel_transfer declined_transfer failed_transfer pending_transfer receiving_money transfer_into_account transfer_not_received_by_recipient transfer_timing automatic_top_up pending_top_up top_up_failed top_up_limits top_up_reverted topping_up_by_card top_up_by_cash_or_cheque verify_top_up
- **CASH_ATM**: atm_support declined_cash_withdrawal pending_cash_withdrawal wrong_amount_of_cash_received card_swallowed
- **FEES_FX**: card_payment_fee_charged card_payment_wrong_exchange_rate cash_withdrawal_charge exchange_charge exchange_rate exchange_via_app extra_charge_on_statement top_up_by_bank_transfer_charge top_up_by_card_charge transfer_fee_charged wrong_exchange_rate_for_cash_withdrawal fiat_currency_support
- **ACCOUNT_KYC**: age_limit country_support edit_personal_details terminate_account unable_to_verify_identity verify_my_identity verify_source_of_funds why_verify_identity passcode_forgotten supported_cards_and_currencies

Urgency rubric. **high** (money or account at risk now): compromised_card lost_or_stolen_card lost_or_stolen_phone card_payment_not_recognised cash_withdrawal_not_recognised direct_debit_payment_not_recognised card_swallowed transaction_charged_twice wrong_amount_of_cash_received.
**low** (information or how-to): age_limit country_support exchange_rate fiat_currency_support supported_cards_and_currencies visa_or_mastercard top_up_limits disposable_card_limits card_delivery_estimate transfer_timing why_verify_identity getting_spare_card getting_virtual_card get_disposable_virtual_card get_physical_card order_physical_card apple_pay_or_google_pay atm_support card_acceptance exchange_via_app receiving_money top_up_by_cash_or_cheque topping_up_by_card automatic_top_up card_about_to_expire change_pin edit_personal_details verify_source_of_funds top_up_by_bank_transfer_charge top_up_by_card_charge exchange_charge.
**medium**: every other intent (something failed, is pending, or was charged).
Team and urgency are this project's rubric, not labels from the dataset. Say so wherever they are reported.

## Database (SQLite, SQLAlchemy models in `sanket/db.py`)

| Table | Columns |
|---|---|
| `tickets` | id PK, created_at, channel (`web`/`seed`/`scenario`), text_redacted, pii_json, n_chars, n_tokens, oov_rate, status (`auto_routed`/`needs_review`/`reviewed`) — index (status, created_at) |
| `predictions` | id PK, ticket_id FK, model_version, intent, intent_conf, team, team_conf, urgency, p_high, top_terms_json, decision (`auto`/`human`), reason (`ok`/`low_confidence`/`unfamiliar_words`), latency_ms, created_at — index (ticket_id) |
| `reviews` | id PK, ticket_id FK **UNIQUE**, reviewer, action (`confirm`/`override`), final_intent, final_team, final_urgency, note, created_at |
| `drift_reports` | id PK, created_at, status (`green`/`amber`/`red`/`insufficient_data`), n_tickets, report_json |

Raw text is never written to the database, a log or a file. No ground-truth label is stored in the database.
Foreign keys on (`PRAGMA foreign_keys=ON`), WAL mode. At most 5,000 tickets: oldest non-seed rows are deleted beyond that.

## Interfaces

```python
# sanket/pipeline/clean.py
@dataclass
class CleanResult: text: str; pii: dict[str, int]; n_chars: int; n_tokens: int
def validate(text: str) -> list[str]      # problems: empty, over 2000 chars, no letters. Empty list = ok
def clean(text: str) -> CleanResult       # redact then normalise. Same function at train and serve time
# sanket/pipeline/pii.py  — placeholders [EMAIL] [PHONE] [CARD] [ACCOUNT]; card needs a valid Luhn checksum
def redact(text: str) -> tuple[str, dict[str, int]]

# sanket/models/base.py
class Classifier(Protocol):
    version: str
    def predict_proba(self, texts: list[str]) -> np.ndarray   # shape (n, 77), order = taxonomy.INTENTS, rows sum to 1
# sanket/models/baseline.py
class BaselineModel:   # implements Classifier; saved with joblib in artifacts/models/<version>/model.joblib
    def explain(self, text: str, intent: str, k: int = 5) -> list[dict]   # {"term", "weight"}; weight = coef * tfidf value
    def oov_rate(self, text: str) -> float                                # share of word tokens not in the word vocabulary
    def save(self, dir: Path) -> None;  @classmethod def load(cls, dir: Path) -> "BaselineModel"
# sanket/models/nn/onnx_model.py
class OnnxModel:       # implements Classifier; onnxruntime only; files artifacts/nn/model.onnx + vocab.json

# sanket/routing/decide.py — pure function, no I/O
def decide(proba: np.ndarray, oov_rate: float, th: Thresholds) -> Decision
# Decision: intent, intent_conf, top_intents[5], team, team_conf, team_probs, urgency, p_high, decision, reason
# team_probs[t] = sum of intent probabilities in team t.  p_high = sum over high-urgency intents.
# urgency = "high" if p_high >= th.tau_high else the likelier of medium/low.
# decision = "human" if team_conf < th.tau_team ("low_confidence") or oov_rate > th.oov_max ("unfamiliar_words"), else "auto".

# sanket/monitoring/drift.py — NumPy only
def psi(expected: np.ndarray, actual: np.ndarray, bins) -> float
def ks_2samp(a: np.ndarray, b: np.ndarray) -> tuple[float, float]     # statistic D, p-value
def drift_report(reference: dict, live: dict) -> dict                  # shape of fixtures/drift_report.json
```

Model directory `artifacts/models/<version>/`: `model.joblib`, `thresholds.json` (`tau_team`, `tau_high`, `oov_max`),
`reference.json` (from `val`, written by B2: `{n_tokens: [..], oov_rate: [..], team_conf: [..], team_mix: {team: share}}`, raw values; `live` has the same shape), `card.json`
(data, metrics on val and test, stress-set results, limits, date, code version). `artifacts/registry.json`:
`{"champion": "v1", "history": [{"version", "created_at", "decision": "promoted"|"rejected", "reasons": [], "metrics": {}}]}`.
Version names: `v1`, `v2`, ... Only the champion directory and `artifacts/nn/` are committed.

Threshold rules (B2, on `val` only): `tau_team` = smallest value in steps of 0.05 where auto-routed team accuracy
is at least 0.985; `tau_high` = largest value in steps of 0.05 where high-urgency recall is at least 0.97;
`oov_max` = 99th percentile of `oov_rate`.
Drift status: PSI under 0.1 green, 0.1 to 0.25 amber, above 0.25 red. KS: red if D >= 0.2 and p < 0.01, amber if
D >= 0.1 and p < 0.01. Fewer than 200 live tickets: `insufficient_data`. Overall = worst indicator.
Promote gate (`sanket/retrain.py`): candidate replaces champion only if, on `test`, intent macro-F1 >= champion − 0.005
**and** high-urgency recall >= champion − 0.01 **and** data-quality checks pass **and** size limits hold.

## REST API (prefix `/api`, JSON, errors as `{"detail": "..."}`)

| Method and path | Request | Response |
|---|---|---|
| GET `/health` | | `{status, model_version, tickets}` |
| POST `/tickets` | `{text, channel?}` | 201 `TicketResult`; 422 with the `validate` problems |
| GET `/tickets?status=&limit=` | | `[TicketSummary]`, `needs_review` ordered urgent first then oldest |
| GET `/tickets/{id}` | | `TicketResult` (trace rebuilt from stored rows, `review` filled if any); 404 |
| POST `/tickets/{id}/review` | `{reviewer, action, final_intent?, final_urgency?, note?}` | 200 `Review`; 404; 409 if already reviewed; 422 unknown intent |
| GET `/stages` | | `[{id, title, what, why, file, function, code}]` for ingest, clean, classify, explain, route, review, monitor |
| GET `/taxonomy` | | `{teams: {team: [intent]}, urgency: {intent: level}}` |
| POST `/compare` | `{text}` | `{baseline: {intent, conf, ms}, nn: {intent, conf, ms}}` (text is cleaned, nothing stored) |
| GET `/monitor/drift` | | latest `DriftReport` |
| POST `/monitor/drift/run` | | computes over the latest 500 tickets, stores and returns `DriftReport` |
| POST `/demo/scenario` | `{name: "hinglish_surge" \| "reset"}` | `{inserted}`; pushes at most 300 prepared tickets through the pipeline |
| GET `/metrics` | | `{override_rate_by_team, auto_share_by_day, latency_by_model}` from `sql/metrics.sql` |
| GET `/model` | | `{champion: card, registry, bench}` |

`TicketResult` = `{ticket_id, created_at, status, text_redacted, prediction: Decision + {model_version, top_terms, latency_ms},
trace: [{stage, ms, summary, detail}], review: Review | null}`. `trace` has five entries from one POST: ingest, clean,
classify, explain, route. `detail` is the stage's own data (clean: `{before_masked, after, pii}`; classify:
`{top_intents}`; explain: `{terms}`; route: `{team_probs, p_high, thresholds, rule}`).
Review transaction: insert the review and set `tickets.status='reviewed'` only where it is not yet reviewed; if no row changed, roll back and return 409.
`action=confirm` copies the predicted intent. `final_team` always comes from the taxonomy. Retraining uses `final_intent` only.
No endpoint trains or promotes a model. CORS origins from `SANKET_CORS_ORIGINS`.

## Fixtures (`fixtures/`, written by B0 from the Pydantic schemas, validated by a test)

`health.json`, `ticket_result.json` (auto), `ticket_result_review.json` (needs review, with fake PII redacted),
`ticket_list.json`, `review.json`, `stages.json`, `taxonomy.json`, `compare.json`, `drift_report.json` (green),
`drift_report_red.json`, `metrics.json`, `model.json`. The web app has two data sources only, the live API and `web/public/replay.json`
(no separate mock mode); both use exactly these shapes: `replay.json` = `{generated_at, model_version, health, stages, taxonomy, samples: [TicketResult],
compare: {sample_index: ...}, queue, drift, drift_after_scenario, metrics, model}`.
