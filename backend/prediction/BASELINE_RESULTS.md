# Logistic regression v1: first measured results

Dataset: 3,420 completed Premier League matches downloaded from
[Football-Data](https://www.football-data.co.uk/englandm.php), seasons 2016/17–2024/25.
Reproduction commands are in [README.md](README.md). The local generated evaluation
JSON contains source hashes and scikit-learn version (1.6.1 for this run).

- Training: 2016/17–2022/23, 2,660 matches.
- Validation: 2023/24, 380 matches. Selected C=10 using validation log loss.
- Held-out test: 2024/25, 380 matches.
- Model uses 12 pre-match features; no odds, injuries or lineups.
- Classifier and scaler are frozen after training; rolling team features update
  with earlier-day results throughout evaluation.

| Test metric | Logistic regression | Training-frequency baseline |
|---|---:|---:|
| Accuracy | 51.84% | 40.79% |
| Log loss (lower is better) | 0.9973 | 1.0816 |
| Multiclass Brier, sum (lower is better) | 0.5980 | 0.6561 |

The frequency baseline predicts the same training-set outcome distribution for
every fixture; its most likely outcome is always a home win. These results show
improvement over that simple baseline on one held-out season. They do not establish
superiority over bookmaker odds, profitability, calibration, or future performance.
Validation accuracy was 60.0%, illustrating why held-out evaluation matters.

The local model artifact is available to the prediction CLI and the dashboard API.
Live history is stored separately from this benchmark. Grounded LLM explanations
are not implemented yet.
