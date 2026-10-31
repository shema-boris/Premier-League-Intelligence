"""Serve frozen model predictions and retain immutable pre-kickoff evidence."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from prediction.pipeline import FEATURES, LABELS, ROOT, History, read_matches

logger = logging.getLogger(__name__)
ALIASES = {
    "manchester city": "Man City", "manchester united": "Man United",
    "newcastle united": "Newcastle", "nottingham forest": "Nott'm Forest",
    "tottenham hotspur": "Tottenham", "wolverhampton wanderers": "Wolves",
    "west ham united": "West Ham", "leeds united": "Leeds",
    "leicester city": "Leicester", "sheffield united": "Sheffield United",
    "brighton and hove albion": "Brighton", "brighton & hove albion": "Brighton",
    "afc bournemouth": "Bournemouth", "ipswich town": "Ipswich",
    "luton town": "Luton",
}


class SnapshotStore:
    def __init__(self, path):
        self.path = Path(path)

    def save(self, prediction, now):
        """First snapshot per fixture + model version wins; refreshes never rewrite it."""
        if datetime.fromisoformat(prediction["kickoff_utc"]) <= now:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=15)) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS learned_predictions (
                fixture_key TEXT NOT NULL, model_version TEXT NOT NULL,
                kickoff_utc TEXT NOT NULL, predicted_at TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY (fixture_key, model_version))""")
            key = json.dumps([prediction["home_team"], prediction["away_team"], prediction["kickoff_utc"]])
            conn.execute("INSERT OR IGNORE INTO learned_predictions VALUES (?, ?, ?, ?, ?)",
                                 (key, prediction["model_version"], prediction["kickoff_utc"],
                                  now.isoformat(), json.dumps({k: v for k, v in prediction.items() if k != "snapshot_saved"}, sort_keys=True)))
            return True


class PredictionService:
    def __init__(self, artifact=None, directories=None, store=None, max_age_days=35):
        self.artifact = Path(artifact or os.getenv("PREDICTION_MODEL_PATH", str(ROOT / "data/models/logistic-v1/model.joblib")))
        self.directories = directories or [ROOT / "data/historical", ROOT / "data/live-history"]
        self.store = store or SnapshotStore(os.getenv("LEARNED_PREDICTIONS_DB", str(ROOT / "data/learned_predictions.db")))
        self.max_age_days = max_age_days
        self._lock = threading.Lock()
        self._signature = None

    def _load(self):
        paths = sorted(p for directory in self.directories for p in Path(directory).glob("*.csv"))
        if not self.artifact.exists() or not paths:
            raise ValueError("The trained model or historical results are not installed.")
        signature = [(str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in [self.artifact, *paths]]
        if signature != self._signature:
            bundle = joblib.load(self.artifact)  # Trusted local artifact only.
            if bundle["features"] != FEATURES or list(bundle["model"].classes_) != LABELS:
                raise ValueError("The installed model has an incompatible feature or outcome schema.")
            matches = read_matches(paths)
            if not matches:
                raise ValueError("No completed historical results are installed.")
            self.bundle, self.matches = bundle, matches
            self.version = "logistic-v1-" + hashlib.sha256(self.artifact.read_bytes()).hexdigest()[:16]
            self.history_version = hashlib.sha256(b"".join(p.read_bytes() for p in paths)).hexdigest()
            self._signature = signature

    def predict(self, home, away, kickoff, market=None, now=None):
        live_clock = now is None
        now = now or datetime.now(timezone.utc)
        if kickoff.tzinfo is None or now.tzinfo is None:
            raise ValueError("Timezone-aware kickoff and current time required")
        kickoff = kickoff.astimezone(timezone.utc)
        result = {"status": "unavailable", "message": "Prediction unavailable.",
                  "home_team": home, "away_team": away, "kickoff_utc": kickoff.isoformat(),
                  "generated_at": now.isoformat(), "probabilities": None, "market_probabilities": market,
                  "model_version": None, "training_last_date": None,
                  "history_last_date": None, "team_history_dates": {}, "features": {},
                  "history_version": None, "snapshot_saved": False}
        if kickoff <= now:
            result.update(status="started", message="Kickoff has passed; no new prediction is generated.")
            return result
        with self._lock:
            try:
                self._load()
                result.update(model_version=self.version, history_version=self.history_version,
                              training_last_date=self.bundle["metadata"]["training_last_date"])
                # Exclude today's results as well as future results for prospective predictions.
                cutoff = min(now.astimezone(timezone.utc).date(), kickoff.date())
                if cutoff.isoformat() <= result["training_last_date"]:
                    raise ValueError("The model was trained after this prediction's information cutoff.")
                history = History()
                for match in self.matches:
                    if match["day"] < cutoff:
                        history.update(match)
                names = {name.casefold(): name for name in history.last}
                h = names.get(ALIASES.get(home.casefold(), home).casefold())
                a = names.get(ALIASES.get(away.casefold(), away).casefold())
                if not h or not a or h == a:
                    raise ValueError("A team has no recognized historical results; prediction withheld.")
                result["history_last_date"] = str(max(history.last.values()))
                result["team_history_dates"] = {"home": str(history.last[h]), "away": str(history.last[a])}
                ages = [(now.date() - history.last[t]).days for t in (h, a)]
                if max(ages) > self.max_age_days:
                    result.update(status="stale", message="Recent results are missing for at least one team; prediction withheld.")
                    return result
                if min(len(history.form[h]), len(history.form[a])) < 5:
                    raise ValueError("At least five earlier matches per team are required.")
                x = history.features(h, a, kickoff.date())
                probabilities = self.bundle["model"].predict_proba([x])[0]
                if not np.isfinite(probabilities).all() or (probabilities < 0).any() or not np.isclose(probabilities.sum(), 1):
                    raise ValueError("Model returned invalid probabilities.")
                result.update(status="ready", message="Historical model prediction; probabilities are estimates.",
                              probabilities={key: float(value) for key, value in zip(("away", "draw", "home"), probabilities)},
                              features=dict(zip(FEATURES, x)))
            except (OSError, ValueError, KeyError, EOFError, pickle.UnpicklingError, AttributeError) as exc:
                logger.warning("Learned prediction unavailable: %s", exc)
                result["message"] = "Model or historical data unavailable. Check model setup and team coverage."
                return result
            try:
                result["snapshot_saved"] = self.store.save(result, datetime.now(timezone.utc) if live_clock else now)
            except (sqlite3.Error, OSError):
                logger.exception("Could not persist learned prediction")
                result["message"] += " Prediction could not be recorded."
            return result


service = PredictionService()
