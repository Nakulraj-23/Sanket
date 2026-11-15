# Audit log (append-only)

## 2026-11-14 B1 fixes for Q1 findings
- Finding: PII hidden by formatting (card with double spaces, " - ", ".", "/"; dashed or Devanagari-digit phones; UK/US phones; `(at)` emails; lower-case IBAN; `ref <card>`).
- Evidence: 12 of 35 attack formats missed in `tests/data/test_audit_pii.py`; `clean` collapsed whitespace after `redact`.
- Fix: `pii.py` maps digits of any script to ASCII, allows separators between digit groups, finds the Luhn window inside a digit run, new phone/email/IBAN patterns; id exception kept for order/tracking/invoice/txn/awb only.
- Test: `test_audit_pii.py::test_formerly_missed`, `::test_masked`, `::test_not_redacted`, `tests/unit/test_pii.py::test_probe_file_all_rows_match`.

- Finding: a 10-digit amount starting 6-9 was masked as a phone.
- Evidence: `amount 6000000000` and `i paid 9812345678 rupees` became [PHONE].
- Fix: `_mask_phones` skips numbers right after rs/inr/amount/paid/currency sign or right before rupees/rs/inr.
- Test: `test_audit_pii.py::test_amount_not_a_phone`. Remaining risk: a real phone written right after the word "paid" is left unmasked.

- Finding: quality checks missed 8 of 13 corruptions (shuffled labels, test paraphrase in train, HTML/mojibake, raw PII, upper case, class cut to 5, repeated row_id, test rows dropped).
- Evidence: `test_audit_quality.py` strict xfails.
- Fix: `check_frame` requires clean(text)==text, no markup, unique row_id, train class floor 20; `check_splits` requires test = 3080 rows, unique ids across splits, no train text with TF-IDF cosine > 0.99 to a test text, 1-nearest-text label agreement of val/stream vs train >= 0.72 (clean 0.75, 10% shuffled 0.685).
- Test: `test_audit_quality.py::test_corruption_caught_after_fix[*]`, `tests/data/test_quality.py::test_uncleaned_text_fails`, `::test_duplicate_row_id_fails`.

- Finding: test paraphrases leak into train (near-duplicates).
- Evidence: 392 test rows had a train text with cosine > 0.9 (46 pairs >= 0.999); test is frozen.
- Fix: `split.py` drops the 68 train rows with cosine > 0.99 to a test text (1.0% of train); 0.9-0.99 pairs are too many to drop (351 test rows, 11.4%, remain), reported in docs/data_card.md.
- Test: `tests/data/test_split.py::test_row_counts_add_up`, `check_splits` leak check in `test_audit_quality.py`.

- Finding: `script=mixed` on 6 Latin-only Hinglish rows.
- Evidence: `test_audit_hinglish_rubric.py::test_hinglish_script_column_matches_characters` xfail.
- Fix: `hinglish.csv` script now computed from characters: roman 46, devanagari 10, mixed (Devanagari plus Latin) 4.
- Test: same test, xfail removed; `test_perturb_stress.py::test_hinglish_stress_file`.

## 2026-11-14 B1: stream split shuffled (Q2 point 4)
- Finding: `stream.csv` was sorted by row_id, so its first 500 rows looked like drift.
- Evidence: Q2 handoff point 4; the first rows covered few intents.
- Fix: `split.py` shuffles the stream with seed 42 after the stratified split; train, val and test are unchanged.
- Test: `tests/data/test_split.py::test_stream_is_shuffled_so_any_slice_is_representative`.

## B2 fixes after Q2 (2026-11-14)
- Finding: HIGH `predict_proba` rebuilt a 77 x 20,672 float64 matrix on every call; bench said the NN was about 125x faster.
- Fix: the matrix is built once in `BaselineModel.__init__`; outputs are identical. `make bench`: baseline p50 7.69 -> 0.82 ms, ONNX 0.055 ms, so about 15x.
- Test: `test_audit_q2.py::test_baseline_predict_has_no_per_call_matrix_copy` (xfail removed). B3 handoff sentence corrected.

- Finding: HIGH 200 reviews with all labels wrong were promoted; the sabotage demo only worked because it also flipped train.
- Fix: `label_sanity_problems` rejects if the champion disagrees with more than 30% of new reviews; the same gate also runs on frozen val; a best-ever macro-F1 check (0.01) stops slack ratcheting; `--sabotage` flips new rows only; `min_new` counts rows after dedup.
- Test: `test_audit_q2.py::test_retrain_rejects_poisoned_reviews` (xfail removed), `test_quality_gates.py` all-wrong, noisy, ratchet and duplicate cases.

- Finding: MED confidence under-stated (test ECE 0.160); tau_high 0.25 gave test high recall 0.9694.
- Fix: one temperature T = 0.591 fitted on val log-loss, stored in model.joblib and card; tau_team and tau_high re-picked on val (0.70, 0.20).
- Result (test): ECE 0.0146, auto share 94.2%, high recall 0.983, auto team accuracy 0.992. Caveat: T and thresholds share val. Test: `test_calibration_in_card`.

- Finding: MED the OOV rule sent 65% of 10%-typo tickets to a human, 45% of them needlessly.
- Fix: unknown words escalate only if team confidence < `oov_conf`. Q2's 0.8 was measured before calibration; after it, 0.8 gave 1.6% silent wrong-team on a val typo set, so `oov_conf` = 0.98 (smallest step on 0.8..0.98 with val-typo silent wrong-team under 1%).
- Result (test typos 10%): human 38.3%, silent wrong-team 0.55%. Hinglish: 27 of 60 (45%) go to a human, not all 60; 0 silent wrong-team, 1 silent wrong-intent. Clean test auto share 94.2%.
- Test: `test_routing.py::test_unfamiliar_words_alone_do_not_escalate_a_certain_team`.

## B2 second fix round after Q2 re-check (2026-11-15)
- Finding: HIGH the 30% champion-disagreement rule rejected honest reviews: on the 85 stream tickets the champion sends to a human, true labels disagree with it 56%.
- Fix: `label_sanity_problems` now requires at least 75% of new labels to be in the champion's top 5 intents. Honest human-routed batch 0.86, honest random 0.97, 30% noise 0.58 to 0.72, all wrong 0.05. Nearest-train-text agreement was tried first and could not separate honest hard tickets (0.29) from 30% noise on them (0.22).
- Val gate slack is 0.01 (val is half the size of test); the honest 85-ticket batch scored val F1 0.8914 vs 0.8981 and test 0.9003 -> 0.9052, so 0.005 on val only measured noise. Best-ever check and `--sabotage` (new rows only) kept.
- Tests: `test_quality_gates.py` accepts human-routed and random true labels, rejects all-wrong and 30% noise (both batch shapes, 3 seeds), promotes the human-routed batch end to end.

- Finding: MED `oov_conf` 0.98 was a hard-coded default.
- Fix: `train_baseline.choose_oov_conf` picks it on a typo copy of val (seed 1042): smallest human share with silent wrong-team under 1%. Chosen 0.97 (val typos: human 35.6%, silent wrong-team 0.94%); table stored in card.json and `oov_conf` in thresholds.json.
- Result (test, 10% typos): human 35.4%, silent wrong-team 0.55%; Hinglish 26 of 60 to a human, 0 silent wrong-team (n=60). Test: `test_oov_conf_is_selected_on_val_typos_and_stored`.

## 2026-11-15 B1: whitespace tricks in PII (Q3 HIGH)
- Finding: a card split by newlines or tabs was stored raw.
- Evidence: `tests/api/test_audit_q3.py` tab/newline test (was xfail).
- Fix: `pii.unify_spaces` turns any whitespace and zero-width characters into one space before `redact` and `clean`.
- Test: `tests/data/test_audit_pii.py::test_any_whitespace_between_groups`; the 35 earlier formats still pass.

## 2026-11-15 B1: lone surrogate (Q3 MED)
- Finding: an unpaired surrogate in input gave a 500 downstream.
- Evidence: `test_audit_q3.py::test_lone_surrogate_is_a_clean_error` (was xfail).
- Fix: `unify_spaces` drops surrogates, so `clean` output is always valid UTF-8.
- Test: `tests/data/test_audit_pii.py::test_lone_surrogate_is_dropped`.

## B2 fix after Q3 (2026-11-15)
- Finding: MED model card limit said Hinglish is "mostly sent to a human or misrouted"; measured (n=60): 26 sent to a human, 0 silently wrong team, 1 silently wrong intent, intent accuracy 0.65.
- Fix: sentence rewritten with those numbers and the small-sample caveat in `train_baseline.py`, `artifacts/models/v1/card.json`, `web/public/replay.json`, `docs/plan/PLAN.md`; the flaky wall-clock test in `test_audit_q2.py` now checks the cached matrix directly plus a best-of-3 relative bound of 3x.

## B4 fixes after Q3 (2026-11-15)
- Finding: HIGH review `note` and `reviewer` were stored and returned as typed (card, email, phone reached `reviews` and the WAL).
- Fix: `review.safe_text` joins lines and runs `redact` on both before anything is written or returned; note limit 1,000 characters.
- Result: card, email and phone in a note are gone from the response, the table and the db, -wal and -shm files. Test: `test_review_safety.py::test_note_and_reviewer_are_redacted_everywhere`.

- Finding: MED an empty or 5,000-character reviewer was accepted, so an override could be unattributable.
- Fix: reviewer must be 1 to 64 characters after trimming, else 422 (checked in `save_review`).
- Test: `test_bad_reviewer_is_422` (empty, spaces, 65 characters), `test_long_note_is_422`.

- Finding: MED the ticket cap deleted reviews with old tickets, and `channel: "seed"` from a client escaped the cap.
- Fix: the cap prunes only unreviewed, non-seed tickets; POST /tickets accepts channel `web` only (seed and scenario are set by code).
- Result: a reviewed ticket survives 15 later posts at cap 10; seed and scenario channels give 422. Tests: `test_cap_never_deletes_reviewed_tickets`, `test_reserved_channels_refused`.

- Finding: MED a lone surrogate in the text gave an unhandled 500 at insert.
- Fix: `service.validate_text` refuses text that cannot be encoded (422); /compare uses it too.
- Not changed: chunked bodies skip the 20 kB header check (text is still limited to 2,000 characters); /health already returns status ok, so the web app can poll it to notice a dead API (B5).
- DEPLOY.md rewritten with LFS, CORS-after-Vercel, redeploy, local `VITE_API_URL` and troubleshooting.

## 2026-11-15 B1: cards split by punctuation (Q3 re-check MED)
- Finding: cards with `_`, en/em-dash or comma between groups were stored raw.
- Evidence: strict xfail `test_card_split_by_punctuation_is_masked` in `tests/api/test_audit_q3.py` (removed).
- Fix: `CARD_RUN_RE` allows up to 3 non-word characters between digits; separated groups must be 4-8 digits, so amount lists and dates are not read as cards; order/tracking id exception kept.
- Test: `tests/data/test_audit_pii.py::test_indian_and_punctuation_formats`, `::test_new_classes_do_not_overmask`.

## 2026-11-15 B1: Indian identifiers and obfuscated emails
- Finding: Aadhaar, PAN, UPI ids and "jane dot doe at example dot com" were not masked.
- Evidence: Q3 request; none of these appeared in the probe set.
- Fix: `[AADHAAR]` (12 digits, groups of 4, any separators, Verhoeff checked; chosen because plain 12-digit ids then fail 90% of the time), `[PAN]`, `[UPI]` (name@handle with no dot after it), obfuscated emails become `[EMAIL]` (needs a known top-level domain). `service.py` placeholder list and its `before_masked` step updated to match.
- Test: probe set now 71 rows (16 negatives); `test_pii.py::test_probe_file_all_rows_match`, `test_verhoeff`, `test_ordinary_email_is_email_not_upi`.
