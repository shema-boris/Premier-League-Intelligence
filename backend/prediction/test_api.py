"""Exercise API serialization without network calls, startup threads or real DB writes."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.main import app, _analysis_cache, _with_learned_prediction


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.result = dict(home_team="Arsenal", away_team="Chelsea", kickoff_utc="2099-01-01T15:00:00+00:00",
                           market_favorite="Arsenal", market_favorite_prob=.4,
                           model_favorite="Arsenal", model_favorite_prob=.4,
                           discrepancies=[dict(outcome=o, market_probability=p, model_probability=p, delta=0)
                                          for o, p in (("home", .4), ("draw", .3), ("away", .3))], conclusion="Legacy")
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_analysis_uses_learned_probabilities_and_preserves_market(self):
        prediction = {"status": "ready", "probabilities": {"home": .2, "draw": .25, "away": .55}}
        with patch("api.main.prediction_service.predict", return_value=prediction):
            result = _with_learned_prediction(self.result)
        self.assertEqual(result["model_favorite"], "Chelsea")
        self.assertEqual(result["market_favorite_prob"], .4)
        home = next(d for d in result["discrepancies"] if d["outcome"] == "home")
        self.assertAlmostEqual(home["delta"], -.2)

    def test_endpoint_uses_server_fixture_and_handles_missing_fixture(self):
        with patch.dict(_analysis_cache, {"data": [self.result]}), patch("api.main.prediction_service.predict", return_value={"status": "stale"}) as predict:
            response = self.client.get("/predict", params={"home_team": "Arsenal", "away_team": "Chelsea"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "stale")
            self.assertEqual(predict.call_args.args[2].year, 2099)
            response = self.client.get("/predict", params={"home_team": "Unknown", "away_team": "Chelsea"})
            self.assertEqual(response.status_code, 404)

    def test_learned_metrics_endpoint_is_separate_from_legacy_metrics(self):
        expected = {"total": 2, "settled": 0, "pending": 2, "versions": []}
        with patch("api.main.ResultTracker.metrics", return_value=expected):
            response = self.client.get("/model-metrics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)


if __name__ == "__main__":
    unittest.main()
