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
