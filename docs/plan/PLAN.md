# SANKET — plan

**SANKET** (संकेत, "signal"): it reads the signals in a customer complaint, signals which team should
handle it and how urgent it is, and signals a human when it is not sure.
Repo: `/home/user/sanket`. Python package: `sanket`. This file is read by the orchestrator and the docs
agent only. Builders read `CONTRACTS.md` and their own brief.

## 1. Pitch

A bank customer types a complaint. SANKET removes personal data, predicts what the complaint is about
(one of 77 intents), turns that into a team and an urgency through a routing table anyone can read, shows
the words that drove the prediction, and sends the ticket either straight to the team or to a human
reviewer when confidence is low. Every human correction is logged. A monitor compares live tickets with
the training data and raises a flag when they drift apart. A retrain script learns from the corrections and
replaces the live model only if the new one is not worse on a frozen test set. Six small components, one
page of UI, a live link, real public data, honest numbers.

## 2. Why it fits Tech Mahindra

The JD says AI Engineers "do more than train models" and build "reliable, responsible and scalable
solutions". Triage is the smallest end-to-end system that shows that sentence: data, model, API, human
control, monitoring, safe retraining. It also matches work the company describes in public. D1 must open
each link, quote only what the page says, and drop any link that does not load. No claim about internal systems.

| Public source | What the candidate may say |
|---|---|
| NexGen service desk paper: https://insights.techmahindra.com/assets/next-generation-service-desk-solution-for-smarter-support.pdf | TechM sells AI-assisted service desks; ticket triage is the first step of one |
| agentAssistX: https://techmahindra.com/node/2617 | TechM automates IT support from ticket creation to resolution |
| AI-enabled contact centre case study: https://insights.techmahindra.com/assets/nps-boost-with-ai-enabled-contact-center-operations.pdf | Complaint handling for banks is a real TechM service line |
| Agentic AI in banking: https://insights.techmahindra.com/assets/redefining-intelligent-banking-with-agentic-ai.pdf | Banking is a TechM AI focus; SANKET uses banking complaints |
| TechM Orion: https://www.techmahindra.com/insights/press-releases/tech-mahindra-unveils-techm-orion/ | Human oversight and guardrails are part of TechM's agentic platform message |
| VerifAI: https://www.techmahindra.com/services/artificial-intelligence/verifai/ | TechM markets AI validation; SANKET has quality gates and audits |
| Project Indus: https://www.techmahindra.com/insights/press-releases/tech-mahindra-launches-project-indus-large-language-model-llm/ | TechM invests in Indian languages; SANKET measures its own Hinglish failure honestly |
| FY26 AI investment: https://india.entrepreneur.com/technology/tech-mahindra-increases-ai-investment-in-fy26-working-on/498829 | Context only |

The first four were found by web search on 2026-11-14 and were not opened by the planner. The last four
come from `/home/user/prahari/docs/plan/PLAN.md` §9.

## 3. JD line to project evidence

| JD line | Where in SANKET |
|---|---|
| Implement ML and AI models as per solution designs | `sanket/models/baseline.py` (TF-IDF + logistic regression), `sanket/models/nn/` (PyTorch `IntentNet`) |
| AI-driven features for applications | Pipeline-view dashboard, review queue, word-level explanation |
| Convert analytical models into production-ready components | `Classifier` interface, versioned artifacts, `artifacts/registry.json`, model cards |
| Integrate models with APIs, applications, data pipelines | `sanket/api/` (FastAPI), `sanket/service.py` (clean, classify, explain, route in one call) |
| Deployment on cloud or on-prem | `Dockerfile`, Hugging Face Space (API), Vercel (web), static replay fallback |
| Monitoring and basic drift indicators | `sanket/monitoring/drift.py`: PSI and KS in NumPy; override rate from SQL |
| Support feature pipelines | `sanket/pipeline/`: load, split, clean; the same `clean()` at train and serve time |
| Data preprocessing and transformation | Normalisation, PII redaction, TF-IDF, tokeniser for the PyTorch model |
| Data compatibility and reliability | `sanket/pipeline/quality.py` checks; input validation with 422 errors |
| Functional testing of AI components | `tests/unit`, `tests/data`, `tests/model` (quality gates), `tests/api`, `web/e2e` |
| Optimisation for performance, scalability, latency | `make bench`: p50/p95 latency for LR, PyTorch, ONNX; artifact size; honest table in `docs/bench.md` |
| Debugging inference and integrations | `docs/EXPERIMENTS.md`, `docs/AUDIT_LOG.md`, ONNX parity test, per-stage timings in the trace |
| Collaboration across DS, engineering, QA | Contracts file, handoff notes, three audit gates that play the QA role |
| Documentation | README, ARCHITECTURE, model cards, GLOSSARY, ELI5, interview guide |
| Standards, security guidelines | ruff, CI, PII never stored raw, no pickle from users, input limits, CORS allow-list |
| Python; a bit of JavaScript | Backend in Python 3.11; dashboard in React + Vite (plain JavaScript) |
| DSA | Luhn check, hash-map vocabulary, heap for top-k words, sort-and-walk KS test, priority-ordered queue |
| OOP | `Classifier` protocol with two implementations, dataclasses, Pydantic schemas |
| DBMS, SQL | 4-table SQLite schema, foreign keys, indexes, unique constraint, transaction on review, hand-written SQL in `sanket/sql/metrics.sql` |
| Statistics, probability | Softmax probabilities, summing probabilities over a group, precision/recall, thresholds, calibration (ECE), PSI, KS |
| Linear algebra | TF-IDF vector times weight matrix; embedding average and matrix layers in `IntentNet` |
| NumPy, pandas, scikit-learn | Drift maths (NumPy), data pipeline (pandas), baseline (scikit-learn) |
| PyTorch | `IntentNet`, trained on CPU, exported to ONNX, benchmarked against the baseline |
| Git, REST APIs | Wave-by-wave commits, CI; REST resources with correct status codes (201, 409, 422) |
| Reason about accuracy, performance, trade-offs | Threshold choice, LR-versus-NN decision rule written before the results |
| Data privacy and responsible AI | Redaction before storage, human in the loop, override log, promote gate, Hinglish failure report, model cards |
| Resilience when experiments fail | `docs/EXPERIMENTS.md` records failures; the NN result is reported even if it loses |

## 4. Architecture

Six components and two surfaces.

```
 complaint text
      |
 [1 INTAKE+CLEAN] validate -> redact PII -> normalise        sanket/pipeline/
      |
 [2 CLASSIFY]     TF-IDF + logistic regression -> 77 intent probabilities   sanket/models/
      |                (PyTorch IntentNet -> ONNX: benchmarked second opinion)
 [3 EXPLAIN+ROUTE] top words; sum probabilities per team and per urgency;
      |            low confidence or unfamiliar words -> human     sanket/routing/
      |
   auto-routed ----------------------> team
   needs review -> [4 REVIEW] human confirms or overrides; logged     sanket/review.py
      |
 [5 MONITOR]  live tickets vs training reference: PSI, KS, override rate   sanket/monitoring/
      |
 [6 RETRAIN GATE] train on corrections; promote only if not worse   sanket/retrain.py
      '----------------------------> new champion -> [2]

 Surfaces: REST API (FastAPI + SQLite) and one-page React dashboard (pipeline view).
```

Key design decisions (each has a rejected alternative for the interview):

1. **One model predicts the intent; team and urgency come from a table.** The public data has 77 real
   intent labels and no urgency label. Inventing a learned urgency label would be dishonest. So
   `taxonomy.yaml` maps each intent to a team and an urgency, and P(team) is the sum of the intent
   probabilities in that team. A reorganisation is a YAML edit, not a retrain. B2 also trains a direct
   7-team model as an ablation and reports both.
2. **The linear model always serves.** Its explanation is exact: contribution = weight x TF-IDF value.
   The PyTorch model is a benchmarked challenger shown as a "second opinion". Rule fixed before any
   result: if the NN wins, the report says so with the number and explains why LR still serves (exact
   explanations, lower latency, human in the loop). If the NN loses, the report says that and why
   (10k short texts favour sparse word features). No tuning the NN until it wins.
3. **Urgency errs on the safe side.** A ticket is flagged urgent when P(high) passes a threshold chosen
   on validation data for high recall, not when "high" is merely the most likely.
4. **Overrides separate model errors from policy disagreements.** A wrong intent feeds retraining. A
   right intent with a disputed urgency means the table should change, not the model.
5. **The frozen test set never enters the live system.** Live demo tickets come from a separate
   `stream` split, so corrections used for retraining cannot leak the test set.

## 5. Stack and why each piece is explainable

| Piece | Why |
|---|---|
| pandas, NumPy | Taught in every ML course; drift maths is 40 lines of NumPy |
| scikit-learn TF-IDF + LR | Word counts and weights; every number can be shown |
| PyTorch (training only) | One embedding layer, an average, two linear layers; fits on one screen |
| ONNX + onnxruntime | Lets the API run the NN without installing PyTorch (about 15 MB instead of 800 MB) |
| FastAPI + Pydantic | Typed request and response models double as documentation (`/docs`) |
| SQLAlchemy + SQLite | One file, zero setup, real SQL; free hosting has no database |
| React + Vite, JavaScript | One page, no router, no state library |
| pytest, Playwright, ruff, GitHub Actions, Docker | Standard tools; one command each |

Not used, on purpose: LLMs, transformers, vector stores, message queues, Kubernetes, feature stores.

## 6. Scope tiers

- **MVP**: components 1 to 4, API, pipeline view with live trace, tests, Dockerfile, README.
- **Full (the target)**: drift monitor, retrain gate with sabotage test, PyTorch + ONNX benchmark and
  second opinion, Hinglish and typo stress sets, replay fallback, CI, model cards, all interview docs.
- **Optional, only if everything above is green**: temperature scaling, int8 quantisation of the ONNX
  model, Aadhaar/PAN redaction, rate limiter, `render.yaml`.

## 7. UX: the pipeline view (one page)

Header: name, one-line meaning, badge **Live** (green) or **Replay** (amber, "recorded responses, server
asleep"), champion model version.

Row 1, **Try it**: text box, Submit, and six sample chips: clear case, urgent fraud, ambiguous, message
with fake PII, Hinglish, gibberish. In Replay mode only the chips work and the box says why.

Row 2, **Pipeline strip**: seven cards left to right joined by arrows, with a return arrow from Monitor
to Classify labelled "retrain gate". After a submit each card lights up in turn and shows a one-line result and its time in ms.

| Card | One-line result on the card | Live example in the drawer |
|---|---|---|
| Ingest | "accepted, 142 chars" or the validation error | raw input (only in the browser, never stored), checks passed |
| Clean | "2 items redacted" | before/after text with redactions highlighted, counts by type |
| Classify | "card_arrival 0.91" | top-5 intents as bars; second opinion from the NN with both latencies |
| Explain | "arrived, card, waiting" | words coloured by contribution, table of weight x value |
| Route | "CARDS, medium, auto" | team and urgency bars, the thresholds, which rule fired |
| Review | "in queue" or "auto-routed" | the review form for this ticket; after saving, the logged row |
| Monitor | "drift: green" | current drift indicators and what they compare |

Clicking a card opens a drawer with four tabs: **What it does** (3 sentences), **Why this way** (the
decision and the rejected alternative), **Code** (file path and the real function source, served by the
API with `inspect.getsource`, so it cannot go stale), **Live example** (this ticket's data for that stage).

Row 3, three panels:
- **Review queue**: tickets needing a human, urgent first then oldest; confirm or override (intent from
  the model's top 5 or a searchable list, optional urgency, note); toast shows the logged row.
- **Monitor**: four indicators with green/amber/red chips (ticket length KS, unfamiliar-word rate KS,
  confidence KS, predicted-team mix PSI), override rate by team, buttons "Simulate Hinglish surge" and "Reset".
- **Model**: champion version and test metrics, LR-versus-NN table (accuracy, p50/p95 ms, size),
  registry history with promoted and rejected candidates and the reason.

Style: light theme, system font, one accent colour, no charts library (bars are CSS). Works at 1280 px and on a phone (strip scrolls sideways).

## 8. Data decision

Checked from the sandbox on 2026-11-14 with `curl` through the proxy:

| Source | Result |
|---|---|
| CFPB bulk file `files.consumerfinance.gov/ccdb/complaints.csv.zip` | 403 at the proxy (policy) |
| CFPB search API on `consumerfinance.gov`, S3 mirror | 403 |
| Hugging Face (`huggingface.co`, `datasets-server`) | 403 |
| Kaggle, Zenodo, data.gov, UCI | 403 |
| `raw.githubusercontent.com` | reachable |
| **Banking77** `raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/{train,test}.csv` | **200**, 10,003 + 3,080 rows |
| PyPI, npm | reachable; `download.pytorch.org` is not |

**Decision: real data, Banking77** (Casanueva et al., 2020, PolyAI). Real customer-service messages to a
bank, 77 intents, licence CC-BY-4.0 (attribution required; recorded in `data/raw/SOURCE.md`). Both
files (1.1 MB) are committed, so CI and Docker need no network.

Planner's probe (indicative only; builders must re-measure): TF-IDF + LR gets intent accuracy 0.906 on
the official test set; team accuracy 0.974 after summing probabilities; at team confidence >= 0.6, 94%
of tickets are auto-routed with 0.994 accuracy; P(high) >= 0.3 gives high-urgency recall 0.967. A depth-3
tree scores macro-F1 0.04 on intent and the majority class 0.013, so no single word gives the label away.
Six test messages also appear in train (after lower-casing); B1 removes them from train.

What is real and what is not, to be stated everywhere:
- Text and intent labels: real, public. Known to contain some label noise.
- Team and urgency: **our rubric** over the 77 intents (`taxonomy.yaml`). Not labels from real agents.
- Messages are short English questions (median 10 words), not long complaints, and contain no PII.
  Fake PII is injected into 10% of seeded demo tickets, and a hand-written 40-row PII probe tests redaction.
- **Hinglish/Hindi set**: 60 hand-written rows (`data/stress/hinglish.csv`), test-only. The model is
  trained on English, so it is expected to fail. The report gives accuracy, the share sent to a human by
  the unfamiliar-word rule, and the share that fails silently.
- **Typo set**: the test set with 10% character noise, generated by a seeded function.

Audit hooks for Q1: duplicate and near-duplicate overlap across splits, shallow-tree and keyword
baselines, length-only model, label-pure tokens, class balance, the rubric's consistency, and an
expected band for the baseline (intent macro-F1 0.85 to 0.93; outside it means investigate).

## 9. Deployment

Target: API on a free Hugging Face Space (Docker SDK), dashboard on Vercel free tier, replay fallback built in.
Serve-time image has no PyTorch: scikit-learn, onnxruntime, FastAPI, SQLite. Committed artifacts stay under
40 MB in total and 10 MB per file (the Space git limit without LFS).

What the agents do: `Dockerfile` (port from `$PORT`, default 7860, non-root user, seeds the database at
start), `make space-bundle` (writes `dist/space/` with the Space `README.md` front matter `sdk: docker`,
`app_port: 7860`), `web/vercel.json`, `web/public/replay.json`, `docs/DEPLOY.md`, a `docker build`
and run check if the daemon is available (otherwise recorded as not verified).

What only the candidate can do (agents have no credentials):
1. Push the repo to GitHub.
2. Hugging Face: create an account, New Space, SDK Docker, hardware CPU basic (free). Clone the Space
   repo, copy `dist/space/*` into it, commit, push. Wait for "Running". Open `https://<user>-sanket-api.hf.space/api/health`.
3. In Space settings add variable `SANKET_CORS_ORIGINS=https://<project>.vercel.app`.
4. Vercel: Import the GitHub repo, root directory `web`, framework Vite, environment variable
   `VITE_API_URL=https://<user>-sanket-api.hf.space`, Deploy.
5. Open the Vercel link: badge must read Live. Stop the Space and reload: badge must read Replay.
6. Put both links in the README and the CV. Open the link 10 minutes before the interview to wake the Space.

Honest limits of free hosting: the Space sleeps after long inactivity and takes about a minute to wake;
its disk is wiped on restart, so the database is re-seeded and visitor tickets are lost. The dashboard
waits 4 seconds for the API, then shows Replay and keeps retrying in the background. Alternative host:
Render free web service with the same Dockerfile (sleeps after 15 minutes).

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Disk: 3.7 GB free; PyPI torch pulls about 5 GB of CUDA libraries; CPU wheel index is blocked | Sandbox reuses torch 2.15 from `/home/user/prahari/.venv` through a `.pth` file (`make link-torch`). Elsewhere `pip install torch --index-url https://download.pytorch.org/whl/cpu`. Venv without torch about 0.5 GB. Orchestrator may run `pip cache purge` (frees 3 GB) |
| Data judged too easy or leaky again | Q1 gate with the checks in §8 before any model work; 77-way task has headroom; stress sets |
| Urgency is our rubric | Said plainly in README, model card and guide; Q1 reviews the rubric; candidate reviews it too |
| NN does not beat LR | Expected and acceptable; decision rule fixed in §4; at most 3 NN variants, all logged |
| Confidence is not trustworthy | Coverage-versus-accuracy table and ECE on test; thresholds chosen on validation only |
| Two reviewers save the same ticket | Unique constraint on `reviews.ticket_id` plus conditional update in one transaction; 409; test with threads |
| Public demo abused | 2,000-char limit, table cap, no retrain endpoint, database re-seeds, no secrets in the image |
| Free backend asleep at interview time | Replay fallback, wake-up step in the demo script, local `make serve` as third option |
| Replay goes stale | Test validates `replay.json` against the schemas and the champion version |
| Candidate cannot explain a part | `EXPLAINABILITY.md` budget: one minute per component; glossary; 5 exercises |
| Agents drift from contracts | Fixtures are the frozen shapes; contract changes only through handoff notes |

## 11. Demo script (4 minutes)

| Time | Action | Say |
|---|---|---|
| 0:00 | Open the link, point at the strip | "A complaint goes left to right through seven steps. Each is one small file." |
| 0:25 | Click chip "urgent fraud" | "It predicted the intent, the table mapped it to Fraud and high urgency. Total time is in milliseconds." |
| 0:55 | Open Explain | "These words pushed the decision. Each number is weight times TF-IDF value, so it is exact, not an estimate." |
| 1:20 | Chip "message with fake PII", open Clean | "Email, phone and card number are replaced before anything is stored. The card check uses the Luhn algorithm." |
| 1:45 | Chip "ambiguous", then Review queue, override it | "Low confidence goes to a person. My correction is logged with who and when, and becomes training data." |
| 2:20 | Chip "Hinglish" | "It is trained on English, so here it is weak. I measured that: [numbers]. The unfamiliar-word rule sends most of these to a human." |
| 2:45 | Monitor, "Simulate Hinglish surge" | "PSI and KS compare live tickets with training data. I wrote both in NumPy. Red means look before trusting the model." |
| 3:15 | Model panel | "Retraining uses the corrections. The gate promotes only if the frozen test score is not worse. This rejected row is a poisoned candidate the gate stopped." |
| 3:40 | LR-versus-NN table, Code tab of any card | "I also built a PyTorch model and report it honestly against the baseline. And this is the real code behind the card." |

Fallback: if the badge says Replay, say so ("free server is asleep; these are recorded responses from the
same API") and continue with the chips. If the network is down, run `make serve` and `make web` locally.
