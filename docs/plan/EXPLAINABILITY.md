# EXPLAINABILITY — one minute per component

Read by B4 (text for the stage cards) and D1 (expands each entry in the interview guide).
Rule for both: no term may appear that is not defined in `docs/GLOSSARY.md`.
Numbers in square brackets are filled in from model cards, never guessed.

## 1. Intake and Clean — `sanket/pipeline/clean.py`, `pii.py`, `quality.py`
Pipeline cards: **Ingest**, **Clean**.
**One minute.** "Before the model sees a complaint I do two things. First I check it is usable: not empty,
not too long, contains letters. Second I remove personal data: emails, phone numbers, card numbers and
account numbers become placeholders like [CARD]. For cards I do not trust the pattern alone: a 16-digit
number is only treated as a card if it passes the Luhn checksum, the same check banks use, so an order
number is not redacted by mistake. Only the cleaned text is stored. The same clean function runs when I
train and when I serve, so the model never sees text in production that was prepared differently from its
training text. For the training files there is a separate quality step that fails loudly on missing
values, duplicates, unknown labels or rows shared between splits."
**Concepts.** Regular expressions; Luhn algorithm (double every second digit from the right, sum, mod 10);
train/serve skew; data-quality checks; data minimisation.
**Open and show.** `pii.py: redact`, `luhn_ok`. **Why not** an ML entity recogniser: heavier, cannot be
verified by reading it, and the patterns here are regular.

## 2. Classify — `sanket/models/baseline.py` (and `sanket/models/nn/net.py` as the challenger)
Pipeline card: **Classify**.
**One minute.** "The model turns the text into numbers and the numbers into 77 probabilities. TF-IDF
gives each word and short character group a score: high if it is frequent in this message and rare in
general. Logistic regression holds one weight per word per intent. It multiplies scores by weights, adds
them up, and softmax turns the 77 totals into probabilities that sum to one. I also built a small PyTorch
network: it looks up a 64-number vector for each word, averages them, and passes the average through two
layers. On my test set the baseline scores [x] and the network [y], at [a] ms versus [b] ms. I serve the
baseline because [measured reason], and I report both."
**Concepts.** Bag of words, TF-IDF formula with a 3-word worked example; dot product; softmax;
cross-entropy loss; regularisation (C); embeddings; mean pooling; ReLU; overfitting and early stopping;
macro-F1 versus accuracy; ONNX as a portable model file.
**Open and show.** `baseline.py: predict_proba`; `net.py: IntentNet.forward` (under 15 lines).
**Why not** a transformer: no GPU, 100x the size, cannot be hosted free, and the candidate could not explain attention honestly.

## 3. Explain and Route — `sanket/routing/explain.py`, `decide.py`, `sanket/taxonomy.yaml`
Pipeline cards: **Explain**, **Route**.
**One minute.** "For a linear model the explanation is exact. The score for an intent is a sum of
weight times TF-IDF value, one term per word, so I show the five largest terms. Then routing. The data has
77 intents; a table maps each intent to one of 7 teams and to an urgency. The probability of a team is
the sum of the probabilities of its intents. If the best team has less than [tau_team] probability, or
too many words are unknown to the model, the ticket goes to a human. A ticket is marked urgent when the
summed probability of the high-urgency intents passes [tau_high]. I chose that threshold on validation
data to catch at least 97% of urgent tickets, accepting some false alarms, because missing a fraud report
costs more than a wasted look."
**Concepts.** Additive explanations; probabilities of disjoint events add; confidence threshold;
precision versus recall; coverage versus accuracy; cost of errors; calibration (do 0.9 predictions come true 90% of the time).
**Open and show.** `decide.py: decide` (pure function, about 30 lines); `taxonomy.yaml`.
**Why not** SHAP/LIME: approximate and slow; unnecessary when the model is linear. **Why not** a learned
urgency model: the public data has no urgency labels; the rubric is mine and I say so.

## 4. Review — `sanket/review.py`, table `reviews`
Pipeline card: **Review**.
**One minute.** "Tickets the model is unsure about wait in a queue, urgent first, then oldest. A person
confirms the prediction or picks the right intent. The decision is saved with who, when and a note. A
unique constraint and a transaction make sure two people cannot both decide the same ticket: the second
gets a clear 'already reviewed' answer. These rows are the override log and also the training data for the
next model. If the intent was right but the reviewer disagrees with the urgency, that is a sign the table
needs changing, not the model."
**Concepts.** Human in the loop; audit trail; primary and foreign keys; unique constraint; transaction
and race condition; HTTP 409; ORDER BY as a priority queue; selection bias (only uncertain tickets get reviewed).
**Open and show.** `review.py: save_review`; `sql/metrics.sql` (override rate per team: JOIN + GROUP BY).

## 5. Monitor — `sanket/monitoring/drift.py`
Pipeline card: **Monitor**.
**One minute.** "A model is trained on yesterday's messages. If today's look different it can be wrong
without knowing. True labels arrive late, so I watch things I can measure now: message length, the share
of unknown words, the model's confidence, and the mix of predicted teams. PSI puts both periods into the
same bins and sums (actual − expected) x ln(actual / expected): under 0.1 is stable, over 0.25 is a real
shift. The KS test sorts both samples and finds the largest gap between their cumulative curves. I wrote
both in NumPy and checked KS against SciPy in a test. I also track the override rate, which is the
closest thing to live accuracy. Drift is a reason to look, not proof the model is wrong."
**Concepts.** Data drift versus concept drift; histogram and bins; PSI with a 3-bin worked example;
empirical CDF; KS statistic and p-value in plain words; delayed labels; minimum sample size.
**Open and show.** `drift.py: psi` (about 10 lines), `ks_2samp` (about 15 lines).

## 6. Retrain gate — `sanket/retrain.py`, `artifacts/registry.json`
Shown as the return arrow from Monitor to Classify and in the Model panel.
**One minute.** "Retraining adds the human-corrected tickets to the training set and fits a new model
with the same code. Then the gate: the new model is scored on a test set that neither model has ever
trained on. It replaces the live model only if its macro-F1 and its urgent-ticket recall are not worse
than the current model's, within a small tolerance. Either way the decision and the numbers are written
to a registry file. To prove the gate works I retrain with 30% of labels deliberately wrong; the gate
rejects it and a test checks that."
**Concepts.** Champion and challenger; frozen hold-out set; regression test for models; tolerance for
noise; reproducibility (seed, versioned artifacts); limit: reusing one test set many times slowly overfits to it.
**Open and show.** `retrain.py: gate` (about 20 lines); `registry.json`.

## Surfaces
**REST API — `sanket/api/`, `sanket/service.py`.** "One POST runs clean, classify, explain and route,
stores the result and returns every stage's output and time, so the page can show the pipeline. Resources
are nouns (tickets, reviews), verbs are HTTP methods, and status codes mean something: 201 created, 409
conflict, 422 invalid input." Concepts: REST, JSON schema validation, status codes, idempotency, CORS.
**Dashboard — `web/src/`.** "One page. Seven cards in a row, one per stage. Clicking a card shows what
it does, why, the real code, and this ticket's data. If the free server is asleep the page switches to
recorded responses and says so." Concepts: component, state, fetch, fallback, honest labelling.

## Whole-system sentence (30 seconds)
"SANKET reads a bank complaint, hides personal data, predicts the intent with a simple model I can
explain word by word, routes it to a team with an urgency, asks a human when unsure, logs every
correction, watches for drift, and only replaces its model when a frozen test says the new one is not worse."
