import json
import math
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from prediction.service import SnapshotStore
from prediction.tracking import ResultTracker, score


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = SnapshotStore(self.root / "snapshots.db")
        self.tracker = ResultTracker(self.store.path, [self.root])
        self.path = self.root / "results.csv"
        self.write_result(2, 0, "H")
        self.prediction = {"home_team": "Manchester City", "away_team": "Chelsea",
                           "kickoff_utc": "2026-10-25T15:00:00+00:00", "model_version": "v1",
                           "probabilities": {"home": .5, "draw": .3, "away": .2},
                           "market_probabilities": {"home": .4, "draw": .3, "away": .3},
                           "features": {"home_elo": 1600}}
        self.before = datetime(2026, 10, 24, tzinfo=timezone.utc)
        self.after = datetime(2026, 10, 26, tzinfo=timezone.utc)

    def write_result(self, hg, ag, outcome):
        self.path.write_text(f"Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n25/10/2026,Man City,Chelsea,{hg},{ag},{outcome}\n", encoding="utf-8")

    def test_settlement_is_idempotent_and_does_not_change_snapshot(self):
        self.store.save(self.prediction, self.before)
        with closing(sqlite3.connect(self.store.path)) as conn:
            original = conn.execute("SELECT payload FROM learned_predictions").fetchone()[0]
        self.assertEqual(self.tracker.settle(self.after)["updated"], 1)
        self.assertEqual(self.tracker.settle(self.after)["updated"], 0)
        metrics = self.tracker.metrics()
        self.assertEqual((metrics["total"], metrics["settled"], metrics["pending"]), (1, 1, 0))
        version = metrics["versions"][0]
        self.assertEqual(version["model"]["accuracy"], 1)
        self.assertAlmostEqual(version["model"]["log_loss"], -math.log(.5))
        self.assertAlmostEqual(version["model"]["brier_multiclass_sum"], .38)
        self.assertEqual(version["market_comparison"]["paired_matches"], 1)
        with closing(sqlite3.connect(self.store.path)) as conn:
            self.assertEqual(conn.execute("SELECT payload FROM learned_predictions").fetchone()[0], original)
            self.assertTrue(conn.execute("SELECT source_hash FROM prediction_results").fetchone()[0])

    def test_current_day_and_unmatched_results_remain_pending(self):
        self.store.save(self.prediction, self.before)
        self.assertEqual(self.tracker.settle(datetime(2026, 10, 25, 23, tzinfo=timezone.utc))["pending"], 1)
        self.write_result(0, 0, "D")
        self.path.write_text(self.path.read_text().replace("Man City", "Arsenal"))
        self.assertEqual(self.tracker.settle(self.after)["pending"], 1)
        self.assertIsNone(self.tracker.metrics()["versions"][0]["model"])

    def test_source_corrections_are_flagged_without_overwriting(self):
        self.store.save(self.prediction, self.before)
        self.tracker.settle(self.after)
        self.write_result(0, 2, "A")
        self.assertEqual(self.tracker.settle(self.after)["conflicts"], 1)
        self.assertEqual(self.tracker.metrics()["versions"][0]["model"]["accuracy"], 1)

    def test_versions_separate_and_market_cohort_is_paired(self):
        self.store.save(self.prediction, self.before)
        self.store.save({**self.prediction, "model_version": "v2", "market_probabilities": None}, self.before)
        self.tracker.settle(self.after)
        versions = self.tracker.metrics()["versions"]
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[1]["market_comparison"]["paired_matches"], 0)
        self.assertIsNone(versions[1]["market_comparison"]["market"])

    def test_empty_tracking_and_zero_probability_loss_are_finite(self):
        self.assertEqual(self.tracker.metrics()["total"], 0)
        self.assertEqual(self.tracker.settle(self.after)["updated"], 0)
        result = score([("home", {"home": 0, "draw": .5, "away": .5})])
        self.assertTrue(math.isfinite(result["log_loss"]))


if __name__ == "__main__":
    unittest.main()
