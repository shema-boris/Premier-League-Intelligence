"""Run from backend: python -m unittest prediction.test_pipeline -v."""
import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np

from prediction.pipeline import FEATURES, LABELS, dataset, read_matches, train


def match(day, home="Alpha", away="Beta", hg=2, ag=0):
    return dict(day=day, home=home, away=away, hg=hg, ag=ag,
                result="H" if hg > ag else "A" if ag > hg else "D")


class PipelineTests(unittest.TestCase):
    def test_current_and_future_scores_do_not_change_prematch_features(self):
        first = date(2020, 1, 1)
        original = [match(first), match(first + timedelta(days=7)), match(first + timedelta(days=14))]
        changed = [original[0], match(first + timedelta(days=7), hg=0, ag=5), original[2]]
        before, after = dataset(original), dataset(changed)
        self.assertEqual(before[0][1], after[0][1])
        self.assertEqual(before[1][1], after[1][1])
        self.assertNotEqual(before[2][1], after[2][1])

    def test_same_day_results_are_held_back(self):
        day = date(2020, 1, 1)
        rows = dataset([match(day), match(day, away="Gamma")])
        self.assertEqual(rows[0][1], rows[1][1])

    def test_csv_validation_and_duplicate_handling(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matches.csv"
            path.write_text("Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n01/01/20,Alpha,Beta,2,0,H\n", encoding="utf-8")
            self.assertEqual(len(read_matches([path, path])), 1)
            path.write_text("Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n01/01/20,Alpha,Beta,2,0,A\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_matches([path])

    def test_train_evaluate_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "matches.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])
                for i in range(90):
                    hg, ag, result = [(2, 0, "H"), (1, 1, "D"), (0, 1, "A")][i % 3]
                    writer.writerow([(date(2020, 1, 1) + timedelta(days=i)).isoformat(),
                                     "Alpha", "Beta", hg, ag, result])
            report = train([path], date(2020, 2, 15), date(2020, 3, 1), root / "model")
            self.assertEqual(report["training_matches"], 45)
            self.assertEqual(report["validation"]["model"]["matches"], 15)
            self.assertEqual(report["test"]["model"]["matches"], 30)
            bundle = joblib.load(root / "model" / "model.joblib")
            self.assertEqual(list(bundle["model"].classes_), LABELS)
            x = dataset(read_matches([path]))[-1][1]
            p = bundle["model"].predict_proba([x])[0]
            self.assertTrue(np.isfinite(p).all())
            self.assertAlmostEqual(sum(p), 1)
            self.assertEqual(len(x), len(FEATURES))
            self.assertEqual(json.loads((root / "model" / "evaluation.json").read_text())["selected_C"], report["selected_C"])
            # The scaler must see training rows only.
            self.assertEqual(bundle["model"].named_steps["standardscaler"].n_samples_seen_, 45)


if __name__ == "__main__":
    unittest.main()
