# SANKET candidate handbook

For: a final-year B.Tech student interviewing for Tech Mahindra's **Digital Catalyst - AI Engineer** campus role.
Projects: **SANKET** (main) and **PRAHARI** (a larger system I also built).

| | Link |
|---|---|
| SANKET live demo | <https://sanket-omega.vercel.app> |
| SANKET code | <https://github.com/Nakulraj-23/sanket> |
| PRAHARI live demo (recorded replay) | <https://prahari-red.vercel.app> |
| PRAHARI code | <https://github.com/Nakulraj-23/prahari> |

This handbook brings together, and does not replace, the existing docs: `README.md`, `docs/EXPLAIN_LIKE_IM_5.md`, `docs/GLOSSARY.md`, `docs/INTERVIEW_GUIDE.md`, `docs/ARCHITECTURE.md`, `docs/AUDIT_LOG.md`, `docs/data_card.md`, `docs/bench.md`, `docs/DEPLOY.md`, the model cards in `artifacts/`, the handoff notes in `docs/handoffs/`, and PRAHARI's README, explainer and interview guide.
If this handbook and one of those files ever disagree, the model card and the handoff notes win. Tell me (or fix the handbook).

---

## 1. How to use this handbook

### 1.1 The rules this handbook follows

- **Every number has a source.** It comes from the SANKET model card (`artifacts/models/v1/card.json`), the network card (`artifacts/nn/card.json`), `docs/bench.md`, `docs/EXPERIMENTS.md`, `docs/AUDIT_LOG.md`, a handoff note in `docs/handoffs/`, or PRAHARI's README and handoffs. A few numbers were measured again while this handbook was written (test count, live demo answers, seed counts). Those are marked **(measured 2026-11-15)**.
- **Every technical word is explained** the first time it appears, in plain words. All of them are also in `docs/GLOSSARY.md` (about 170 terms).
- **Nothing is invented.** Where you must give a personal example (an internship, a team project, a grade), the handbook leaves a placeholder like **[your own example]**. Fill it with something true, or leave the question out.
- **Things the build machine could not check** are marked **check this**. The main ones are the Tech Mahindra web pages: the build machine's network blocked them.

### 1.2 How to read it

1. Read section 1 (this one) and the cheat sheet. Say the 30-second pitch out loud five times.
2. Read sections 2 and 3: what you built and how. These are the stories you will tell.
3. Read sections 4 to 7 with the code open. Sections 5 and 6 are reference: you do not need to memorise them, but you should be able to find anything in them in 30 seconds.
4. Use section 8, the question bank, out loud. Cover the answer, say yours, then compare.
5. Do section 9 (Tech Mahindra angle) the night before. Open every link yourself.
6. Section 11 has a 5-day plan, 10 hands-on exercises and the glossary pointer.

### 1.3 The one rule for the interview

Say what is true, say the number, say where it comes from.
"Macro-F1 0.900 on the 3,080-row official test set, from the model card" is much stronger than "very accurate".
When you do not know, say "I don't know, here is how I would find out" (section 10.4).

---

## Cheat sheet (one page)

### The 30-second pitch

"SANKET is a support-ticket triage system for a bank.
It reads a customer's message, hides personal data like card and Aadhaar numbers, and predicts what the customer wants, out of 77 intents.
A table I wrote turns that into one of 7 teams and an urgency.
If the model is sure, the ticket goes straight to the team. If not, a person reviews it and the correction is logged.
It watches for drift, and a new model replaces the old one only if a frozen test says it is not worse.
On the official test set it routes 94% of tickets on its own, and 99% of those reach the right team.
It is live at sanket-omega.vercel.app."

### The 2-minute pitch

"I wanted to build the smallest system that shows what an AI engineer does beyond training a model: data checks, a model, an API, human control, monitoring and safe retraining.

The data is Banking77: about 13,000 real customer-service messages to a bank, each labelled with one of 77 intents. I split it into train, validation, a 'stream' that feeds the live demo, and the official test set, which stays frozen.

First, every message is cleaned. Emails, phones, card, Aadhaar, PAN, UPI and account numbers become placeholders like [CARD]. A long number counts as a card only if it passes the Luhn checksum, so an order number is not hidden by mistake. The same clean function runs at training time and at serving time.

The model is TF-IDF plus logistic regression. Each word gets a score, the model multiplies scores by learned weights and adds them up, one total per intent. Because it is a sum, I can show exactly which words drove each answer. I also built a small PyTorch network and benchmarked it fairly. It lost by 1.4 points of macro-F1, so the simple model serves. I decided that rule before I saw the results.

A YAML table maps each intent to a team and an urgency. If the best team's probability is under 0.70, a person looks. If the chance of a high-urgency intent is 0.20 or more, it is urgent; that catches 98.3% of urgent test tickets.

People review uncertain tickets in a queue, and the database makes sure two reviewers cannot both decide one ticket. A monitor compares live tickets with validation tickets using PSI and a KS test written in NumPy. A retrain command learns from corrections and is blocked if the new model is worse or the labels look poisoned.

It was built with an AI-assisted, multi-agent workflow under my direction, and three independent audit agents tried to break it. They found real bugs, like card numbers hidden by odd spacing and a speed comparison that was wrong by a factor of eight. Every fix has a test. 261 tests pass."

### 10 numbers to remember

| # | Number | What it means | Source |
|---|---|---|---|
| 1 | **77 → 7** | 77 intents mapped to 7 teams by my own rubric | `sanket/taxonomy.yaml` |
| 2 | **6,946 / 1,489 / 1,489 / 3,080** | train / val / stream / frozen official test rows | `docs/data_card.md` |
| 3 | **0.900** | intent macro-F1 and accuracy on the 3,080 test messages | model card |
| 4 | **94.2% and 0.992** | share routed without a person, and team accuracy of those | model card |
| 5 | **0.983 / 0.915** | recall / precision for high-urgency tickets (cut-off 0.20) | model card |
| 6 | **0.160 → 0.0146** | calibration error (ECE) before / after temperature scaling, T = 0.591 | AUDIT_LOG, model card |
| 7 | **0.9003 vs 0.8865** | linear model vs PyTorch network, macro-F1 (the network lost) | `docs/bench.md` |
| 8 | **0.82 ms vs 0.055 ms** | per-ticket model time, linear vs network (ONNX). Full API call p50 9.9 ms, p95 12.0 ms | bench.md, B4 handoff |
| 9 | **26 of 60, 0 wrong** | Hinglish messages sent to a person, and silently sent to the wrong team | model card |
| 10 | **261 passed, 1 xfail** | Python tests (plus 11 browser tests); 3 audits | measured 2026-11-15 |

### 5 weaknesses, and how to say them

| Weakness | Say this |
|---|---|
| Teams and urgency are my rubric | "The dataset gives intents. Teams and urgency are a table I wrote. So my team and urgency scores measure agreement with my table, not with real bank agents. In a bank, operations would own that table, and the override log shows where it is wrong." |
| Short English data; Hinglish weak | "Banking77 is short English questions, median about 10 words. Real complaints are longer and mixed-language. I measured the gap instead of hiding it: on 60 Hinglish messages intent accuracy is 0.65, but 26 went to a person and none went silently to the wrong team. n = 60 is small." |
| Personal-data masking is pattern-based | "It masks cards with Luhn, Aadhaar with Verhoeff, PAN, UPI, phones, emails and account numbers. It does not mask names or addresses, or any format nobody wrote a pattern for. In production I would add a reviewed entity recogniser and a privacy review." |
| Not production-hardened | "SQLite, no login, and the free Vercel deployment is stateless, so live reviews may vanish. The Docker image was never built because the sandbox had no Docker daemon. These are listed in the README; I know what production needs: Postgres, auth, a queue." |
| Built with AI tools | "Yes. AI coding agents planned, built and audited it under my direction. I chose the problem and the scope, I own the design decisions, and I reviewed the results. I can explain any file and change it in front of you." |

---

## 2. What we built

### 2.1 SANKET in plain words

SANKET (संकेत, "signal") is a helper for a bank's support desk.
A customer types a message. SANKET:

1. **Ingest.** Checks the message is usable: not empty, not over 2,000 characters, has letters, can be stored. If not, it refuses with a clear reason (HTTP 422) and stores nothing.
2. **Clean.** Hides personal data. Card numbers, phones, emails, Aadhaar, PAN, UPI ids and account numbers become `[CARD]`, `[PHONE]`, `[EMAIL]`, `[AADHAAR]`, `[PAN]`, `[UPI]`, `[ACCOUNT]`. Then it lower-cases the text and tidies spaces. Only this cleaned text is ever stored.
3. **Classify.** A model reads the cleaned text and gives a probability for each of 77 intents, such as `card_arrival` or `lost_or_stolen_card`.
4. **Explain.** It shows the five words (or letter groups) that pushed hardest towards the answer, with numbers that add up to the model's score.
5. **Route.** A table I wrote maps each intent to one of 7 teams and an urgency (high, medium, low). It adds up probabilities per team. Sure → straight to the team. Unsure, or full of unknown words → a person.
6. **Review.** A person confirms or corrects unsure tickets in a queue, urgent first. Who, when and what are logged. Two people cannot both decide one ticket.
7. **Monitor.** It compares the latest 500 tickets with the tickets the model was tuned on, and turns green, amber or red.

Then, outside the web page: a **retrain gate**. A person runs `make retrain`. It learns from the corrections and replaces the live model only if a frozen test says the new one is not worse and the labels look honest.

The seven words Ingest, Clean, Classify, Explain, Route, Review, Monitor are exactly the seven cards on the dashboard.

**The analogy (from `docs/EXPLAIN_LIKE_IM_5.md`).** A bank's post room. A helper checks each letter, covers private numbers with a black marker, reads it, points at the words that made it decide, drops it in the right desk's tray, puts unsure letters in a special tray for a person, and watches whether today's letters look different from the ones it learned from.

#### The picture

```
 message (raw text lives only in memory)
    |
 [1 Ingest]   validate: empty? too long? no letters? cannot be stored?   -> 422, nothing stored
    |
 [2 Clean]    redact PII -> lower-case, tidy spaces                     sanket/pipeline/
    |
 [3 Classify] TF-IDF + logistic regression -> 77 probabilities          sanket/models/
    |
 [4 Explain]  top 5 terms: weight x TF-IDF value
    |
 [5 Route]    sum per team; team < 0.70 or (unknown words and team < 0.97) -> person
    |                         \
    | auto-routed               [6 Review] confirm or override, logged, 409 on a second review
    |
 [7 Monitor]  latest 500 vs validation: KS on 3 signals, PSI on team mix
    |
 retrain gate (a person runs it): promote only if not worse -> new champion
```

#### What one request looks like

When the browser sends `POST /api/tickets` with `{"text": "Someone used my card abroad, I did not make this payment"}`, the live demo answered **(measured 2026-11-15)**:

- intent `card_payment_not_recognised` at 0.793;
- team `FRAUD_SECURITY` at 0.966 (six fraud intents added up);
- urgency `high` (p_high 0.966, far above 0.20);
- decision `auto` (team confidence above 0.70);
- top terms: "payment", "make", "this payment", "did not", "someone".

"I tried to pay and it did not work" gave `declined_card_payment` with team confidence 0.692, just under 0.70, so it went to a person with reason `low_confidence`.

#### The live demo

- **Address:** <https://sanket-omega.vercel.app>. The dashboard and the API are one free Vercel project. The Python API runs as a **serverless function** (code that starts when a request arrives and may be shut down when idle).
- **Live or Replay badge.** The page asks `/api/health`. If the API answers within 12 seconds, the badge says **Live** and everything is real. If not, the page shows **Replay**: recorded real answers from `web/public/replay.json`, with free text turned off. It keeps retrying every 15 seconds.
- **What resets.** Each cold start builds a new SQLite database under `/tmp` and seeds 250 tickets (`api/index.py`). On 2026-11-15 `/api/health` answered `{"status":"ok","model_version":"v1","tickets":250}`. Reviews you make may vanish when the function is recycled. Say so.
- **The neural network is off on Vercel.** `requirements.txt` has no onnxruntime, so `/api/compare` returns `"nn": null` with the note "The neural network is not available in this deployment." (checked live on 2026-11-15). The benchmark numbers in the Model panel are still the real recorded ones. In Replay mode the Compare table shows the recorded answers from a local run, which did include the network.

#### Where SANKET is strong, in one line each

- Every number traces to a file, and the main numbers were reproduced by an independent audit from scratch (byte-identical model files).
- The explanation is exact, not an approximation.
- Urgency errs on the safe side by design.
- The human is in the loop, and the database enforces one review per ticket.
- The model that lost was reported, not hidden.

### 2.2 PRAHARI, a larger system I also built

PRAHARI (प्रहरी, "sentinel") is a **network-operations copilot for telecom**. Keep this section short in the interview unless they ask; SANKET is the main story.

**In plain words.** When a fibre cable is cut, dozens of devices send alarms at once and most are noise. PRAHARI:

1. ignores the noise (an **alarm validator**: gradient boosting, calibrated);
2. groups the real alarms into one incident;
3. finds the device that is the real cause with a **graph neural network** (GNN: a model that passes information between connected nodes) written by hand in PyTorch;
4. looks up a runbook, proposes a fix and explains it in English or Hindi;
5. runs **10 governance checks** (confidence, blast radius, drift, PII, model card, ...) and asks a person to press Approve;
6. watches for drift with PSI and KS; when drift is red, governance blocks new actions.

**Say this first, every time: all PRAHARI data is synthetic.** A simulator in the repo builds a 120-node network, KPIs every minute and faults. No PRAHARI number is real-network accuracy.

**Key numbers (PRAHARI README and handoffs).**

| What | Number |
|---|---|
| RCA GNN root-cause top-1 on 88 test incidents | 96.6% (top-3 100%) |
| No-graph MLP on the same test | 95.5%; over 10 seeds the GNN wins by only +1.0 point, p about 0.07: **not significant** |
| Unseen 80-node network, top-1 | 100% on 47 incidents (small sample) |
| Alarm validator precision / recall | 0.962 / 0.991; the 0.998 PR-AUC is inflated by a simulator shortcut, honest number noise-class AP 0.9675 |
| Anomaly detector (IsolationForest) F1 | 0.779, **beaten by a tuned 3-sigma rule (0.809)** |
| Live injected faults | 8 of 10 detected, root and fault type 8/8 correct, 2 missed |
| RCA forward pass p50 | PyTorch 0.244 ms, ONNX 0.135 ms, ONNX int8 0.122 ms (43 KB vs 113 KB, same accuracy) |
| Tests | 175 passing (README) |

**Live demo.** <https://prahari-red.vercel.app> is a static **demo replay**: data captured from a real run. The buttons do not change a backend. The full system needs a 2.3 GB database and about 10 minutes of `make seed train`, and runs locally.

**How to connect the two in one sentence.** "PRAHARI was the bigger, synthetic-data project where I learned the audit-and-fix loop and governance gates; SANKET applies the same discipline to real public data, with an explainable model and a live link."

---

## 3. How it was built

### 3.1 The honest summary

SANKET and PRAHARI were built with an **AI-assisted, multi-agent workflow**. That means several AI coding agents, each with one job, worked under my direction:

- **I** chose the problem (bank ticket triage), the scope (six components, one page, a live link, real public data, honest numbers), and the rules that matter, such as "if the neural network loses, report it and do not tune it until it wins". I reviewed results and I own the design decisions.
- A **planner** agent turned that brief into written plans and contracts (`docs/plan/PLAN.md`, `CONTRACTS.md`, `ORCHESTRATION.md`). Be exact if asked: the plan text was drafted by the planner from my brief, and I approved it.
- **Builder** agents (B0 to B5 in SANKET) each built one part against the contract: scaffold, data, model, neural network, API, dashboard.
- **Independent auditor** agents (Q1 data, Q2 model, Q3 system) did not build anything. Their job was to break what the builders made, write failing tests for each problem, and re-check after the fix.
- A **docs** agent (D1) wrote the README, architecture, glossary and guide.
- **Fix rounds.** After each audit, the builder fixed the HIGH and MEDIUM findings, added a test per finding, and wrote an entry in `docs/AUDIT_LOG.md`. The auditor then re-checked only its own items and wrote PASS or FAIL.

`AUTHORS.md` says the same: the owner "chose the problem, defined the scope, reviewed the results and owns the design"; the AI assistant "planned, built and independently audited the code under the owner's direction", and is credited in the commit trailers.

### 3.2 The workflow, step by step (from `docs/plan/ORCHESTRATION.md`)

| Wave | Who | What | Gate |
|---|---|---|---|
| 0 | B0 builder | scaffold: settings, database tables, taxonomy, fixtures, CI | `make setup && make test` (17 passed) |
| 1 | B1 builder | data splits, PII masking, cleaning, quality checks | **Q1 data audit**, one fix round |
| 2 | B2, B3, B5 builders in parallel | baseline model and routing; PyTorch network, ONNX, benchmark, drift maths; dashboard on fixtures | **Q2 model audit**, fix rounds |
| 3 | B4 builder | API, review queue, seed, replay file | **Q3 system audit**, fix rounds |
| 4 | D1 docs | README, architecture, glossary, interview guide | `make test`, links checked |
| later | V1 | Vercel single-project deployment | tested locally, then deployed |

How the agents talked: through files, never through one long chat. `CONTRACTS.md` fixed the shapes of data and API answers. `fixtures/*.json` gave sample answers so the dashboard could be built before the API existed. Each agent ended by writing a handoff note of at most 30 lines in `docs/handoffs/`.

Why this is a real engineering lesson, not a shortcut: it is the same shape as a team with a tech lead, developers and a separate QA team. The contracts are the interface agreement. The audits are QA that is not allowed to fix its own findings. The audit log is the change record.

**What you should do before the interview** so the ownership claim is solid: do at least three of the hands-on exercises in section 11.2 yourself, on your laptop, and be ready to name them: "For example, I added passport masking with a test" **[your own example: name the exercises you actually did]**.

### 3.3 The audit-and-fix loop: the 8 best stories

Tell these as short stories: what was found, the evidence, the fix, the test that now guards it. Five are from SANKET (`docs/AUDIT_LOG.md`), three from PRAHARI (`docs/handoffs/Q1.md`, `Q2.md`, `Q3.md`, `A2.md`, `A4.md`).

#### Story 1 (SANKET, data audit Q1): card numbers hidden by formatting

- **Finding.** Personal data slipped through when it was formatted oddly.
- **Evidence.** The auditor tried 35 ways of writing personal data; **12 were stored raw**. Examples: a card with double spaces or dashes, phone numbers in Devanagari digits (९८१२३४५६७८), `john(at)gmail.com`. The cause: `clean` collapsed spaces *after* `redact`, so double spaces broke the card pattern.
- **Fix.** Digits of any script become 0-9 first; separators between digit groups are allowed; the code searches for a Luhn-valid window inside a run of digits. Later the system audit (Q3) found cards split by newlines and tabs, then by `_`, en-dash and comma; now every kind of whitespace and zero-width character becomes one space before redaction, and up to 3 punctuation characters between digits are allowed. Aadhaar (Verhoeff-checked), PAN, UPI and written-out emails were added in a later round.
- **Test.** `tests/data/test_audit_pii.py` (74 tests, including all 35 formats, `test_any_whitespace_between_groups`, `test_indian_and_punctuation_formats`, `test_new_classes_do_not_overmask`); `tests/unit/test_pii.py::test_probe_file_all_rows_match` on a 71-row probe file.

#### Story 2 (SANKET, model audit Q2): the speed comparison was wrong by about eight times

- **Finding.** The first benchmark said the network was about 125 times faster than the baseline.
- **Evidence.** `BaselineModel.predict_proba` rebuilt a 77 × 20,672 matrix (`self.coef.T.astype(np.float64)`) on **every** prediction. The auditor measured that a precomputed matrix gave identical probabilities, much faster.
- **Fix.** The matrix is built once in `BaselineModel.__init__` (`self._weights`). Baseline p50 went from 7.69 ms to 0.82 ms; ONNX is 0.055 ms. So the real gap is about **15 times**, not 125.
- **Test.** `tests/model/test_audit_q2.py::test_baseline_predict_has_no_per_call_matrix_copy`. A first version used wall-clock timing and was flaky under load (Q3), so it now checks the cached matrix directly plus a best-of-3 bound of 3×.
- **Lesson to say.** "Measure before you claim. A benchmark that flatters your new model deserves the most suspicion."

#### Story 3 (SANKET, Q2 and its re-check): the retrain gate let poison in, then blocked honest people

- **Finding 1.** 200 reviews with **every** label wrong were promoted, because the new model was still within 0.005 macro-F1 on the test set.
- **Fix 1.** Reject a batch if the champion disagrees with more than 30% of new labels.
- **Finding 2 (re-check).** That rule blocked honest reviewers: on the 85 stream tickets the model sends to a person, true labels disagree with the model 56% of the time, because people only see the hard tickets. So retraining could never promote in real use.
- **Fix 2.** Ask a better question: is the new label among the champion's **top 5** guesses? Honest batches score 0.86 to 0.97; 30% wrong labels 0.58 to 0.72; all wrong 0.05. The limit is 0.75. (A first idea, agreement with the nearest training text, could not separate honest hard tickets, 0.29, from noisy ones, 0.22. That failure is logged in `docs/EXPERIMENTS.md`.)
- **Result.** In the system audit, a retrain with 30% poisoned labels was rejected at 57% top-5 coverage; an honest one was promoted from 0.9003 to 0.9058 macro-F1.
- **Test.** `tests/model/test_quality_gates.py` (accepts human-routed and random true labels; rejects all-wrong and 30% noise over 3 seeds; `test_honest_human_routed_batch_is_promoted_end_to_end`; `test_best_ever_check_stops_the_slack_ratchet`).

#### Story 4 (SANKET, Q2): the model's confidence was dishonest

- **Finding.** When the model said "74% sure" on average, it was right 90% of the time: it was **under-confident**.
- **Evidence.** ECE (expected calibration error) 0.160. Also high-urgency recall on test was 0.9694, just under the 0.97 target.
- **Fix.** **Temperature scaling**: divide every score by one number T before softmax, with T chosen on validation data to minimise log-loss. T = 0.591. Then the thresholds were re-chosen by the same written rules.
- **Result.** Test ECE 0.0146, auto-routed 94.2%, high-urgency recall 0.983, auto-routed team accuracy 0.992. Accuracy itself does not change (same ranking).
- **Caveat to say yourself.** T and the thresholds share the validation set.
- **Test.** `tests/model/test_quality_gates.py::test_calibration_in_card`.

#### Story 5 (SANKET, system audit Q3): the reviewer's note leaked personal data

- **Finding.** The masking ran on tickets, but not on the free text a **reviewer** types.
- **Evidence.** The auditor typed a card number, a phone and an email into a review note. They were stored as typed, in the `reviews` table and in the database's write-ahead log file.
- **Fix.** `review.safe_text` joins lines and runs `redact` on the note and the reviewer name before anything is written or returned. The reviewer name must be 1 to 64 characters, the note at most 1,000.
- **Test.** `tests/api/test_review_safety.py::test_note_and_reviewer_are_redacted_everywhere` (checks the response, the table and the `-wal` and `-shm` files), `test_bad_reviewer_is_422`, `test_long_note_is_422`.
- **Lesson.** "Privacy is about every input, not only the main one."

#### Story 6 (PRAHARI, data audit Q1): the first dataset was too easy

- **Finding.** One feature alone separated real alarms from noise.
- **Evidence.** `kpi_z_max` alone gave AUC 0.976 for alarm validity, because simulated noise alarms ignored the KPIs. 9 of 15 alarm types appeared in only one class; the root node was simply the node with the largest latency change in 82.9% of incidents.
- **Fix.** The simulator was changed: 30% of noise alarms got a real KPI blip, every alarm type and severity appears in both classes, fault size varies per incident, training windows start at a random offset. One-feature AUC fell to 0.846; "largest latency change = root" fell to 52.8%.
- **Test.** `tests/data/test_leakage.py::test_single_kpi_feature_does_not_solve_validation`, `::test_no_alarm_type_is_label_pure`, `::test_root_not_trivially_max_latency_delta`.
- **Lesson.** "When a model scores near 100%, suspect the data before you celebrate."

#### Story 7 (PRAHARI, model audit Q2): the anomaly detector learned the fault as normal

- **Finding.** The IsolationForest anomaly detector scored PR-AUC 0.346.
- **Evidence.** Its "normal" reference was the last 60 minutes, so a lasting fault slowly became normal: recall was 0.02 at 30 to 60 minutes after a fault started. Also 157 of 444 "positive" nodes had no visible KPI effect, so the labels were partly wrong.
- **Fix.** The reference window now ends 75 minutes before the current minute (a lagged baseline), and labels come from the simulated KPI effect. PR-AUC rose to 0.8135. The tuned 3-sigma rule still wins on F1 (0.809 vs 0.779), and the model card says so.
- **Test.** `tests/models/test_quality_gates.py::test_card_anomaly_gates` and the live gate `test_live_anomaly_test_split`.

#### Story 8 (PRAHARI, system audit Q3): approve did not re-check governance

- **Finding.** A safety check could be bypassed by timing.
- **Evidence.** An action was proposed while drift was green. Then a red drift report arrived. Pressing Approve still returned 200 and executed the action, because approval never re-ran the checks. A second HIGH: a fault-type guess with only 0.36 confidence passed governance and the wrong fix ran.
- **Fix.** Approve now re-runs all 10 checks and returns 409 on any failure, and writes an audit event `approval_blocked_by_governance`. Check G1 now also requires fault-type confidence.
- **Test.** `tests/serving/test_api.py::test_approve_reruns_governance_and_returns_409`, `tests/test_governance.py::test_reevaluate_at_approve_time`, `::test_g1_fault_type_prob`.
- **Bonus story (same audit).** Under 32 parallel users, `/v1/rca` failed with `database is locked`. Fix: SQLite WAL mode, a busy timeout, a 30-second cache and a clean 503 with `Retry-After` instead of a 500. Then 0 errors at 50 clients (`test_lock_contention_is_503_with_retry_after`).

#### How to tell any of these in 40 seconds

"An independent audit found X. The evidence was Y. I fixed it by Z, and the test T now fails if it ever comes back."
Then stop. Let them ask for more.

---

## 4. Tech stack

Versions are the exact pins in `pyproject.toml`, `requirements.txt` and `web/package.json`.
"Rejected" means the alternative that was considered and not used, with the reason.

### 4.1 SANKET

| Tool | What it is | Why chosen | Alternative rejected | Say this |
|---|---|---|---|---|
| Python 3.11 | The programming language of the back end | The standard language for ML; every library below is Python | Java (fewer ML libraries) | "Python, because the whole ML stack lives there." |
| NumPy 2.4.6 | Fast arrays of numbers | Drift maths (PSI, KS), softmax, team sums | A monitoring library such as Evidently | "I wrote PSI and KS in NumPy so I can explain every line; KS is checked against SciPy in a test." |
| pandas 3.1.1 | Tables of data in Python | Reading CSVs, splitting, counting per team | Plain CSV module | "pandas for the data pipeline: load, clean, split, count." |
| scikit-learn 1.9.1 | Classic ML library | `TfidfVectorizer`, `LogisticRegression`, `train_test_split`, `f1_score` | A transformer such as BERT | "On short texts with about 90 examples per intent, TF-IDF plus logistic regression is strong, fast and exactly explainable." |
| SciPy 1.17.1 | Science maths library | Sparse matrices, and `minimize_scalar` to fit the temperature | Hand-written search | "SciPy finds the one temperature that minimises log-loss." |
| joblib 1.6.0 | Saves Python objects to disk | Stores the vectorisers and weights in `model.joblib` (4.93 MB) | pickle by hand | "joblib for the model file; it is only ever loaded from our own artifacts folder, never from a user." |
| PyYAML 6.0.3 | Reads YAML files | The routing table `taxonomy.yaml` | Hard-coded Python dicts | "The rubric is a YAML file, so moving an intent to another team is an edit, not a retrain." |
| PyTorch 2.15 (training only) | Deep learning library | The challenger network `IntentNet` | TensorFlow (either works; PyTorch is simpler to read) | "I trained a small PyTorch network on CPU and benchmarked it honestly; it lost." |
| ONNX + onnxruntime 1.32.0 | A file format for models, and a fast engine to run it | Serve the network without PyTorch (small, fast) | Ship PyTorch in the server (big) | "Export once to ONNX, run with onnxruntime; a parity test checks the outputs match torch." |
| FastAPI 0.163.0 | A Python web framework for APIs | Typed request and response models, automatic docs, fast | Flask (no built-in validation) | "FastAPI gives me validation and correct status codes almost for free." |
| Pydantic 2.14.3 + pydantic-settings 2.16.3 | Data validation with Python type hints | Every request and response shape in `schemas.py`; settings from `SANKET_*` environment variables | Hand-written checks | "Pydantic rejects bad input with a 422 before my code runs." |
| SQLAlchemy 2.1.8 | A library to talk to databases from Python | Table classes in `db.py`, safe parameterised queries | Raw SQL strings everywhere | "SQLAlchemy for the tables; I still wrote three queries by hand in `metrics.sql`." |
| SQLite (WAL mode) | A database in one file | Free, no server, real SQL with foreign keys, unique constraints and transactions | PostgreSQL (needs a server; free hosting has none) | "SQLite is enough for a demo and shows real DBMS ideas. Production would be Postgres." |
| uvicorn 0.54.0 | A server that runs FastAPI | `make serve` | gunicorn | "uvicorn runs the API locally on port 8000." |
| React 18.3.1 | A JavaScript library for web pages | The one-page dashboard, plain JavaScript | A server-rendered page | "A small React page: seven stage cards, a review queue, monitor and model panels." |
| Vite 5.4.8 | A fast build tool for web apps | Dev server and production build (52.6 kB of JavaScript gzipped) | Webpack (slower, more setup) | "Vite builds the page." |
| pytest 9.2.0 + httpx 0.28.1 | Test runner; HTTP client used by FastAPI's TestClient | 262 Python tests | unittest | "pytest for everything from Luhn to the full API." |
| Playwright 1.47.2 | Drives a real browser in tests | 11 end-to-end tests, replay and live | Selenium | "Playwright clicks through the real page in Chromium." |
| ruff 0.17.5 | A fast Python linter | `make lint` in CI | flake8 | "ruff keeps the style clean; CI runs it." |
| GitHub Actions | Runs jobs on every push | Lint, Python tests, web build, replay browser tests | Manual testing | "CI runs lint and tests on every push." |
| Git | Version control | 23 commits in SANKET, wave by wave, fixes separate | | "Each wave and each fix round is its own commit." |
| Vercel | Hosting for web pages and serverless functions | Live demo: static page plus a Python function, same address, free | Hugging Face Space for the API plus Vercel for the page (prepared in `make space-bundle`, not used for the live link) | "One Vercel project serves the page and the API on the same origin, so no CORS." |
| Docker (file only) | Packages an app with its dependencies | `Dockerfile` for any container host | | "The Dockerfile exists but was never built: the sandbox had no Docker daemon. I say that." |
| Make | Runs named commands | `make setup data train seed serve test lint bench retrain replay` | Long README commands | "One word per step, the same on every machine." |
| Python-Markdown 3.11.3 | Turns Markdown into HTML | Builds the HTML guides | | (only for docs) |

### 4.2 Extra tools in PRAHARI

| Tool | What it is | Used for | Say this |
|---|---|---|---|
| networkx | Graph library | Builds the 120-node network topology | "networkx builds the simulated network; the GNN uses its adjacency matrix." |
| HistGradientBoosting (scikit-learn) | Many small decision trees added together | Alarm validator, with isotonic calibration | "Gradient boosting for real vs noise alarms; a logistic regression baseline is close." |
| IsolationForest (scikit-learn) | Finds unusual points by how quickly random splits isolate them | Anomaly score per node and minute | "A tuned 3-sigma rule beat it on F1, and I report that." |
| PyTorch GCN (hand-written) | A graph convolutional network | Root-cause ranking | "Three graph layers; a no-graph MLP scores almost the same." |
| ONNX int8 quantisation | Stores weights as 8-bit integers | Model 113 KB → 43 KB, same accuracy | "Quantisation made it smaller and slightly faster with no accuracy loss." |
| Tailwind, Cytoscape.js, Recharts | CSS utility classes, graph drawing, charts | The PRAHARI dashboard | "Cytoscape draws the network and rings the root cause." |
| docker-compose (file only) | Runs several containers together | API, web, Postgres | "Written, not run; Postgres is untested." |

---

## 5. Component and function reference (SANKET)

How to use this section: when an interviewer says "show me where X happens", find X here, open the file, and read the function aloud.
Each entry says what the module does in plain words, its important functions or classes with one line each, the inputs and outputs, and the tests that cover it.

Test file names are relative to `tests/`. "Covered indirectly" means no test imports the module directly, but tests that run the whole pipeline go through it.

### 5.1 Core files

#### `sanket/__init__.py`
Marks `sanket` as a Python package. One line, nothing else.

#### `sanket/config.py`
**What.** All settings in one place, read from environment variables that start with `SANKET_`.
- `Settings` (Pydantic settings class): `db_url` (default `sqlite:///sanket.db`), `artifacts_dir`, `data_dir`, `cors_origins` (default `http://localhost:5173`), `max_chars` 2000, `max_tickets` 5000, `seed` 42.
- `get_settings()`: builds the settings fresh each time, so tests can change the environment.

**In / out.** Environment variables in; a `Settings` object out.
**Tests.** Used by almost every test; `api/conftest.py` sets `SANKET_DB_URL` to a temporary file.

#### `sanket/taxonomy.yaml` and `sanket/taxonomy.py`
**What.** The rubric: which of 7 teams owns each of the 77 intents, and which intents are high or low urgency (everything else is medium). 9 intents are high, such as `compromised_card`, `lost_or_stolen_card`, `card_payment_not_recognised`, `card_swallowed`, `transaction_charged_twice`.
- `TEAMS`, `TEAM_NAMES`, `INTENTS`: the lists, read once at import time (`yaml.safe_load`, which cannot run code).
- `team_of(intent)`: the team of an intent; fails loudly on an unknown intent.
- `urgency_of(intent)`: high, medium or low.
- `taxonomy_payload()`: the shape returned by `GET /api/taxonomy`.

**In / out.** The YAML file in; dictionaries and lists out.
**Tests.** `unit/test_scaffold.py::test_taxonomy_counts_and_uniqueness`, `::test_taxonomy_matches_dataset_labels`, `::test_team_and_urgency_lookup`; `data/test_audit_hinglish_rubric.py`.

#### `sanket/db.py`
**What.** The four database tables, written as SQLAlchemy classes, and how to connect.
- `Ticket` (`tickets`): id, created_at, channel, `text_redacted` (only cleaned text), `pii_json` (counts per kind, not the values), n_chars, n_tokens, oov_rate, status. Index on (status, created_at).
- `Prediction` (`predictions`): ticket_id (foreign key), model_version, intent, intent_conf, team, team_conf, urgency, p_high, top_terms_json, decision, reason, latency_ms. Index on ticket_id.
- `Review` (`reviews`): ticket_id with a **UNIQUE** constraint (one review per ticket), reviewer, action, final_intent, final_team, final_urgency, note.
- `DriftReport` (`drift_reports`): status, n_tickets, report_json.
- `_set_pragmas`: turns on `PRAGMA foreign_keys=ON` and `journal_mode=WAL` for every new SQLite connection.
- `make_engine(url)`, `init_db(engine)`, `session_factory(engine)`, `utcnow()`.

**In / out.** A database URL in; an engine and sessions out.
**Tests.** `unit/test_scaffold.py::test_db_foreign_keys_wal_and_unique_review`; `api/test_api.py::test_pii_never_stored`.

#### `sanket/schemas.py`
**What.** Pydantic classes for every API request and response (the contract). The important ones:
- `TicketCreate` (POST body: text, channel), `PredictionOut`, `TraceStep` (stage, ms, summary, detail), `TicketResult` (the full answer), `TicketSummary` (a list row).
- `ReviewIn` (reviewer, action confirm or override, final_intent, final_urgency, note) and `Review`.
- `DriftIndicator`, `DriftReportOut`, `Metrics`, `ModelInfo`, `Stage`, `Taxonomy`, `CompareIn`, `CompareOut`, `ModelAnswer`, `Health`, `Inserted`, `ScenarioIn`.
- Literal types fix the allowed values, for example `Urgency = Literal["high", "medium", "low"]` and `reason` in `ok | low_confidence | unfamiliar_words`.

**Tests.** `unit/test_scaffold.py::test_fixture_validates` (every fixture file parses), `api/test_api.py::test_health_and_shapes`, `api/test_replay_and_bundle.py`.

#### `sanket/service.py`
**What.** The pipeline for one ticket, in one call. Also loads everything once at start-up.
- `Runtime` (dataclass): the champion `BaselineModel`, the optional network, thresholds, reference, card, registry, benchmark, database engine and sessions.
- `load_runtime(settings)`: reads `artifacts/registry.json` to find the champion, loads its model, thresholds and reference, opens the database.
- `load_nn(dir)`: the ONNX network, or `None` if onnxruntime or the file is missing (this is why Vercel works without it).
- `validate_text(text)`: `validate` plus a refusal of text that cannot be encoded (a lone surrogate), so it is a 422 and not a 500.
- `process_ticket(text, channel, rt)`: validate → clean → analyse → build trace → store; returns a `TicketResult`. Raises `InvalidTicket` on bad input (nothing stored).
- `analyse(rt, text)`: classify, explain and route an already cleaned text, timing each stage.
- `shown_terms(model, text, intent)`: top terms, hiding a letter group that only repeats a word already shown.
- `mask_with_bullets(raw)`: the "before" view for the Clean card, with personal characters replaced by bullets, built in memory only.
- `build_trace(...)`: the five trace steps (ingest, clean, classify, explain, route).
- `store_ticket(...)`: inserts the ticket and the prediction in **one transaction**, then `_enforce_cap`.
- `_enforce_cap(session, limit)`: keeps at most 5,000 tickets by deleting the oldest **unreviewed, non-seed** ones; reviewed tickets are never deleted.
- `timed(fn, *args)`: runs a function and returns (result, milliseconds) using `time.perf_counter`.

**In / out.** Raw text in (memory only); a stored ticket and a `TicketResult` with a trace out.
**Tests.** `api/test_api.py` (shapes, 422s, `test_pii_never_stored`, `test_parallel_posts`, `test_no_torch_and_cap`), `api/test_review_safety.py::test_cap_never_deletes_reviewed_tickets`, `unit/test_load_nn.py` (2 tests: the API starts without the network), `api/test_audit_q3.py`.

#### `sanket/stages.py`
**What.** The text and the real code behind each of the seven dashboard cards (`GET /api/stages`).
- `SOURCES`: for each stage, the file and the function whose code is shown (`validate`, `clean`, `BaselineModel.predict_proba`, `BaselineModel.explain`, `decide`, `save_review`, `psi`).
- `_texts(card, th, bench, nn_available)`: "what it does" and "why this way" for each stage, with numbers read from the model card at run time.
- `build_stages(...)`: returns the seven `Stage` objects; the code comes from `inspect.getsource`, so the page can never show code that is not the code that runs.

**Tests.** `api/test_api.py::test_stage_files_exist_and_code_not_empty`; `web/e2e/q3_audit.spec.js` ("drawer Code tab shows the functions that really run").

#### `sanket/review.py`
**What.** The human review step: save a decision exactly once per ticket, and list the queue.
- `TicketNotFound`, `AlreadyReviewed`, `BadReview`: custom exceptions that the API turns into 404, 409 and 422.
- `safe_text(value)`: joins lines and runs `redact`, so free text is safe to store.
- `_clean_free_text(body)`: redacts the reviewer and note; reviewer 1 to 64 characters, note at most 1,000.
- `_final_values(body, pred)`: confirm keeps the model's intent; override needs a known `final_intent`; urgency comes from the rubric unless given.
- `save_review(sessions, ticket_id, body)`: the whole save, all or nothing.
- `_claim_and_insert(...)`: `UPDATE tickets SET status='reviewed' WHERE id=? AND status!='reviewed'`; if no row changed, raise `AlreadyReviewed`; else insert the review row. The unique constraint is a second lock.
- `list_tickets(sessions, status, limit)`: the queue is ordered urgent first (a SQL `CASE`), then oldest; other lists newest first.
- `queue(...)`, `summary_from_rows(...)`, `review_to_schema(...)`.

**In / out.** A `ReviewIn` in; a stored `Review` out, or an exception.
**Tests.** `api/test_api.py::test_review_race_gives_one_200_one_409`, `::test_404_and_review_errors`; `api/test_review_safety.py` (redaction everywhere, bad reviewer, long note); `api/test_audit_q3.py`.

#### `sanket/retrain.py`
**What.** Learn from reviewed tickets; promote the new model only if it is not worse (`make retrain`). No web endpoint calls it.
- `gate(champion, candidate, slack, recall_slack)`: macro-F1 at most 0.005 below and high-urgency recall at most 0.01 below the champion; returns (ok, reasons).
- `top5_coverage(champion, rows)` and `label_sanity_problems(...)`: at least 75% of new labels must be in the champion's top 5 guesses.
- `best_ever_problems(registry, candidate)`: within 0.01 of the best model ever promoted, so small losses cannot add up round after round.
- `size_problems(dir)`: each file under 10 MB, all artifacts under 40 MB.
- `quality_problems(frame, val, test)`: re-runs the data-quality checks on the combined training data.
- `read_reviewed_from_db()`: reviewed tickets as (cleaned text, reviewer's final intent).
- `build_training_frame(train, new)`: train plus new rows, cleaned, unknown intents and already-seen texts dropped.
- `flip_labels(df, share)`: makes wrong labels on purpose, only to prove the gate catches them (`--sabotage 0.3`).
- `next_version(registry)`, `run_retrain(new, min_new=50, sabotage)`, `main(argv)` (options `--min-new`, `--sabotage`, `--from-csv`).

**In / out.** Reviewed rows in; a new model folder plus a registry entry (promoted or rejected, with reasons) out.
**Tests.** `model/test_quality_gates.py` (gate rules, sabotage rejected, clean retrain accepted, minimum rows, all-wrong rejected, label sanity cases, best-ever, duplicates, end-to-end promotion); `model/test_audit_q2.py::test_gate_accepts_equal_candidate_and_has_no_skip_flag`.

#### `sanket/bench.py`
**What.** The benchmark behind `docs/bench.md` (`make bench`): quality, latency, throughput and size for the baseline, the torch network and the ONNX network on the test set.
- `quality(proba, y)`: intent accuracy, macro-F1, team accuracy (team of the top intent).
- `latency(model, texts, n=1000, warm=50)`: p50 and p95 of one call **including `clean`**, after 50 warm-up calls.
- `throughput(model, texts, batch=64)`: tickets per second in batches of 64.
- `load_torch_model`, `load_baseline`, `measure`, `write_docs` (writes `docs/bench.md` and `artifacts/nn/card.json`), `main`.

**Tests.** Covered indirectly: `model/test_quality_gates.py::test_single_ticket_latency_p95_under_20ms` checks latency separately; the bench numbers were re-run by the Q2 audit.

#### `sanket/sql/metrics.sql`
**What.** Three hand-written SQL queries behind `GET /api/metrics`, each starting with `-- name:`.
- `override_rate_by_team`: of reviewed tickets, the share overridden, per team (JOIN reviews to predictions, GROUP BY team).
- `auto_share_by_day`: share auto-routed per calendar day.
- `latency_by_model`: average latency per model version.

**Tests.** `api/test_api.py::test_list_compare_taxonomy_stages_model_metrics`.

### 5.2 Data pipeline: `sanket/pipeline/`

#### `pipeline/load.py`
**What.** Reads the raw Banking77 CSV files and renames the dataset's `category` column to `intent`.
- `load_raw(raw_dir)`: returns (official train, official test) with columns row_id, text, intent.

**Tests.** `data/test_split.py`, `data/test_audit_leakage.py`.

#### `pipeline/pii.py`
**What.** Masks personal data with readable patterns.
- `luhn_ok(number)`: the Luhn checksum that real card numbers pass (12 lines, one pass over the digits).
- `verhoeff_ok(number)`: the Verhoeff checksum that Aadhaar numbers pass (two lookup tables).
- `unify_spaces(text)`: drops lone surrogates and zero-width characters, turns every kind of whitespace into one space.
- `ascii_digits(text)`: turns Devanagari, Arabic-Indic or full-width digits into 0-9.
- `_find_card(run)`: inside a run of digits and separators, the longest span of 13 to 19 digits that passes Luhn; separated groups must be 4 to 8 digits so lists of amounts are not cards.
- `_mask_cards`, `_mask_aadhaar`, `_mask_phones`: masking with exceptions: a number right after "order", "tracking", "invoice", "txn" or "awb" is an id, not a card; a number after "rs", "paid", "amount" or a currency sign is money, not a phone.
- `redact(text)`: runs everything in a fixed order (email, written-out email, UPI, PAN, card, Aadhaar, account, IBAN, phone); returns (masked text, counts per kind).

**In / out.** Text in; text with `[CARD]`-style placeholders and a count dictionary out.
**Tests.** `unit/test_pii.py` (5 tests including the 71-row probe file and `test_verhoeff`), `data/test_audit_pii.py` (74 tests), `api/test_audit_q3.py`.

#### `pipeline/clean.py`
**What.** Validate and clean one ticket; the same code at training and serving time.
- `validate(text)`: lists problems: `empty`, `too_long` (over 2,000 characters), `no_letters`. Empty list means fine.
- `clean(text)`: `unify_spaces` → Unicode NFKC normalisation → `redact` → one space between words → lower-case except the placeholders. Returns a `CleanResult` (text, pii counts, n_chars, n_tokens). Running it twice gives the same text (it is **idempotent**).
- `CleanResult` (dataclass), `_lower_keep_placeholders`.

**Tests.** `unit/test_clean.py` (10 tests), `data/test_audit_pii.py`, `data/test_quality.py::test_uncleaned_text_fails`.

#### `pipeline/quality.py`
**What.** Data checks that stop the pipeline with a clear message instead of training on bad data.
- `DataQualityError`: the exception, naming the frame and the problem.
- `check_frame(df, name)`: no nulls, no empty text, no unknown intents, no duplicate texts (except in the frozen test set), unique row_id, no HTML or broken characters, `clean(text) == text`, length 5 to 2,000, at least 20 rows per class in train (5 in val and stream).
- `check_splits(splits)`: ids unique across splits, test exactly 3,080 rows, no text shared between splits, no train text with cosine similarity above 0.99 to a test text, and nearest-text label agreement at least 0.72 (clean data scores 0.75; 10% shuffled labels 0.685).

**Tests.** `data/test_quality.py` (10), `data/test_audit_quality.py` (13, each a corruption that must be caught).

#### `pipeline/similarity.py`
**What.** TF-IDF and cosine-similarity helpers for the data checks (not a shipped model).
- `near_duplicates(a, b, threshold)`: pairs of texts whose cosine similarity is above the threshold; works in chunks of 500 rows.
- `nearest_label_agreement(...)`: share of texts whose single most similar reference text has the same label.

**Tests.** Through `data/test_quality.py`, `data/test_audit_quality.py`, `data/test_split.py`.

#### `pipeline/split.py`
**What.** Builds `data/splits/*.csv` (`make data`).
- `build_splits(seed=42)`: cleans every text; removes from train the 7 texts also in test, 4 internal duplicates and 68 near copies of test texts (cosine above 0.99); splits the rest 70/15/15 **stratified by intent** (each intent keeps its share) into train, val and stream; shuffles the stream so any slice is a fair sample.
- `main()`: builds, checks, writes the files and prints counts.

**Tests.** `data/test_split.py` (5, including `test_row_counts_add_up` and `test_stream_is_shuffled_so_any_slice_is_representative`). Re-running is byte-identical (Q1).

#### `pipeline/perturb.py`
**What.** Makes noisy or Hinglish-looking copies of text, always the same for the same seed.
- `add_typos(text, rate, seed)`: swaps, drops or doubles letters inside words (10% for the typo stress test).
- `hinglishify(text, seed)`: swaps common English words and phrases for romanised Hindi. **Synthetic, used only for the drift demo**, never for training or a reported accuracy. (The 60-row Hinglish stress file is hand-written.)

**Tests.** `data/test_perturb_stress.py` (4).

### 5.3 Models: `sanket/models/`

#### `models/base.py`
**What.** The one interface every classifier implements.
- `Classifier` (a `typing.Protocol`): has `version` and `predict_proba(texts) -> array (n, 77)`, rows sum to 1, columns in `INTENTS` order. Both `BaselineModel` and `OnnxModel` fit it, so evaluation and benchmark code works with either. This is **duck typing with a declared shape**.

**Tests.** Indirect, through every model test.

#### `models/baseline.py`
**What.** The model that serves: TF-IDF on words and letter groups, then multinomial logistic regression.
- `BaselineParams` (dataclass): C, use_char, feature caps (8,000 word, 15,000 letter-group), seed. v1 uses C = 5 with letter groups.
- `_make_vectorizers(p)`: word 1-2 grams and `char_wb` 2-5 grams, `sublinear_tf=True`, `min_df=2`, float32.
- `BaselineModel.fit(texts, labels, params)`: trains, then keeps only the vectorisers, the 77 × 20,672 coefficient matrix and 77 intercepts as float32.
- `BaselineModel.__init__`: builds the float64 weight matrix **once** (the Story 2 fix), the unigram vocabulary set and the tokenizer.
- `scores(texts)`: raw scores = sparse TF-IDF matrix × weights + intercepts.
- `predict_proba(texts)`: `softmax(scores / temperature)`.
- `explain(text, intent, k=5)`: the k terms with the largest coefficient × TF-IDF value, using `heapq.nlargest`. Letter groups start with "~".
- `raw_score(text, intent)`: one intent's raw score, used to prove the explanation adds up.
- `oov_rate(text)`: share of word tokens not in the vocabulary ("out of vocabulary").
- `save(dir)`, `load(dir)`: `model.joblib`, only from `artifacts/`.
- `fit_temperature(scores, y)`: the T in 0.2 to 3.0 that minimises validation log-loss (SciPy bounded search).
- `_softmax(scores)`: row-wise softmax, subtracting the row maximum first so `exp` never overflows.

**Tests.** `model/test_baseline.py` (5: shape and sums, `test_explain_contributions_plus_intercept_equal_raw_score`, sorted terms, oov rate, save and load), `model/test_audit_q2.py`.

#### `models/evaluate.py`
**What.** Measures a classifier on val, test and the two stress sets. Numbers only.
- `load_split(name)`: reads `data/splits/<name>.csv`.
- `metrics_from_scores(proba, oov, y, th)`: accuracy, macro-F1, team accuracy, urgency macro-F1, high recall and precision, auto share, auto team accuracy, ECE, coverage table, most confused pairs.
- `expected_calibration_error(conf, correct, bins=10)`: the ECE formula over 10 equal-width bins.
- `coverage_table(team_conf, team_ok)`: share kept and team accuracy at cut-offs 0.5 to 0.95.
- `confused_pairs(true, pred)`: the most common mistakes.
- `stress_metrics`, `stress_from_scores`: human share, silent wrong team, silent wrong intent.
- `typo_texts(texts, seed)`, `evaluate_stress(...)`, `evaluate_all(...)` (the dict stored in the card).

**Tests.** `model/test_quality_gates.py`, `model/test_audit_q2.py`.

#### `models/train_baseline.py`
**What.** Trains v1 and writes `artifacts/models/v1/` (`make train`, about 58 to 72 seconds).
- `run_grid(train, val)`: C in {5, 10, 20} × with or without letter groups, scored on **val only**.
- `float32_cost(...)`: shows float32 weights cost 0.0000 macro-F1.
- `package_version(...)`: fit, fit the temperature, choose thresholds on val, choose `oov_conf`, save the model, thresholds, reference and card.
- `choose_oov_conf(model, val, th)`: on a typo copy of val (seed 1042), the setting with the lowest human share where silent wrong-team stays under 1% (chosen 0.97).
- `reference_from_val(...)`: the raw validation values the drift monitor compares against.
- `calibration_summary`, `write_registry`, `code_version` (git hash), `val_macro_f1`, `main`.

**Tests.** `model/test_quality_gates.py::test_oov_conf_is_selected_on_val_typos_and_stored`, `::test_calibration_in_card`; Q2 re-trained from scratch and got byte-identical files.

#### `models/ablation.py`
**What.** The experiment that justified summing intent probabilities: a direct 7-team model versus summed intents (test team accuracy 0.9636 versus 0.9708). Prints numbers only.
**Tests.** None (an experiment script; the result is logged in `docs/EXPERIMENTS.md`).

#### `models/nn/tokenizer.py`
**What.** Turns cleaned text into a fixed-length list of integer ids. Plain Python, no torch.
- `Tokenizer.fit(texts, min_count=2, trigram_buckets)`: vocabulary from train only; id 0 = padding, 1 = unknown.
- `encode(text)`: up to 48 word ids, padded; optionally 96 extra ids for hashed letter trigrams.
- `_trigram_ids(tokens)`: each trigram of `<word>` is hashed with `zlib.crc32` into one of 8,192 buckets (**the hashing trick**: no dictionary needed for letter pieces).
- `save`, `load` (`vocab.json`), `size`, `seq_len`, `words(text)`.

**Tests.** `model/test_nn_onnx.py::test_tokenizer_basics`.

#### `models/nn/net.py`
**What.** `IntentNet`, the small PyTorch network.
- `IntentNet(vocab_size, dim=64, n_classes=77, dropout=0.3)`: an embedding table, mean over real tokens (padding masked out), dropout, `Linear(64, 128)`, ReLU, `Linear(128, 77)`.
- `forward(ids)`: returns 77 scores (logits) per text.

**Tests.** `model/test_nn_onnx.py::test_torch_onnx_parity_200_texts` (needs torch).

#### `models/nn/train.py`
**What.** Trains three variants on CPU with one thread, early stopping on val macro-F1 (patience 6, at most 60 epochs), Adam at learning rate 0.002, batch 64, seed 42; keeps the best by **val** score.
- `VARIANTS`: `words_d64` (0.8672), `words_trigrams_d64` (0.8820, chosen), `words_trigrams_d128` (0.8759).
- `train_variant`, `macro_f1`, `save_best` (writes `model.onnx`, `vocab.json`, `model.pt`, `expected.json`, `variant.json`), `load_split`, `main`.

**Tests.** Indirect through the saved artifacts and `model/test_nn_onnx.py`.

#### `models/nn/export_onnx.py`
**What.** Exports the trained network to ONNX with a dynamic batch size, softmax included.
- `_WithSoftmax(net)`: wrapper so the file outputs probabilities.
- `export(net, seq_len, path)`: input `ids` (batch, seq_len) int64, output `proba` (batch, 77), opset 17.
- `torch_proba(net, ids)`: torch probabilities for the parity test.

**Tests.** `model/test_nn_onnx.py::test_torch_onnx_parity_200_texts` (difference under 1e-4 on 200 validation texts).

#### `models/nn/onnx_model.py`
**What.** Serves the network with onnxruntime only.
- `OnnxModel(directory)`: one-thread inference session, tokenizer from `vocab.json`, version `nn-words_trigrams_d64`.
- `predict_proba(texts)`: fits the `Classifier` interface.

**Tests.** `model/test_nn_onnx.py::test_onnx_matches_expected_without_torch`, `::test_nn_artifact_size`; `unit/test_load_nn.py`.

### 5.4 Routing: `sanket/routing/`

#### `routing/decide.py`
**What.** The routing rule. A **pure function**: no files, no model, no database, so every rule can be tested alone.
- `TEAM_INDEX`, `HIGH_INDEX`, `MEDIUM_INDEX`, `LOW_INDEX`: which of the 77 columns belong to each team and urgency, computed once.
- `Thresholds` (dataclass): `tau_team` 0.70, `tau_high` 0.20, `oov_max` 0.20, `oov_conf` 0.97 (from `thresholds.json`).
- `Decision` (dataclass): intent, intent_conf, top 5 intents, team, team_conf, team_probs, urgency, p_high, decision, reason.
- `team_probabilities(proba)`: sum of intent probabilities per team.
- `decide(proba, oov_rate, th)`: urgency `high` if p_high ≥ tau_high, else medium or low, whichever group sums higher; decision `human/low_confidence` if team_conf < tau_team, else `human/unfamiliar_words` if oov_rate > oov_max and team_conf < oov_conf, else `auto/ok`.

**Tests.** `unit/test_routing.py` (11, including `test_unfamiliar_words_alone_do_not_escalate_a_certain_team` and `test_low_confidence_wins_over_unfamiliar_words`).

#### `routing/thresholds.py`
**What.** Chooses the thresholds from validation data only, then saves and loads them.
- `team_matrix(proba)`: (n, 7) summed probability per team.
- `choose_tau_team(proba, y)`: the **smallest** step (0.05 to 0.95) where tickets at or above it have team accuracy ≥ 0.985 (val gave 0.70, with 0.9852).
- `choose_tau_high(proba, y)`: the **largest** step where at least 97% of truly high-urgency tickets have p_high at or above it (gave 0.20).
- `choose_thresholds(...)`: both, plus `oov_max` = the 99th percentile of validation unknown-word rates.
- `save_thresholds`, `load_thresholds`.

**Tests.** `unit/test_routing.py::test_tau_team_is_smallest_step_meeting_target`, `::test_tau_high_is_largest_step_meeting_recall`, `::test_choose_thresholds_uses_99th_percentile_for_oov`.

### 5.5 Monitoring: `sanket/monitoring/drift.py`

**What.** Drift maths in plain NumPy and the drift report.
- `bin_edges(reference, n_bins=10)`: cut points with about equal numbers of reference values per bin (quantiles); outer edges are minus and plus infinity.
- `psi(expected, actual, bins)` and `psi_from_shares(e, a)`: PSI = sum of (actual − expected) × ln(actual / expected), with a floor of 0.0001 per bin so the log is defined.
- `ks_2samp(a, b)`: sort both samples, compare their cumulative shares at every value with binary search (`np.searchsorted`), D = the largest gap. Exact p-value by a lattice-path walk (`_exact_sf`) when n × m ≤ one million, else the Kolmogorov series (`_kolmogorov_sf`).
- `ks_status(d, p)`: red if D ≥ 0.2 and p < 0.01; amber if D ≥ 0.1 and p < 0.01; else green. `psi_status(v)`: green under 0.1, amber to 0.25, red above.
- `drift_report(reference, live)`: KS on n_tokens, oov_rate and team_conf, PSI on the team mix; overall status = the worst; under 200 tickets it says `insufficient_data`.

**Tests.** `unit/test_drift.py` (8: `test_ks_matches_scipy` on 5 seeded cases, `test_psi_identical_is_zero_and_grows`, `test_psi_hand_example`, `test_report_statuses`); `model/test_audit_q2.py` (drift on real reference data; one strict xfail: PSI on a constant reference has one bin and always scores 0, a known LOW finding).

### 5.6 The API: `sanket/api/`, `api/index.py`

#### `api/app.py`
- `create_app()`: builds the FastAPI app; loads the runtime once at start-up (lifespan) unless a host already attached one; CORS allow-list from `SANKET_CORS_ORIGINS`.
- `limit_body` middleware: refuses a body over 20 kB (by the `Content-Length` header) with 413.
- `validation_error` handler: every error is `{"detail": "<one string>"}`.
- `app = create_app()`.

#### `api/tickets.py` and `api/ops.py`: the 13 routes

| Method and path | Function | What it does | Codes |
|---|---|---|---|
| `POST /api/tickets` | `create_ticket` | Runs the whole pipeline on one message, stores it, returns the result and trace. Only channel `web` from clients. | 201, 413, 422 |
| `GET /api/tickets?status=&limit=` | `list_tickets` | Lists tickets; `needs_review` is urgent first, then oldest. limit 1 to 500. | 200, 422 |
| `GET /api/tickets/{id}` | `read_ticket` | One ticket; the trace is re-run on the stored cleaned text (raw text is gone by design). | 200, 404 |
| `POST /api/tickets/{id}/review` | `review_ticket` | Confirm or override. | 200, 404, 409, 422 |
| `GET /api/health` | `health` | status ok, champion version, ticket count. The dashboard polls it. | 200 |
| `GET /api/stages` | `stages` | The seven stages with their real code. | 200 |
| `GET /api/taxonomy` | `taxonomy` | Teams with intents, urgency per intent. | 200 |
| `POST /api/compare` | `compare` | Runs the baseline and (if present) the network on the cleaned text. Stores nothing. | 200, 422 |
| `GET /api/monitor/drift` | `drift` | Latest stored drift report, or a fresh unsaved one. | 200 |
| `POST /api/monitor/drift/run` | `drift_run` | Computes drift over the latest 500 tickets and stores it. | 200 |
| `POST /api/demo/scenario` | `scenario` | `hinglish_surge` pushes up to 300 hinglishified stream rows through the pipeline; `reset` removes them. | 200, 422 |
| `GET /api/metrics` | `metrics` | The three queries in `metrics.sql`. | 200 |
| `GET /api/model` | `model` | Champion model card, registry and benchmark. | 200 |

There is **no endpoint that trains or promotes a model**, and no PUT, PATCH or DELETE (Q3 checked).

#### `api/queries.py`
**What.** Database reads for the API.
- `get_ticket_result(rt, id)`: rebuilds a ticket's result from stored rows.
- `live_inputs(rt, window=500)`: the latest 500 tickets' n_tokens, oov_rate, team_conf and team mix.
- `compute_drift`, `run_drift` (stores a report), `latest_drift`.
- `_named_queries()`: splits `metrics.sql` at each `-- name:` line; `metrics(rt)` runs the three queries.
- `run_scenario(rt, name)`: stream rows 400 to 699 through `hinglishify` and the real pipeline, channel `scenario`; `reset_scenario` deletes them.

**Tests.** `api/test_api.py::test_scenario_and_drift`, `::test_list_compare_taxonomy_stages_model_metrics`, `::test_compare_stores_nothing`; `api/test_audit_q3.py` (22 tests: abuse, PII, cap, encoding, CORS, no train route).

#### `api/index.py` (Vercel entry point)
**What.** The same FastAPI app for Vercel: puts the database under `/tmp`, deletes any old file, loads the models once, seeds `SANKET_SEED_TICKETS` (default 250) tickets, and exports `app`.
- `_seed_module()`: imports `scripts/seed.py` by path. `build_app()`: the steps above.

**Tests.** Covered indirectly by `unit/test_load_nn.py` (start without the network) and V1's local check with only `requirements.txt` installed. Verified live on 2026-11-15 (`/api/health` ok, 250 tickets).

### 5.7 Scripts: `scripts/`

| Script | What it does | Functions | Tests |
|---|---|---|---|
| `seed.py` | Fills a fresh database with demo data (`make seed`): 400 stream tickets through the real pipeline (every tenth gets a fake PII sentence), a simulated reviewer handles the queue except up to 15, one drift report. True labels live only in memory. | `remove_old_database`, `push_tickets`, `simulate_reviewer`, `count`, `main(n_tickets, rt)` | Indirect: `api/index.py` uses it; seed run 2026-11-15: 373 auto, 13 queued, 14 reviewed, 11 overrides, drift green, 3.3 s |
| `make_replay.py` | Records real API answers into `web/public/replay.json` (`make replay`): the six chips plus six more tickets, queue, drift before and after the surge, metrics, model, stages, taxonomy | `get`, `post`, `build`, `main` | `api/test_replay_and_bundle.py::test_replay_validates_and_matches_champion` |
| `space_bundle.py` | Writes `dist/space/` for a Hugging Face Space (Dockerfile, README with `sdk: docker`, package, champion, network files, stream, seed): 7.8 MB | `copy_files`, `main` | Q3 ran the bundle from its own folder (serves, no torch) |
| `make_fixtures.py` | Writes `fixtures/*.json` from the Pydantic schemas; invented but realistic values, used to build the web page before the API existed | `write`, `prediction`, `trace`, `summary_of`, `drift`, `main` | `unit/test_scaffold.py::test_fixture_validates` |
| `build_guide_html.py` | Builds `docs/INTERVIEW_GUIDE.html` from the Markdown | `convert`, `collapse_questions`, `wrap_tables`, `build` | Checked with a browser at 390 px (D1) |
| `build_handbook_html.py` | Builds this handbook's HTML and PDF from `docs/CANDIDATE_HANDBOOK.md` | `convert`, `collapse_questions`, `wrap_tables`, `build_html`, `build_pdf` | Run once; checked at 390 px |

### 5.8 The dashboard: `web/`

| File | What it does | Important parts | Tests |
|---|---|---|---|
| `src/main.jsx` | Starts React and mounts `App` | 6 lines | all e2e |
| `src/App.jsx` | The page. Decides Live or Replay once (`checkHealth`), polls health every 10 s while Live and falls back to Replay with a notice if the API dies, retries every 15 s while in Replay. Text box (2,000 limit), Submit, six chips, then the strip and three panels. Cards light up one by one (120 ms) when a result arrives. | `run`, `submit`, `chip`, `fallBack`, `light` | `e2e/replay.spec.js`, `e2e/live.spec.js`, `e2e/q3_audit.spec.js` (badge leaves Live when the API dies) |
| `src/api.js` | All data access. `liveApi` has one function per REST route; `makeReplayApi(replay)` has the same function names but answers from `replay.json` and keeps reviews in memory (a second review in the same tab gives 409). Health timeout 4 s, 12 s for a same-origin build. | `call`, `checkHealth`, `loadReplay`, `liveApi`, `makeReplayApi`, `fromQueueRow` | e2e specs |
| `src/samples.js` | The six chip texts and the stage order | `CHIPS`, `STAGE_ORDER`, `STAGE_TITLES` | `api/test_replay_and_bundle.py` checks the chip order in replay.json |
| `src/Pipeline.jsx` | Seven cards with arrows and the "retrain gate" return line | `Pipeline`, `cardText`, `cardMs` | `replay.spec.js` |
| `src/Drawer.jsx` | Side panel with four tabs: What it does, Why this way, Code (real source from `/api/stages`), Live example (this ticket's data: masked before/after, top-5 bars, term bars, team bars and the rule in words, compare table). Esc closes it. | `Drawer`, `Example`, `Classify`, `Bars`, `Marked`, `ruleInWords` | `q3_audit.spec.js` (Code tab; script and HTML render as text, never run) |
| `src/ReviewForm.jsx` | Confirm or override: top-5 chips, searchable intent list grouped by team, optional urgency and note; shows "Someone already reviewed this ticket" on 409 | `ReviewForm`, `send` | `replay.spec.js` (every queued ticket can be reviewed) |
| `src/Panels.jsx` | Review queue, Monitor (drift indicators, override rate by team, Simulate Hinglish surge, Reset), Model (card summary, LR vs NN table, registry history) | `QueuePanel`, `MonitorPanel`, `ModelPanel`, `flat` | `replay.spec.js` (surge turns drift red) |
| `src/styles.css` | One CSS file; the strip scrolls sideways inside itself so the page does not at 390 px | | `replay.spec.js` (narrow screen) |
| `scripts/fixtures_to_replay.mjs` | Builds a replay file from fixtures only if none exists (`npm run build`) | | |
| `playwright.config.js` | Finds Chromium in `PLAYWRIGHT_BROWSERS_PATH`; replay specs by default, `@live` specs with `SANKET_LIVE_API` | | |

Known small gaps: the drawer is not focus-trapped; `Drawer.jsx` highlights only `[EMAIL]`, `[PHONE]`, `[CARD]`, `[ACCOUNT]`, not `[UPI]`, `[AADHAAR]`, `[PAN]` (cosmetic, Q3 LOW).

### 5.9 PRAHARI at module level

| Folder | What it does | Main pieces | Tested by |
|---|---|---|---|
| `prahari/sim/` | Simulator: 120-node topology (core, aggregation, access, cell), 6 KPIs per node per minute, faults that spread downstream, true and noise alarms, live injection | `topology.py`, `kpi.py`, `faults.py`, `alarms.py`, `generate.py`, `live.py` | `tests/test_sim.py`, `tests/data/test_realism.py` |
| `prahari/db.py` | SQL tables (nodes, links, kpi_samples, alarms, incidents, predictions, actions, audit_log, drift_reports, detected_incidents), indexes, WAL | `init_db`, `get_engine` | `tests/test_db.py` |
| `prahari/pipeline/` | Features in pandas and NumPy, label-free loaders, quality checks, chronological splits | `store.py`, `features.py`, `quality.py`, `splits.py` | `tests/test_pipeline.py`, `tests/data/*` (leakage, corruption, splits) |
| `prahari/models/validator/` | Alarm real vs noise: HistGradientBoosting + isotonic calibration; LogisticRegression baseline; threshold 0.18 for recall ≥ 0.98 on val | `model.py`, `train.py` | `tests/test_models_classical.py`, `tests/models/test_quality_gates.py` |
| `prahari/models/anomaly/` | IsolationForest on 14 lagged KPI features; 3-sigma baseline | `model.py`, `train.py` | same |
| `prahari/models/rca/` | `RCAGNN`: input layer + 3 residual GCN layers, root head and fault-type head; two rule baselines and an MLP; ONNX export | `model.py`, `baselines.py`, `train.py`, `predictor.py` | `tests/test_rca.py`, quality gates |
| `prahari/agent/` | Runbook search (TF-IDF), a guarded SQL tool, propose action, English/Hindi templates, optional LLM adapters (tested only with fake transports) | `retrieval.py`, `sqlguard.py`, `tools.py`, `agent.py`, `flow.py`, `templates.py`, `llm.py` | `tests/test_agent.py` (19 SQL attack strings rejected in Q3) |
| `prahari/governance/` | 10 checks G1 to G10 as subclasses of an abstract `Check`, configured in `policy.yaml`; fail closed on errors | `checks.py`, `redact.py`, `evaluate` | `tests/test_governance.py` (one pass and one fail test per check) |
| `prahari/serving/` | FastAPI: detector loop, incidents, approve/reject, typed errors, request ids, latency histogram at `/metrics` | `app.py`, `incidents.py`, `services.py`, `data.py`, `obs.py` | `tests/serving/test_api.py` |
| `prahari/monitoring/` | PSI and KS in NumPy, drift reports, retrain with promote rule, benchmark, load test | `stats.py`, `drift.py`, `retrain.py`, `bench.py`, `loadtest.py` | `tests/test_monitoring.py` |
| `web/` | React + Vite + Tailwind + Cytoscape + Recharts: Live Ops, Incident, Model health, Audit views; mock mode from fixtures | `src/views/*.jsx`, `src/api.js` | Playwright mock and real-API specs |

---

## 6. How everything was tested

### 6.1 The test pyramid

A **test pyramid** means many small, fast tests at the bottom and fewer, slower, wider tests at the top.
Counts below come from `pytest --collect-only` on the real test files and from the e2e spec files **(measured 2026-11-15)**.
The full Python run on that day: **261 passed, 1 xfailed, in about 162 seconds** (the README badge says 259 from an earlier run, before two tests were added).
An **xfail** is a test marked "expected to fail": a known, documented finding. The one left is a LOW finding (PSI on a constant reference).

```
                 /\        audits (Q1, Q2, Q3) + clean clone          people-style checks, slowest
                /  \       load test (Q3: 1, 8, 32 clients)
               /    \      browser e2e: 11 Playwright tests
              /------\     API: 45 tests
             /        \    model quality gates: 46 tests
            /          \   data audits and checks: 118 tests
           /------------\  unit: 53 tests                                fastest
```

| Layer | Folder and count | What it catches | Run it |
|---|---|---|---|
| Unit | `tests/unit/`: **53** (`test_scaffold` 17, `test_routing` 11, `test_clean` 10, `test_drift` 8, `test_pii` 5, `test_load_nn` 2) | One function wrong: Luhn and Verhoeff, cleaning, each routing rule, PSI and KS maths (KS checked against SciPy), taxonomy counts, foreign keys and the unique review rule, artifact sizes | `.venv/bin/python -m pytest tests/unit -q` |
| Data audits | `tests/data/`: **118** (`test_audit_pii` 74, `test_audit_quality` 13, `test_quality` 10, `test_split` 5, `test_audit_leakage` 5, `test_audit_hinglish_rubric` 4, `test_perturb_stress` 4, `test_audit_tokens` 2, `test_audit_easy` 1) | Bad data before training: 35+ PII formats, 13 kinds of corruption (shuffled labels, HTML, raw PII, repeated ids, test rows dropped), leaks between splits, near copies of test texts, "is the task too easy?" probes, the token "1" shortcut | `.venv/bin/python -m pytest tests/data -q` |
| Model quality gates | `tests/model/`: **46** (`test_quality_gates` 20, `test_audit_q2` 17, `test_baseline` 5, `test_nn_onnx` 4) | A model that got worse: macro-F1, team accuracy, high-urgency recall, auto-routed accuracy, p95 latency under 20 ms, calibration stored, explanation adds up exactly, ONNX equals torch, the retrain gate rejects poison and accepts honest reviews | `.venv/bin/python -m pytest tests/model -q` |
| API | `tests/api/`: **45** (`test_audit_q3` 22, `test_api` 14, `test_review_safety` 8, `test_replay_and_bundle` 1) | Wrong status codes (201, 404, 409, 413, 422), PII in the database or its side files, two reviewers on one ticket, 20 parallel posts, the cap deleting reviews, bad encoding giving 500, CORS, no train route, replay file shapes | `.venv/bin/python -m pytest tests/api -q` |
| Browser e2e | `web/e2e/`: **11** Playwright tests, 6 replay (`replay.spec.js` 4, `q3_audit.spec.js` 2) and 5 `@live` (`live.spec.js` 2, `q3_audit.spec.js` 3) | The real page in Chromium: chips fill the strip, drawer tabs show real code, a queued ticket can be overridden, the surge turns drift red, 390 px width has no sideways page scroll, script and HTML render as text, the badge leaves Live when the API dies | `cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers npm test` (replay); with the API running: `SANKET_LIVE_API=http://localhost:8000 npm run test:live` |
| Load test | Run by the Q3 auditor, numbers in `docs/handoffs/Q3.md`; no script committed in SANKET (`test_api.py::test_parallel_posts` sends 20 at once) | Slowdowns and errors under many users | uvicorn 1 worker: 1 client p50 8.6 ms, p95 12.1 ms; 8 clients 32.8 / 160.4 ms; 32 clients 163.7 / 719.9 ms; **0 errors in 1,400 requests**, no "database is locked" |
| Clean clone | Q3 cloned from GitHub into an empty folder | Missing files, steps that only work on the build machine | setup 40 s, data 4 s (byte-identical), train 72 s (model identical), seed 5 s, tests 197 pass / 1 skip / 1 flaky timing test (since fixed), lint clean. Docker not verified. |
| Audits | Q1 data, Q2 model, Q3 system; each wrote strict xfail tests for its findings | Problems the builders did not think of | Read `docs/handoffs/Q1.md`, `Q2.md`, `Q3.md`; `docs/AUDIT_LOG.md` |
| Lint and CI | `ruff check .`; `.github/workflows/ci.yml` has two jobs: python (setup, lint, test) and web (npm ci, build, Playwright replay specs) | Style errors; anything broken on a fresh runner | `make lint`; push to GitHub |

### 6.2 What "strict xfail" means and why it matters

When an auditor found a problem, it wrote a test that **should** pass once the problem is fixed, and marked it `xfail(strict=True)`.
"Strict" means: if the test suddenly passes, pytest reports an error until someone removes the marker.
So a fix cannot be claimed without the test flipping, and a finding cannot be forgotten. This is how "every fix has a test" was enforced, not just promised.

### 6.3 How the main numbers were checked

- Q2 re-ran `make train train-nn bench` from scratch in a separate folder: `model.joblib`, thresholds, reference and `model.onnx` were **byte-identical**, and every card number reproduced exactly.
- `make data` twice (and with a different `PYTHONHASHSEED`) gives byte-identical splits (Q1).
- The baseline-vs-network gap has a bootstrap 95% interval of +0.004 to +0.024 macro-F1 (Q2). A **bootstrap** resamples the test set many times with replacement and recomputes the gap, to see how much it moves by chance.
- Explanations: contributions plus intercept equal the raw score (maximum error 8e-8 over 20 tickets, Q2; and a unit test).

### 6.4 Commands in one place

```bash
make setup                 # venv and pip install -e '.[dev]'
make data train            # splits (about 3 s), model v1 (about 1 minute)
make test                  # all 262 Python tests
make lint                  # ruff
make bench                 # writes docs/bench.md
make seed serve            # demo database, API on :8000
VITE_API_URL=http://localhost:8000 make web   # dashboard on :5173 (cd web && npm install once)
make retrain               # learn from reviews; promote only through the gate
.venv/bin/python -m sanket.retrain --from-csv some.csv --sabotage 0.3   # prove the gate rejects poison
```

---

## 7. Job description mapping

Ratings: **strong** = built, measured and tested here; **partial** = shown, but small, or done by tools you should be able to explain; **not shown** = not in either project. Be ready to say the "not shown" ones out loud without apology.

### 7.1 Role bullets

| JD bullet | Evidence (files, tests, numbers) | Rating |
|---|---|---|
| Implement ML and AI models as per solution designs | `sanket/models/baseline.py` (TF-IDF + logistic regression, macro-F1 0.900), `sanket/models/nn/` (PyTorch `IntentNet`, 0.8865); built to `docs/plan/CONTRACTS.md`. PRAHARI: GNN, gradient boosting, IsolationForest | strong |
| Support AI-driven features for applications and platforms | Dashboard: word-level explanation, review queue, drift panel, live/replay fallback (`web/src/`) | strong |
| Convert analytical models into production-ready components | `Classifier` protocol, versioned `artifacts/models/v1/`, `registry.json`, model cards, ONNX export, a gate before promotion | strong |
| Integrate trained models with APIs, applications and data pipelines | `sanket/service.py: process_ticket` (one call: clean, classify, explain, route, store), 13 REST routes, same `clean()` at train and serve | strong |
| Support deployment on cloud or on-prem | Live on Vercel (serverless Python function + static page, `vercel.json`, `api/index.py`); Hugging Face Space bundle prepared (`make space-bundle`, 7.8 MB); `Dockerfile` written but **not built**; on-prem **not shown** | partial |
| Monitor model performance and basic drift indicators | `sanket/monitoring/drift.py` (PSI, KS, 4 indicators, red on the Hinglish surge: unknown-word D 0.58); override rate by team in `sanket/sql/metrics.sql`; latency per model | strong |
| Support feature pipelines with data scientists and engineers | `sanket/pipeline/` (load, clean, split, quality), contracts and fixtures between components | strong (pipeline) / partial (no human team) |
| Data preprocessing and transformation | NFKC, digit unification, PII masking, lower-casing, TF-IDF, tokenizer with hashed trigrams | strong |
| Data compatibility and reliability for model execution | `quality.py` checks (13 corruptions caught), 422 on bad input, `validate_text` refuses un-storable text | strong |
| Functional testing of AI components and services | 262 Python tests, 11 browser tests, quality gates, ONNX parity, strict xfails | strong |
| Model optimisation for performance, scalability, latency | `make bench` (p50 0.82 ms vs 0.055 ms ONNX); the 8× speed bug fixed; float32 weights (no accuracy cost, 4.93 MB); PRAHARI int8 quantisation (113 → 43 KB) and a 36× faster KPI query (1,078 → 30 ms) | partial-to-strong |
| Debug issues in inference and integrations | Audit stories 1 to 8; per-stage timings in every trace; lone surrogate 500 → 422; Vercel without onnxruntime → graceful `nn: null` | strong |
| Collaborate with data science, engineering and QA | Multi-agent workflow with contracts, handoffs, independent QA audits. **With people: [your own example]** | partial |
| Maintain documentation for components and integrations | README, ARCHITECTURE, GLOSSARY, data card, model cards, DEPLOY, AUDIT_LOG, EXPERIMENTS, this handbook | strong |
| Adhere to engineering standards, security guidelines and timelines | ruff, CI, exact version pins, PII never stored raw, input limits, CORS allow-list, no pickle from users, no train endpoint | strong |

### 7.2 Skills

| Skill | Evidence | Rating | If asked what is missing |
|---|---|---|---|
| Python | Whole back end, 3.11, type hints, dataclasses, Protocol, context managers | strong | |
| JavaScript (advantage) | React dashboard in plain JavaScript (`web/src/`, about 700 lines); Playwright tests in JS | partial | "The dashboard is plain JavaScript and React. I can read and change it; front end is not my main strength yet." |
| Java or C++ (advantage) | none | **not shown** | "Neither project uses Java or C++. I have [your own example: coursework or labs]. The ideas carry over: interfaces, classes, collections." |
| Data structures and algorithms | Hash maps (vocabulary, unknown words), heap for top-k (`heapq.nlargest`), sort plus binary search in KS, lattice-path dynamic programming for the exact KS p-value, Luhn and Verhoeff checksums, hashing trick (`zlib.crc32`), priority order in the queue | strong (applied) | "I have not done competitive programming in these projects; the DSA is applied." **[your own example]** |
| OOP | `Classifier` protocol with two implementations; dataclasses (`Thresholds`, `Decision`, `CleanResult`, `Runtime`); custom exceptions mapped to HTTP codes; PRAHARI abstract `Check` with 10 subclasses (G1 to G10) | partial-to-strong | "SANKET is mostly functions on purpose; PRAHARI's governance is the clearest class hierarchy." |
| DBMS | 4 tables, foreign keys (`PRAGMA foreign_keys=ON`), composite index (status, created_at), unique constraint, transactions, conditional update for a race condition, WAL mode | strong | "No Postgres in production, no migrations tool, no replication." |
| SQL | `sanket/sql/metrics.sql` (JOIN, GROUP BY, CASE, AVG, date()); queue ordering with CASE; section 8.6 | strong | |
| Software engineering fundamentals | Contracts, small modules, pure routing function, CI, version pins, Makefile, reproducible builds | strong | |
| Statistics and probability | Softmax, summing disjoint probabilities, precision/recall trade-off, calibration (ECE, temperature), PSI, KS with exact p-value, bootstrap interval, p-values, n = 60 caveats | strong | |
| Linear algebra | TF-IDF vector (1 × 20,672) times weight matrix (20,672 × 77); dot products as explanations; embeddings, mean pooling and two dense layers; PRAHARI normalised adjacency Â = D^-1/2 (A + I) D^-1/2 | partial-to-strong | "No eigen-decomposition or SVD work here." |
| Machine learning | Train/val/test discipline, stratified split, grid on val only, regularisation (C), early stopping, ablation, calibration, error analysis, leakage checks | strong | |
| NumPy, pandas, scikit-learn | Drift maths, softmax, team sums; data pipeline; vectorisers, logistic regression, metrics | strong | |
| PyTorch (or TensorFlow) | `IntentNet` trained on CPU, early-stopped, exported to ONNX, parity-tested, benchmarked; PRAHARI hand-written GCN | strong (small models) | "No GPU training, no transformers, no TensorFlow." |
| SQL, Git, REST APIs | SQL above; 23 commits, wave by wave, CI on push; 13 REST routes with meaningful status codes | strong (SQL, REST) / partial (Git: the commits were made by the orchestrating agent; practise branching yourself) | |
| Debug systematically; reason about accuracy, performance and trade-offs | Audit stories; coverage table (0.7 → 94.4% at 0.992; 0.8 → 92.2% at 0.995); network faster but less accurate; urgency threshold favours recall | strong | |
| Deployment | Vercel serverless (live), HF Space bundle, Dockerfile (not built), replay fallback | partial | "Cloud here means serverless on Vercel, not AWS, Azure or GCP. Containers were written, not run. On-prem not shown." |
| Drift and monitoring | PSI, KS, override rate, insufficient-data guard, simulated surge | strong | "No alerting or scheduled job; drift is run on demand." |
| Testing | Section 6 | strong | |
| Optimisation | See 7.1 | partial-to-strong | "No GPU, batching server or caching layer in SANKET; PRAHARI has a 30 s cache." |
| Documentation | Section 7.1 | strong | |
| Collaboration across locations | Agents and contracts; **[your own example]** with people | partial | |
| Responsible AI and privacy | PII masking before storage (tickets and reviewer notes), human in the loop, override log, promote gate with label sanity, rubric disclaimer, Hinglish failure reported, model cards with limits; PRAHARI governance checks and audit log | strong (design) / partial (legal compliance: DPDP Act not formally implemented) | "I designed for data minimisation and human oversight. I have not done a formal DPDP compliance review; that needs a legal and privacy team." |
| Curiosity, learning from failed experiments | `docs/EXPERIMENTS.md`: network lost; nearest-text label check failed; 128-dim network worse than 64; threads slowed training 5× | strong | |

### 7.3 What to say when they ask "what is missing?"

"Three things. First, Java or C++: neither project uses them. Second, enterprise deployment: my live demo is serverless on Vercel, the Docker image was written but not built, and I have not deployed on-prem or on a big cloud. Third, real production data and real users: Banking77 is public and short, and my team and urgency labels are my own rubric. I would like to learn all three on a real project."

---

## 8. The question bank

How to use it: read the question, cover the answer, say yours out loud, then compare. The answers are written in your voice: short, plain, honest. Say them in your own words; do not recite.
In the HTML version, click a question to open its answer; "Open all answers" opens every one, and printing opens them all.

### 8.1 HR and motivation

#### Q1. Tell me about yourself.
"[your own example: name, college, branch, year, one line about what you enjoy.] Recently I have been building end-to-end AI systems. My main project is SANKET, a bank support-ticket triage system that is live on Vercel: it masks personal data, predicts the intent of a message, routes it to a team with an urgency, and asks a person when it is unsure. I care about the parts around the model: testing, monitoring, privacy and honest numbers. That is why this role appeals to me."

#### Q2. Why Tech Mahindra?
"The job description says AI engineers here do more than train models: they build reliable, responsible and scalable solutions for enterprises. That is exactly what I tried to practise. Tech Mahindra also talks publicly about AI for service desks, contact centres, banking and telecom networks, which are the two areas my projects are in. [Add one sentence from a Tech Mahindra page you read yourself, section 9.]"

#### Q3. Why this role, Digital Catalyst - AI Engineer?
"I like the step from a model to a working product: the API, the data checks, the monitoring, the human review. The role lists integration, deployment, drift monitoring, testing and documentation. Those are the parts I spent most of my time on."

#### Q4. Where do you see yourself in three to five years?
"Owning an AI component end to end in a client project: from data checks to deployment and monitoring, and being the person others ask when a model behaves strangely in production. [Adjust to your own goals.]"

#### Q5. What is your biggest strength?
"Being honest with evidence. When my PyTorch model lost to the simple model, I reported it and kept the simple one. When an audit found a bug, I fixed it and added a test so it cannot come back."

#### Q6. What is your biggest weakness?
"I can go too deep checking things. On SANKET I had three separate audits and many fix rounds. I am learning to time-box: decide what 'good enough' means before I start. [Or use a true weakness of your own.]"

#### Q7. Are you comfortable relocating or working at client sites?
"[your own answer. The JD says PAN India and client locations depending on the project.]"

#### Q8. Do you have any offers or other interviews?
"[your own answer. Be truthful and brief.]"

### 8.2 Project overview

#### Q9. Walk me through SANKET.
Use the 2-minute pitch. Then offer: "I can show it live; it takes four minutes."

#### Q10. What problem does it solve, and for whom?
"A bank's support desk gets thousands of messages. Someone has to read each one and send it to the right team, and urgent ones like fraud must not wait. SANKET does the first read: it routes the clear ones automatically and sends unclear ones to a person, with the reason shown."

#### Q11. What are the components?
"Seven stages on the dashboard: ingest, clean, classify, explain, route, review, monitor. Plus a retrain gate that a person runs. Each one is a small file: for example routing is one pure function, `decide`, in `sanket/routing/decide.py`."

#### Q12. What is the most interesting design decision?
"Predicting the intent, not the team, and getting the team by adding up the intent probabilities. A message can be unclear between two card intents but clearly a card message. Summing beat a model trained directly on the 7 teams: 0.9708 against 0.9636 team accuracy on test. And reorganising teams is a YAML edit, not a retrain."

#### Q13. How does a ticket decide between auto and human?
"If the best team's probability is under 0.70, a person looks. If more than 20% of the words are unknown and the team is under 0.97, a person looks. Otherwise it is automatic. On test that sends 94.2% automatically, and 99.2% of those reach the right team."

#### Q14. How is urgency decided?
"I add the probabilities of the 9 high-urgency intents, like lost or stolen card and unrecognised payment. If that sum is at least 0.20, the ticket is high. Otherwise medium or low, whichever group adds up higher. The low cut-off is on purpose: missing a fraud report costs more than an extra look. Test recall 0.983, precision 0.915."

#### Q15. How did you choose those thresholds?
"By written rules on validation data only. The team cut-off is the smallest step where auto-routed validation tickets are at least 98.5% right: 0.70. The urgency cut-off is the largest step where at least 97% of urgent validation tickets are caught: 0.20. The test set was only used to report."

#### Q16. What does the explanation show, exactly?
"For the predicted intent, the five terms with the biggest weight times TF-IDF value. The score of an intent is the sum of those products plus an intercept, so the explanation is exact, not an estimate. A unit test checks the sum equals the raw score."

#### Q17. What is your accuracy, and is it good?
"Intent accuracy and macro-F1 are both 0.900 on the 3,080 official test messages. To check the task is not trivially easy, an audit tried simple baselines: a depth-3 decision tree got macro-F1 0.036, a length-only model 0.022, one keyword per intent 0.338. So 0.90 on 77 classes is real work. Team accuracy is 0.971, but that measures agreement with my own table."

#### Q18. How fast is it?
"The model takes 0.82 ms per ticket at the median, including cleaning. A full `POST /api/tickets` through the API, including the database write, was 9.9 ms at p50 and 12.0 ms at p95 over 200 requests."

#### Q19. What does the dashboard do when the server is asleep?
"It asks `/api/health`. If there is no answer, it switches to Replay: real answers recorded from the same pipeline in `replay.json`, with an amber badge, and it keeps retrying. If the API dies while you are using it, it notices within about ten seconds and switches, with a notice."

#### Q20. What is PRAHARI, in one minute?
"A larger project: a network-operations helper for telecom. When a fibre is cut, many devices raise alarms. PRAHARI filters noise alarms, uses a graph neural network to find the root-cause device, proposes a fix in English or Hindi, and runs 10 governance checks before a person approves. The data is synthetic, from my own simulator, so I never quote its numbers as real accuracy. Honest result: the graph model beats a no-graph model by only 1 point over 10 seeds, which is not significant."

### 8.3 Data

#### Q21. Where does the data come from? Is it real?
"Banking77, published by PolyAI in 2020 under CC-BY-4.0: about 13,000 real customer-service questions to a bank, each labelled with one of 77 intents. The texts are real, but they contain no real personal data. The team and urgency labels are mine; they are not in the dataset."

#### Q22. How did you split it?
"The official test set, 3,080 rows, is frozen. From the official train set I removed 7 texts that also appear in test, 4 duplicates and 68 near copies of test texts. The rest was split by intent into train 6,946, validation 1,489 and stream 1,489, with seed 42. Running it twice gives byte-identical files."

#### Q23. Why a separate 'stream' split?
"It feeds the live demo and the review queue. Corrections from reviews become training data, so if demo tickets came from the test set, test rows would leak into training. A separate stream makes that impossible."

#### Q24. What is data leakage, and did you have any?
"Leakage is when information from the test set gets into training, so the score looks better than it really is. Exact overlap was zero after cleaning. 68 near copies of test texts were removed from train. But 351 of 3,080 test rows, 11.4%, still have a training text with cosine similarity above 0.9; they are paraphrases, too many to drop without thinning train, and the test set is official, so I documented it in the data card."

#### Q25. What data-quality checks run?
"`check_frame` and `check_splits` in `quality.py`: no nulls or empty text, no unknown intents, no duplicate texts, unique ids, no HTML or broken characters, text already cleaned, length 5 to 2,000, at least 20 rows per class in train, test exactly 3,080 rows, no near copies of test in train, and a label-agreement check that catches shuffled labels. An audit tried 13 kinds of corruption; after the fix all are caught."

#### Q26. Is the data balanced?
"Training classes range from 25 to 129 rows. The test set has exactly 40 per intent, which is why accuracy and macro-F1 are both 0.900 there. Every team is at least 6.4% and high urgency at least 11.7% in every split."

#### Q27. What is wrong with the labels?
"An audit re-labelled 150 training rows by hand and disagreed with 12, about 8%. For example 'wheres my pin' is labelled get_physical_card. I listed them in the data card instead of silently changing them."

#### Q28. Did you find any shortcuts in the data?
"Yes. The token '1', as in '£1 charge', appears in 58 of 114 training rows of `extra_charge_on_statement`. So a ticket about a different amount might be routed wrongly, and the test score would not show it. It is written down as a caveat."

#### Q29. How did you test Hinglish and typos?
"Two stress sets, used only for reporting. 60 hand-written Hinglish messages: intent accuracy 0.65, 26 sent to a person, none silently sent to the wrong team, one given the wrong intent in the right team. And the test set with 10% of letters changed: intent accuracy 0.817, 35.4% sent to a person, 0.55% silently wrong team. I always say n = 60 for Hinglish."

### 8.4 Machine learning basics

#### Q30. What is the difference between bias and variance?
"Bias is error from a model that is too simple to capture the pattern; it is wrong in the same way on training and new data. Variance is error from a model that fits the training data too closely; it changes a lot with different training samples and does worse on new data. Regularisation, more data and simpler models reduce variance; richer features reduce bias. My network reached about 0.99 training accuracy but 0.8865 test macro-F1, so it was on the high-variance side."

#### Q31. What is overfitting, and how did you limit it?
"The model memorises the training set and does worse on new data. I limited it with regularisation (C in logistic regression), early stopping for the network, choosing every setting on validation only, and a frozen test set touched only for reporting."

#### Q32. Explain precision, recall and F1.
"Precision: of the tickets I flagged urgent, how many really were urgent. Recall: of the truly urgent tickets, how many I flagged. F1 is their harmonic mean, 2PR/(P+R), which is low if either is low. For urgency I care most about recall: 0.983 with precision 0.915. If I raised the cut-off from 0.20 to 0.50, recall would drop to 0.936 and precision rise to 0.963 (measured on test, 2026-11-15)."

#### Q33. Macro-F1 versus micro-F1 versus accuracy?
"Macro-F1 computes F1 per class and averages them equally, so a rare class counts as much as a common one. Micro-F1 pools all decisions; for single-label classification it equals accuracy. On a balanced test set like mine they are all about the same; on real, skewed ticket data macro-F1 is the honest one."

#### Q34. What is calibration, and why did it matter here?
"A model is calibrated if, among answers given at about 90% confidence, about 90% are right. My routing thresholds and reviewers read the confidence, so it must be honest. Before the fix the model said 74% on average but was right 90% of the time: ECE 0.160. After temperature scaling, test ECE 0.0146."

#### Q35. What is ECE, and how is it computed?
"Expected calibration error. Put predictions into 10 confidence buckets, compare average confidence with accuracy in each bucket, and take the average gap weighted by how many predictions are in each bucket. The code is `expected_calibration_error` in `evaluate.py`."

#### Q36. What is temperature scaling?
"Divide every raw score by one number T before softmax. T below 1 sharpens the probabilities, above 1 flattens them. The ranking does not change, so accuracy does not change; only the confidence does. T is chosen to minimise log-loss on validation data. Mine is 0.591."

#### Q37. What is cross-validation, and did you use it?
"K-fold cross-validation splits the data into k parts, trains on k−1 and tests on the remaining one, k times, and averages. It gives a steadier estimate on small data. I did not use it: I had enough data for a fixed validation set of 1,489 rows, and a fixed split made every threshold reproducible and kept the stream separate. With a small dataset I would use stratified k-fold."

#### Q38. What is regularisation? What does C do?
"A penalty on large weights, so the model cannot memorise by giving huge weights to rare words. In scikit-learn's logistic regression C is the inverse strength: smaller C means a stronger brake. I tried C = 5, 10 and 20 on validation; with letter groups C = 5 was best (0.8981)."

#### Q39. Explain TF-IDF.
"Term frequency times inverse document frequency. A word scores high if it appears in this message and is rare in the collection. 'lost' is more informative than 'card', because 'card' is everywhere. Example: three messages 'card not working', 'card lost', 'transfer not working'. IDF of 'card' is ln(3/2) = 0.405; of 'lost' ln(3/1) = 1.099. scikit-learn uses a smoothed IDF and scales each vector to length 1. I also use sublinear TF, 1 + ln(count), and letter groups of 2 to 5 characters, which help with spelling variants."

#### Q40. Explain logistic regression for 77 classes.
"For each intent there is one weight per feature plus an intercept. The score of an intent is the dot product of the TF-IDF vector with that intent's weights, plus the intercept. Softmax turns the 77 scores into probabilities. Training finds weights that minimise cross-entropy plus the regularisation penalty. In SANKET the weight matrix is 77 × 20,672."

#### Q41. Explain softmax with numbers.
"Raise e to each score and divide by the sum. Scores 2.0, 1.0, 0.1 give e-powers 7.39, 2.72, 1.11, total 11.21, so probabilities 0.659, 0.242, 0.099. They are all positive and add up to 1. In code I subtract the largest score first, so `exp` never overflows; that does not change the result."

#### Q42. What is cross-entropy loss?
"Minus the log of the probability given to the right answer. If the right intent gets 0.857, the loss is 0.15; if it gets 0.09, the loss is 2.41. Confident and wrong is punished hard. Both my models minimise it."

#### Q43. What is gradient descent?
"A way to train: compute how the loss changes with each weight (the gradient), and move every weight a small step in the direction that lowers the loss. Repeat. The step size is the learning rate. My network used Adam, a variant that adapts the step per weight, at 0.002, on mini-batches of 64."

#### Q44. What is an embedding?
"A learned list of numbers for each word, so words used in similar ways end up with similar lists. My network uses 64 numbers per word, plus 64 for each hashed three-letter piece. The weakness of averaging them is that word order is lost: 'not lost, arrived' and 'arrived, not lost' look the same."

#### Q45. Why did you not use BERT or an LLM?
"Four reasons. No GPU and a free host with tight size limits. Short texts with about 90 examples per class, where TF-IDF is already strong. I wanted explanations that are exact, not approximate. And I wanted to explain every part honestly in an interview. With more data, longer complaints or many languages, a fine-tuned transformer would be the next experiment, through the same retrain gate."

#### Q46. What is the difference between the validation set and the test set?
"Validation is for choosing things: C, the temperature, the thresholds, the network variant, early stopping. Test is for the final score, used only to report. If you tune on test, the test score lies."

#### Q47. What is an ablation?
"Removing or swapping one part to see how much it matters. I compared summing intent probabilities with a direct 7-team model: 0.9708 against 0.9636 test team accuracy, so the design stayed."

#### Q48. What does a coverage table tell you?
"For each team-confidence cut-off: how many tickets go automatically and how accurate those are. At 0.5: 98.3% automatic, 0.979 accurate. At 0.7: 94.4%, 0.992. At 0.9: 87.3%, 0.999. It shows the trade-off between people's workload and mistakes, so the business can choose."

#### Q49. Why does the urgency cut-off favour recall?
"The costs are not equal. A missed fraud report can cost a customer money; an extra look costs a reviewer a minute. So the rule was 'catch at least 97% of urgent validation tickets' and accept some false alarms: on test, 23 medium tickets were flagged high, and the 2 high tickets predicted low both went to a person anyway."

### 8.5 The PyTorch model

#### Q50. Describe your PyTorch network.
"`IntentNet` in `sanket/models/nn/net.py`. Each word id looks up a 64-number embedding; hashed three-letter pieces have their own embeddings. I average the vectors of real tokens, masking out padding. Then dropout 0.3, a linear layer to 128, ReLU, and a linear layer to 77 scores. It is trained with Adam and cross-entropy, early-stopped on validation macro-F1."

#### Q51. Why is the PyTorch model worse?
"Three reasons. Only about 90 short training messages per intent, which is little for learning embeddings from scratch. Averaging vectors throws away word order. And TF-IDF on words plus letter groups is a very strong fit for short texts at this size. It lost by 1.4 macro-F1 points, 0.8865 against 0.9003, and the bootstrap interval for the gap is +0.004 to +0.024, so the loss is real."

#### Q52. Was the comparison fair?
"An independent audit checked: same cleaned text, same 3,080 test rows, cleaning included in both timings, 50 warm-up calls, one CPU thread. The network was early-stopped at about 0.99 training accuracy, so it was not starved. Other seeds gave 0.887 to 0.889. The baseline was not weakened: its feature caps did not bind."

#### Q53. Then why build it at all?
"To compare honestly instead of assuming. To show I can train, export and benchmark a neural model. And because the rule was written before the results: 'if the network loses, say so and do not tune it until it wins'. It still has a job as a second opinion in the Compare view, when onnxruntime is installed."

#### Q54. Why is the network faster if it is worse?
"It does a few hundred lookups and two small matrix multiplications. The baseline builds sparse TF-IDF vectors with 2 to 5 letter pieces, which is most of its 0.82 ms. ONNX p50 is 0.055 ms, about 15 times faster. But both are far below a millisecond, while the whole API call is about 10 ms, so speed does not decide it."

#### Q55. What is ONNX and why use it?
"ONNX is a standard file format for trained models, and onnxruntime is a fast engine that runs it. The server does not need PyTorch, which is huge. A test checks ONNX and PyTorch outputs agree within 1e-4 on 200 validation texts."

#### Q56. Which variants did you try?
"Three, all chosen on validation only: words only 0.8672; words plus hashed letter trigrams with 64 numbers 0.8820, which I kept; the same with 128 numbers 0.8759. The bigger one was worse. The chosen one was run on test once."

#### Q57. What did you learn about PyTorch performance?
"My first training run used the default number of CPU threads and took over 5 minutes on tiny matrices. Setting one thread brought all three variants under a minute. Extra threads add overhead when the work per step is small."

#### Q58. What would make a neural model win here?
"Much more data, or a pre-trained language model fine-tuned on this task, or longer and messier messages where context matters. I would test it through the same retrain gate, against the same frozen test set, and I would need an explanation method that reviewers trust."

### 8.6 SQL (on SANKET's schema)

The tables (see `sanket/db.py`): `tickets(id, created_at, channel, text_redacted, pii_json, n_chars, n_tokens, oov_rate, status)`, `predictions(id, ticket_id, model_version, intent, intent_conf, team, team_conf, urgency, p_high, top_terms_json, decision, reason, latency_ms, created_at)`, `reviews(id, ticket_id UNIQUE, reviewer, action, final_intent, final_team, final_urgency, note, created_at)`, `drift_reports(id, created_at, status, n_tickets, report_json)`.
Every query below was run on a freshly seeded database (2026-11-15).

#### Q59. Write SQL for the override rate per team.
```sql
SELECT p.team,
       AVG(CASE WHEN r.action = 'override' THEN 1.0 ELSE 0.0 END) AS rate,
       COUNT(*) AS n
FROM reviews r
JOIN predictions p ON p.ticket_id = r.ticket_id
GROUP BY p.team
ORDER BY p.team;
```
"This is in `sanket/sql/metrics.sql`. The CASE turns each review into 1 or 0, so the average is the share overridden. A high rate for a team tells me where the model or the rubric is weakest."

#### Q60. Write the review queue: urgent first, then oldest.
```sql
SELECT t.id, t.text_redacted, p.urgency, t.created_at
FROM tickets t
JOIN predictions p ON p.ticket_id = t.id
WHERE t.status = 'needs_review'
ORDER BY CASE p.urgency WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
         t.created_at, t.id
LIMIT 50;
```
"SQLite's query plan uses the index on (status, created_at) to find the rows and the ticket_id index for the join; it sorts the small result in a temporary tree because of the CASE."

#### Q61. Which predicted intents do reviewers correct most, and to what?
```sql
SELECT p.intent AS predicted, r.final_intent AS corrected, COUNT(*) AS n
FROM reviews r
JOIN predictions p ON p.ticket_id = r.ticket_id
WHERE r.action = 'override'
GROUP BY p.intent, r.final_intent
ORDER BY n DESC
LIMIT 5;
```

#### Q62. Compare the confidence of automatic and human-routed tickets.
```sql
SELECT decision, COUNT(*) AS n,
       ROUND(AVG(team_conf), 3) AS avg_team_conf,
       ROUND(MIN(team_conf), 3) AS min_team_conf
FROM predictions
GROUP BY decision;
```
"On the seeded demo database: auto 373 tickets, average 0.975, minimum 0.718; human 27 tickets, average 0.594. The automatic minimum is above 0.70, as the rule says."

#### Q63. Find tickets waiting for review for more than a day.
```sql
SELECT id, created_at
FROM tickets
WHERE status = 'needs_review'
  AND created_at < datetime('now', '-1 day')
ORDER BY created_at;
```
"This is a service-level check. In Postgres I would write `now() - interval '1 day'`."

#### Q64. How many of each kind of personal data were masked?
```sql
SELECT SUM(COALESCE(json_extract(pii_json, '$.CARD'), 0))    AS cards,
       SUM(COALESCE(json_extract(pii_json, '$.EMAIL'), 0))   AS emails,
       SUM(COALESCE(json_extract(pii_json, '$.PHONE'), 0))   AS phones,
       SUM(COALESCE(json_extract(pii_json, '$.ACCOUNT'), 0)) AS accounts
FROM tickets;
```
"Only counts are stored, never the values. On the seeded database: 15 cards, 10 emails, 8 phones, 7 accounts, from the 40 fake PII sentences the seed script adds."

#### Q65. Check that no ticket has two predictions.
```sql
SELECT ticket_id, COUNT(*) AS n
FROM predictions
GROUP BY ticket_id
HAVING COUNT(*) > 1;
```
"WHERE filters rows before grouping; HAVING filters groups after. This returns no rows, which is what I want."

#### Q66. Running total of tickets per day (a window function).
```sql
SELECT day, n, SUM(n) OVER (ORDER BY day) AS running_total
FROM (SELECT date(created_at) AS day, COUNT(*) AS n
      FROM tickets GROUP BY day)
ORDER BY day;
```
"SQLite supports window functions from version 3.25; this machine has 3.53."

#### Q67. Queued tickets with no review yet (LEFT JOIN).
```sql
SELECT t.id
FROM tickets t
LEFT JOIN reviews r ON r.ticket_id = t.id
WHERE t.status = 'needs_review' AND r.id IS NULL;
```
"An inner join would drop tickets without a review; a LEFT JOIN keeps them with NULLs, and `r.id IS NULL` picks exactly those."

#### Q68. Which team sends the largest share of tickets to a person?
```sql
SELECT team,
       SUM(CASE WHEN decision = 'human' THEN 1 ELSE 0 END) AS to_person,
       COUNT(*) AS n,
       ROUND(1.0 * SUM(CASE WHEN decision = 'human' THEN 1 ELSE 0 END) / COUNT(*), 3) AS share
FROM predictions
GROUP BY team
ORDER BY share DESC;
```
"On the seeded database CARD_PAYMENTS is highest at 0.111 (4 of 36). `1.0 *` avoids integer division."

### 8.7 REST and API design

#### Q69. What makes your API RESTful?
"URLs name resources, like `/tickets/{id}` and `/tickets/{id}/review`. HTTP methods are the actions: GET reads, POST creates. Status codes carry meaning: 201 created, 404 not found, 409 already reviewed, 413 too large, 422 bad input. Errors always look like `{"detail": "..."}`."

#### Q70. Which status codes do you use, and when?
"200 for reads and a saved review. 201 when a ticket is created. 404 for an unknown ticket. 409 when a second reviewer tries the same ticket. 413 when the body is over 20 kB. 422 for empty text, over 2,000 characters, no letters, an unknown intent, a bad reviewer name or a reserved channel. 500 should never happen; an audit found one (a broken character) and it became a 422."

#### Q71. Is POST /tickets idempotent?
"No. Sending it twice creates two tickets. GET is idempotent. A review is once-only in effect: the second attempt gets 409. If clients could retry on network errors, I would add an idempotency key header so a retry returns the first result."

#### Q72. Why 422 and not 400?
"FastAPI uses 422 Unprocessable Entity for a request that is well-formed JSON but fails validation. I kept that for all input problems so the client sees one consistent rule."

#### Q73. How do you validate input?
"Twice. Pydantic checks the shape and types; for example urgency must be high, medium or low. Then my own `validate_text` checks the content: not empty, at most 2,000 characters, has letters, can be encoded. A middleware refuses bodies over 20 kB before reading them."

#### Q74. What is CORS and how did you handle it?
"A browser rule: a page from one address may only call an API at another address if that API allows it. The API has an allow-list from `SANKET_CORS_ORIGINS`. On Vercel the page and the API share one address, so CORS is not needed there. An audit checked an unknown origin is refused."

#### Q75. How would you version this API?
"Put the version in the path, like `/api/v1/tickets`, keep old versions working while clients move, and never change the meaning of a field in place. The model version is already returned in every prediction."

#### Q76. Why is there no endpoint to retrain the model?
"Anyone with the link could poison the model with wrong labels or overload the server. Retraining is a command a person runs, and the gate checks the result. That is a deliberate security and governance choice."

### 8.8 Git

#### Q77. How did you use Git?
"Work landed in waves: scaffold, data, model, API, docs, deployment, each with its own commit, and fixes after each audit as separate commits, so the history shows what changed and why. There are 23 commits. CI runs lint and tests on every push. To be precise: the commits were made by the orchestrating agent in my workflow; I practise the commands myself in a branch."

#### Q78. What is the difference between merge and rebase?
"Merge joins two branches with a merge commit and keeps the history as it happened. Rebase replays my commits on top of the other branch, giving a straight line, but it rewrites my commits, so I never rebase a branch others already use."

#### Q79. How do you undo a bad commit that is already pushed?
"`git revert <commit>` makes a new commit that undoes it, which is safe for shared branches. `git reset` rewrites history and is only for local work."

#### Q80. What would your branching look like on a team?
"A protected main branch, short feature branches, a pull request with review and CI green before merging. Model files would be versioned in a registry or Git LFS, not as plain large files."

### 8.9 Python and OOP

#### Q81. What OOP ideas are in SANKET?
"An interface: the `Classifier` protocol says 'anything with `predict_proba(texts)` returning 77 probabilities'. `BaselineModel` and `OnnxModel` both fit it, so the benchmark and evaluation code work with either. Dataclasses for plain records like `Thresholds` and `Decision`. Custom exceptions, `TicketNotFound`, `AlreadyReviewed`, `BadReview`, that the API maps to 404, 409 and 422. In PRAHARI, an abstract `Check` class with ten subclasses, one per governance check."

#### Q82. What is a Protocol, and how is it different from an abstract base class?
"A Protocol describes the methods a class must have, and any class with those methods fits, without inheriting anything: structural typing. An abstract base class requires inheritance and can provide shared code. I used a Protocol in SANKET because the two models share nothing but the method. PRAHARI's `Check` is an abstract base class because the checks share code."

#### Q83. What is a dataclass?
"A class whose main job is to hold data; Python writes `__init__`, `__repr__` and equality for me from the field list. `Decision` has intent, team, urgency, decision, reason and so on."

#### Q84. What is a context manager? Where do you use one?
"An object used with `with` that sets something up and always cleans it up, even on an error. `with sessions() as session, session.begin():` opens a database session and a transaction; it commits at the end or rolls back on an exception."

#### Q85. Why is `decide` a pure function?
"It reads only its inputs and returns a result, with no files, model or database. So I can test every routing rule with a hand-made probability array in milliseconds, and the same function runs in evaluation, the API and the threshold search."

#### Q86. What is a generator, and would you use one here?
"A function that yields values one at a time instead of building a whole list. For scoring millions of tickets from a file, I would read and score them in chunks with a generator so memory stays flat. `similarity.py` already processes rows in chunks of 500."

#### Q87. How do you manage configuration?
"One `Settings` class with pydantic-settings. Every field can be overridden by an environment variable starting with `SANKET_`, for example `SANKET_DB_URL`. Tests set a temporary database that way; Vercel sets `/tmp`."

### 8.10 DSA

#### Q88. What is the time complexity of processing one ticket?
"Roughly linear in the message length. Cleaning and the regular expressions are about O(L) for L characters. TF-IDF looks up each word and letter piece in a hash map, O(L). Scoring is a sparse vector times the weight matrix: O(k × 77) for k non-zero features. Top-5 terms with a heap is O(k log 5). Team sums are O(77). So about O(L + 77k), well under a millisecond."

#### Q89. Write the Luhn check.
```python
def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 2:
        return False
    total = 0
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:          # every second digit from the right
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0
```
"O(n) time, O(n) space for the digit list (O(1) if I walk the string backwards). 4111 1111 1111 1111 passes; change the last digit to 2 and it fails. That is the real code in `pii.py`."

#### Q90. Compute PSI by hand and in code.
"PSI = sum over bins of (actual − expected) × ln(actual / expected). Reference 50/50, live 70/30: 0.2 × ln(1.4) = 0.067, plus (−0.2) × ln(0.6) = 0.102, total 0.17, amber. In code:"
```python
import numpy as np
def psi_from_shares(expected, actual, floor=1e-4):
    e = np.maximum(np.asarray(expected, float), floor)
    a = np.maximum(np.asarray(actual, float), floor)
    return float(np.sum((a - e) * np.log(a / e)))
```
"The floor stops ln(0) when a bin is empty. Binning is O(n log n) for the quantiles, then O(n) to count. `psi_from_shares([0.5, 0.5], [0.7, 0.3])` returns 0.1695."

#### Q91. How do you get the top k terms efficiently?
"With a heap of size k: `heapq.nlargest(k, pairs)`, O(n log k), instead of sorting everything in O(n log n). For k = 5 and a few hundred non-zero terms it barely matters, but on millions of items it does. A quickselect would give O(n) on average if order inside the top k does not matter."

#### Q92. How does the KS statistic work, and what is its complexity?
"Sort both samples. For every value in the merged list, find the share of each sample at or below it with binary search (`np.searchsorted`), and take the biggest gap. Sorting is O(n log n + m log m), the searches O((n + m) log(n + m)). My exact p-value walks a lattice of n × m steps, so I only use it when n × m is at most a million, like SciPy; beyond that I use the asymptotic formula."

#### Q93. Where is hashing used?
"Three places. Python dicts and sets for the vocabulary and the unknown-word check: O(1) average lookups. The network's letter trigrams are hashed with `zlib.crc32` into 8,192 buckets, the hashing trick, so no dictionary of trigrams is needed; collisions just share a vector. And Git and the model-file checks use content hashes."

#### Q94. Whiteboard: given a stream of tickets, keep the 10 most frequent intents.
"Keep a hash map from intent to count: O(1) per ticket. To report the top 10, use `heapq.nlargest(10, counts.items(), key=lambda kv: kv[1])`, O(m log 10) for m intents. With only 77 intents that is trivial. For a huge vocabulary in limited memory I would use a Count-Min sketch or the Misra-Gries algorithm and accept approximate counts."

#### Q95. Whiteboard: find all 13-to-19-digit card candidates in a string.
"Scan once with a regular expression for runs of digits and separators, O(n). For each run, try spans of digit groups and check the length and Luhn on each, which is O(g² × d) for g groups and d digits; g is tiny in practice. That is `_find_card` in `pii.py`. The important part is not speed but avoiding false positives: Luhn, group sizes of 4 to 8, and skipping numbers after 'order' or 'tracking'."

#### Q96. Whiteboard: two reviewers save at once. How do you guarantee one wins?
"Do not check-then-write in Python; let the database decide atomically. `UPDATE tickets SET status='reviewed' WHERE id=? AND status!='reviewed'`, then look at the number of rows changed: 1 means I won, 0 means someone else did, so return 409. A unique constraint on `reviews.ticket_id` is a second lock. An audit ran 5 tickets × 10 reviewers at once: exactly one success per ticket."

### 8.11 DBMS

#### Q97. Is your schema normalised?
"Mostly third normal form: tickets, predictions and reviews are separate tables linked by `ticket_id`, and each fact lives in one place. Two deliberate exceptions: `final_team` in reviews can be derived from `final_intent` through the rubric, but I store it so the log shows what the team was at that time even if the rubric changes later; and `top_terms_json`, `pii_json` and `report_json` are JSON columns for data I only display, never query by parts."

#### Q98. Which indexes do you have, and why?
"A composite index on tickets (status, created_at), because the queue filters by status and sorts by time. An index on predictions(ticket_id) for the join. The unique constraint on reviews(ticket_id) creates its own index. An index makes reads faster but every insert slower and uses space, so I only add ones a real query needs."

#### Q99. What is a transaction? Where do you use them?
"A group of changes that happen together or not at all. ACID: atomic, consistent, isolated, durable. I use one to insert a ticket and its prediction together, so a ticket never exists without its prediction, and one for the review: flip the status and insert the review, or neither."

#### Q100. What is WAL mode in SQLite?
"Write-ahead logging: changes are written to a side file first, so readers can keep reading while one writer writes. It improves concurrency. That side file is also why the privacy audit checked the `-wal` and `-shm` files, not only the table."

#### Q101. SQLite or Postgres for production?
"Postgres. SQLite allows one writer at a time: the audit saw p95 latency rise to 720 ms at 32 parallel clients, with zero errors, which shows where it starts to strain. Postgres handles many writers, has row-level locking, replication, roles and backups. SQLite was right for a free demo that needs no server."

#### Q102. Why do foreign keys need a PRAGMA in SQLite?
"SQLite does not enforce foreign keys unless you turn them on per connection. `db.py` runs `PRAGMA foreign_keys=ON` for every new connection, and a test checks that a review for a missing ticket is refused."

### 8.12 Deployment and MLOps

#### Q103. How is SANKET deployed?
"One free Vercel project. The React page is built as static files, and the FastAPI app runs as a Python serverless function from `api/index.py`, on the same address, so no CORS is needed. `vercel.json` sets the build and sends `/api/*` to the function. Each cold start makes a fresh SQLite database in `/tmp` and seeds 250 tickets. The server installs only `requirements.txt`, so no PyTorch and no onnxruntime: the network is off there and the linear model serves every ticket."

#### Q104. What are the limits of that deployment?
"It is stateless: reviews made on one instance may not appear on another, and they vanish when the instance is recycled. A cold start takes a few seconds. So the live review queue is a demonstration, and Replay mode is the reliable showcase. It is not on-prem and not on a big cloud. The Dockerfile exists but was never built, because the build sandbox had no Docker daemon."

#### Q105. How would you deploy it for a real bank?
"As a container on the bank's own cloud or on-prem Kubernetes, because banking data usually cannot leave approved infrastructure: a few API replicas behind a load balancer, Postgres with backups, a queue in front of the model for bursts, secrets in a vault, logs without raw text, and the model files in a registry. Promotion would go through the same gate plus a human sign-off."

#### Q106. What is MLOps, in your own words?
"Treating models like software that keeps running: versioned data and models, reproducible training, automated tests and quality gates, safe deployment, monitoring in production, and a controlled way to retrain and roll back. SANKET has small versions of each: splits that rebuild byte-identically, a registry, model cards, CI gates, drift monitoring and a promote gate."

#### Q107. What is a model registry? What does yours hold?
"A record of every model version and its status. Mine is `artifacts/registry.json`: the current champion, and a history of every attempt, promoted or rejected, with its test macro-F1, high-urgency recall and the reasons. The API loads whatever the registry names as champion at start-up."

#### Q108. How do you roll back a bad model?
"Point the registry's champion back to the previous version and restart the API; the old model folder is still there. In production I would keep the last few versions deployed-ready and make rollback one command."

#### Q109. What is train/serve skew, and how did you avoid it?
"When text is prepared differently in production than in training, so the model sees inputs it never learned from. SANKET uses one `clean()` function for both: the splits were built with it, and every live ticket goes through it. A data check even fails if a training row is not equal to `clean(row)`."

#### Q110. What is in a model card?
"What the model is, what data and parameters, thresholds and the temperature, metrics on validation and test, stress results, calibration before and after, the threshold choice tables, the file size, the code version, and its limits in plain sentences, such as 'English only' with the Hinglish numbers. Mine is `artifacts/models/v1/card.json`."

### 8.13 Drift and monitoring

#### Q111. What is drift?
"The data arriving now stops looking like the data the model was tuned on. Then the model can be wrong without knowing it. Drift is a reason to look, not proof that the model is wrong."

#### Q112. Data drift versus concept drift?
"Data drift: the inputs change, for example more Hinglish. Concept drift: the right answer for the same input changes, for example a new product makes 'card' mean something else. Data drift is visible immediately; concept drift needs labels, so the override rate is my best early signal for it."

#### Q113. What exactly do you monitor?
"The latest 500 tickets against the validation set, on four signals: message length, share of unknown words, and team confidence, each with a KS test, and the mix of predicted teams with PSI. The overall status is the worst of the four. Under 200 tickets it says 'insufficient data'. Plus the override rate by team and latency by model version from SQL."

#### Q114. What happens in the Hinglish surge demo?
"It pushes up to 300 hinglishified stream messages through the real pipeline and re-runs drift. The unknown-word signal jumps: KS D 0.58, red; team confidence D 0.15, amber. Reset removes those tickets. The hinglishified text is synthetic and used only for this demo."

#### Q115. Why does a KS test need 200 tickets?
"With few points, big gaps happen by chance. Five plus five lengths can give D = 0.8 with p = 0.079, so it would not even count as significant. Under 200 live tickets the report refuses to guess."

#### Q116. When would you retrain?
"When drift stays red, when the override rate rises, or on a schedule once at least 50 new reviewed tickets exist. Always through the gate, and with a fresh labelled sample for testing now and then, because reusing one test set for every decision slowly overfits to it."

### 8.14 Responsible AI and privacy

#### Q117. What responsible-AI practices are in SANKET?
"Personal data is masked before anything is stored, including reviewer notes. A person decides uncertain cases. Every override is logged with who and when. Urgency errs towards safety. A gate stops worse or poisoned models. The model card states the limits. Failures, like Hinglish and typos, are measured and published. And there is no endpoint that changes the model."

#### Q118. What does India's DPDP Act mean for a system like this?
"The Digital Personal Data Protection Act, 2023 governs digital personal data in India. In plain words: collect personal data only for a clear, lawful purpose, usually with notice and consent; keep only what you need; keep it accurate; protect it with reasonable security; delete it when the purpose is served; report breaches to the Data Protection Board and to the people affected; and let people access, correct and erase their data. A bank is the 'data fiduciary' and the customer the 'data principal'. SANKET's design fits the spirit: data minimisation by masking before storage, only counts of PII kept, no raw text in logs. But I have not done a formal compliance review: retention periods, consent records and breach procedures need a legal and privacy team." **(check this: read the Act's summary on an official government site, and check the current status of the DPDP Rules, before quoting details or penalty amounts.)**

#### Q119. What personal data could still leak?
"Anything without a pattern: names, addresses, passport numbers, and a phone written right after 'paid', which is treated as an amount on purpose. There are also over-masking cases: 'refund at amazon dot in' becomes [EMAIL]. In production I would combine patterns with a reviewed named-entity recogniser, and have a privacy team review the patterns."

#### Q120. Why patterns and not a machine-learning PII detector?
"Cards, phones, Aadhaar, PAN and UPI ids have regular shapes, and checksums like Luhn and Verhoeff cut false positives. A pattern can be read and tested line by line, which matters for privacy. A learned detector is heavier and harder to verify. Its weakness is names and addresses, which is why I would add one later, not instead."

#### Q121. Why keep a human in the loop?
"The model is wrong about 1 in 10 intents. Sending only the unsure tickets to a person keeps the workload small, 5.8% on test, while the automatic ones are 99.2% right on team. People also catch what the model cannot know, like a new kind of fraud. And their corrections are the training data."

#### Q122. Could the model be biased against some customers?
"The data has no customer attributes like age or gender, so I cannot measure group fairness directly. What I can measure is language: Hinglish does worse, intent accuracy 0.65. The design response is to send unfamiliar text to a person rather than guess, and to report the gap. In a real bank I would check performance by language, region and channel, and watch the override rate per group."

#### Q123. How is the model explainable?
"The explanation is exact for a linear model: each term's contribution is its weight times its TF-IDF value, and the contributions plus an intercept add up to the score. The dashboard shows the top five terms, the top five intents, the team sums and the rule in words, such as 'Sent to a person: team confidence 0.69 is below 0.70'."

#### Q124. What is the risk of the review data itself?
"It is a biased sample: people only see tickets the model was unsure about. So the override rate says little about the automatic tickets, and retraining on reviews over-represents hard cases. That is also why the first label-sanity rule failed: honest reviewers disagree with the model 56% of the time on those tickets."

### 8.15 Security

#### Q125. What security measures does the API have?
"Input limits: 20 kB body, 2,000 characters, only the `web` channel from clients. Validation before any work. PII masked before storage. A CORS allow-list. SQLAlchemy uses parameterised queries, so ticket text cannot become SQL. Only `model.joblib` from our own artifacts folder is ever unpickled, never anything from a user. No train, promote, PUT, PATCH or DELETE routes. The dashboard renders ticket text as text, so a `<script>` in a ticket never runs; a browser test checks that."

#### Q126. What is missing for production security?
"Authentication and roles for reviewers, rate limiting, a streaming body limit (chunked requests skip the 20 kB header check, though text is still limited to 2,000 characters), audit-log retention, secrets management, and a security review. Right now anyone with the link can review in the demo."

#### Q127. What is SQL injection, and why are you safe from it?
"Sneaking SQL commands into input that gets pasted into a query. SANKET never builds SQL from user text; SQLAlchemy sends values as parameters. The system audit stored SQL text in a ticket and it stayed inert. In PRAHARI, where an agent can run SQL, a guard allows only single SELECT statements on allowed tables; 19 injection probes were rejected."

#### Q128. Why is unpickling dangerous?
"A pickle file can run code when it is loaded. So the server loads `model.joblib` only from its own `artifacts/` folder, which comes from the repository, and never accepts a model file from a request. PyTorch weights in the benchmark are loaded with `weights_only=True`."

### 8.16 Scaling to millions of tickets

#### Q129. How would you scale this to millions of tickets a day?
"One million a day is about 12 per second on average, maybe ten times that at peak. The model is not the problem: in batches of 64 the baseline does about 13,400 tickets per second on one thread. The bottlenecks are the database and the single process. I would put a queue such as Kafka or RabbitMQ between intake and scoring, run several stateless scoring workers that batch predictions, move to Postgres with partitioning by date, keep the API behind a load balancer with rate limits, and archive old tickets. Monitoring and retraining stay offline jobs."

#### Q130. What breaks first today?
"SQLite with one writer. The audit measured POST /tickets at 1 client p50 8.6 ms; at 32 parallel clients p50 164 ms and p95 720 ms, still with zero errors in 1,400 requests. That shows where it starts to strain."

#### Q131. How would you make inference faster if you had to?
"Batch requests, cache repeated texts, use the ONNX network for a first pass if its accuracy were good enough, or prune features. But first measure: the model is about 1 ms of the 10 ms request; the rest is the database write and the web framework, so those would be the first targets."

#### Q132. How many reviewers would a bank need?
"Rough estimate: at one million tickets a month and 5.8% sent to a person, that is 58,000 reviews. At one minute each, about 970 hours, or about six full-time reviewers at 160 hours a month. Raising the team cut-off to 0.8 would send 7.8% to people but cut mistakes. The coverage table lets the business choose."

### 8.17 What would you do differently

#### Q133. What would you improve first?
"Real or Hinglish training data; masking for names and addresses; a second labelled test sample so the gate does not wear out one test set; login and roles for reviewers; Postgres; and fitting the temperature on half of validation so it does not share data with the thresholds."

#### Q134. What would you do differently from the start?
"Write the load test as a committed script, not a one-off. Build the Docker image on a machine that has Docker. Keep a small labelled sample from the demo stream for monitoring accuracy, not only drift. And plan the deployment target earlier: the Vercel limits shaped the end of the project."

#### Q135. What was the hardest bug?
"The retrain gate. The obvious fix, reject if the model disagrees a lot with the new labels, blocked honest reviewers, because people only review hard tickets. What worked was asking whether the new label is in the model's top 5 guesses. It took measuring both honest and poisoned batches to find a rule that separates them."

### 8.18 Behavioural questions (STAR)

STAR means **Situation, Task, Action, Result**. Every story below uses only real project events. Where the question needs your own life, use the placeholder.

#### Q136. Tell me about a time an experiment failed.
- **Situation.** I built a PyTorch network as a challenger to the simple model.
- **Task.** Decide honestly which one serves.
- **Action.** Before training, I wrote the rule: if it loses, report it and do not tune until it wins. I trained three variants, chose on validation only, ran test once, and had an independent audit check fairness.
- **Result.** It lost by 1.4 macro-F1 points, though it was 15 times faster. I kept the linear model, reported both, and the network became a second opinion. I learned that a fair, pre-registered comparison is worth more than a fancier model.

#### Q137. Tell me about a time you found a mistake in your own work.
- **Situation.** My first benchmark said the network was 125 times faster.
- **Task.** Make sure the number was real before putting it in the README.
- **Action.** The model audit profiled the baseline and found it rebuilt a 77 × 20,672 matrix on every prediction. I moved it to the constructor and checked the probabilities were identical.
- **Result.** Baseline p50 went from 7.69 ms to 0.82 ms; the real gap is about 15 times. A test now guards it. Lesson: be most suspicious of results that flatter what you hoped.

#### Q138. Tell me about a disagreement and how you resolved it.
- **Situation.** The auditor said my retrain gate let poisoned labels in. The first fix rejected batches the model disagreed with; the auditor then showed it also rejected honest reviews.
- **Task.** Find a rule both sides could accept.
- **Action.** Instead of arguing, we measured: honest batches shaped like the real review queue, 30% noise, and all wrong, over three seeds.
- **Result.** The top-5 rule separated them (0.86 to 0.97 honest, 0.58 to 0.72 noisy, limit 0.75). Lesson: settle disagreements with data. **[your own example with people, if you have one]**

#### Q139. Tell me about working under a time limit.
- **Situation.** The plan allowed one fix round after each audit.
- **Task.** Fix what mattered without endless polishing.
- **Action.** HIGH and MEDIUM findings were fixed with a test each; LOW findings were fixed only if cheap, otherwise added to the limitations list in the README and data card.
- **Result.** All HIGH and MEDIUM items in the system audit were re-checked as PASS; the remaining LOW items are documented, not hidden.

#### Q140. Tell me about learning something new quickly.
- **Situation.** I had to put SANKET online for free with the API and the page on one address.
- **Task.** Make a FastAPI app run as a Vercel serverless function.
- **Action.** I learned how Vercel functions work: stateless, read-only files, a size limit. I moved the database to `/tmp`, seeded it at cold start, kept only serving dependencies, and made the app start even without onnxruntime.
- **Result.** It is live; `/api/health` answers with 250 seeded tickets; the network gracefully reports "not available in this deployment".

#### Q141. Tell me about a time you worked in a team.
"[your own example: a real college, hackathon or internship team. Use STAR. Do not use the AI agents as a substitute for people.]" If you have none, say: "My closest experience is coordinating builder and auditor agents through written contracts and handoff notes, which taught me to define interfaces clearly. I would like more experience with human teams."

#### Q142. Tell me about a time you showed leadership or ownership.
"[your own example.] On SANKET, ownership meant setting the rules before the results: frozen test set, written threshold rules, the 'report the network even if it loses' rule, and refusing to publish a number without a source."

### 8.19 Tricky traps

#### Q143. Is this real data?
"The texts are real: Banking77 is a public set of real customer-service questions to a bank. But it contains no real personal data, the messages are short English questions, and the team and urgency labels are my own rubric. PRAHARI's data is fully synthetic, from my simulator. I say that first, every time."

#### Q144. Did you write this code?
"I built it with AI coding agents working under my direction: I chose the problem and the scope, set the rules and contracts, and reviewed the results; agents wrote most of the code and separate agents audited it. I do not claim I typed every line. I do claim I understand every part and can change it. Pick any file and I will walk you through it, or ask me to make a change now. For example, I did [your own example: an exercise from section 11.2]."

#### Q145. Why is the PyTorch model worse? Isn't deep learning better?
"Not on small, short text. About 90 examples per intent is little data for learning embeddings from scratch, and averaging word vectors loses word order. TF-IDF with letter groups is a strong, well-known baseline for this. The gap is real, with a bootstrap interval of +0.004 to +0.024. Deep learning would likely win with much more data or a pre-trained model."

#### Q146. The client says it must be 100% accurate. What do you say?
"No model is 100% accurate, and I would not promise it. What I can promise is control: the system can be tuned so that what it routes automatically is very accurate, and everything else goes to a person. On test, at cut-off 0.9 it routes 87.3% automatically at 0.999 team accuracy; at 0.7 it routes 94.4% at 0.992. The client chooses the trade-off between automation and reviewer workload, and every decision is logged and explainable."

#### Q147. 11% of your test set has near-duplicates in training. Isn't your score inflated?
"Possibly a little, and I say so. The test set is the official one, so I could not change it; I removed 68 near copies from training and documented the 351 that remain. On a narrower set of 89 almost-identical rows, an audit found that dropping them moved test macro-F1 only from 0.876 to 0.873, but I would not claim that for all 351."

#### Q148. Team accuracy 0.971 sounds excellent.
"It measures agreement with my own table, not with real bank agents. The intent accuracy, 0.900, is the number against real labels. In a bank, the table would come from operations."

#### Q149. Your Hinglish test had zero silent wrong-team errors, so it is safe?
"Only 60 messages, and only about 34 were routed without a person. Zero errors out of about 34 still allows a true error rate up to about 9% at 95% confidence. So it is encouraging, not proof. The fix is Hinglish training data."

#### Q150. You use the test set in the retrain gate. Isn't that tuning on test?
"The gate only compares models, it does not fit anything on test, so one decision is fine. But over many retrain rounds, choosing the model that does best on the same test set slowly overfits to it. That is a listed limitation; production needs a fresh labelled sample each period."

#### Q151. Why not just call ChatGPT or another LLM?
"For this job I need low cost per ticket, low latency, the same answer every time, exact explanations, and no customer text leaving the bank. A 5 MB linear model does that at under 1 ms. An LLM could help with long, messy complaints or summarising for the reviewer, behind the same masking and human review. I would test it through the same gate."

#### Q152. If the model is calibrated, why do you still need people?
"Calibration means the confidence is honest, not that the answer is right. A ticket at 60% confidence is still wrong 40% of the time. Honest confidence is exactly what lets me decide which tickets need a person."

### 8.20 Curveballs

#### Q153. Explain SANKET to a 10-year-old.
"It is like a helper in a bank's post room. It covers private numbers with a black marker, reads each letter, puts it in the right desk's tray, and when it is not sure it gives the letter to a grown-up. It also notices when the letters start to look different from before."

#### Q154. How would you add a new intent, say 'UPI payment failed'?
"Add it to `taxonomy.yaml` with a team and an urgency. Collect labelled examples: at least 20 for the training floor, ideally around 90 like the others. Retrain with `make train` or through reviews and `make retrain`, check it passes the gate, and watch its override rate after release. The quality check would fail if the class had too few rows, which is the point."

#### Q155. The bank wants Hindi and Tamil. What changes?
"The masking already handles Devanagari digits, but the model only knows English. I would need labelled data in each language, probably a multilingual pre-trained model or one model per language, a language detector at intake, stress sets per language, and drift and override rates per language. Until then, unfamiliar text keeps going to a person."

#### Q156. A manager sees a wrong automatic routing and wants the system switched off. What do you do?
"First, look at the ticket: the trace shows the top words, the team sums and the rule that fired. Then put it in context: on test, about 0.8% of automatic tickets go to the wrong team. If this is a new pattern, I can raise the team cut-off immediately, which sends more to people, without retraining. And the correction becomes training data. Switching it off loses the 94% that work."

#### Q157. How would SANKET's ideas apply to telecom support at Tech Mahindra's clients?
"The pipeline is the same shape: mask personal data, classify the ticket, route by a rubric operations owns, send uncertain ones to a person, monitor drift, retrain through a gate. PRAHARI is the network side: alarms instead of messages. I would not assume anything about Tech Mahindra's internal systems; I would ask how their teams handle labels and approvals." (See section 9.)

#### Q158. What is one thing you would not trust in your own project?
"The team and urgency numbers, because they compare with my own table. And any PRAHARI accuracy number as a real-network number, because the data is synthetic."

#### Q159. What did you learn that a course would not teach?
"That most of the work is around the model: data checks, privacy edge cases like a card number split by tabs, honest benchmarks, and deployment limits. And that independent review finds things you cannot find in your own work."

#### Q160. If you had one more week, what would you do?
"Write a committed load-test script, add name and address masking with a reviewed recogniser, collect a small Hinglish training set and measure the change through the gate, and add login for reviewers."

---

## 9. The Tech Mahindra angle

### 9.1 What you can say safely

**From the job description itself** (the PDF you were given, read for this handbook): Tech Mahindra describes itself as a provider of digital transformation, consulting and business re-engineering services, present in over 90 countries, with 1,100+ global customers including Fortune 500 companies, part of the Mahindra Group, with the promise to help customers "scale at speed". The role is PAN India, works with internal business units on client projects, and lists: AI solution development, model integration and deployment (cloud or on-prem), monitoring and drift, data and pipeline support, testing and optimisation, collaboration and documentation. The "AI-ready mindset" asks for curiosity, structured problem solving, ownership, integrity, attention to data privacy and responsible AI, clear communication, and "resilience when experiments fail and the discipline to learn from evidence". That last line is your PyTorch story.

**Why triage and network operations match enterprise AI work (in your words):**

- Enterprises do not need a model; they need a model inside a process, with checks, people and logs. Both projects are exactly that shape.
- Ticket triage is the first step of any service desk or contact centre: classify, route, escalate. SANKET is a small, honest version of that step for banking.
- Network operations for telecom operators is alarm filtering, root-cause analysis and governed fixes. PRAHARI is a small, synthetic version of that.
- Both put a person in the loop and a gate before change, which is what regulated clients (banks, telecoms) ask for.

**Never say** "Tech Mahindra uses X internally" or "your platform does Y" unless a public page says it and you read it yourself.

### 9.2 Links to read the night before

The build machine could not open any Tech Mahindra or news page (its network refused the connection, checked again on 2026-11-15). So **every claim in the "what to check" column is a check this**: it is what the project plans expected the page to say, not something verified. Open each link yourself. Use a link only if it loads. Quote only what the page actually says. Write one sentence per page in your own words.

| # | Link | What to check (check this) | Source of the link |
|---|---|---|---|
| 1 | <https://insights.techmahindra.com/assets/next-generation-service-desk-solution-for-smarter-support.pdf> | Does it describe an AI-assisted service desk? Ticket classification or routing? | SANKET `docs/plan/PLAN.md` |
| 2 | <https://techmahindra.com/node/2617> | What the page is (the plan expected "agentAssistX", IT support automation from ticket creation to resolution) | SANKET plan |
| 3 | <https://insights.techmahindra.com/assets/nps-boost-with-ai-enabled-contact-center-operations.pdf> | Who the client is; whether complaint handling for a bank is described | SANKET plan |
| 4 | <https://insights.techmahindra.com/assets/redefining-intelligent-banking-with-agentic-ai.pdf> | What it says about AI in banking and about human oversight | SANKET plan |
| 5 | <https://www.techmahindra.com/insights/press-releases/tech-mahindra-unveils-techm-orion/> | TechM Orion: the plan says an agentic AI platform (July 2025), 200+ agents, 30+ configurable governance checks per agent, cloud/on-prem/hybrid | both plans |
| 6 | <https://www.techmahindra.com/services/artificial-intelligence/verifai/> | VerifAI: the plan says validation of AI from discovery to production (data quality, model testing, hallucination detection, monitoring) | both plans |
| 7 | <https://www.techmahindra.com/insights/press-releases/tech-mahindra-launches-project-indus-large-language-model-llm/> | Project Indus: the plan says a Makers Lab Indic LLM, Hindi and 37 dialects | both plans |
| 8 | <https://india.entrepreneur.com/technology/tech-mahindra-increases-ai-investment-in-fy26-working-on/498829> | Context only: AI investment news for FY26 | both plans |
| 9 | <https://www.techmahindra.com/insights/press-releases/techm-advances-ai-driven-autonomous-network-operations-csps/> | The plan says (March 2026, with NVIDIA) reasoning agents for telecom operators covering alarm validation, root-cause analysis and resolution, human in the loop | PRAHARI `docs/plan/PLAN.md` §9 |
| 10 | <https://www.techmahindra.com/insights/press-releases/techm-collaborates-with-microsoft-to-launch-ontology-driven-agentic-ai-platform/> | The plan says (March 2026, with Microsoft) an ontology-driven agentic AI platform for telecom | PRAHARI plan §9 |
| 11 | <https://www.techmahindra.com/insights/events/tech-mahindra-platinum-sponsor-tm-forum-dtw-ignite-2026/> | The plan says "GNN-Healing Networks" was showcased at TM Forum DTW Ignite 2026 | PRAHARI plan §9 |
| - | "AI Delivered Right" | The PRAHARI plan mentions this strategy (April 2025) but gives **no link**. Find the official page before quoting it, or do not quote it. | PRAHARI plan §1 |

### 9.3 How to connect each page to your work (only if the page says it)

- Service-desk paper or agentAssistX describe AI ticket handling → "Triage is the first step of a service desk; SANKET is a small, honest version of that step."
- Contact-centre case study is about a bank → "Banking support messages are the data I used."
- Orion or the agentic-banking paper talk about guardrails or human oversight → "SANKET has a human in the loop, a promote gate and an override log; PRAHARI has 10 configurable governance checks. Those ideas in miniature."
- VerifAI is about validating AI → "My three audits, quality gates in CI and model cards are the same idea at project scale."
- Project Indus covers Indian languages → "My Hinglish stress test shows why that matters: my English model sends 26 of 60 Hinglish tickets to a person."
- The NVIDIA network-operations release talks about alarm validation and root cause → "PRAHARI mirrors those three stages on synthetic data. I would say 'mirrors', never 'matches your system'."

### 9.4 Ten smart questions to ask the interviewer

1. "In your service-desk or support projects, how do teams decide when a model's answer goes straight through and when a person reviews it?"
2. "How do you get reliable labels for training in client projects: from historical tickets, from agents' corrections, or from expert review?"
3. "How do you handle Indian-language and code-mixed text, like Hinglish, in client projects?"
4. "What does monitoring look like after an AI model goes live for a client, and who acts on a drift alert?"
5. "How do your teams test and validate AI components before release? Is there a standard quality gate?"
6. "When a client needs on-prem deployment, how does the delivery of an AI component change compared with cloud?"
7. "How do teams handle personal data and the DPDP Act in AI projects, for example masking or data residency?"
8. "For a new AI engineer in Digital Catalyst, what does the first three months of work usually look like?"
9. "How does an AI engineer here split time between building models and making them production-ready?"
10. "What is one thing that new AI engineers usually find harder than they expected on client projects?"

---

## 10. What to say to impress (honestly)

### 10.1 Talking points that are true and specific

- **Ownership.** "I set the rules before the results: a frozen test set, written threshold rules, and 'report the network even if it loses'. I can explain every file and change it."
- **Evidence-based decisions.** "My PyTorch model was 15 times faster but 1.4 points less accurate, with a bootstrap interval that excludes zero. Speed was not the bottleneck, explanations matter to reviewers, so the linear model ships. I report both."
- **Safety and privacy thinking.** "Personal data is masked before anything is stored, including the reviewer's own note, which an audit found leaking and I fixed. Urgency is tuned for recall because a missed fraud report costs more than an extra look."
- **Audit discipline.** "Three independent audits wrote failing tests for every finding. A fix only counted when the test flipped. That is how I found a benchmark that was wrong by a factor of eight."
- **Communication.** "Every number in my README has a source file. The model card says the limits in plain sentences, like 'English only' with the Hinglish numbers."
- **Learning speed.** "I got a FastAPI app running as a Vercel serverless function, with a fresh database at each cold start and a graceful fallback when onnxruntime is missing."
- **Systems view.** "Most of the work was around the model: data checks, the API, the review race condition, drift, the retrain gate."

### 10.2 Phrases to use

- "On the 3,080-row official test set..." (always say which data a number is from)
- "That number measures agreement with my rubric, not with real agents."
- "n = 60, so it is encouraging, not proof."
- "I decided the rule before I saw the result."
- "An independent audit found... the fix was... the test is..."
- "I don't know that yet. Here is how I would find out."
- "Mirrors" (for PRAHARI vs Tech Mahindra's public work), never "matches".
- "AI-assisted build; I own the design and can change any part."

### 10.3 Phrases to avoid

- "It's 97% accurate" without saying what (team accuracy against your own rubric).
- "Production-ready" or "enterprise-grade". Say "a demo with production habits".
- "I wrote every line" or, the opposite, "the AI did it". Both are untrue.
- "Real data" for PRAHARI. It is synthetic.
- "Deep learning is always better" or "simple is always better". Say "on this data".
- "Tech Mahindra uses..." unless you read it on a public page.
- Unexplained jargon. If you say "PSI", say what it measures in the same sentence.

### 10.4 When you do not know the answer

1. Say so plainly: "I don't know."
2. Say what you do know that is close: "I know X, which is related because..."
3. Say how you would find out: "I would check the docs for Y, or test it with a small experiment."
4. If it is a concept question, reason out loud from first principles; interviewers value the reasoning.
5. Never invent a number. "I don't have that number with me; it is in the model card" is a good answer.

### 10.5 The 4-minute live demo, with fallbacks

**Before the interview.** Open <https://sanket-omega.vercel.app> 10 minutes early to wake the function. Check the badge says **Live**. Have a terminal ready with the local setup in case the network fails. Keep `docs/screens/live.png` and `docs/screens/replay.png` open in a tab as the last fallback.

| Time | Do | Say |
|---|---|---|
| 0:00 | Open the page; point at the seven cards | "A message goes left to right through seven steps. Each card is one small file, and the Code tab shows the real function." |
| 0:20 | Click chip **Urgent fraud** | "It predicted card_payment_not_recognised at 79%. The six fraud intents add up to 97%, so the team is clear, and it is marked urgent. A few milliseconds." |
| 0:50 | Click the **Explain** card, tab **Live example** | "These words pushed the decision: 'payment', 'make', 'this payment', 'did not', 'someone'. Each number is weight times TF-IDF value, so it is exact." |
| 1:15 | Chip **Fake PII**, open **Clean** | "The card number and email became [CARD] and [EMAIL] before anything was stored. The card check uses the Luhn checksum." |
| 1:40 | Chip **Ambiguous** ("I tried to pay and it did not work") | "Team confidence is 0.69, just under 0.70, so it goes to a person." |
| 1:55 | Review queue → **Review** → Override → pick an intent → save | "My correction is logged with who and when and becomes training data. A second save would get 409." |
| 2:20 | Chip **Hinglish** | "Trained on English, so it is weak here. Many words are unknown, so it asks a person. On 60 Hinglish messages, 26 went to a person, none silently to the wrong team." |
| 2:45 | Monitor → **Simulate Hinglish surge** | "PSI and KS compare live tickets with validation tickets. The unknown-word signal jumps to red. Red means look before trusting the model." Then click **Reset**. |
| 3:15 | Model panel: LR vs NN table and registry | "I built a PyTorch model; it is about 15 times faster but 1.4 points less accurate, so the simple model serves. On this free deployment the network is switched off to fit the size limit; the numbers you see are the recorded benchmark. Retraining is gated: in the audit a poisoned retrain was rejected and an honest one promoted." |
| 3:40 | Open any card's **Code** tab | "And this is the real code behind the card, read from the running function." |

**Fallback 1: the badge says Replay.** Say: "The free server is asleep; these are recorded real answers from the same API." Carry on with the chips; they all work. Review works in this tab only; free text is off.

**Fallback 2: no network at all.** Locally: `make serve` in one terminal, `VITE_API_URL=http://localhost:8000 make web` in another, open <http://localhost:5173>. Locally the network second opinion is on, if onnxruntime is installed.

**Fallback 3: nothing runs.** Show the two screenshots in `docs/screens/` and walk through `sanket/routing/decide.py` and `sanket/pipeline/pii.py: luhn_ok` in the editor. Code you can explain beats a demo you cannot.

**Note.** The committed registry has only v1. If asked to show a rejected candidate, run exercise 10 (section 11.2) or quote the audit: 30% poisoned labels rejected at 57% top-5 coverage.

**PRAHARI demo (only if asked, 1 minute).** Open <https://prahari-red.vercel.app>. Say first: "This is a recorded replay of a real local run, on synthetic data." Show the alarm storm with noise greyed and the root ringed, the 10 governance checks, the Hindi narrative, then the drift view turning red and the new action blocked.

---

## 11. Study plan, exercises and glossary

### 11.1 Five-day study plan (about 2 to 3 hours a day)

**Day 1: the story and the data.**
Read `docs/EXPLAIN_LIKE_IM_5.md` (15 min). Say the 30-second pitch out loud five times and the 2-minute pitch twice (20 min). Read sections 1 to 3 of this handbook (45 min). Open `sanket/pipeline/pii.py` and do the Luhn example by hand (exercise 6, 20 min). Run `make setup data train seed serve`, then the dashboard, and click every chip (40 min).

**Day 2: the model and the routing.**
Read sections 4 and 5.1 to 5.4 with the files open (45 min). Read `docs/INTERVIEW_GUIDE.md` section 4 (worked examples: TF-IDF, softmax, cross-entropy, calibration) with paper (45 min). Do exercises 2, 3 and 8 (45 min). Answer questions Q30 to Q58 aloud.

**Day 3: review, monitor, retrain, API, databases.**
Read sections 5.5 to 5.8 (30 min). Read `review.py`, `drift.py: psi, ks_2samp` and `retrain.py: gate, label_sanity_problems` (40 min). Do exercises 5, 7, 9 and 10 (60 min). Answer Q59 to Q102 aloud, writing each SQL query yourself before reading it.

**Day 4: testing, JD, honesty, PRAHARI.**
Read sections 6 and 7 (40 min). Practise the 5 weaknesses and section 10 out loud (20 min). Read PRAHARI's `docs/EXPLAIN_LIKE_IM_5.md` and section 2.2 here (30 min). Answer Q103 to Q160 aloud; mark the ones you stumble on and re-read those parts (60 min). Do exercise 1 or 4.

**Day 5: company, demo, mock interview.**
The night before or this morning: open every link in section 9.2 and write one sentence per page (40 min). Rehearse the demo with a timer three times, once in Replay mode (30 min). Fill every **[your own example]** placeholder you will use (20 min). Timed mock: someone picks 10 random questions plus "walk me through your project"; record yourself and listen back (40 min).

### 11.2 Ten hands-on exercises with expected results

Do these on your laptop in a Git branch (`git checkout -b practice`). Undo with `git checkout .` afterwards. Commands assume the project folder and `.venv`. Expected results were measured on the build machine unless marked otherwise.

#### Exercise 1: add a [PASSPORT] redaction with a test
Read how `[PAN]` is done in `sanket/pipeline/pii.py` (`PAN_RE` and its line in `redact`). Indian passport numbers look like `K1234567`: one letter, then 7 digits, the first not 0.
1. Add `PASSPORT_RE = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z][1-9]\d{6}(?![A-Za-z0-9])")`.
2. In `redact`, add `"PASSPORT": 0` to `counts` and `text = PASSPORT_RE.sub(lambda m: _count(counts, "PASSPORT"), text)`.
3. Trap: `clean` lower-cases everything except known placeholders. Add `PASSPORT` to `_PLACEHOLDER` in `clean.py` and to `PLACEHOLDER` in `service.py`.
4. Add a test in `tests/unit/test_pii.py`.

**Expected.** Today, `clean("My passport is K1234567").text` is `my passport is k1234567` (checked 2026-11-15). After your change: `my passport is [PASSPORT]` with `pii == {"PASSPORT": 1}`, and `make test` still passes (D1 checked that no split or probe row contains a passport-shaped string).

#### Exercise 2: move two intents to another team, no retraining
The data audit suggested `apple_pay_or_google_pay` and `supported_cards_and_currencies` belong in TRANSFERS_TOPUPS. Move both in `sanket/taxonomy.yaml`, then run:
```bash
.venv/bin/python -c "
from pathlib import Path; from sanket.models.baseline import BaselineModel
from sanket.models.evaluate import load_split; from sanket.routing.thresholds import team_matrix
from sanket.taxonomy import TEAM_NAMES, team_of; import numpy as np
m = BaselineModel.load(Path('artifacts/models/v1'))
for s in ['val', 'test']:
    d = load_split(s); tm = team_matrix(m.predict_proba(d.text.tolist()))
    pred = np.array(TEAM_NAMES)[tm.argmax(1)]; true = np.array([team_of(i) for i in d.intent])
    print(s, round((pred == true).mean(), 4))"
```
**Expected (D1 handoff).** Before: val 0.9691, test 0.9705. After: val 0.9691, test 0.9714. A reorganisation is a table edit, not a retrain.

#### Exercise 3: read the coverage table and change tau_team
Open `artifacts/models/v1/card.json`, find `metrics.test.coverage_table`. Then set `tau_team` to 0.8 in `artifacts/models/v1/thresholds.json`, restart `make serve`, and submit "I tried to pay and it did not work".
**Expected.** Table: at 0.7, 94.4% automatic at 0.992 team accuracy; at 0.8, 92.2% at 0.995. The ambiguous message (team confidence about 0.69) still goes to a person. Explain why validation chose 0.70: the smallest step where automatic validation tickets reached 0.985 (0.9852). Put 0.7 back afterwards.

#### Exercise 4: add a fifth drift indicator (message length in characters)
1. `train_baseline.py: reference_from_val`: add `"n_chars": [len(t) for t in val["text"]]`.
2. `api/queries.py: live_inputs`: also select `Ticket.n_chars` and return it.
3. `drift.py: drift_report`: loop over `("n_tokens", "oov_rate", "team_conf", "n_chars")`, skipping a key missing from `reference`.
4. A unit test in `tests/unit/test_drift.py` with `rng = np.random.default_rng(42)`, reference `rng.normal(60, 15, 500)`, then live `rng.normal(75, 15, 500)`.

**Expected (D1 handoff).** D = 0.422, p about 0, status red; the report has 5 indicators. Run `make train` to refresh `reference.json`.

#### Exercise 5: SQL, reviews per reviewer
After `make seed`:
```sql
SELECT reviewer, COUNT(*) AS n,
       ROUND(AVG(CASE WHEN action = 'override' THEN 1.0 ELSE 0.0 END), 2) AS override_rate
FROM reviews GROUP BY reviewer ORDER BY n DESC;
```
Run it with `.venv/bin/python -c "import sqlite3; print(sqlite3.connect('sanket.db').execute('''<query>''').fetchall())"`.
**Expected (measured 2026-11-15).** `[('sim-reviewer', 14, 0.79)]`: the seed's simulated reviewer handled 14 tickets and changed 11 (the seed printed "auto 373, queued 13, reviewed 14, overrides 11"). The older interview guide shows `12, 0.83`; that was measured before the seed script was changed to leave at most half the queue unreviewed. Then review one ticket in the dashboard as "me" and run it again: a second row appears.

#### Exercise 6: Luhn by hand and in code
On paper, check 4111 1111 1111 1111: double every second digit from the right (seven 1s → 2s, and the leading 4 → 8), add the other eight 1s. Total 14 + 8 + 8 = 30, ends in 0, valid. Then:
```bash
.venv/bin/python -c "from sanket.pipeline.pii import luhn_ok; print(luhn_ok('4111111111111111'), luhn_ok('4111111111111112'))"
.venv/bin/python -c "from sanket.pipeline.clean import clean; print(clean('order 4111111111111111 has not arrived').text)"
```
**Expected.** `True False`. The second line prints `order 4111111111111111 has not arrived`: a Luhn-valid number right after "order" is treated as an order id, not a card. Explain why that rule exists and what risk it carries.

#### Exercise 7: PSI and KS by hand, then check
On paper: PSI for reference 50/50, live 70/30, and for reference 0.3/0.4/0.3, live 0.2/0.4/0.4. KS for reference lengths 3, 5, 6, 8, 9 and live 7, 10, 11, 12, 14 (walk the number line, write each sample's share at or below each value). Then:
```bash
.venv/bin/python -c "
import numpy as np; from sanket.monitoring.drift import psi_from_shares, ks_2samp
print(round(psi_from_shares([.5,.5],[.7,.3]),4), round(psi_from_shares([.3,.4,.3],[.2,.4,.4]),4))
print(ks_2samp(np.array([3,5,6,8,9]), np.array([7,10,11,12,14])))"
```
**Expected.** `0.1695 0.0693` (amber, green) and `(0.8, 0.07936507936507942)`: D = 0.8 but p about 0.08, so with 5 + 5 points it is not significant. That is why the monitor waits for 200 tickets.

#### Exercise 8: prove the explanation adds up
```bash
.venv/bin/python -c "
from pathlib import Path; from sanket.models.baseline import BaselineModel
from sanket.pipeline.clean import clean; from sanket.taxonomy import INTENTS
m = BaselineModel.load(Path('artifacts/models/v1')); t = clean('How do I order a physical card?').text
p = m.predict_proba([t])[0]; i = int(p.argmax()); terms = m.explain(t, INTENTS[i], k=10000)
print(INTENTS[i], round(sum(x['weight'] for x in terms) + float(m.intercept[i]), 5), round(m.raw_score(t, INTENTS[i]), 5))
print([(x['term'], round(x['weight'], 3)) for x in terms[:3]])"
```
**Expected (measured 2026-11-15).** `order_physical_card 9.93958 9.93958`: all contributions plus the intercept equal the raw score exactly. Top three: `physical card` 0.804, `physical` 0.76, `order` 0.698.

#### Exercise 9: every status code, with the real app
```bash
SANKET_DB_URL=sqlite:////tmp/practice.db .venv/bin/python -c "
from fastapi.testclient import TestClient; from sanket.api.app import create_app
with TestClient(create_app()) as c:
    r = c.post('/api/tickets', json={'text': 'asdf qwer zxcv'}); p = r.json()['prediction']
    print(r.status_code, p['decision'], p['reason'], round(p['team_conf'], 2))
    print(c.post('/api/tickets', json={'text': '   '}).status_code, c.post('/api/tickets', json={'text': '1234'}).json())
    tid = c.post('/api/tickets', json={'text': 'I tried to pay and it did not work'}).json()['ticket_id']
    body = {'reviewer': 'me', 'action': 'confirm'}
    print(c.post(f'/api/tickets/{tid}/review', json=body).status_code, c.post(f'/api/tickets/{tid}/review', json=body).status_code)
    print(c.get('/api/tickets/99999').status_code, c.post('/api/tickets', json={'text': 'hello', 'channel': 'seed'}).status_code)"
```
**Expected (measured 2026-11-15).** `201 human low_confidence 0.22` (gibberish is stored but sent to a person); `422 {'detail': 'no_letters: the message has no letters'}`; `200 409` (the second review is refused); `404 422` (unknown ticket; reserved channel).

#### Exercise 10: watch the retrain gate reject poison
Work on a copy of the artifacts so the real ones stay untouched:
```bash
cp -r artifacts /tmp/art && .venv/bin/python -c "
import pandas as pd; s = pd.read_csv('data/splits/stream.csv')
s.iloc[700:800][['text','intent']].to_csv('/tmp/reviews100.csv', index=False)"
SANKET_ARTIFACTS_DIR=/tmp/art .venv/bin/python -m sanket.retrain --from-csv /tmp/reviews100.csv --sabotage 0.3
SANKET_ARTIFACTS_DIR=/tmp/art .venv/bin/python -m sanket.retrain --from-csv /tmp/reviews100.csv
```
Each run trains a candidate (about a minute).
**Expected (measured 2026-11-15).** The sabotaged run: `"promoted": false`, reason "label sanity: only 71% of 100 new labels are in the champion's top 5 (limit 75%)". The honest run: `"promoted": true`, no reasons. **The lesson:** in both runs the candidate's test macro-F1 printed 0.9027 against the champion's 0.9003, so the test-set gate alone would have promoted the poisoned model. That is exactly the Q2 audit finding, and why the label-sanity check exists.

### 11.3 Glossary pointer

Every technical word in this handbook is defined in one plain sentence, with an example from SANKET, in **`docs/GLOSSARY.md`** (about 170 terms, alphabetical). If a word is not there, treat it as a gap and look it up before the interview. PRAHARI-specific words (GCN, normalised adjacency, IsolationForest, quantisation, union-find) are explained in PRAHARI's `docs/INTERVIEW_GUIDE.md` section 5.

---

*Generated for the candidate from the SANKET and PRAHARI repositories. Source: `docs/CANDIDATE_HANDBOOK.md`; HTML and PDF built by `scripts/build_handbook_html.py`.*
