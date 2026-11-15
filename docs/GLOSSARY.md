# Glossary

Every technical word used in the SANKET docs, the dashboard and the stage cards.
Each entry has one plain sentence and one example from this project.
Terms are in alphabetical order. If you meet a word that is not here, it is a bug in the docs.

---

**Ablation.** Removing or swapping one part of a system to see how much that part matters.
*Here:* B2 trained a model that predicts the 7 teams directly and compared it with summing intent probabilities (test team accuracy 0.9636 against 0.9708; `docs/EXPERIMENTS.md`).

**Accuracy.** The share of predictions that are right.
*Here:* intent accuracy on the test set is 0.900, which means 9 in 10 test messages got the right intent.

**Adam.** A popular rule for nudging a neural network's weights during training; it adapts the step size for each weight.
*Here:* `sanket/models/nn/train.py` trains `IntentNet` with Adam at learning rate 0.002.

**Additive explanation.** An explanation where the parts add up exactly to the score.
*Here:* for the linear model, the term contributions plus the intercept add up to the intent's raw score (`baseline.py: explain`).

**Agentic AI.** Software where an AI system takes several steps on its own (calls tools, makes decisions) towards a goal.
*Here:* not used in SANKET. The word appears only in the company sheet, because Tech Mahindra's public material uses it.

**AI coding agent.** An AI model that writes and edits code when a person gives it tasks.
*Here:* SANKET was planned and built with several AI coding agents under the candidate's direction (see the interview guide, question on AI tools).

**Amber / green / red.** Traffic-light labels for drift: green is stable, amber is worth a look, red is a real shift.
*Here:* PSI under 0.1 is green, 0.1 to 0.25 amber, above 0.25 red (`drift.py: psi_status`).

**API (Application Programming Interface).** A fixed set of requests one program can send to another, with fixed answers.
*Here:* the dashboard talks to the Python back end only through the REST API in `sanket/api/`.

**Artifact.** A file produced by training that the running system loads.
*Here:* `artifacts/models/v1/model.joblib`, `thresholds.json`, `card.json`, and `artifacts/nn/model.onnx`.

**Audit / audit gate.** A review by a separate agent that tries to break the work, writes failing tests for what it finds, and blocks until fixed.
*Here:* Q1 (data), Q2 (model) and Q3 (system) audits; their findings and fixes are in `docs/AUDIT_LOG.md`.

**Auto-routed.** A ticket the system sends straight to a team without a person checking it.
*Here:* 94.2% of test tickets are auto-routed, and 99.2% of those go to the right team (model card).

**Bag of words.** Treating a text as a set of word counts and ignoring word order.
*Here:* TF-IDF is a weighted bag of words; "card not working" and "working card not" look the same to it, except for 2-word terms.

**Baseline.** The simple model you build first so that fancier models have something to beat.
*Here:* TF-IDF plus logistic regression in `sanket/models/baseline.py`. It also turned out to be the best model, so it serves.

**Best-ever check.** The retrain gate also compares a candidate with the best model ever promoted, so many small "within tolerance" losses cannot pile up (a "ratchet").
*Here:* `retrain.py: best_ever_problems`, tolerance 0.01.

**Batch.** A group of examples processed together.
*Here:* the neural network trains on batches of 64 messages; throughput in `docs/bench.md` is measured with batches of 64.

**Big-O.** A way to say how the work grows with input size, ignoring constant factors.
*Here:* the Luhn check is O(n) in the number of digits; sorting for the KS test is O(n log n).

**Bin.** One interval of values when you group numbers into a histogram.
*Here:* PSI splits message lengths into 10 bins with equal numbers of reference tickets in each (`drift.py: bin_edges`).

**Bootstrap confidence interval.** Resample the test set many times with replacement, recompute a score each time, and see the range where most results fall.
*Here:* Q2 found the baseline beats the network on macro-F1 by +0.0138, with a 95% interval of +0.0042 to +0.0242, so the gap is real.

**Calibration.** Whether a model's confidence matches how often it is right. A calibrated model that says 0.9 is right about 90% of the time.
*Here:* before the fix the model said about 0.74 on average while being right 90% of the time (it was under-confident).

**Champion / challenger.** The champion is the model in service; a challenger is a new model that must prove it is not worse before it replaces the champion.
*Here:* `artifacts/registry.json` names the champion (`v1`); `sanket/retrain.py` builds challengers.

**Character n-gram.** A short run of letters inside a word, such as "car" or "ard" from "card".
*Here:* the baseline uses 2 to 5 letter pieces; the dashboard shows them with a leading `~`, like `~virt`.

**CI (Continuous Integration).** A server that runs the tests automatically on every push.
*Here:* `.github/workflows/ci.yml` runs lint and tests for Python and builds and tests the web app.

**Class.** One of the possible answers a classifier can give.
*Here:* there are 77 classes, one per intent.

**Classifier.** A model that picks a class for an input.
*Here:* `sanket/models/base.py` defines the `Classifier` interface: anything with `predict_proba` that returns 77 probabilities per text.

**Clean (stage).** Mask personal data, then normalise the text.
*Here:* `sanket/pipeline/clean.py: clean`, the same function at training and serving time.

**Coefficient / weight.** A number the model learned that says how much one feature pushes towards one class.
*Here:* the baseline has one weight per term per intent: a 77 by 20,672 table.

**Component (web).** A reusable piece of a web page written as a function.
*Here:* `web/src/Pipeline.jsx` is the component that draws the seven stage cards.

**Concept drift.** The link between input and correct answer changes (the same words now mean a different intent).
*Here:* SANKET cannot see this directly; the override rate is the closest signal.

**Container / Docker.** A packaged mini-computer image that holds the app and everything it needs, so it runs the same anywhere.
*Here:* the `Dockerfile` builds an image with the API, the model files and no PyTorch. Not verified here: there was no Docker daemon in the sandbox.

**CORS (Cross-Origin Resource Sharing).** A browser rule: a page from one web address may call an API on another address only if the API says that address is allowed.
*Here:* `SANKET_CORS_ORIGINS` lists the dashboard's address; an unknown origin is refused (Q3 checked).

**Cosine similarity.** How similar two vectors point, from 0 (unrelated) to 1 (same direction).
*Here:* two texts with TF-IDF cosine above 0.99 are treated as copies; 351 test rows have a train text above 0.9 (`docs/data_card.md`).

**Coverage.** The share of tickets the system handles alone at a given confidence cut-off.
*Here:* at team confidence 0.7, coverage on test is 94.4% (model card, coverage table).

**Cross-entropy (log-loss, NLL).** The training penalty: minus the log of the probability the model gave to the right answer. Confident and wrong costs a lot.
*Here:* if the right intent got 0.659, the loss is −ln(0.659) = 0.42; if it got 0.090, the loss is 2.41.

**CSV.** A plain text table with commas between columns.
*Here:* `data/splits/train.csv` with columns `row_id,text,intent`.

**Contract / handoff note / orchestrator.** The contract (`docs/plan/CONTRACTS.md`) fixes file layout, data shapes and API shapes that all agents share; each agent ends with a short handoff note; the orchestrator is the coordinating agent that assigned the work and made the commits.
*Here:* `docs/handoffs/B0.md` ... `Q3.md`.

**Data card.** A short document that says where data came from, how it was split and what is wrong with it.
*Here:* `docs/data_card.md`.

**Data drift.** The inputs arriving now look different from the data the model was tuned on.
*Here:* the Hinglish surge makes the unfamiliar-word rate jump; the oov_rate KS indicator turns red.

**Data minimisation.** Keep only the data you need.
*Here:* raw ticket text is never stored; only the cleaned, redacted text is.

**Data-quality check.** Code that refuses bad data with a clear message before training.
*Here:* `sanket/pipeline/quality.py: check_frame` and `check_splits`.

**Dataclass.** A Python class that mainly holds named fields.
*Here:* `Thresholds`, `Decision` (`decide.py`) and `CleanResult` (`clean.py`).

**Decision (auto / human).** Whether the ticket goes straight to the team or waits for a person.
*Here:* `decide.py` returns `decision` and a `reason`: `ok`, `low_confidence` or `unfamiliar_words`.

**Dot product.** Multiply two lists of numbers position by position and add the results.
*Here:* an intent's raw score is the dot product of the TF-IDF vector and that intent's weights, plus the intercept.

**Dropout.** During training, randomly hide some numbers so the network cannot lean on any single one.
*Here:* `IntentNet` uses dropout 0.3 on the averaged vector.

**E2E test (end-to-end).** A test that drives the real web page in a browser like a user would.
*Here:* `web/e2e/replay.spec.js` uses Playwright.

**Early stopping.** Stop training when the score on validation data stops improving.
*Here:* the network stops after 6 epochs without a better validation macro-F1.

**ECE (Expected Calibration Error).** Put predictions into confidence buckets, compare average confidence with accuracy in each bucket, and take the weighted average gap.
*Here:* test ECE fell from 0.160 to 0.0146 after temperature scaling (`docs/AUDIT_LOG.md`, model card).

**Embedding.** A short list of numbers (a vector) learned for each word, so similar words get similar vectors.
*Here:* `IntentNet` learns a 64-number vector per word id.

**Empirical CDF.** For a sample, the share of values at or below each point.
*Here:* the KS test compares the empirical CDFs of reference and live message lengths.

**Endpoint.** One URL plus method on an API.
*Here:* `POST /api/tickets` runs the whole pipeline on one message.

**Entity recogniser (NER).** A trained model that finds names, places and other entities in text.
*Here:* not used; patterns were chosen because they can be read and tested line by line.

**Environment variable.** A setting passed to a program from outside its code.
*Here:* every setting in `sanket/config.py` can be changed with `SANKET_<NAME>`, for example `SANKET_DB_URL`.

**Epoch.** One full pass over the training data.
*Here:* the chosen network trained for 31 epochs.

**Explain (stage).** Show the words that pushed the model to its answer.
*Here:* `baseline.py: explain` returns the five largest weight × TF-IDF terms.

**F1 / macro-F1.** F1 is the balance of precision and recall for one class. Macro-F1 is the plain average of F1 over all classes, so small classes count as much as big ones.
*Here:* test macro-F1 is 0.900 for the baseline and 0.8865 for the network.

**FastAPI.** A Python library for writing web APIs with typed inputs and outputs.
*Here:* `sanket/api/app.py`.

**Feature.** A number that describes the input, which the model uses.
*Here:* each TF-IDF term score is a feature; the baseline has 20,672 of them.

**Fixture.** A saved example of an API response used to fix its shape.
*Here:* `fixtures/*.json`; a test checks the real API matches them.

**float32 / float64.** Ways to store decimal numbers with about 7 or about 16 significant digits.
*Here:* weights are stored as float32 to halve the file; this cost 0.0000 macro-F1.

**Foreign key.** A column that must point at an existing row in another table.
*Here:* `predictions.ticket_id` must be an id in `tickets`.

**Frozen test set.** Data kept aside and never used for training or choosing settings, only for the final score.
*Here:* `data/splits/test.csv`, the official Banking77 test file, 3,080 rows.

**Git / commit.** Git records versions of files; a commit is one saved version with a message.
*Here:* the project history is in `.git`; the orchestrator made the commits.

**Git LFS (Large File Storage).** A Git add-on that stores big binary files outside the normal history.
*Here:* Hugging Face needs it for `model.joblib` and `model.onnx` (`docs/DEPLOY.md`).

**Hash map (dictionary).** A structure that finds a value by key in about constant time.
*Here:* the vocabulary that maps a word to its column number; `oov_rate` checks each word against a set.

**Hashing trick.** Turn a string into a number with a hash function and take the remainder, so unseen strings still get a slot.
*Here:* the network's tokenizer hashes each 3-letter piece into one of 8,192 buckets.

**Heap.** A structure that gives you the largest (or smallest) items fast.
*Here:* `heapq.nlargest` picks the top-k terms in `explain`.

**Hinglish.** Hindi written in Latin letters, often mixed with English words.
*Here:* `data/stress/hinglish.csv`, 60 hand-written rows, used only to measure failure.

**Hold-out set.** Data held back from training to measure the model fairly.
*Here:* both `val` and `test` are hold-out sets; only `val` is used to choose settings.

**HTTP status code.** A number in an API answer that says what happened.
*Here:* 200 OK, 201 created, 404 not found, 409 conflict (already reviewed), 413 body too large, 422 invalid input, 500 server error.

**Hugging Face Space.** A free hosting service for small apps; one option runs a Docker image.
*Here:* the planned home for the API (`docs/DEPLOY.md`).

**Human in the loop.** A person checks the cases the machine is unsure about.
*Here:* the review queue.

**Idempotent.** Doing it twice gives the same result as doing it once.
*Here:* `clean(clean(x)) == clean(x)`, tested in `tests/unit/test_clean.py`.

**IDF (Inverse Document Frequency).** A score that is high for words that appear in few messages and low for common ones.
*Here:* "card" appears in many tickets, so its IDF is low; "swallowed" is rare, so it is high.

**Index (database).** A sorted lookup structure that makes searches on a column fast.
*Here:* `tickets` has an index on `(status, created_at)` so the review queue query is quick.

**Inference.** Using a trained model to make a prediction.
*Here:* about 0.82 ms per ticket for the baseline at p50, including cleaning (`docs/bench.md`).

**Intent.** What the customer wants, as one of 77 labels from Banking77.
*Here:* `card_arrival`, `lost_or_stolen_card`, `exchange_rate`, ...

**Intercept.** A fixed number added to a class's score regardless of the words.
*Here:* each of the 77 intents has one intercept in `baseline.py`.

**JSON.** A text format for nested data with keys and values.
*Here:* every API answer and `card.json`.

**joblib / pickle.** Python ways to save objects to a file. Loading a pickle can run code, so only load files you made.
*Here:* `model.joblib` is only ever loaded from `artifacts/`.

**KS test (Kolmogorov-Smirnov).** Compares two samples by the largest gap between their empirical CDFs (called D), and gives a p-value.
*Here:* `drift.py: ks_2samp`, written in NumPy and checked against SciPy in a test.

**Label noise.** Training labels that are wrong.
*Here:* Q1 disagreed with 12 of 150 sampled train labels (8%).

**Latency.** Time to answer one request.
*Here:* `POST /tickets` p50 9.9 ms, p95 12.0 ms over 200 requests (B4 handoff).

**Leakage.** When information from the test set sneaks into training, so the score looks better than it is.
*Here:* 68 train rows nearly identical to test rows were removed (`split.py`).

**Linear model.** A model whose score is a weighted sum of features.
*Here:* the baseline.

**Lint / ruff.** A lint tool reads code and flags style problems and likely bugs; `ruff` is the one used here.
*Here:* `make lint`.

**Learning rate.** How big a step the training takes each time it adjusts the weights.
*Here:* 0.002 for the network (`docs/EXPERIMENTS.md`).

**Linear layer.** Multiply a vector by a weight matrix and add a bias: the basic building block of a neural network.
*Here:* `IntentNet` has two: 64 → 128 and 128 → 77.

**Load balancer.** A front door that spreads requests across several copies of a service.
*Here:* not used; it is part of the answer to "how would you handle 10,000 tickets a minute?".

**Load test.** Sending many requests at once to see how latency and errors change.
*Here:* Q3 ran 1, 8 and 32 parallel clients: p95 12.1 ms, 160.4 ms and 719.9 ms, zero errors in 1,400 requests.

**Logistic regression.** A linear model that turns weighted sums into probabilities with softmax (or sigmoid for two classes).
*Here:* multinomial logistic regression over 77 intents.

**Logit (raw score).** The score of a class before softmax.
*Here:* `baseline.py: scores`.

**Luhn check.** A checksum on card numbers: from the right, double every second digit, subtract 9 if over 9, add everything; valid if the total ends in 0.
*Here:* `pii.py: luhn_ok`. A 16-digit number is masked as `[CARD]` only if it passes.

**Makefile / make target.** A file of named shell recipes; `make train` runs the `train` recipe.
*Here:* `Makefile`.

**Mean pooling.** Average a list of vectors into one vector.
*Here:* `IntentNet.forward` averages the word vectors, ignoring padding.

**Message queue.** A buffer where incoming work waits until a worker is free, so bursts do not overload a service.
*Here:* not used; listed under what production would need.

**Middleware.** Code that runs on every request before the endpoint.
*Here:* `limit_body` in `api/app.py` refuses bodies over 20 kB (413).

**Model card.** A short file that says what a model is, how it was tested, its numbers and its limits.
*Here:* `artifacts/models/v1/card.json` and `artifacts/nn/card.json`.

**Mojibake.** Garbled text from reading bytes in the wrong encoding, like "Ã©".
*Here:* `check_frame` refuses rows with it.

**Near-duplicate.** Two texts that are almost the same sentence.
*Here:* 351 of 3,080 test rows (11.4%) have a train text with cosine above 0.9.

**Neural network.** A model made of layers of weighted sums with simple non-linear steps between them.
*Here:* `IntentNet` in `sanket/models/nn/net.py`.

**NFKC.** A Unicode rule that turns look-alike characters into one standard form, such as full-width "４" into "4".
*Here:* the first step of `clean`.

**Normalisation (text).** Making text consistent: one kind of space, lower case, standard characters.
*Here:* `clean` lower-cases everything except placeholders like `[CARD]`.

**NumPy / pandas / scikit-learn.** Python libraries for arrays, tables and classic machine learning.
*Here:* drift maths (NumPy), data pipeline (pandas), baseline (scikit-learn).

**ONNX / onnxruntime.** ONNX is a portable model file format; onnxruntime runs it without PyTorch.
*Here:* `artifacts/nn/model.onnx` lets the API run the network without installing PyTorch.

**OOV rate (unfamiliar words).** OOV means out of vocabulary: the share of words in a message the model never saw in training.
*Here:* above 0.20 unknown words, a ticket goes to a person unless the team confidence is at least 0.97.

**Overfitting.** The model memorises training data and does worse on new data.
*Here:* the network reached about 0.99 training accuracy but 0.882 validation macro-F1; early stopping limits this.

**Override.** A reviewer replaces the model's intent with a different one.
*Here:* `action=override` in `POST /tickets/{id}/review`.

**Override rate.** The share of reviewed tickets where the person changed the answer.
*Here:* computed per team by the SQL in `sanket/sql/metrics.sql`.

**p50 / p95.** The median time, and the time that 95% of requests beat.
*Here:* baseline p50 0.82 ms, p95 1.02 ms (`docs/bench.md`).

**p-value.** If there were truly no difference, how likely a gap at least this big would be by chance. Small means "probably a real difference".
*Here:* KS is amber or red only when p < 0.01.

**Padding.** Filler ids added so all inputs have the same length.
*Here:* id 0 in the network's tokenizer; it is zeroed out before averaging.

**Parity test.** A test that two versions of the same model give the same output.
*Here:* PyTorch and ONNX outputs agree within 1e-4 on 200 validation texts.

**PII (Personally Identifiable Information).** Data that can identify a person: email, phone, card number, account number, Aadhaar, PAN, UPI id.
*Here:* masked by `pii.py: redact` before anything is stored.

**PII probe.** A hand-written file of messages with personal data in many formats, and the expected masked text for each.
*Here:* `data/stress/pii_probe.csv`; `tests/unit/test_pii.py` checks every row.

**Placeholder.** A token that replaces masked data.
*Here:* `[EMAIL]`, `[UPI]`, `[PHONE]`, `[CARD]`, `[AADHAAR]`, `[PAN]`, `[ACCOUNT]`.

**Playwright.** A tool that drives a real browser for tests and screenshots.
*Here:* `web/e2e/` and the screenshots in `docs/screens/`.

**Precision.** Of the tickets flagged as X, the share that really are X.
*Here:* high-urgency precision on test is 0.915.

**Primary key.** The column that uniquely names each row.
*Here:* `id` in each of the four tables.

**Probability.** A number from 0 to 1 for how likely something is; the 77 intent probabilities add up to 1.
*Here:* `predict_proba` returns them.

**Protocol (interface).** A description of the methods a class must have, without saying how.
*Here:* `Classifier` in `models/base.py`; `BaselineModel` and `OnnxModel` both fit it.

**PSI (Population Stability Index).** Sum over bins of (live share − reference share) × ln(live share / reference share).
*Here:* used for the predicted-team mix; under 0.1 stable, over 0.25 a real shift.

**Pydantic / schema.** Pydantic checks that data has the right fields and types; a schema is that description.
*Here:* `sanket/schemas.py`; a bad request gets a 422 automatically.

**PyTorch.** A Python library for building and training neural networks.
*Here:* used only for training `IntentNet`; the server never imports it.

**Quantile.** The value below which a given share of the data lies (the 0.5 quantile is the median).
*Here:* `oov_max` is the 99th percentile (0.99 quantile) of validation OOV rates.

**Race condition.** Two actions at the same time interfere, and the result depends on who is first.
*Here:* two reviewers saving the same ticket; the conditional update plus unique constraint lets only one win.

**React / Vite.** React builds web pages from components; Vite is the tool that serves and bundles them.
*Here:* `web/`.

**Rate limit.** A cap on how many requests one client may send per minute.
*Here:* not built; the 2,000-character limit, 20 kB body limit and 5,000-ticket cap are the current abuse guards.

**Recall.** Of the tickets that truly are X, the share the system caught.
*Here:* high-urgency recall on test is 0.983.

**Redaction.** Replacing sensitive text with a placeholder.
*Here:* `pii.py: redact`.

**Registry.** A file that records every model version and whether it was promoted or rejected, with reasons.
*Here:* `artifacts/registry.json`.

**Regular expression (regex).** A pattern language for finding text.
*Here:* `EMAIL_RE`, `CARD_RUN_RE` and the phone patterns in `pii.py`.

**Regularisation (C).** A brake that stops weights growing too large, which reduces overfitting. In scikit-learn a smaller C means a stronger brake.
*Here:* C = 5 was chosen on validation data.

**ReLU.** A simple step inside a network: keep positive numbers, turn negatives into 0.
*Here:* between the two linear layers of `IntentNet`.

**Replay mode.** The dashboard shows recorded real API answers when the live API cannot be reached, and says so with an amber badge.
*Here:* `web/public/replay.json`, made by `make replay`.

**REST.** A style of web API where URLs name things (tickets, reviews) and HTTP methods (GET, POST) are the actions.
*Here:* `GET /api/tickets/{id}`, `POST /api/tickets/{id}/review`.

**Retrain gate (promote gate).** Rules a new model must pass before it replaces the champion.
*Here:* `retrain.py: gate` plus label sanity, val, best-ever and size checks.

**Route (stage).** Turn intent probabilities into a team, an urgency and auto-or-human.
*Here:* `sanket/routing/decide.py: decide`.

**Rubric.** A table of rules a person wrote.
*Here:* `taxonomy.yaml` maps each intent to a team and urgency. It is this project's rubric, not dataset labels.

**Seed.** A fixed starting number for randomness so results repeat exactly. Also: filling a database with demo data.
*Here:* seed 42 everywhere; `make seed` fills the database with 400 demo tickets.

**Shortcut (data artefact).** A feature that predicts the label in this dataset for an accidental reason.
*Here:* the token "1" (as in "£1 charge") appears in 58 of 114 training rows of `extra_charge_on_statement`.

**Selection bias.** A sample that is not representative because of how it was chosen.
*Here:* only uncertain tickets are reviewed, so the review log says little about easy tickets.

**Silent wrong-team.** A ticket auto-routed (no person) to the wrong team. The worst kind of error, because nobody sees it.
*Here:* 0.55% of the 10%-typo test set; 0 of 60 Hinglish rows.

**Slack (tolerance).** How much worse a candidate may be and still pass, to allow for random noise.
*Here:* macro-F1 0.005 and high-urgency recall 0.01 on test (`retrain.py: gate`).

**Softmax.** Turns a list of scores into probabilities: raise e to each score and divide by the total.
*Here:* scores 2.0, 1.0, 0.1 become 0.659, 0.242, 0.099.

**Sparse matrix.** A table that stores only the non-zero numbers.
*Here:* the TF-IDF matrix: a short message uses a handful of the 20,672 columns.

**Split (train / val / stream / test).** Separate parts of the data: train to learn, val to choose settings, stream to feed the live demo, test for the final score.
*Here:* 6,946 / 1,489 / 1,489 / 3,080 rows (`docs/data_card.md`).

**SQL / SQLite / SQLAlchemy.** SQL is the language for querying tables; SQLite is a database in one file; SQLAlchemy is the Python library that talks to it.
*Here:* `sanket/db.py` and `sanket/sql/metrics.sql`.

**Stratified split.** A split that keeps each class's share the same in every part.
*Here:* `split.py` stratifies by intent.

**Stress set.** Hard test data built to find where the model breaks.
*Here:* the Hinglish set (60 rows) and the typo set (test with 10% character noise).

**Surrogate (lone).** A broken half of an emoji-style character that cannot be saved as valid text.
*Here:* `unify_spaces` drops it; `validate_text` refuses text that still cannot be encoded (422).

**Team.** One of 7 groups that handle tickets: CARDS, FRAUD_SECURITY, CARD_PAYMENTS, TRANSFERS_TOPUPS, CASH_ATM, FEES_FX, ACCOUNT_KYC.
*Here:* from `taxonomy.yaml`, the project's rubric.

**Temperature scaling.** Divide all raw scores by one number T before softmax. T below 1 makes the model more confident; T above 1 less. T is fitted on validation data.
*Here:* T = 0.591 (`baseline.py: fit_temperature`).

**TF (term frequency).** How often a term appears in this message. "Sublinear" TF uses 1 + log(count) so repeats count less.
*Here:* both vectorisers use sublinear TF.

**TF-IDF.** TF × IDF: high for a term that is frequent in this message and rare overall.
*Here:* the baseline's features.

**Threshold.** A cut-off number that turns a probability into a yes or no.
*Here:* `tau_team` 0.70, `tau_high` 0.20, `oov_max` 0.20, `oov_conf` 0.97 (`thresholds.json`).

**Throughput.** How many items per second the system can process.
*Here:* 13,393 tickets per second for the baseline in batches of 64 (`docs/bench.md`).

**Token / tokenizer.** A token is one unit of text, usually a word; a tokenizer splits text into tokens and maps them to ids.
*Here:* `sanket/models/nn/tokenizer.py`: 0 = padding, 1 = unknown word.

**Top-5 coverage.** The share of new labels that are among the model's five most likely intents.
*Here:* the retrain gate rejects a batch below 0.75 (`retrain.py: label_sanity_problems`).

**Trace.** The list of stages one request went through, with time and output per stage.
*Here:* `POST /tickets` returns five trace steps: ingest, clean, classify, explain, route.

**Train/serve skew.** The model sees data prepared one way in training and another way in production.
*Here:* avoided by using the same `clean()` for both.

**Transaction.** A group of database changes that happen all together or not at all.
*Here:* saving a review and marking the ticket reviewed happen in one transaction.

**Transformer.** A large neural network design behind modern language models (BERT, GPT).
*Here:* not used, on purpose: no GPU, far larger, and harder to explain honestly.

**Unique constraint.** A database rule that no two rows may share a value in a column.
*Here:* `reviews.ticket_id` is unique, so a ticket has at most one review.

**Urgency.** high, medium or low.
*Here:* from the project's rubric in `taxonomy.yaml`; 9 intents are high.

**Uvicorn.** The small web server that runs a FastAPI app.
*Here:* `make serve`.

**Validation set.** Held-out data used to choose settings (thresholds, C, temperature).
*Here:* `data/splits/val.csv`, 1,489 rows.

**Vercel.** A hosting service for static web pages and front ends.
*Here:* the planned home for the dashboard.

**Vocabulary.** The list of terms the model knows.
*Here:* the word vectoriser's vocabulary decides what counts as an unfamiliar word.

**Verhoeff checksum.** A check-digit rule, stronger than Luhn, that Aadhaar numbers satisfy.
*Here:* `pii.py: verhoeff_ok`; a 12-digit number is masked as `[AADHAAR]` only if it passes.

**UPI id.** An Indian payment address like `name@okaxis`.
*Here:* masked as `[UPI]`; an ordinary email (with a dot after the @ part) stays `[EMAIL]`.

**WAL (Write-Ahead Log).** A SQLite mode that writes changes to a side file first, so reads and writes can overlap.
*Here:* turned on in `db.py`; Q3 checked that no PII reaches the `-wal` file.

**xfail (strict).** A pytest mark that says "this test is expected to fail". Strict means the suite breaks if it suddenly passes, so the mark must be removed when the bug is fixed.
*Here:* the auditors wrote strict xfails for each finding; one is left (`test_audit_q2.py`, PSI with a constant reference).

**XSS (cross-site scripting).** An attack where text containing a script runs in someone else's browser.
*Here:* Q3 submitted `<script>` tickets; the dashboard shows them as plain text.

**Zero-width character.** An invisible character that can hide inside a number to dodge a pattern.
*Here:* `unify_spaces` removes them before redaction.
