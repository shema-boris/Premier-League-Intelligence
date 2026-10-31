import csv
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from prediction.pipeline import train
from prediction.service import PredictionService, SnapshotStore


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.csv = self.root / "matches.csv"
        with self.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])
            for i in range(90):
                hg, ag, result = [(2, 0, "H"), (1, 1, "D"), (0, 1, "A")][i % 3]
                writer.writerow([(date(2020, 1, 1) + timedelta(days=i)).isoformat(),
                                 "Man City", "Chelsea", hg, ag, result])
        train([self.csv], date(2020, 2, 15), date(2020, 3, 1), self.root / "model")
        self.store = SnapshotStore(self.root / "snapshots.db")
        self.service = PredictionService(self.root / "model/model.joblib", [self.root], self.store)
        self.now = datetime(2020, 4, 1, tzinfo=timezone.utc)
        self.kickoff = self.now + timedelta(days=2)

    def predict(self, **kwargs):
        return self.service.predict("Manchester City", "Chelsea", self.kickoff, now=self.now, **kwargs)

    def test_ready_aliases_probabilities_and_immutable_snapshots(self):
        first = self.predict(market={"home": .4, "draw": .3, "away": .3})
        self.assertEqual(first["status"], "ready")
        self.assertAlmostEqual(sum(first["probabilities"].values()), 1)
        self.assertTrue(first["snapshot_saved"])
        second = self.predict(market={"home": .6, "draw": .2, "away": .2})
        self.assertTrue(second["snapshot_saved"])
        with closing(sqlite3.connect(self.store.path)) as conn:
            rows = conn.execute("SELECT payload FROM learned_predictions").fetchall()
        self.assertEqual(len(rows), 1)
        snapshot = json.loads(rows[0][0])
        self.assertEqual(snapshot["market_probabilities"]["home"], .4)
        self.assertEqual(snapshot["features"], first["features"])
        self.assertTrue(snapshot["model_version"])

    def test_stale_unknown_and_started_do_not_save(self):
        stale = self.service.predict("Man City", "Chelsea", self.kickoff + timedelta(days=90), now=self.now + timedelta(days=80))
        self.assertEqual(stale["status"], "stale")
        self.assertIsNone(stale["probabilities"])
        unknown = self.service.predict("Unknown", "Chelsea", self.kickoff, now=self.now)
        self.assertEqual(unknown["status"], "unavailable")
        started = self.service.predict("Man City", "Chelsea", self.now, now=self.now)
        self.assertEqual(started["status"], "started")
        self.assertFalse(self.store.path.exists())

    def test_missing_model_is_explicit(self):
        self.service.artifact = self.root / "missing.joblib"
        self.assertEqual(self.predict()["status"], "unavailable")

    def test_future_and_current_day_results_excluded(self):
        before = self.predict()
        with self.csv.open("a", encoding="utf-8") as handle:
            handle.write("2020-04-01,Man City,Chelsea,20,0,H\n2020-04-02,Man City,Chelsea,0,20,A\n")
        after = self.predict()
        self.assertEqual(before["features"], after["features"])
        self.assertEqual(before["probabilities"], after["probabilities"])

    def test_storage_failure_keeps_prediction_but_reports_failure(self):
        with patch.object(self.store, "save", side_effect=sqlite3.OperationalError("read only")):
            result = self.predict()
        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["snapshot_saved"])

    def test_snapshot_refuses_post_kickoff(self):
        result = self.predict()
        self.assertFalse(self.store.save(result, self.kickoff))


if __name__ == "__main__":
    unittest.main()
