# Deployment and operations

## Targets and release boundaries

The existing project uses Vercel for `frontend/` and Render for `backend/`.
`render.yaml` specifies a model bootstrap during the build; `frontend/vercel.json`
handles single-page app routes. A Git push is not evidence of a successful backend
deployment or durable storage. Verify both services after every release.

## Backend configuration

In the existing Render service:

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Runtime | Python 3.11 |
| Build command | `pip install -r requirements.txt && python -m prediction.bootstrap` |
| Start command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/health` |
| `ODDS_API_KEY` | Existing secret for upcoming fixtures and odds |
| `FOOTBALL_API_KEY` | Existing secret for optional supporting context |
| `FRONTEND_URL` | Actual production frontend origin, for CORS |
| `AUTO_REFRESH_HISTORY` | `1` |
| `LEARNED_PREDICTIONS_DB` | Absolute database path under persistent storage |

Gemini credentials are not required by the trained prediction path. The default
model path is generated during bootstrap; override `PREDICTION_MODEL_PATH` only
for a trusted compatible artifact. Run a single backend instance/worker: caches
and the refresh/settlement thread are process-local.

`render.yaml` only affects a service managed/synced by a Blueprint. For an existing
dashboard-configured service, update its build/start/environment settings directly.
Do not assume a repository YAML edit changes an independently managed service.

## Durable SQLite storage

Render's default filesystem is ephemeral. Persistent disks are available on paid
services and preserve only files beneath their mount path. See the official
[persistent disk documentation](https://render.com/docs/disks) and
[Blueprint reference](https://render.com/docs/blueprint-spec).

The repository deliberately does not create a paid disk or change the hosting plan.
For a disk-backed deployment, configure a mount such as `/var/data`, then set:

```text
LEARNED_PREDICTIONS_DB=/var/data/learned_predictions.db
```

The model artifact can stay in the build's filesystem; it is reproducible.
Snapshot evidence must survive deploys. Do not mount a disk over `backend/data`
without accounting for the model/history files built there, because the mount can
hide build contents. The legacy database is separate and is not migrated.

Before moving an existing learned database, stop concurrent writers and use a
SQLite-consistent backup/restore. Do not copy a changing database blindly. Preserve
both `learned_predictions` and `prediction_results`; never backfill pre-kickoff
forecasts after a result is known.

After configuration, record a genuine future fixture, verify `/model-metrics`
reports it, redeploy/restart, and verify the count and exact stored payload survive.
One successful write on an ephemeral filesystem does not prove persistence.

## Frontend configuration

Use project root `frontend`, build command `npm run build`, output directory
`build`, and set `REACT_APP_API_URL` to the verified backend HTTPS origin before
building. This variable is embedded in the bundle. Updating a runtime environment
variable without rebuilding the frontend does not change its API target.

Confirm both the automatic Git integration and the production alias point to this
repository/branch before relying on a push to publish. Never place API secrets in
`REACT_APP_*` variables; they are public frontend configuration.

## Verification

Locally, before release:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m unittest discover -s prediction -p "test_*.py" -v
cd ../frontend
node node_modules/react-scripts/bin/react-scripts.js test --watchAll=false --runInBand
npm run build
```

After hosting reports deployment success, from `backend`:

```powershell
python -m prediction.smoke --base-url https://YOUR-BACKEND-HOST
```

This checks process health, the new metrics endpoint, fixture analysis, learned
inference and snapshot recording. It deliberately fails if no ready forecast exists,
which can also occur legitimately outside the season or with insufficient history.
It uses the normal match API and may populate the cache/store for actual upcoming
fixtures. It does not place bets or modify real results.

In the browser, confirm probability comparisons, model/history dates, live tracking,
stale/sample fallback labels and the correct backend origin. Perform the restart
test above separately; the smoke test cannot prove disk durability.

## Results and recurring work

The background worker refreshes analysis about every 10 minutes and attempts
settlement after each refresh. It refreshes current/previous season results at most
every 12 hours. Completed matches on the current UTC date are settled only on a
later UTC day, so metrics intentionally lag final whistles.

Operator commands, using the same database environment as the service:

```powershell
python -m prediction.history
python -m prediction.tracking settle
python -m prediction.tracking metrics
```

Settlement output reports updated, pending, conflicting and invalid snapshots.
Review conflicts against the provider; there is no automatic overwrite tool. Check
pending fixtures for postponements, name mismatches and missing result coverage.
No automatic model retraining occurs. Plan promotion and evaluate a new version
explicitly before replacing an artifact.

## Failure handling and rollback

- Failed result downloads retain the last validated CSV. Stale team histories
  withhold forecasts. Empty/malformed CSVs are rejected before replacement.
- Missing/incompatible model artifacts produce an unavailable forecast status.
- Failed snapshot writes leave the forecast visible with a recording failure.
- Failed settlement retains the original snapshots and is retried on later cycles.
- Failed metrics reads are labeled unavailable in the dashboard.

Rollback the application/artifact to a previously verified revision while preserving
the persistent database. Separate version keys retain past results. Never delete
the evidence database to fix an application deployment.

## Current verification boundary

The repository includes automated checks and deployment configuration. Hosting
account access, actual build settings and durable storage must be confirmed in
the target environment. Documentation is not a claim that those external actions
have completed.
