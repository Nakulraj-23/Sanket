# SANKET interview guide

For: the Tech Mahindra Digital Catalyst AI Engineer interview.
Goal: you can explain every part of SANKET in plain words, show the code, and answer honestly.

How to use this guide:

- Read one section at a time. Each paragraph has one idea.
- Every technical word is explained the first time it appears here, and again in [GLOSSARY.md](GLOSSARY.md).
- Every number comes from the model card (`artifacts/models/v1/card.json`), `docs/bench.md`, a handoff note in `docs/handoffs/`, or `docs/AUDIT_LOG.md`. If a number changed during the audits, this guide uses the latest one.
- The 5-day plan at the end tells you what to read each day.

---

## 1. Pitches

### 30 seconds

"SANKET is a support-ticket triage system for a bank.
It reads a customer message, hides personal data like card numbers, and predicts what the customer wants, out of 77 intents.
A table I wrote turns that into a team and an urgency.
If the model is sure, the ticket goes straight to the team; if not, a person reviews it and the correction is logged.
It watches for drift, and a new model replaces the old one only if a frozen test says it is not worse.
On the official test set it routes 94% of tickets on its own, and 99% of those go to the right team."

### 2 minutes

"I wanted to build the smallest system that shows what an AI engineer does beyond training a model: data, model, API, human control, monitoring and safe retraining.

The data is Banking77, a public set of about 13,000 real customer messages to a bank, each labelled with one of 77 intents. I split it into train, validation, a 'stream' that feeds the live demo, and the official test set, which I never touch until the end.

First, every message is cleaned. Emails, phones, card numbers and account numbers become placeholders. A long number counts as a card only if it passes the Luhn checksum, so order numbers are not hidden by mistake. The same clean function runs at training and serving time.

The model is TF-IDF plus logistic regression. That means: each word gets a score, the model multiplies scores by learned weights and adds them up, one total per intent. Because it is a sum, I can show exactly which words drove each answer. I also built a small PyTorch network and benchmarked it honestly. It lost by 1.4 points of macro-F1, so the simple model serves.

A YAML table maps each intent to one of 7 teams and an urgency. I add up intent probabilities per team. If the best team is under 0.70, a person looks. If the chance of a high-urgency intent is 0.20 or more, it is marked urgent; that cut-off catches 98.3% of urgent test tickets.

People review uncertain tickets in a queue. A database rule makes sure two reviewers cannot both decide one ticket. A monitor compares live tickets with validation tickets using PSI and a KS test that I wrote in NumPy. A retrain command learns from corrections and is blocked if the new model is worse or the labels look poisoned.

Three separate audits tried to break it. They found real bugs, like card numbers hidden by odd spacing, and a speed comparison that was wrong by a factor of eight. Each fix has a test. Everything is in one FastAPI service and a React page with a fallback when the free server is asleep."

---

## 2. Why I built this for Tech Mahindra

Say this only in this form. Do not claim any knowledge of Tech Mahindra's internal systems.

"The job description says AI engineers do more than train models: they build reliable, responsible and scalable solutions. Ticket triage is the smallest complete system where you can show all of that: data checks, a model, an API, a human in the loop, monitoring and a safe update process. Tech Mahindra's public material talks about AI for service desks, contact centres and banking, so I picked a banking support problem."

**Public links to read before the interview.** The build machine could not open any of these pages (its network blocked every Tech Mahindra and news address). So this guide does not quote them. Before the interview, open each link yourself. Use a link only if it loads. Quote only what the page actually says. If a link fails, drop it.

| Link | What to check on the page |
|---|---|
| <https://insights.techmahindra.com/assets/next-generation-service-desk-solution-for-smarter-support.pdf> | Does it describe an AI-assisted service desk? Does it mention ticket classification or routing? |
| <https://techmahindra.com/node/2617> | What the page is about (the plan expected "agentAssistX", IT support automation). |
| <https://insights.techmahindra.com/assets/nps-boost-with-ai-enabled-contact-center-operations.pdf> | Who the client is, and whether complaint handling is described. |
| <https://insights.techmahindra.com/assets/redefining-intelligent-banking-with-agentic-ai.pdf> | What it says about AI in banking and about human oversight. |
| <https://www.techmahindra.com/insights/press-releases/tech-mahindra-unveils-techm-orion/> | What TechM Orion is; any sentence on guardrails or human oversight. |
| <https://www.techmahindra.com/services/artificial-intelligence/verifai/> | What VerifAI checks (AI validation and testing?). |
| <https://www.techmahindra.com/insights/press-releases/tech-mahindra-launches-project-indus-large-language-model-llm/> | Project Indus and the Indian languages it covers. |
| <https://india.entrepreneur.com/technology/tech-mahindra-increases-ai-investment-in-fy26-working-on/498829> | Context only: AI investment news. |

When you have read them, write one sentence per page in your own words in the margin. The company sheet in section 13 shows how to connect each one to SANKET.

---

## 3. The components, one by one

Each block has: what it does, how, why this way, the file to open, and the one-minute answer to say out loud.

### 3.1 Intake and clean

**What.** Checks a message is usable, hides personal data, and tidies the text.

**How.** `validate` refuses empty text, text over 2,000 characters and text with no letters. `redact` finds emails (also written out as "name at gmail dot com"), UPI ids, phones, card numbers, Aadhaar numbers, PAN numbers and account numbers with **regular expressions** (a pattern language for finding text) and replaces them with placeholders such as `[CARD]`. Cards must pass the Luhn checksum and Aadhaar numbers the **Verhoeff checksum** (another check-digit rule), so random long numbers are left alone. Then `clean` lower-cases the text and makes spacing consistent.

**Why this way.** Patterns can be read and tested line by line. A learned detector cannot. The same `clean` runs at training and serving time, which avoids **train/serve skew** (the model seeing text prepared differently in production than in training).

**Open.** `sanket/pipeline/pii.py: redact, luhn_ok`; `sanket/pipeline/clean.py: clean`; `sanket/pipeline/quality.py: check_frame`.

**One minute.** "Before the model sees a complaint I do two things. First I check it is usable: not empty, not too long, has letters. Second I remove personal data: emails, UPI ids, phones, card, Aadhaar, PAN and account numbers become placeholders like [CARD]. For cards I do not trust the pattern alone: a long number is treated as a card only if it passes the Luhn checksum, the check card numbers are built to pass, so an order number is not hidden by mistake. Only the cleaned text is stored. The same clean function runs when I train and when I serve. For the training files there is a separate quality step that fails loudly on missing values, duplicates, unknown labels, uncleaned text or rows shared between splits."

### 3.2 Classify

**What.** Turns cleaned text into 77 probabilities, one per intent.

**How.** **TF-IDF** (term frequency times inverse document frequency: a score that is high for a word that is frequent in this message and rare overall) turns the text into numbers. It uses words and pairs of words, plus 2 to 5 letter pieces inside words. **Logistic regression** (a linear model: a weighted sum per class, turned into probabilities) holds one weight per term per intent. The 77 totals go through **softmax** (raise e to each total, divide by the sum) to become probabilities. Finally the totals are divided by a **temperature** of 0.591 so the confidence is honest (section 4.6).

**Why this way.** It is strong on short texts, fast (0.82 ms per ticket at p50) and fully explainable. The challenger, a small PyTorch network, scored lower (section 5.2).

**Open.** `sanket/models/baseline.py: predict_proba, scores`; `sanket/models/nn/net.py: IntentNet.forward`.

**One minute.** "The model turns the text into numbers and the numbers into 77 probabilities. TF-IDF gives each word and short letter group a score: high if it is frequent in this message and rare in general. Logistic regression holds one weight per term per intent. It multiplies scores by weights, adds them up, and softmax turns the 77 totals into probabilities that sum to one. I also built a small PyTorch network: it looks up a 64-number vector for each word, averages them, and passes the average through two layers. On the test set the baseline scores macro-F1 0.900 and the network 0.887. The network is about 15 times faster, 0.055 against 0.82 milliseconds, but both are far below a millisecond. So the linear model serves because it is more accurate and its explanations are exact. I report both."

### 3.3 Explain and route

**What.** Shows the words behind the answer, then picks a team, an urgency, and whether a person must look.

**How (explain).** For a linear model, the score of an intent is a sum of (weight × TF-IDF value) over the words in the message, plus an **intercept** (a fixed number per intent). So the five biggest terms are an exact explanation, not an estimate.

**How (route).** `taxonomy.yaml` maps each intent to one of 7 teams and to an urgency. Team probability = sum of its intents' probabilities. Then:

- team confidence under **0.70** → a person looks (`low_confidence`);
- more than **20%** unknown words **and** team confidence under **0.97** → a person looks (`unfamiliar_words`);
- otherwise → auto-routed;
- urgent ("high") if the summed probability of the 9 high-urgency intents is at least **0.20**.

**Why this way.** Banking77 has no team or urgency labels, so a learned urgency model would be invented. The table is the project's **rubric** (a rule table a person wrote), and I say so. The urgent cut-off is low on purpose: missing a fraud report costs more than an extra look.

**Open.** `sanket/routing/decide.py: decide` (about 30 lines, no files, no database); `sanket/taxonomy.yaml`; `sanket/routing/thresholds.py`.

**One minute.** "For a linear model the explanation is exact. The score for an intent is a sum of weight times TF-IDF value, one term per word, so I show the five largest terms. Then routing. The data has 77 intents; my table maps each to one of 7 teams and to an urgency. The probability of a team is the sum of its intents' probabilities. If the best team is under 0.70, or many words are unknown and the team is not very clear, the ticket goes to a person. A ticket is urgent when the high-urgency intents together reach 0.20. I chose that on validation data to catch at least 97% of urgent tickets; on test it catches 98.3% with 91.5% precision. Missing a fraud report costs more than a wasted look."

### 3.4 Review

**What.** A queue where a person confirms or corrects uncertain tickets.

**How.** The queue is ordered urgent first, then oldest (`ORDER BY` with a `CASE`). Saving a review runs a **transaction** (a group of database changes that happen together or not at all): it flips the ticket to `reviewed` only if it is not already reviewed, then inserts the review. If no row changed, the second reviewer gets **HTTP 409** (conflict). A **unique constraint** on `reviews.ticket_id` is a second lock. The reviewer name and note are redacted too.

**Why this way.** Two people can open the same ticket at the same time. That is a **race condition** (the result depends on who is first). The conditional update makes the database decide.

**Open.** `sanket/review.py: save_review, _claim_and_insert, list_tickets`; `sanket/sql/metrics.sql`.

**One minute.** "Tickets the model is unsure about wait in a queue, urgent first, then oldest. A person confirms the prediction or picks the right intent. The decision is saved with who, when and a note, and the note is redacted like the ticket. A transaction and a unique constraint make sure two people cannot both decide the same ticket: the second gets a clear 'already reviewed' answer, HTTP 409. These rows are the override log and the training data for the next model. If the intent was right but the reviewer disagrees with the urgency, that means my table needs changing, not the model."

### 3.5 Monitor

**What.** Warns when live tickets stop looking like the tickets the model was tuned on.

**How.** It compares the latest 500 tickets with the validation set on four signals: message length, unfamiliar-word rate, team confidence (each with a **KS test**, which finds the biggest gap between two cumulative curves), and the predicted-team mix (with **PSI**, the Population Stability Index). Overall status is the worst of the four. Under 200 tickets it says `insufficient_data`.

**Why this way.** True labels arrive late. These signals are available now. Both formulas are written in NumPy so I can explain every line; KS is checked against SciPy in a test.

**Open.** `sanket/monitoring/drift.py: psi, ks_2samp, drift_report`; `sanket/api/queries.py: live_inputs`.

**One minute.** "A model is trained on yesterday's messages. If today's look different it can be wrong without knowing. True labels arrive late, so I watch what I can measure now: message length, the share of unknown words, the model's confidence, and the mix of predicted teams. PSI puts both periods into the same bins and sums (actual minus expected) times the log of actual over expected: under 0.1 is stable, over 0.25 is a real shift. The KS test sorts both samples and finds the largest gap between their cumulative curves. I wrote both in NumPy and checked KS against SciPy. When I simulate a Hinglish surge, the unknown-word signal goes red. Drift is a reason to look, not proof the model is wrong."

### 3.6 Retrain gate

**What.** Learns from corrections, and replaces the live model only if the new one is not worse.

**How.** `make retrain` reads reviewed tickets, adds them to the training data, and trains a **challenger** (a candidate model) with the same code. It is promoted over the **champion** (the model in service) only if all of these hold:

1. at least 75% of the new labels are among the champion's top 5 guesses (label sanity);
2. data-quality checks pass;
3. on the frozen test set: macro-F1 at most 0.005 below the champion, high-urgency recall at most 0.01 below;
4. on the frozen validation set: the same rule with double slack;
5. macro-F1 at most 0.01 below the best model ever promoted;
6. file sizes within limits.

Every attempt, promoted or rejected, is written to `artifacts/registry.json` with reasons.

**Why this way.** A bad reviewer, or someone malicious, could poison the labels. The gate catches it.

**Open.** `sanket/retrain.py: gate, label_sanity_problems, run_retrain`; `tests/model/test_quality_gates.py`.

**One minute.** "Retraining adds the human-corrected tickets to the training set and fits a new model with the same code. Then the gate: the new model is scored on a test set that neither model has trained on, and it replaces the live model only if its macro-F1 and urgent-ticket recall are not worse, within a small tolerance. There is also a label sanity check: at least 75% of the new labels must be among the old model's top five guesses. Honest batches score 0.86 to 0.97; batches with 30% wrong labels score 0.58 to 0.72. In the audit, a retrain with 30% poisoned labels was rejected at 57%, and an honest one was promoted from 0.9003 to 0.9058 macro-F1. Nothing on the web can trigger this; a person runs it."

### 3.7 The two surfaces

**REST API (`sanket/api/`, `sanket/service.py`).** **REST** is an API style where URLs name things and HTTP methods are the actions. One `POST /api/tickets` runs clean, classify, explain and route, stores the result, and returns every stage's output and time (the **trace**). Status codes: 201 created, 404 not found, 409 already reviewed, 413 body too large, 422 invalid input. **CORS** (the browser rule about which web addresses may call the API) is an allow-list from `SANKET_CORS_ORIGINS`.

**Dashboard (`web/src/`).** One page: a text box, six sample chips, seven stage cards, then the review queue, monitor and model panels. Clicking a card shows what it does, why, the real code (read from the running function, so it cannot go stale), and this ticket's data. If the API does not answer `/api/health` within 4 seconds, the page shows recorded real answers from `web/public/replay.json` with an amber "Replay" badge, and keeps retrying.

---

## 4. Concepts from first principles, with tiny examples

Work through each example on paper. You need a calculator only for logs and exponents.

### 4.1 TF-IDF on three tiny messages

Messages: (1) "card not working", (2) "card lost", (3) "transfer not working". N = 3 messages.

**Document frequency** (df) = in how many messages a word appears:
card 2, not 2, working 2, lost 1, transfer 1.

**IDF** (textbook version) = ln(N / df):
card = ln(3/2) = 0.405; lost = ln(3/1) = 1.099.

**TF** (term frequency) for message 2 is 1 for "card" and 1 for "lost". So TF-IDF: card 0.405, lost 1.099.

**Reading it.** "lost" is almost three times as informative as "card", because "card" appears everywhere.

**What scikit-learn actually does.** It uses a smoothed IDF, ln((1+N)/(1+df)) + 1: card 1.288, lost 1.693. Then it scales the vector to length 1: card 0.61, lost 0.80. SANKET also uses "sublinear" TF, 1 + ln(count), so a word repeated five times does not count five times as much.

### 4.2 Dot product and a logistic-regression score by hand

A **dot product** multiplies two lists position by position and adds the results.

Message "card lost", TF-IDF vector: card 0.61, lost 0.80. Three intents with made-up weights (the real model has 20,672 weights per intent):

| Intent | weight for "card" | weight for "lost" | intercept | score |
|---|---|---|---|---|
| lost_or_stolen_card | 0.5 | 3.0 | −0.2 | 0.61×0.5 + 0.80×3.0 − 0.2 = **2.505** |
| card_arrival | 1.2 | −0.8 | 0.1 | 0.732 − 0.640 + 0.1 = **0.192** |
| exchange_rate | −0.3 | 0.0 | 0.0 | **−0.183** |

The explanation for `lost_or_stolen_card` is the table row itself: "lost" contributed 2.40, "card" 0.31, intercept −0.2. They add up to the score. That is why the linear model's explanation is exact.

### 4.3 Softmax with three classes

Softmax: p_i = e^(score_i) / sum of e^(score_j).

From 4.2: e^2.505 = 12.24, e^0.192 = 1.21, e^−0.183 = 0.83. Total 14.29.
Probabilities: 12.24 / 14.29 = **0.857**, 0.085, 0.058. They add up to 1.

A simpler set to remember: scores 2.0, 1.0, 0.1 → 0.659, 0.242, 0.099.

### 4.4 Cross-entropy (the training penalty)

**Cross-entropy** for one example = −ln(probability given to the right answer).

- Right intent got 0.857 → loss = −ln(0.857) = 0.15. Small.
- Right intent got 0.659 → loss 0.42.
- Right intent got 0.090 → loss 2.41. Confident and wrong is punished hard.

Training adjusts the weights to make the average loss small. **Regularisation** (in scikit-learn, the setting C; smaller C = stronger brake) stops weights growing huge to memorise the training set. SANKET uses C = 5, chosen on validation data.

### 4.5 Summing probabilities per team

Intents are **disjoint** (a message has one intent), so probabilities of a group of intents add up.

Real example from the demo ("Someone used my card abroad, I did not make this payment"): the top intent `card_payment_not_recognised` has 0.79. But FRAUD_SECURITY has six intents, and their probabilities add up to **0.97**. So the intent is a bit uncertain, but the team is clear. That is why routing uses the team sum.

The same trick gives urgency: p_high = sum of the 9 high-urgency intents' probabilities. Here p_high = 0.97, above 0.20, so the ticket is urgent.

Measured benefit: summing gave test team accuracy 0.9708, against 0.9636 for a model trained directly on the 7 teams (`docs/EXPERIMENTS.md`).

### 4.6 Precision, recall and choosing a threshold

**Precision**: of the tickets flagged urgent, how many really are urgent.
**Recall**: of the truly urgent tickets, how many were flagged.

Lowering the urgent cut-off raises recall and lowers precision. The rule (CONTRACTS): pick the **largest** cut-off, in steps of 0.05, where validation recall is at least 0.97. Result: tau_high = 0.20. On test: recall 0.983, precision 0.915.

Same idea for auto-routing: pick the **smallest** team cut-off where auto-routed validation tickets are at least 98.5% right. Result: tau_team = 0.70. On test, the coverage table shows the trade-off:

| Team cut-off | Share auto-routed (test) | Team accuracy of those |
|---|---|---|
| 0.5 | 98.3% | 0.979 |
| 0.6 | 96.6% | 0.986 |
| **0.7** | **94.4%** | **0.992** |
| 0.8 | 92.2% | 0.995 |
| 0.9 | 87.3% | 0.999 |

(Coverage at 0.7 is 94.4%; the card's auto share is 94.2% because the unfamiliar-word rule sends a few more to a person.)

### 4.7 Calibration: why "0.9 confident" is not "90% right"

A model is **calibrated** if, among all answers given with confidence around 0.9, about 90% are right.

Nothing forces this. Logistic regression with regularisation tends to give softer probabilities. Measured before the fix: average confidence on test was 0.741, but accuracy was 0.900. The model was **under-confident**.

**ECE** (expected calibration error) measures the gap: put predictions into confidence buckets (for example 0.8 to 0.9), compare average confidence with accuracy in each bucket, and take the average gap weighted by bucket size. Before: **0.160**.

**Temperature scaling** fixes it with one number. Divide every raw score by T before softmax. T below 1 sharpens the probabilities; T above 1 flattens them. T is chosen to minimise cross-entropy on validation data. Here T = **0.591**.

Tiny example: scores 2.0, 1.0, 0.1 give 0.659 / 0.242 / 0.099 at T = 1. At T = 0.591 they give 0.817 / 0.150 / 0.033. Same ranking, so accuracy does not change. Only the confidence changes.

After: test ECE **0.0146**. Then the thresholds were re-chosen by the same rules (tau_team 0.70, tau_high 0.20). This also lifted test high-urgency recall from 0.9694 (just under the 0.97 target) to 0.983.

Caveat to say yourself: T and the thresholds were both chosen on the same validation set. A stricter setup fits T on half of it.

### 4.8 Embedding average (the neural network)

An **embedding** is a learned list of numbers per word. With 2 numbers per word (the real one uses 64):

- "card" → [0.2, 0.9], "lost" → [0.8, −0.1], padding → [0, 0].

**Mean pooling** averages the real words: ([0.2, 0.9] + [0.8, −0.1]) / 2 = [0.5, 0.4]. Padding is ignored by a mask.

Then a linear layer (64 → 128 numbers), **ReLU** (negatives become 0), and another linear layer (128 → 77 scores). **Dropout** 0.3 hides random parts during training.

Weakness: the average ignores word order. "not lost, arrived" and "arrived, not lost" look identical.

### 4.9 PSI on two bins (and three)

PSI = sum over bins of (actual − expected) × ln(actual / expected).

**Two bins.** Reference: 50% short messages, 50% long. Live: 70% short, 30% long.
Bin 1: (0.7 − 0.5) × ln(0.7/0.5) = 0.2 × 0.336 = 0.067.
Bin 2: (0.3 − 0.5) × ln(0.3/0.5) = (−0.2) × (−0.511) = 0.102.
PSI = **0.17** → amber (between 0.1 and 0.25).

Notice both terms are positive: a share going up or down both add to PSI.

**Three bins.** Reference 0.3 / 0.4 / 0.3, live 0.2 / 0.4 / 0.4: 0.041 + 0 + 0.029 = **0.069** → green.

An empty bin would give ln(0), so the code puts a floor of 0.0001 on every share.

### 4.10 KS on 5 + 5 numbers

Reference lengths: 3, 5, 6, 8, 9. Live lengths: 7, 10, 11, 12, 14.

Walk along the number line. At each value, write the share of each sample at or below it:

| value | reference share | live share | gap |
|---|---|---|---|
| 6 | 3/5 = 0.6 | 0 | 0.6 |
| 7 | 0.6 | 0.2 | 0.4 |
| 9 | 1.0 | 0.2 | **0.8** |
| 12 | 1.0 | 0.8 | 0.2 |

The largest gap is **D = 0.8**. The code's p-value is 0.079: with only 5 numbers each, a gap this big happens by chance about 8% of the time. SANKET's rule needs p < 0.01, so this would be green. That is why it waits for 200 tickets.

With real sizes (1,489 reference, 500 live), even D = 0.15 is very unlikely by chance. In the recorded Hinglish surge, the unknown-word signal had D = 0.58 (red) and team confidence D = 0.15 (amber).

### 4.11 Luhn on one card number

Take 4111 1111 1111 1111 (a standard test number).

1. Start from the right. Double every second digit: the 2nd, 4th, ..., 16th from the right.
2. Those are seven 1s and the leading 4. Doubled: seven 2s (= 14) and 8.
3. If a doubled digit is over 9, subtract 9 (none here).
4. Add the undoubled digits: eight 1s = 8.
5. Total = 14 + 8 + 8 = 30. It ends in 0, so it is **valid**.

Change the last digit to 2: total 31, **invalid**, so SANKET would not mask it as a card. Code: `pii.py: luhn_ok`, 12 lines, O(n).

### 4.12 Transaction and unique constraint

Two reviewers, A and B, click Save on ticket 7 at the same moment.

1. A's transaction runs: `UPDATE tickets SET status='reviewed' WHERE id=7 AND status!='reviewed'` → 1 row changed. Insert review. Commit.
2. B's transaction runs the same UPDATE → 0 rows changed (it is already reviewed). The code raises `AlreadyReviewed`, rolls back, and the API returns 409.
3. If B somehow got past step 2, inserting a second review for ticket 7 breaks the unique constraint, which also becomes 409.

Q3 tested this with 5 tickets × 10 reviewers at once: exactly one success per ticket, no orphan rows.

### 4.13 REST status codes used here

| Code | Meaning | When in SANKET |
|---|---|---|
| 200 | OK | GET a ticket; save a review |
| 201 | Created | POST /api/tickets |
| 404 | Not found | unknown ticket id |
| 409 | Conflict | second review of the same ticket |
| 413 | Payload too large | body over 20 kB |
| 422 | Unprocessable | empty text, over 2,000 characters, unknown intent, bad reviewer name |
| 500 | Server error | should never happen; Q3 found one (a broken character) and it was fixed to 422 |

### 4.14 Big-O of the main steps

**Big-O** says how work grows with input size.

| Step | Cost | Why |
|---|---|---|
| Luhn check | O(d), d = digits | one pass |
| TF-IDF for one message | O(L), L = characters | each word and letter piece looked up in a hash map |
| Score 77 intents | O(k × 77), k = non-zero features | sparse matrix times weights |
| Top-5 terms | O(k log 5) | `heapq.nlargest` |
| Team sums | O(77) | fixed index lists |
| KS statistic | O((n+m) log(n+m)) | sort, then binary search |
| KS exact p-value | O(n × m) | walks a grid (only for n × m up to one million) |
| Review queue | O(log N) to find rows | index on (status, created_at), then sort |

---

## 5. Results and how to read them

### 5.1 The main numbers (test set, 3,080 messages, official Banking77 test)

| Measure | Value |
|---|---|
| Intent accuracy | 0.900 |
| Intent macro-F1 | 0.900 |
| Team accuracy (summed probabilities) | 0.971 |
| Urgency macro-F1 | 0.956 |
| High-urgency recall / precision | 0.983 / 0.915 |
| Auto-routed share | 94.2% |
| Team accuracy of auto-routed tickets | 0.992 |
| ECE after temperature scaling | 0.0146 |

**How to read them.** **Macro-F1** averages the score over all 77 intents equally, so rare intents count as much as common ones. Accuracy and macro-F1 are equal here because the test set has exactly 40 messages per intent.

**Is 0.90 good?** The audit checked the task is not trivially easy: a depth-3 decision tree scored macro-F1 0.036, a length-only model 0.022, one keyword per intent 0.338 (Q1). The plan's expected band for this kind of model was 0.85 to 0.93.

**Team and urgency numbers measure agreement with my rubric**, not with real bank agents. Say this every time you quote them.

### 5.2 Linear model versus PyTorch network

| Model | Macro-F1 | p50 latency | Size |
|---|---|---|---|
| TF-IDF + logistic regression | 0.9003 | 0.82 ms | 4.93 MB |
| IntentNet (ONNX) | 0.8865 | 0.055 ms | 2.51 MB |

Three network variants were tried, all on validation only (`docs/EXPERIMENTS.md`): words only 0.8672; words plus hashed 3-letter pieces with 64 numbers per word 0.8820 (chosen); 128 numbers 0.8759. The chosen one was run on test once.

**Why the network loses.** About 90 short training messages per intent. Averaging word vectors throws away word order. TF-IDF on words and letter pieces is a very strong fit at this size.

**Was it a fair fight?** Q2 checked: same cleaned text, same test rows, cleaning included in both timings, 50 warm-up calls, 1 thread. The network was early-stopped and reached about 0.99 training accuracy, so it was not starved. Other seeds gave 0.887 to 0.889. The baseline's lead has a 95% bootstrap interval of +0.004 to +0.024, so it is real.

**Why this is a good result to present.** The decision rule was written before any result: "if the network loses, say so and explain why; no tuning until it wins". You followed it. Interviewers trust a candidate who reports a loss and knows why. And the network still has a job: it is the "second opinion" in the Compare view.

### 5.3 Hinglish and typos

**Hinglish** (Hindi in Latin letters, mixed with English), 60 hand-written rows, test only:

- intent accuracy 0.65, team accuracy 0.717;
- 26 of 60 went to a person;
- 0 were silently sent to the wrong team;
- 1 was silently given the wrong intent in the right team ("top up nahi ho raha card se": the true intent `top_up_failed` became `topping_up_by_card`).

Say "n = 60" every time. With 60 rows, "0 silent wrong-team" still allows a true rate of up to about 9% (Q2's estimate).

**Typos**: the test set with 10% of characters changed:

- intent accuracy 0.817, team accuracy 0.936;
- 35.4% sent to a person;
- 0.55% silently sent to the wrong team.

### 5.4 Error analysis

The most common confusions on test (model card) are near-synonyms:

- `verify_my_identity` → `why_verify_identity` (6)
- `pending_top_up` → `top_up_failed` (6)
- `virtual_card_not_working` → `get_disposable_virtual_card` (5)
- `pending_transfer` → `transfer_timing` (4)

Most of these stay in the same team, which is why team accuracy (0.971) is much higher than intent accuracy (0.900).

Urgency errors that matter (Q2, test): 2 high-urgency tickets were predicted low, and both were sent to a person anyway ("trapped card", "cannot find my credit card"). 9 high became medium. 23 medium became high (false alarms, acceptable by design).

Weakest teams by recall: FRAUD_SECURITY 0.921, CASH_ATM 0.930 (Q2).

A data artefact: the token "1" (as in "£1 charge") appears in 58 of 114 training rows of `extra_charge_on_statement`. A ticket about a different amount may be misrouted, and the test score will not show it (`docs/data_card.md`).

---

## 6. What reviewers found and what I fixed

SANKET was checked by three audit agents: Q1 (data), Q2 (model) and Q3 (system). Each wrote failing tests for its findings. A builder fixed them, the tests flipped to passing, and the auditor re-checked. Full log: `docs/AUDIT_LOG.md`. Present this as a strength: you did not trust your own work.

**Story 1: card numbers hidden by formatting.**
The data audit tried 35 ways of writing personal data and 12 slipped through, such as a card with double spaces or dashes, phone numbers in Devanagari digits, and `john(at)gmail.com`.
The fix maps digits of any script to 0-9, allows separators between digit groups, and searches for a Luhn-valid window inside a run of digits. Later the system audit found cards split by newlines and tabs; now every kind of whitespace becomes one space before redaction.
Tests: `tests/data/test_audit_pii.py` (all 35 formats, plus `test_any_whitespace_between_groups`).

**Story 2: the speed comparison was wrong by about eight times.**
The first benchmark said the network was about 125 times faster than the baseline.
The model audit found the baseline rebuilt a 77 × 20,672 matrix on every single prediction; building it once in `__init__` took p50 from 7.69 ms to 0.82 ms with identical outputs, so the real gap is about 15 times.
Test: `tests/model/test_audit_q2.py::test_baseline_predict_has_no_per_call_matrix_copy`.

**Story 3: the retrain gate let poison through, then blocked honest people.**
First, 200 reviews with every label wrong were promoted, because the new model was still within 0.005 on test. The fix rejected batches where the champion disagreed with over 30% of labels, but the re-audit showed honest reviewers disagree 56% of the time, because people only see the hard tickets.
The final rule asks whether the new label is in the champion's top 5 guesses: honest 0.86 to 0.97, 30% noise 0.58 to 0.72, all wrong 0.05, limit 0.75. Tests: `tests/model/test_quality_gates.py`.

**Story 4: the model's confidence was dishonest.**
The model audit measured ECE 0.160: average confidence 0.741 against accuracy 0.900, and urgent recall on test was 0.9694, just under target.
One temperature (T = 0.591, fitted on validation) brought test ECE to 0.0146, and re-chosen thresholds gave urgent recall 0.983 and 94.2% auto-routed.
Test: `test_calibration_in_card`.

**Story 5: the unknown-word rule drowned reviewers.**
With 10% typos, 65% of tickets went to a person, and most of those were routed correctly anyway.
Now unknown words escalate only when team confidence is under `oov_conf`, chosen on a typo copy of validation data (0.97): test typos now send 35.4% to a person with 0.55% silent wrong-team.
Test: `test_oov_conf_is_selected_on_val_typos_and_stored`.

**Story 6: the review note leaked personal data.**
The system audit typed a card number, phone and email into a reviewer's note; they were stored as typed, in the table and in the database's side file.
Now the note and reviewer name go through `redact` before anything is written or returned, and the reviewer name must be 1 to 64 characters.
Test: `tests/api/test_review_safety.py::test_note_and_reviewer_are_redacted_everywhere`.

**Smaller ones worth knowing.** The stream file was sorted, so its first 500 rows looked like drift (fixed by shuffling). The ticket cap deleted reviewed tickets (now it never does). A broken character gave a 500 (now 422). 68 training rows were near-copies of test rows (removed).

**Failed experiments (`docs/EXPERIMENTS.md`).** Nearest-training-text label agreement could not separate honest hard tickets (0.29) from noisy ones (0.22), so it was replaced by top-5 coverage. A bigger network (128 numbers per word) scored lower than the 64 version. Training first ran on all CPU threads and took over 5 minutes on tiny matrices; one thread brought all three variants under a minute.

---

## 7. Honest limitations and how to say them

### 7.1 The list

- Short English questions (median about 10 words), not long complaints; no real personal data in them.
- Team and urgency are my rubric, not labels from the dataset or from a bank.
- Label noise: an audit disagreed with 12 of 150 sampled training labels (8%).
- Near-duplicates: 351 of 3,080 test rows (11.4%) have a training text with **cosine similarity** (how alike two texts' word vectors point, 0 to 1) above 0.9. The test set is official and frozen, so they stay. Before the fix, Q1 checked a narrower set (89 test rows with almost the same words as a train row): a plain TF-IDF model got 0.978 accuracy on them against 0.872 on the rest, yet dropping them moved test macro-F1 only from 0.876 to 0.873.
- One test set is reused by every retrain gate decision; over many rounds that slowly overfits to it.
- Temperature and thresholds share the validation set.
- Review data is a biased sample: only uncertain tickets get reviewed.
- PII is pattern-based. The last fix round added Aadhaar (Verhoeff-checked), PAN, UPI ids and written-out emails, but any format nobody wrote a pattern for (a passport number, for example) is not masked. A phone written right after "paid" is left alone on purpose (it looks like an amount).
- Chunked request bodies skip the 20 kB size check (text is still limited to 2,000 characters).
- SQLite: one writer at a time. Q3 load test: 1 client p50 8.6 ms; 32 clients p50 164 ms, p95 720 ms, zero errors in 1,400 requests.
- No login: anyone with the link can review.
- Free hosting sleeps and wipes the disk; reviews on the free host are lost on restart.
- The Docker image was not built here (no Docker daemon). Deployment needs your own accounts.
- One known small bug is still marked as an expected failure: PSI on a constant reference gives one bin and always scores 0 (`test_audit_q2.py`). It does not affect the four live indicators.

### 7.2 How to say each weakness out loud

| Weakness | Say this |
|---|---|
| The network lost | "I built a PyTorch model and it lost by 1.4 macro-F1 points. I wrote the decision rule before seeing results, so I reported the loss and kept the simpler model. With 90 short examples per class, word features are hard to beat." |
| Rubric, not labels | "The dataset gives intents. Teams and urgency are a table I wrote. So my team and urgency scores measure agreement with my table. In a real bank, the table would come from operations, and overrides tell you where it is wrong." |
| Short English data | "Banking77 is short English questions. Real complaints are longer and mixed language. I measured that gap with a Hinglish set and a typo set instead of hiding it." |
| Hinglish | "On 60 Hinglish messages, 26 went to a person, none went silently to the wrong team, and one got the wrong intent in the right team. It is a small sample. The fix is Hinglish training data, not a bigger threshold." |
| Near-duplicates | "About 11% of test rows have a close paraphrase in training. I could not drop them because the test set is official, so I documented it. On the closest copies an audit found the score barely moves without them, but I would not claim that for all 351." |
| Calibration | "The raw model was under-confident: 74% average confidence, 90% accuracy. One temperature fixed it, ECE 0.16 to 0.015. I fitted it on the same validation set as the thresholds, which I would split in a stricter setup." |
| Reused test set | "Every gate decision uses the same test set. That is fine for a few rounds; over many it overfits. Production needs a fresh labelled sample each month." |
| PII gaps | "Redaction is pattern-based: emails, UPI ids, phones, cards with Luhn, Aadhaar with Verhoeff, PAN, account numbers. Anything without a pattern, like a passport number, is not caught. Adding a pattern is a few lines plus a test; I practised it with passports." |
| Chunked bodies | "The 20 kB limit reads the Content-Length header. A chunked request has none, so it is read fully and then refused by the 2,000-character rule. A streaming limit in middleware would close that." |
| Docker not verified | "The sandbox had no Docker daemon, so I could not build the image. The same app runs with `make serve`, and the Space bundle was tested by running it from its own folder." |
| Built with AI tools | See question Q60 in section 10. |

### 7.3 What production would need

Authentication and reviewer roles; PostgreSQL; a message queue for bursts; streaming body limits; PII patterns reviewed by a privacy team (or a pattern plus entity-recogniser mix); a fresh labelled test sample per period; real team and urgency labels from the operations team; alerting on drift; per-language models or Hinglish training data; audit retention rules.

---

## 8. Job description line → evidence in SANKET

| JD line | Where to point |
|---|---|
| Implement ML and AI models | `sanket/models/baseline.py`, `sanket/models/nn/` |
| Production-ready components | `Classifier` interface, versioned artifacts, `artifacts/registry.json`, model cards |
| Integrate models with APIs and data pipelines | `sanket/api/`, `sanket/service.py: process_ticket` |
| Deployment on cloud | `Dockerfile`, `make space-bundle`, `web/vercel.json`, `docs/DEPLOY.md`, replay fallback |
| Monitoring and drift | `sanket/monitoring/drift.py`; override rate in `sanket/sql/metrics.sql` |
| Feature pipelines, preprocessing | `sanket/pipeline/`; one `clean()` for train and serve |
| Data reliability | `sanket/pipeline/quality.py`; 422 on bad input |
| Functional testing of AI components | `tests/` (232 passing), `web/e2e/`, ONNX parity test |
| Performance and latency | `make bench`, `docs/bench.md` |
| Debugging inference | `docs/AUDIT_LOG.md` (the eight-times speed bug), per-stage timings in the trace |
| Collaboration with QA | three audit gates, handoff notes, contracts file |
| Documentation | README, ARCHITECTURE, GLOSSARY, model cards, this guide |
| Security, privacy | redaction before storage, no raw text in logs, input limits, CORS allow-list, no pickle from users |
| Python, a bit of JavaScript | Python 3.11 back end; React dashboard in plain JavaScript |
| DSA | Luhn, hash-map vocabulary, heap for top-k, sort-and-walk KS, priority-ordered queue |
| OOP | `Classifier` protocol with two implementations, dataclasses, Pydantic schemas, custom exceptions |
| DBMS, SQL | 4 tables, foreign keys, index, unique constraint, transaction, hand-written SQL |
| Statistics, probability | softmax, summed probabilities, precision/recall, calibration, PSI, KS |
| Linear algebra | TF-IDF vector × weight matrix; embedding average and layers |
| NumPy, pandas, scikit-learn, PyTorch | drift maths, data pipeline, baseline, IntentNet |
| Git, REST | wave-by-wave history, CI; REST with 201/404/409/422 |
| Responsible AI | human in the loop, override log, promote gate, Hinglish failure report, rubric disclaimer |
| Resilience when experiments fail | `docs/EXPERIMENTS.md`; the network result reported though it lost |

---

## 9. Four-minute demo script

Before the interview: open the live link 10 minutes early to wake the free API. Have a terminal ready with `make serve` and `make web` in case the network fails.

| Time | Do | Say |
|---|---|---|
| 0:00 | Open the page; point at the seven cards | "A message goes left to right through seven steps. Each card is one small file." |
| 0:20 | Click chip **Urgent fraud** | "It predicted card_payment_not_recognised at 79%. The six fraud intents add up to 97%, so the team is clear, and it is marked urgent. A few milliseconds in total." |
| 0:50 | Click the **Explain** card | "These words pushed the decision: 'payment', 'make', 'this payment', 'did not', 'someone'. Each number is weight times TF-IDF value, so it is exact." |
| 1:15 | Chip **Fake PII**, open **Clean** | "The card number and email became [CARD] and [EMAIL] before anything was stored. The card check uses the Luhn checksum." |
| 1:40 | Chip **Ambiguous** ("I tried to pay and it did not work") | "Team confidence is 0.69, just under 0.70, so it goes to a person." |
| 1:55 | Review queue → **Review** → override → save | "My correction is logged with who and when, and becomes training data. A second save would get 409." |
| 2:20 | Chip **Hinglish** | "Trained on English, so it is weak here. Many words are unknown, so it asks a person. On 60 Hinglish messages, 26 went to a person, none silently to the wrong team." |
| 2:45 | Monitor → **Simulate Hinglish surge** | "PSI and KS compare live tickets with validation tickets. The unknown-word signal jumps to red. Red means look before trusting the model." Then click **Reset**. |
| 3:15 | Model panel, scroll to the LR-versus-NN table and registry | "I built a PyTorch model; it is 15 times faster but 1.4 points less accurate, so the simple model serves. Retraining is gated: in the audit a poisoned retrain was rejected and an honest one promoted." |
| 3:40 | Open any card's **Code** tab | "And this is the real code behind the card, read from the running function." |

**Fallback if the badge says Replay.** Say: "The free server is asleep; these are recorded answers from the same API." Carry on with the chips; they all work. The review form works in this tab only. Free text is off in Replay.

**Fallback if there is no network.** Run `make serve` in one terminal and `VITE_API_URL=http://localhost:8000 make web` in another, then open http://localhost:5173.

**Note.** The committed registry has only v1. If asked to show a rejected candidate, open `tests/model/test_quality_gates.py` and explain the poisoned-label test, or quote the audit: 30% poisoned labels rejected at 57% top-5 coverage.

---

## 10. Question bank (66 questions)

Click a question to see a model answer. Say it in your own words.

### A. This project

#### Q1. What does SANKET do, in one sentence?
It reads a bank customer's message, hides personal data, predicts the intent, routes it to a team with an urgency, and asks a person when it is unsure.

#### Q2. Why ticket triage?
It is the smallest complete AI system that needs data checks, a model, an API, a human in the loop, monitoring and safe updates. It also matches the kind of support and banking work Tech Mahindra describes publicly.

#### Q3. Where does the data come from?
Banking77, from PolyAI (2020), licence CC-BY-4.0. About 13,000 real customer-service messages to a bank, each with one of 77 intents.

#### Q4. How did you split the data?
Official test set kept frozen (3,080 rows). The official training set, minus copies of test texts, was split by intent into train 70% (6,946), validation 15% (1,489) and stream 15% (1,489). Seed 42, so the split is the same every time.

#### Q5. What is the stream split for?
It feeds the live demo and the review queue. Keeping it separate means corrections used for retraining can never contain test rows.

#### Q6. Why not use the test set to pick thresholds?
Then the test score would be optimistic, because the settings were tuned to it. Thresholds are chosen on validation only.

#### Q7. Why TF-IDF and logistic regression?
It is strong on short texts, trains in about a minute, answers in under a millisecond, and every prediction can be explained exactly as weight times feature value.

#### Q8. What features does the model use?
TF-IDF on words and word pairs (up to 8,000), and on 2 to 5 letter pieces inside words (up to 15,000). In total 20,672 features after removing terms seen in fewer than 2 messages.

#### Q9. Why letter pieces?
They help with spelling variants and word forms. On validation they added about 0.02 macro-F1.

#### Q10. How did you choose C?
I tried C = 5, 10 and 20, with and without letter pieces, on validation only. With letter pieces, C = 5 was best (0.8981).

#### Q11. What is the PyTorch model?
IntentNet: one embedding of 64 numbers per word (plus hashed 3-letter pieces), averaged over the message, then a 128-unit layer with ReLU, then 77 scores. It is exported to ONNX so the server runs it without PyTorch.

#### Q12. Why did the network lose?
About 90 training messages per intent, all short. Averaging vectors ignores word order. TF-IDF on words and letter pieces is a very strong fit for that size. The audit confirmed the comparison was fair.

#### Q13. Then why build it?
To compare honestly, to show I can train, export and benchmark a neural model, and because the rule was decided beforehand. It also serves as a second opinion in the Compare view.

#### Q14. Why is the network faster?
It does a few hundred lookups and two small matrix multiplications. The baseline builds sparse TF-IDF vectors with 2 to 5 letter pieces, which is most of its 0.82 ms.

#### Q15. Why sum probabilities per team?
Because a message has one intent, intent probabilities in a team add up to the team's probability. A ticket can be unclear between two card intents but clearly a card ticket. Summing beat a direct team model: 0.9708 against 0.9636.

#### Q16. How is urgency decided?
Summed probability of the 9 high-urgency intents. If it is at least 0.20, the ticket is high. Otherwise medium or low, whichever group sums higher.

#### Q17. Why such a low urgent cut-off?
The rule was: catch at least 97% of urgent tickets on validation. Missing a fraud report is worse than a false alarm. On test: recall 0.983, precision 0.915.

#### Q18. Who decided which intents are urgent?
I did. It is the project's rubric, in `taxonomy.yaml`. The data audit listed debatable rows, such as `cancel_transfer` possibly being high.

#### Q19. When does a person review a ticket?
When team confidence is under 0.70, or when more than 20% of words are unknown and team confidence is under 0.97.

#### Q20. How did you choose 0.97?
On a copy of validation data with 10% typos: the smallest human share where silently wrong-team tickets stay under 1%. It gave 35.6% to a person and 0.94% silent errors on validation typos.

#### Q21. What is the explanation, exactly?
For the predicted intent, the five terms with the largest weight × TF-IDF value. With the intercept they add up to the raw score. Letter pieces start with "~" and are hidden when they only repeat a shown word.

#### Q22. Why not SHAP or LIME?
They approximate a model's behaviour and are slow. For a linear model the exact answer is a dot product, so approximation adds nothing.

#### Q23. How do you stop two reviewers deciding the same ticket?
A transaction with a conditional update (only change status if not yet reviewed) plus a unique constraint on `reviews.ticket_id`. The second reviewer gets 409.

#### Q24. How is personal data handled?
Masked before storage, in the ticket and in reviewer notes. Raw text exists only in memory during the request. The audit checked the database, its side files, the server log and the replay file: zero hits.

#### Q25. How does the dashboard work without the API?
It calls `/api/health` with a 4-second timeout. If that fails, it loads `web/public/replay.json`, which holds recorded real answers, shows an amber Replay badge, and retries in the background.

#### Q26. How long does one request take?
`POST /api/tickets` p50 9.9 ms, p95 12.0 ms over 200 requests. Model work alone is about 1 ms; the rest is the database write and the web framework.

#### Q27. How do you know the tests test anything?
The audits wrote strict "expected to fail" tests for every finding. A fix had to turn them into passing tests. 232 tests pass now, with one known small finding still marked.

#### Q28. What would you do with the overrides?
Wrong intent → training data. Right intent but disputed urgency → change the table. The override rate per team, from SQL, shows where the model or the table is weakest.

### B. Machine learning basics

#### Q29. What is overfitting and how did you limit it?
The model memorises training data and does worse on new data. Limits: regularisation (C), early stopping for the network, choosing settings on validation, and a frozen test set.

#### Q30. Precision versus recall?
Precision: of what I flagged, how much was right. Recall: of what was really there, how much I caught. For fraud I want high recall.

#### Q31. Why macro-F1 and not only accuracy?
Macro-F1 averages over classes, so small classes count equally. Here the test set is balanced (40 per intent), so both are 0.900, but on real data they differ.

#### Q32. What is calibration, and why did it matter here?
Whether "90% confident" means right 90% of the time. Reviewers and thresholds read the confidence, so it must be honest. Before: ECE 0.160. After temperature scaling: 0.0146.

#### Q33. What does temperature scaling change?
Only the confidence, not the ranking. It divides the scores by one number fitted on validation data. Accuracy stays the same.

#### Q34. What is cross-entropy?
Minus the log of the probability given to the right answer. Confident and wrong costs a lot. Logistic regression and the network both minimise it.

#### Q35. Difference between validation and test sets?
Validation is for choosing settings. Test is for the final score, used once per decision. If you tune on test, the score lies.

#### Q36. What is data leakage? Did you have any?
Test information getting into training. Exact overlap was zero; 68 near-copies of test texts were removed from train. 351 test rows still have a close paraphrase in train (cosine above 0.9); this is documented.

#### Q37. What is an embedding?
A learned vector per word, so words used in similar ways end up with similar vectors.

#### Q38. Why not a transformer like BERT?
No GPU, far larger than the free host allows, and I could not explain attention honestly in an interview. The point here was a system I fully understand.

### C. Statistics and linear algebra

#### Q39. Explain softmax.
Raise e to each score, divide by the sum. All outputs are positive and add up to 1. Bigger scores get bigger shares.

#### Q40. Explain PSI with numbers.
Reference 50/50, live 70/30. (0.2 × ln 1.4) + (−0.2 × ln 0.6) = 0.067 + 0.102 = 0.17, amber.

#### Q41. Explain the KS test.
Sort both samples, draw each one's cumulative share curve, and take the largest vertical gap, D. The p-value says how likely such a gap is by chance. Red needs D at least 0.2 and p under 0.01.

#### Q42. What is a p-value, simply?
If nothing had changed, the chance of seeing a difference this big. Small p means "probably a real change".

#### Q43. Why need 200 tickets before reporting drift?
With few points, big gaps happen by chance (5 + 5 numbers can give D = 0.8 with p = 0.08). Below 200 the report says `insufficient_data`.

#### Q44. Where is linear algebra in this project?
TF-IDF vector (1 × 20,672) times the weight matrix (20,672 × 77) plus intercepts gives 77 scores. In the network: embedding lookup, average, then two matrix multiplications.

### D. Python, SQL, REST, Git, DSA, OOP, DBMS

#### Q45. Write SQL for the override rate per team.
```sql
SELECT p.team, AVG(CASE WHEN r.action = 'override' THEN 1.0 ELSE 0.0 END) AS rate, COUNT(*) AS n
FROM reviews r JOIN predictions p ON p.ticket_id = r.ticket_id
GROUP BY p.team ORDER BY p.team;
```
This is in `sanket/sql/metrics.sql`.

#### Q46. Write SQL for the review queue.
```sql
SELECT t.id, t.text_redacted, p.urgency
FROM tickets t JOIN predictions p ON p.ticket_id = t.id
WHERE t.status = 'needs_review'
ORDER BY CASE p.urgency WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, t.created_at
LIMIT 50;
```

#### Q47. Why an index on (status, created_at)?
The queue filters by status and sorts by time. A combined index lets the database find and order those rows without scanning the whole table.

#### Q48. What is a foreign key here?
`predictions.ticket_id` and `reviews.ticket_id` must point at an existing ticket. SQLite only checks this when `PRAGMA foreign_keys=ON`, which `db.py` sets on every connection.

#### Q49. What OOP ideas are used?
A `Classifier` protocol (an interface) with two implementations, `BaselineModel` and `OnnxModel`. Dataclasses for `Thresholds`, `Decision`, `CleanResult`. Custom exceptions (`TicketNotFound`, `AlreadyReviewed`, `BadReview`) mapped to 404, 409 and 422.

#### Q50. Where are data structures used?
Hash maps for the vocabulary and unknown-word check, a heap for top-k terms, sorting and binary search in KS, a priority order for the queue, and the Luhn loop.

#### Q51. What makes an API RESTful here?
URLs name resources (`/tickets/{id}`, `/tickets/{id}/review`), HTTP methods are the actions, and status codes carry meaning: 201, 404, 409, 422.

#### Q52. Is POST /tickets idempotent?
No. Sending it twice creates two tickets. GET requests are idempotent. A review is effectively once-only: the second attempt gets 409.

#### Q53. How did you use Git?
Work landed in waves (scaffold, data, model, API, fixes), each a commit, with CI running lint and tests on every push. Audits and fixes are separate commits so the history shows what changed and why.

### E. Deployment, scaling, drift

#### Q54. How is it deployed?
API: a Docker image on a free Hugging Face Space. Dashboard: Vercel. Both steps need my accounts; the guide is `docs/DEPLOY.md`. The image has no PyTorch: scikit-learn, onnxruntime, FastAPI and SQLite.

#### Q55. What happens when the free server sleeps?
The first request takes about a minute to wake it. The dashboard shows Replay meanwhile. The disk is wiped on restart, so the database is re-seeded and reviews are lost.

#### Q56. How would you handle 10,000 tickets a minute?
That is about 170 per second. The model alone handles over 13,000 per second in batches, so the model is not the problem. SQLite with one writer is. I would move to PostgreSQL, run several API workers behind a load balancer, put a queue between intake and the model to absorb bursts, batch predictions, and add rate limits. Q3 measured that with 32 parallel clients, p95 latency rose to 720 ms on SQLite with zero errors, which shows where it starts to strain.

#### Q57. What is the difference between data drift and concept drift?
Data drift: inputs change (more Hinglish). Concept drift: the right answer for the same input changes (a new product makes "card" mean something else). Data drift is visible now; concept drift needs labels, so the override rate is the best early signal.

#### Q58. When would you retrain?
When drift stays red, when the override rate rises, or on a schedule once enough reviews exist (at least 50 new rows). Always through the gate.

### F. Responsible AI, privacy, honesty

#### Q59. What responsible-AI practices are in SANKET?
Personal data masked before storage; a person decides uncertain cases; every override logged with who and when; urgency errs towards safety; a gate stops bad models; model cards state limits; failures (Hinglish, typos) are measured and published.

#### Q60. Was this built with AI tools?
Yes. I planned it and built it with AI coding agents working under my direction, in a multi-agent setup: builder agents wrote the code to a contract I set, separate auditor agents tried to break it, and a documentation agent wrote these guides. I chose the problem, the data, the rules (like "report the network even if it loses") and reviewed the results. I do not claim I typed every line. What I claim is that I understand every part, can verify it, and can change it, and I am happy to make a change live now.

#### Q61. What if the model is biased against some customers?
The data has no customer attributes, so I cannot measure group fairness directly. What I can measure is language: Hinglish performs worse. The design response is to send unfamiliar text to a person rather than guess, and to report the gap.

#### Q62. What personal data could still leak?
Anything with no pattern: passport numbers, names, addresses, and a phone written right after "paid" (treated as an amount on purpose). Audits pushed the coverage up from email, phone, card and account to also Aadhaar, PAN, UPI ids and written-out emails. In production I would combine patterns with a reviewed entity recogniser.

### G. Reflection

#### Q63. What would you improve first?
Real or Hinglish training data; name and address masking; a second labelled test sample so the gate does not wear out one test set; login for reviewers; PostgreSQL.

#### Q64. What was the hardest bug?
The retrain gate. The obvious fix (reject if the model disagrees a lot) blocked honest reviewers, because people only review hard tickets. The fix that worked was asking whether the label is in the model's top 5.

#### Q65. What did you learn?
Measure before claiming: the "125 times faster" result was a bug. Pick decision rules before seeing results. And a simple model you can explain often beats a complex one on small data.

#### Q66. Why should we trust your numbers?
Each number is in a model card, benchmark file or audit log, with a test or script that reproduces it. An audit re-ran training from scratch and got byte-identical model files.

---

## 11. Five hands-on exercises

Do these alone, on your laptop, in a Git branch (`git checkout -b practice`). Afterwards run `git checkout .` to undo. Each has an expected result so you can check yourself.

### Exercise 1: add a [PASSPORT] redaction with a test

**Task.** First read how `[PAN]` is done in `sanket/pipeline/pii.py` (`PAN_RE` and the line in `redact`). Indian passport numbers look like `K1234567`: one letter, then 7 digits, the first of them not 0. Add the same kind of redaction for them.

1. In `pii.py`, add `PASSPORT_RE = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z][1-9]\d{6}(?![A-Za-z0-9])")`.
2. In `redact`, add `"PASSPORT": 0` to `counts`, and a line like the PAN one: `text = PASSPORT_RE.sub(lambda m: _count(counts, "PASSPORT"), text)`.
3. **Trap:** `clean` lower-cases everything except known placeholders. Add `PASSPORT` to `_PLACEHOLDER` in `clean.py` and to `PLACEHOLDER` in `service.py`, or you will get `[passport]`.
4. Add a test in `tests/unit/test_pii.py`.

**Expected.** `clean("My passport is K1234567").text == "my passport is [PASSPORT]"` and `pii == {"PASSPORT": 1}`. `make test` still passes: no data split and no probe row contains a passport-shaped string (checked). Today, without your change, the same text comes out as `my passport is k1234567`.

### Exercise 2: move an intent to another team and re-evaluate

**Task.** The data audit suggested `apple_pay_or_google_pay` and `supported_cards_and_currencies` belong in TRANSFERS_TOPUPS. Move both in `sanket/taxonomy.yaml`. No retraining is needed: the model predicts intents; only the sums change.

Run:
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

**Expected.** Before: val 0.9691, test 0.9705. After moving both: val 0.9691, test 0.9714. A reorganisation is a table edit, not a retrain. (`tests/unit/test_scaffold.py` still passes; it checks counts, not membership.)

### Exercise 3: change tau_team and read the coverage table

**Task.** Open `artifacts/models/v1/card.json`, find `metrics.test.coverage_table`. Then set `tau_team` to 0.8 in `artifacts/models/v1/thresholds.json`, restart `make serve`, and submit "I tried to pay and it did not work".

**Expected.** From the table: at 0.7, 94.4% auto-routed at 0.992 team accuracy; at 0.8, 92.2% at 0.995. A higher cut-off means more work for people and fewer mistakes. The ambiguous message (team confidence 0.69) still goes to a person. Explain why validation chose 0.70: it is the smallest step where auto-routed validation accuracy reached 0.985 (0.9852).

### Exercise 4: add a fifth drift indicator

**Task.** Add a KS indicator on `n_chars` (message length in characters).

1. In `sanket/models/train_baseline.py: reference_from_val`, add `"n_chars": [len(t) for t in val["text"]]`.
2. In `sanket/api/queries.py: live_inputs`, select `Ticket.n_chars` and return it.
3. In `drift.py: drift_report`, loop over `("n_tokens", "oov_rate", "team_conf", "n_chars")`, skipping a key missing from `reference` so old reference files still work.
4. Add a unit test in `tests/unit/test_drift.py` with synthetic data.

**Expected.** With `rng = np.random.default_rng(42)`, reference `rng.normal(60, 15, 500)` and then live `rng.normal(75, 15, 500)`: D = 0.422, p ≈ 0, status red. The report now has 5 indicators. Run `make train` to refresh `reference.json`.

### Exercise 5: SQL for reviews per reviewer

**Task.** After `make seed`, write:
```sql
SELECT reviewer, COUNT(*) AS n,
       ROUND(AVG(CASE WHEN action = 'override' THEN 1.0 ELSE 0.0 END), 2) AS override_rate
FROM reviews GROUP BY reviewer ORDER BY n DESC;
```
Run it with `.venv/bin/python -c "import sqlite3; print(sqlite3.connect('sanket.db').execute('''<query>''').fetchall())"`. Bonus: add it to `sanket/sql/metrics.sql` as `-- name: reviews_per_reviewer`.

**Expected.** `[('sim-reviewer', 12, 0.83)]`: the seed's simulated reviewer handled 12 tickets and changed 10. Then review one ticket in the dashboard as "me" and run it again: a second row appears.

---

## 12. Five-day study plan (2 hours a day)

**Day 1 — the story and the data.**
Read `EXPLAIN_LIKE_IM_5.md` (15 min). Say the 30-second pitch out loud five times (15 min). Read sections 1 to 3.1 of this guide (40 min). Open `pii.py` and do the Luhn example by hand (20 min). Run `make setup data train seed serve` and click every chip (30 min).

**Day 2 — the model.**
Sections 3.2, 3.3, 4.1 to 4.8 (60 min), with paper for every worked example. Open `baseline.py` and `decide.py` and explain each function aloud (30 min). Exercise 2 (30 min).

**Day 3 — review, monitor, retrain, API.**
Sections 3.4 to 3.7 and 4.9 to 4.14 (50 min). Read `review.py`, `drift.py: psi` and `retrain.py: gate` (30 min). Exercises 1 and 5 (40 min).

**Day 4 — results, honesty, questions.**
Sections 5 to 8 (40 min). Practise the weakness table out loud (20 min). Answer questions Q1 to Q66 aloud, mark the ones you stumble on, re-read those parts (60 min).

**Day 5 — demo and mock interview.**
Exercises 3 and 4 (40 min). Open the Tech Mahindra links in section 2 and write one sentence per page (20 min). Rehearse the demo with a timer three times, once in Replay mode (30 min). Timed mock: someone picks 10 random questions plus "walk me through your project"; record yourself and listen back (30 min).

---

## 13. Company sheet

**What you can say (public sources only).** Read every link in section 2 first. Then connect, in your own words, only what the pages actually say:

- If the service-desk paper describes AI-assisted support: "Triage is the first step of a service desk: classify, route, escalate. SANKET is a small, honest version of that step."
- If the contact-centre case study is about a bank or complaint handling: "Banking complaints are the data I used."
- If the agentic-banking paper or the Orion release talks about guardrails or human oversight: "SANKET has a human in the loop, a promote gate and an override log, so I have built those ideas in miniature."
- If the VerifAI page is about validating AI: "My three audit gates and model cards are the same idea at project scale."
- If the Project Indus page talks about Indian languages: "My Hinglish stress test shows exactly why that work matters: my English model sends 26 of 60 Hinglish tickets to a person."

Never say "Tech Mahindra uses X internally" or "your platform does Y" unless the page says it.

**Five questions to ask the interviewer.**

1. "In your support or service-desk projects, how do teams decide when a model's answer goes straight through and when a person reviews it?"
2. "How do you handle Indian-language and code-mixed text, like Hinglish, in client projects?"
3. "What does monitoring look like after an AI model goes live in a client project, and who acts on alerts?"
4. "For a new AI engineer in Digital Catalyst, what does the first three months of work usually look like?"
5. "How do your teams test and validate AI components before release?"
