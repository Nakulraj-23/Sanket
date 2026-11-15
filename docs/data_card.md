# Data card (B1)

Source: Banking77 (CC-BY-4.0), 77 intents. Team and urgency are this project's rubric, not dataset labels.

## Splits (`make data`, seed 42, byte-identical on re-run)
| split | rows | note |
|---|---|---|
| train | 6946 | 70%; min class 25, max 129 |
| val | 1489 | 15%; thresholds are chosen here |
| stream | 1489 | 15%; live demo, may be absorbed by retraining |
| test | 3080 | official test, frozen, never used for training or thresholds |

Counts below come from `make data` (`sanket/pipeline/split.py`). Removed from the official train (10003 rows): 7 whose text is also in test, 4 internal duplicates, 68 near copies of a
test text (TF-IDF cosine > 0.99). The official test has 1 duplicate text, kept because it is frozen.

## Known caveats
- Near-duplicates remain: 351 of 3080 test rows (11.4%) have a train text with TF-IDF cosine > 0.9 (390 train rows);
  source: `sanket/pipeline/similarity.py::near_duplicates`, run by B1 on the committed splits. They are paraphrases, too
  many to drop without thinning train. Separate Q1 audit measurement (`tests/data/test_audit_leakage.py`, a different
  rule: token-set Jaccard >= 0.9, 89 test rows = 2.9%): a TF-IDF + logistic regression model scored 0.978 accuracy on those
  89 rows against 0.872 on the rest, and test macro-F1 moved 0.876 to 0.873 without them. Those figures do not describe the
  351-row set. Read test scores with this in mind.
- Token artefact: "1" (as in "$1" or "£1 charge") is in 58 of 114 train rows of `extra_charge_on_statement` (19 of 40 in
  test); counted by B1 with a word-boundary search on the committed splits (Q1 counted 60 of 116 on the earlier,
  pre-near-copy-removal train). A ticket about a different amount may be routed wrongly; the metrics will not show it.
- Label noise: Q1 audit (`docs/handoffs/Q1.md`) disagreed with 12 of 150 sampled train labels (8%). Debatable labels still to review (Q1 named only these six; the
  other six were not itemised):
  - tr-4046 "wheres my pin" and tr-4008 "i need my pin, where is it?" = get_physical_card
  - tr-8938 "there is random cash in my account." = cash_withdrawal_not_recognised
  - tr-5576 checkout keeps getting declined = declined_transfer
  - tr-9588 "can i order a new card with the app?" = card_about_to_expire
  - tr-4809 transaction in the app not made by me = direct_debit_payment_not_recognised
- PII masking is pattern based (B1, `sanket/pipeline/pii.py`): it finds numbers and addresses by shape, so names and
  postal addresses are not masked. Known Q3 LOW: "refund at amazon dot in" is read as an obfuscated email, and the word
  before it is swallowed into the same [EMAIL] token. Masked classes: [EMAIL] (also written-out forms), [UPI], [PHONE], [CARD] (Luhn), [AADHAAR] (Verhoeff), [PAN], [ACCOUNT] (only near account/IBAN words): a 10-digit amount written after "paid"/"rs"/"amount" is kept, a real phone number written right
  after those words would be too. Hinglish stress rows are hand-written; `hinglishify` output is synthetic, drift demo only.

## Contested rubric rows (for the candidate to decide; nothing changed)
- Team: `apple_pay_or_google_pay` (texts are mostly top-ups) and `supported_cards_and_currencies` ("which cards can I top up
  with") may fit TRANSFERS_TOPUPS better than CARDS and ACCOUNT_KYC. Q1 audit: moving both lifts val team accuracy 0.951 to 0.953.
- Team: `fiat_currency_support`, `exchange_via_app`, `top_up_by_bank_transfer_charge`, `top_up_by_card_charge` sit on the
  FEES_FX / TRANSFERS_TOPUPS border.
- Urgency: `cancel_transfer` is time-critical (high?). `activate_my_card`, `card_linking`, `verify_top_up`,
  `transfer_into_account`, `verify_my_identity` read as how-to (low?).
