"""Install the reproducible baseline artifact and current serving history."""
from datetime import date

from prediction.history import current_seasons, refresh
from prediction.pipeline import ROOT, train


def main():
    directory = ROOT / "data/historical"
    seasons = [f"{year:02}{year + 1:02}" for year in range(16, 25)]
    missing = [season for season in seasons if not (directory / f"E0_{season}.csv").exists()]
    if missing:
        refresh(directory, missing)
    # Explicit files prevent newer seasons from changing the published benchmark.
    paths = [directory / f"E0_{season}.csv" for season in seasons]
    report = train(paths, date(2023, 7, 1), date(2024, 7, 1), ROOT / "data/models/logistic-v1")
    print(f"Baseline installed; held-out accuracy: {report['test']['model']['accuracy']:.3f}")
    refresh(ROOT / "data/live-history", current_seasons())


if __name__ == "__main__":
    main()
