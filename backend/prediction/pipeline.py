"""Train/evaluate with strictly earlier-day match history. Run via -m prediction.pipeline."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict, deque
from datetime import date, datetime
from itertools import groupby
from pathlib import Path
from urllib.request import urlopen

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LABELS = ["A", "D", "H"]
FEATURES = ["home_elo", "away_elo", "home_points5", "away_points5",
            "home_scored5", "away_scored5", "home_conceded5", "away_conceded5",
            "home_rest", "away_rest", "home_history5", "away_history5"]
ROOT = Path(__file__).resolve().parents[1]


def parse_date(value):
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date: {value}")


def read_matches(paths):
    matches = {}
    for path in paths:
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"{path}: missing columns {required - set(reader.fieldnames or [])}")
            for row in reader:
                if not row.get("Date") or not row.get("FTR"):
                    continue  # Unplayed fixtures are not training examples.
                day = parse_date(row["Date"])
                home, away = row["HomeTeam"].strip(), row["AwayTeam"].strip()
                hg, ag = int(row["FTHG"]), int(row["FTAG"])
                result = "H" if hg > ag else "A" if ag > hg else "D"
                if not home or not away or home == away or min(hg, ag) < 0 or result != row["FTR"]:
                    raise ValueError(f"Invalid match in {path}: {row}")
                match = dict(day=day, home=home, away=away, hg=hg, ag=ag, result=result)
                key = (day, home, away)
                if key in matches and matches[key] != match:
                    raise ValueError(f"Conflicting duplicate: {key}")
                matches[key] = match
    return sorted(matches.values(), key=lambda m: (m["day"], m["home"], m["away"]))


class History:
    def __init__(self):
        self.elo = defaultdict(lambda: 1500.0)
        self.form = defaultdict(lambda: deque(maxlen=5))
        self.last = {}

    def features(self, home, away, day):
        def team(name):
            form = self.form[name]
            averages = [sum(item[i] for item in form) / len(form) if form else default
                        for i, default in enumerate((1.0, 1.3, 1.3))]
            rest = min((day - self.last[name]).days, 30) if name in self.last else 7
            return averages, rest, len(form)
        h, hr, hn = team(home)
        a, ar, an = team(away)
        return [self.elo[home], self.elo[away], h[0], a[0], h[1], a[1],
                h[2], a[2], hr, ar, hn, an]

    def update(self, match):
        h, a = match["home"], match["away"]
        hg, ag = match["hg"], match["ag"]
        score = 1.0 if hg > ag else 0.0 if hg < ag else 0.5
        expected = 1 / (1 + 10 ** ((self.elo[a] - self.elo[h] - 65) / 400))
        change = 20 * (score - expected)
        self.elo[h] += change
        self.elo[a] -= change
        self.form[h].append((3 if hg > ag else 1 if hg == ag else 0, hg, ag))
        self.form[a].append((3 if ag > hg else 1 if hg == ag else 0, ag, hg))
        self.last[h] = self.last[a] = match["day"]


def dataset(matches):
    history, rows = History(), []
    for day, group in groupby(matches, key=lambda m: m["day"]):
        batch = list(group)
        # Dates do not reliably include kickoff times: hold back every same-day result.
        for match in batch:
            rows.append((day, history.features(match["home"], match["away"], day), match["result"]))
        for match in batch:
            history.update(match)
    return rows


def metrics(y, probabilities):
    truth = np.array([[int(label == value) for label in LABELS] for value in y])
    return {"matches": len(y), "accuracy": float(accuracy_score(y, np.array(LABELS)[probabilities.argmax(axis=1)])),
            "log_loss": float(log_loss(y, probabilities, labels=LABELS)),
            "brier_multiclass_sum": float(np.mean(np.sum((probabilities - truth) ** 2, axis=1)))}


def train(paths, validation_start, test_start, output):
    if validation_start >= test_start:
        raise ValueError("validation-start must precede test-start")
    matches = read_matches(paths)
    rows = dataset(matches)
    partitions = [[r for r in rows if r[0] < validation_start],
                  [r for r in rows if validation_start <= r[0] < test_start],
                  [r for r in rows if r[0] >= test_start]]
    if any(not part for part in partitions):
        raise ValueError("Training, validation and test periods must all contain matches")
    if set(r[2] for r in partitions[0]) != set(LABELS):
        raise ValueError("Training data must include all three outcomes")
    def unpack(part):
        return np.array([r[1] for r in part]), np.array([r[2] for r in part])
    x_train, y_train = unpack(partitions[0])
    x_val, y_val = unpack(partitions[1])
    scores, candidates = {}, {}
    for c in (0.01, 0.1, 1.0, 10.0):
        model = make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000))
        model.fit(x_train, y_train)
        scores[str(c)] = float(log_loss(y_val, model.predict_proba(x_val), labels=LABELS))
        candidates[c] = model
    best = min(candidates, key=lambda c: scores[str(c)])
    # Freeze the training-only fit after validation selection; test never selects settings.
    model = candidates[best]
    baseline = np.array([(y_train == label).mean() for label in LABELS])
    report = {"algorithm": "standardized multinomial logistic regression", "selected_C": best,
              "validation_log_loss_by_C": scores, "features": FEATURES,
              "class_order": LABELS, "sklearn_version": sklearn.__version__,
              "training_matches": len(y_train), "training_last_date": partitions[0][-1][0].isoformat(),
              "validation_start": validation_start.isoformat(), "test_start": test_start.isoformat(),
              "evaluation_protocol": "Frozen model; rolling features use only earlier-day observed results.",
              "sources": [{"file": str(p), "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in paths]}
    for name, part in zip(("validation", "test"), partitions[1:]):
        x, y = unpack(part)
        report[name] = {"model": metrics(y, model.predict_proba(x)),
                        "training_frequency_baseline": metrics(y, np.tile(baseline, (len(y), 1)))}
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "metadata": report}, output / "model.joblib")
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    download = sub.add_parser("download")
    download.add_argument("--seasons", nargs="+", required=True, help="Four-digit codes, e.g. 2021 for 2020/21")
    download.add_argument("--directory", type=Path, default=ROOT / "data" / "historical")
    fit = sub.add_parser("train")
    fit.add_argument("--data", type=Path, default=ROOT / "data" / "historical")
    fit.add_argument("--validation-start", type=date.fromisoformat, required=True)
    fit.add_argument("--test-start", type=date.fromisoformat, required=True)
    fit.add_argument("--output", type=Path, default=ROOT / "data" / "models" / "logistic-v1")
    predict = sub.add_parser("predict")
    predict.add_argument("--artifact", type=Path, default=ROOT / "data" / "models" / "logistic-v1" / "model.joblib")
    predict.add_argument("--data", type=Path, default=ROOT / "data" / "historical")
    predict.add_argument("--home", required=True)
    predict.add_argument("--away", required=True)
    predict.add_argument("--date", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    if args.command == "download":
        args.directory.mkdir(parents=True, exist_ok=True)
        for season in args.seasons:
            if len(season) != 4 or not season.isdigit() or int(season[2:]) != (int(season[:2]) + 1) % 100:
                raise ValueError(f"Invalid season code: {season}")
            path = args.directory / f"E0_{season}.csv"
            if path.exists():
                read_matches([path])
                print(f"Already downloaded: {path}")
                continue
            url = f"https://www.football-data.co.uk/mmz4281/{season}/E0.csv"
            with urlopen(url, timeout=60) as response:
                content = response.read()
            # Validate before replacing the destination.
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(content)
            try:
                if not read_matches([temporary]):
                    raise ValueError(f"No completed matches in {url}")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            print(f"Downloaded {url}")
    elif args.command == "train":
        print(json.dumps(train(sorted(args.data.glob("*.csv")), args.validation_start, args.test_start, args.output), indent=2))
    else:
        # Only load locally generated, trusted joblib artifacts.
        bundle = joblib.load(args.artifact)
        if bundle["features"] != FEATURES:
            raise ValueError("Artifact feature schema does not match this implementation")
        if args.date <= date.fromisoformat(bundle["metadata"]["training_last_date"]):
            raise ValueError("Prediction date must be after the model's training period")
        history = History()
        for match in read_matches(sorted(args.data.glob("*.csv"))):
            if match["day"] < args.date:
                history.update(match)
        if args.home == args.away or args.home not in history.last or args.away not in history.last:
            raise ValueError("Use two distinct team names present in historical CSVs")
        x = history.features(args.home, args.away, args.date)
        probabilities = bundle["model"].predict_proba([x])[0]
        print(json.dumps({"home": args.home, "away": args.away, "date": str(args.date),
                          "probabilities": dict(zip(bundle["model"].classes_, probabilities)),
                          "features": dict(zip(FEATURES, x)),
                          "history_last_date": str(max(history.last.values()))}, indent=2))


if __name__ == "__main__":
    main()
