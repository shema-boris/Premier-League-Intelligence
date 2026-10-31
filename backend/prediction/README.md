# Historical prediction baseline

This module trains an independent three-outcome logistic regression model. It does
not use bookmaker odds as features and does not change the dashboard's existing
analysis path. Generative explanations and API/UI integration are later stages.

## Reproduce

Run from `backend` (preferably inside your virtual environment):

```powershell
python -m pip install -r requirements-ml.txt
python -m prediction.pipeline download --seasons 1617 1718 1819 1920 2021 2122 2223 2324 2425
python -m prediction.pipeline train --validation-start 2023-07-01 --test-start 2024-07-01
python -m unittest prediction.test_pipeline -v
```

Source: [Football-Data's historical English results](https://www.football-data.co.uk/englandm.php).
`1617` means 2016/17. Downloads are explicit, validated and cached locally; no API
key is required. Existing files are reused. Use the provider's terms and attribution
when publishing or redistributing data. Generated files are ignored by Git.
You can also supply your own directory with `--data PATH`. Required CSV columns:
`Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR`; results are `H`, `D`, or `A`.
Duplicate matches are deduplicated; conflicting records and inconsistent results
raise errors. Rows without results are skipped.

## What the model learns

For each team: pre-match Elo, average points/goals scored/goals conceded over its
last five matches, rest days (capped at 30), and available history count. Initial
defaults are Elo 1500, points 1, goals 1.3 and rest 7 days. Elo uses K=20 and a fixed
65-point home adjustment. These are baseline assumptions, not tuned findings.
Rolling history and Elo carry across seasons; there is no season reset or decay.

Features only use results from earlier calendar days, conservatively excluding all
same-day results. Scaling is fitted on training data only. The classifier selects
regularization C from 0.01, 0.1, 1, 10 using validation log loss. The selected model
remains fitted on the training period; it is not refitted on validation/test data.
Evaluation is sequential: previous validation/test results may update team history
for later fixtures, but never the fitted classifier or scaler. This simulates
making daily predictions as results become available, not predicting a season at once.

The outputs under `backend/data/models/logistic-v1` are:

- `model.joblib`: classifier, scaler, ordered feature names and metadata.
- `evaluation.json`: date boundaries, sample counts, source SHA-256 hashes,
  scikit-learn version, selected C, accuracy, log loss, and multiclass Brier score
  (sum of squared class errors per match; range 0–2, lower is better).

The baseline always returns training-set outcome frequencies. Better test accuracy
alone does not establish better probabilities. There is no bookmaker comparison
yet, and no claim of profitability or superiority to market odds.

## Predict a fixture

Use exact CSV team names and keep local results up to date:

```powershell
python -m prediction.pipeline predict --home Arsenal --away Chelsea --date 2025-06-01
```

The example is a hypothetical fixture. Only matches before that date are read;
the date must follow the model's training period. Output includes probabilities
(`H` home, `D` draw, `A` away), actual input features and the latest history date,
so stale inputs can be spotted. Unknown team names fail explicitly. Older known
teams can still have stale histories; inspect the output before interpreting it.
This command uses the frozen classifier; it does not retrain it.

Load only trusted local joblib artifacts: joblib uses Python pickle serialization.

## Limits and next steps

This first model excludes injuries, lineups, player quality, xG and odds. Teams new
to the dataset start with defaults. Name changes across data providers require an
explicit mapping before API integration. Next steps are a dated odds benchmark,
calibration checks, stronger competing models, then an API endpoint and grounded
LLM explanations. Do not repeatedly tune against this held-out test season; reserve
a new future period when iterating extensively.
