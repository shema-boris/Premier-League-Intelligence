# Prediction model design

## Model family and optimization

The predictive model is a classical linear classifier: scikit-learn's multinomial
`LogisticRegression`, preceded by `StandardScaler`. It is trained locally, not
downloaded from Hugging Face. It is not a neural network or language model.
The implementation uses the default L-BFGS optimizer, L2 regularization and
`max_iter=2000`; validation selects C from 0.01, 0.1, 1, 10. The initial run selected
C=10 with scikit-learn 1.6.1.

It estimates class logits as weighted sums of standardized features, then softmax
converts them into probabilities for away, draw and home. Training minimizes
regularized multiclass log loss. Coefficients learn from labeled completed matches.

## Features and assumptions

Twelve inputs, ordered in `prediction.pipeline.FEATURES`:

| Pair of features | Meaning |
|---|---|
| Home/away Elo | Sequential team strength, initial 1500; K=20 and 65-point home offset |
| Home/away points5 | Average league points over the previous five available matches |
| Home/away scored5 | Average goals scored over that window |
| Home/away conceded5 | Average goals conceded over that window |
| Home/away rest | Calendar days since last league match, capped at 30 |
| Home/away history5 | Number of available matches in the rolling window |

History carries across seasons without decay or reset. Training defaults for unseen
teams are points 1, goals 1.3, rest 7 and zero history count. Production serving is
stricter: five earlier matches and sufficiently recent team histories are required.
No odds, injuries, confirmed lineups, player quality or xG enter the classifier.
Rest reflects Premier League fixtures, not cup or international appearances.

## Leakage prevention and evaluation

Feature generation holds back all results on a fixture's calendar day. The scaler
is fitted only on training rows. Training uses 2016/17–2022/23, validation 2023/24,
and test 2024/25. Validation selects C; the chosen classifier remains fitted on the
training period and is not refitted on validation or test rows.

Team histories update with earlier-day observed results during validation/test.
The evaluation simulates sequential forecasts as results become available, not
predicting every match in a season before the season begins. The classifier and
scaler remain frozen throughout evaluation.

The first held-out test measured 51.84% accuracy, 0.9973 log loss and 0.5980 Brier
sum on 380 matches. The constant training-frequency baseline measured 40.79%,
1.0816 and 0.6561 respectively. See [the recorded experiment](../backend/prediction/BASELINE_RESULTS.md).
These figures do not establish superiority to bookmakers or generalization to
future seasons. Repeated tuning against this test requires reserving a new period.

## Prospective evaluation

The first recorded pre-kickoff snapshot per fixture/version is authoritative.
Its inputs, model probabilities and normalized market probabilities are retained.
Settlements are separate rows, matched only to completed result records. No model
is retrained during settlement.

Scores:

- Accuracy: fraction whose highest-probability class equals the actual outcome.
- Log loss: mean `-ln(probability of actual outcome)`, clipped at 1e-15 for numerical
  stability. Lower is better.
- Multiclass Brier: mean sum of squared differences from the one-hot result. Range
  0–2; lower is better. This is the sum convention, not the class-average convention.

Metrics reject invalid probability vectors. Market comparisons score the identical
paired fixture cohort. Every model version is reported separately; versions are
never pooled to hide a change in performance. Scores are null until data exists.
Current snapshots use the first available bookmaker's normalized odds, not an
opening/closing-line consensus; they are a dated comparison, not proof of value.

## Versioning and reproducibility

The artifact bundles the scaler, classifier, ordered feature schema and metadata.
Training metadata records split boundaries, source hashes and scikit-learn version.
Serving adds a SHA-256-derived model version and a history-content hash. Snapshots
also save actual feature values so prediction inputs remain inspectable after
history changes. Only trusted local joblib files should be loaded.

Live-history refresh does not automatically retrain the classifier. Retraining and
model promotion remain explicit operations. Next experiments should compare Poisson
and gradient boosting, calibration and rolling temporal stability against suitable
baselines. A generative model may explain evidence later; it should not replace
the probability estimator without its own measured evaluation.
