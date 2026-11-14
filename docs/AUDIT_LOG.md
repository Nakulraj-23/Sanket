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
