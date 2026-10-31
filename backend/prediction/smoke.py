"""Verify a deployed prediction API without printing credentials or full snapshots."""
import argparse
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def check(base):
    def request(path, method="GET"):
        with urlopen(Request(base.rstrip("/") + path, method=method), timeout=90) as response:
            return json.load(response)
    health = request("/health")
    if health.get("status") != "healthy":
        raise ValueError("Backend health is not healthy")
    metrics = request("/model-metrics")
    if not {"total", "settled", "pending", "versions"}.issubset(metrics):
        raise ValueError("Learned prediction metrics endpoint is missing or incompatible")
    fixtures = request("/analyze-all", "POST")
    ready = [match for match in fixtures if (match.get("learned_prediction") or {}).get("status") == "ready"]
    summary = {"health": health["status"], "fixtures": len(fixtures), "ready_predictions": len(ready),
               "recorded": metrics["total"], "settled": metrics["settled"]}
    if not ready:
        summary["prediction_statuses"] = [(m.get("learned_prediction") or {}).get("status", "missing") for m in fixtures]
        raise ValueError(f"No ready predictions; model/data/fixtures need review: {summary}")
    fixture = ready[0]
    prediction = request("/predict?" + urlencode({"home_team": fixture["home_team"], "away_team": fixture["away_team"]}))
    if prediction.get("status") != "ready" or not prediction.get("snapshot_saved"):
        raise ValueError("Forecast could not be generated and recorded")
    summary["model_version"] = prediction["model_version"]
    summary["history_last_date"] = prediction["history_last_date"]
    summary["snapshot_saved"] = True
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.base_url), indent=2))
