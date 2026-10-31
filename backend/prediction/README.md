# Historical prediction baseline

This module trains an independent three-outcome logistic regression model. It does
not use bookmaker odds as features. The API and dashboard now use this model when
its artifact and sufficiently recent history are available. Generative explanations
are a later stage.

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

## Serve predictions in the dashboard

```powershell
python -m prediction.bootstrap
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Bootstrap downloads the fixed nine-season baseline, trains the same evaluated model,
and fetches the previous/current season into `backend/data/live-history`. It does
not retrain on the live data or change the published test split. It requires network
access. The Render build command runs bootstrap too; no model binaries are committed.

The background analysis worker refreshes current/previous season CSVs at most once
per 12 hours, retaining prior files on failure. Set `AUTO_REFRESH_HISTORY=0` for
offline development; manually refresh with `python -m prediction.history`.
The historical provider's date-based results are conservatively used only from
before the current UTC day. Injuries/lineups remain outside the model.

`GET /predict?home_team=Arsenal&away_team=Chelsea` looks up the fixture's kickoff
from provider-backed match data; arbitrary client kickoff times are not accepted.
An odds API key is needed to obtain the upcoming fixtures. The response contains
status (`ready`, `stale`, `unavailable`, or `started`), probabilities, normalized
market probabilities, artifact hash/version, training end, team-history dates,
feature inputs, source-history hash and whether the snapshot was recorded.
`POST /analyze-all` and `POST /analyze` include this under `learned_prediction` and
use learned probabilities for the favorite/discrepancies when ready. When not ready,
legacy numeric fields retain the market-based baseline for compatibility; clients
must inspect `learned_prediction.status` before presenting a learned prediction.

Teams use an explicit provider-name alias map, not fuzzy matching. Unknown teams,
fewer than five prior matches, missing artifacts and either team's latest result
being over 35 days old withhold predictions. This deliberately withholds predictions
during long breaks or for promoted teams without recent Premier League history.
The UI also hides cached predictions after kickoff or after 12 hours.

Ready predictions are stored in a separate `learned_predictions` table in
`backend/data/learned_predictions.db`. The first snapshot for a fixture/model
version is immutable; subsequent dashboard refreshes never rewrite it. The payload
includes model and market probabilities, all inputs, dates and source/model hashes.
New snapshots are refused after kickoff; storage failure is surfaced to the UI.
The legacy `predictions.db` and its metrics still describe the old pipeline, not
these learned snapshots. The background worker settles learned snapshots into a
separate `prediction_results` table using earlier-day completed CSV results.
Use `python -m prediction.tracking settle` to trigger settlement locally, and
`python -m prediction.tracking metrics` to inspect the same data served by
`GET /model-metrics`. Metrics are grouped by version, and model/market comparisons
use exactly the same paired fixtures. Source corrections are flagged for review.

For deployment, configure `LEARNED_PREDICTIONS_DB` to a path on persistent storage;
an ephemeral filesystem loses snapshots on redeploy. `PREDICTION_MODEL_PATH` can
override the default trusted local artifact. This repository does not provision
a persistent hosting disk. Do not claim durable prospective tracking until one is
configured.

Tests: `python -m unittest discover -s prediction -p "test_*.py" -v`.
API tests also require `httpx` (`python -m pip install httpx` if absent).

## Limits and next steps

This first model excludes injuries, lineups, player quality, xG and odds. Teams new
to the dataset start with defaults. Name changes across data providers require an
explicit mapping (see `service.py`). Next steps are verifying production persistence,
a historical dated odds benchmark, calibration checks, stronger competing models,
and grounded LLM explanations. Do not repeatedly tune against this held-out test season; reserve
a new future period when iterating extensively.
