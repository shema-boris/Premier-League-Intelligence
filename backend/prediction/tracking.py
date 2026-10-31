"""Settle immutable predictions against completed CSV results and score by version."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from prediction.pipeline import ROOT, read_matches
from prediction.service import ALIASES

OUTCOMES = ("away", "draw", "home")


def canonical(name):
    return ALIASES.get(name.casefold(), name).casefold()


def valid_probabilities(values):
    return isinstance(values, dict) and all(
        isinstance(values.get(key), (float, int)) and math.isfinite(values[key]) and 0 <= values[key] <= 1
        for key in OUTCOMES) and math.isclose(sum(values[key] for key in OUTCOMES), 1, abs_tol=1e-6)


def score(examples):
    if not examples:
        return None
    return {"matches": len(examples),
            "accuracy": sum(max(OUTCOMES, key=p.get) == actual for actual, p in examples) / len(examples),
            "log_loss": sum(-math.log(max(p[actual], 1e-15)) for actual, p in examples) / len(examples),
            "brier_multiclass_sum": sum(sum((p[key] - int(key == actual)) ** 2 for key in OUTCOMES)
                                         for actual, p in examples) / len(examples)}


class ResultTracker:
    def __init__(self, database=None, directories=None):
        self.database = Path(database or os.getenv("LEARNED_PREDICTIONS_DB", str(ROOT / "data/learned_predictions.db")))
        self.directories = directories or [ROOT / "data/historical", ROOT / "data/live-history"]

    def _snapshots(self):
        if not self.database.exists():
            return []
        with closing(sqlite3.connect(self.database, timeout=15)) as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='learned_predictions'").fetchone():
                return []
            return conn.execute("SELECT fixture_key, model_version, kickoff_utc, predicted_at, payload FROM learned_predictions").fetchall()

    def settle(self, now=None):
        now = now or datetime.now(timezone.utc)
        snapshots = self._snapshots()
        report = {"updated": 0, "pending": 0, "conflicts": 0, "invalid": 0}
        if not snapshots:
            return report
        paths = sorted(path for directory in self.directories for path in Path(directory).glob("*.csv"))
        source_hash = hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()
        results = {(str(m["day"]), canonical(m["home"]), canonical(m["away"])): m
                   for m in read_matches(paths) if m["day"] < now.date()}
        with closing(sqlite3.connect(self.database, timeout=15)) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS prediction_results (
                fixture_key TEXT NOT NULL, model_version TEXT NOT NULL,
                actual_result TEXT NOT NULL, home_goals INTEGER NOT NULL, away_goals INTEGER NOT NULL,
                settled_at TEXT NOT NULL, source_hash TEXT NOT NULL,
                PRIMARY KEY (fixture_key, model_version))""")
            for key, version, kickoff, predicted_at, payload in snapshots:
                prediction = json.loads(payload)
                kickoff_time = datetime.fromisoformat(kickoff)
                predicted_time = datetime.fromisoformat(predicted_at)
                if not kickoff_time.tzinfo or not predicted_time.tzinfo or predicted_time >= kickoff_time:
                    report["invalid"] += 1
                    continue
                result = results.get((str(kickoff_time.astimezone(timezone.utc).date()),
                                      canonical(prediction["home_team"]), canonical(prediction["away_team"])))
                if kickoff_time > now or not result:
                    report["pending"] += 1
                    continue
                actual = {"H": "home", "D": "draw", "A": "away"}[result["result"]]
                previous = conn.execute("SELECT actual_result, home_goals, away_goals FROM prediction_results WHERE fixture_key=? AND model_version=?", (key, version)).fetchone()
                if previous:
                    if previous != (actual, result["hg"], result["ag"]):
                        report["conflicts"] += 1
                    continue  # Corrections require review; never rewrite historical evidence silently.
                conn.execute("INSERT INTO prediction_results VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (key, version, actual, result["hg"], result["ag"], now.isoformat(), source_hash))
                report["updated"] += 1
        return report

    def metrics(self):
        snapshots = self._snapshots()
        results = {}
        if snapshots:
            with closing(sqlite3.connect(self.database, timeout=15)) as conn:
                if conn.execute("SELECT 1 FROM sqlite_master WHERE name='prediction_results'").fetchone():
                    results = {(key, version): actual for key, version, actual in conn.execute(
                        "SELECT fixture_key, model_version, actual_result FROM prediction_results")}
        groups = defaultdict(list)
        for row in snapshots:
            groups[row[1]].append(row)
        versions = []
        for version, rows in sorted(groups.items()):
            model_examples, paired_model, paired_market = [], [], []
            settled = invalid = 0
            for key, _, kickoff, predicted_at, payload in rows:
                actual = results.get((key, version))
                if actual is None:
                    continue
                settled += 1
                prediction = json.loads(payload)
                model, market = prediction.get("probabilities"), prediction.get("market_probabilities")
                if not valid_probabilities(model):
                    invalid += 1
                    continue
                model_examples.append((actual, model))
                if valid_probabilities(market):
                    paired_model.append((actual, model))
                    paired_market.append((actual, market))
            versions.append({"model_version": version, "total": len(rows), "settled": settled,
                             "pending": len(rows) - settled, "invalid_probabilities": invalid,
                             "model": score(model_examples),
                             "market_comparison": {"paired_matches": len(paired_model),
                                                   "model": score(paired_model), "market": score(paired_market)}})
        return {"total": len(snapshots), "settled": sum(v["settled"] for v in versions),
                "pending": sum(v["pending"] for v in versions), "versions": versions,
                "protocol": "First pre-kickoff snapshot per fixture/model. Market comparisons use identical settled fixtures. Accuracy is a fraction; Brier is the multiclass sum (0–2)."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["settle", "metrics"])
    parser.add_argument("--database", type=Path)
    parser.add_argument("--history", type=Path, nargs="+")
    args = parser.parse_args()
    tracker = ResultTracker(args.database, args.history)
    print(json.dumps(tracker.settle() if args.command == "settle" else tracker.metrics(), indent=2))
