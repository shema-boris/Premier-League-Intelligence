"""Refresh completed results independently of the frozen training dataset."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from prediction.pipeline import ROOT, read_matches


def refresh(directory: Path, seasons: list[str]):
    directory.mkdir(parents=True, exist_ok=True)
    for season in seasons:
        if len(season) != 4 or not season.isdigit() or int(season[2:]) != (int(season[:2]) + 1) % 100:
            raise ValueError(f"Invalid season: {season}")
        path = directory / f"E0_{season}.csv"
        with urlopen(f"https://www.football-data.co.uk/mmz4281/{season}/E0.csv", timeout=30) as response:
            content = response.read()
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(content)
        try:
            matches = read_matches([temporary])
            if not matches:
                raise ValueError(f"No completed matches for {season}")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Refreshed {season}: {len(matches)} matches, latest {matches[-1]['day']}")


def current_seasons(now=None):
    day = (now or datetime.now(timezone.utc)).date()
    start = day.year if day.month >= 7 else day.year - 1
    return [f"{year % 100:02}{(year + 1) % 100:02}" for year in (start - 1, start)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", nargs="+")
    parser.add_argument("--directory", type=Path, default=ROOT / "data" / "live-history")
    args = parser.parse_args()
    refresh(args.directory, args.seasons or current_seasons())
