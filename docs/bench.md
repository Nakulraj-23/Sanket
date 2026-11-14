# Benchmark (test split, 1 CPU thread)

| model | intent_accuracy | intent_macro_f1 | team_accuracy | p50_ms | p95_ms | throughput_per_s | size_mb |
|---|---|---|---|---|---|---|---|
| baseline | 0.9003 | 0.9003 | 0.9685 | 0.8204 | 1.0160 | 13393.3981 | 4.9340 |
| nn_torch | 0.8857 | 0.8865 | 0.9630 | 0.1142 | 0.2007 | 39174.4631 | 2.5070 |
| nn_onnx | 0.8857 | 0.8865 | 0.9630 | 0.0550 | 0.1040 | 45583.1268 | 2.5070 |

Latency: 1,000 single-ticket calls after 50 warm-up calls, including `clean`. Throughput: batch of 64. Variants (val macro-F1): {"chosen": "words_trigrams_d64", "val_macro_f1": 0.882}
