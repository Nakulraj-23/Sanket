# Experiments (date, tried, result, change)

## 2026-11-14 B3: neural challenger variants (val macro-F1, seed 42, CPU, 1 thread)
Tried: IntentNet (mean of embeddings, 128 hidden), Adam 2e-3, batch 64, early stop patience 6 on val macro-F1.
- words_d64 (words only, dim 64): 0.8672 (33 epochs, 8 s)
- words_trigrams_d64 (plus 8192 hashed char trigrams, dim 64): 0.8820 (31 epochs, 21 s) <- chosen
- words_trigrams_d128 (dim 128): 0.8759 (27 epochs, 25 s)
Result on test (chosen, once): intent macro-F1 0.8865, accuracy 0.8857, team accuracy 0.9630; baseline 0.9003 / 0.9003 / 0.9685.
Change: none; the NN loses by 1.4 macro-F1 points, so the linear model keeps serving.
Note: first run left torch on its default threads and took over 5 minutes of CPU on tiny matrices; `torch.set_num_threads(1)` brought all three variants to under 1 minute.

## 2026-11-14 B2 baseline grid (val only)
- Tried: TF-IDF + multinomial LR, C in {5,10,20}, with and without char_wb 2-5 grams; word cap 8000, char cap 15000 features (so model.joblib fits under 10 MB).
- Result (val macro-F1): no chars 0.8752 / 0.8791 / 0.8824 for C 5/10/20; with chars 0.8981 / 0.8970 / 0.8956. Char grams add about 0.02.
- Change: v1 uses C=5 with char grams. float32 coefficients cost 0.0000 val macro-F1 (identical to float64); model.joblib 4.93 MB.

## 2026-11-14 B2 team prediction ablation
- Tried: direct 7-class LR on the same features versus summing the 77 intent probabilities per team (C=5, train only).
- Result (team accuracy): val summed 0.9664 vs direct 0.9537; test summed 0.9708 vs direct 0.9636. Summed is better, so the design stays.
- Change: none.

## 2026-11-14 B2 retrain gate checks
- Tried: `make retrain`-style run from 80 reviewed stream rows, and the same with `--sabotage 0.3`.
- Result: clean run promoted (test macro-F1 0.9003 -> 0.9016). Sabotaged run rejected twice over: data-quality label agreement 0.526 < 0.72, and test macro-F1 0.8226.
- Change: the quality check needs a stream frame, so retrain passes stream rows not yet absorbed into train.
