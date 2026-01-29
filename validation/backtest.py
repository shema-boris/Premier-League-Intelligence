"""Backtest runner to validate predictions against actual results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from data_sources.football_api import FootballAPIClient

if TYPE_CHECKING:
    from .database import PredictionDB


class BacktestRunner:
    """Fetches completed match results and updates predictions."""

    def __init__(self, db: "PredictionDB"):
        self.db = db
        self.football_api = FootballAPIClient.from_env()

    def validate_pending(self) -> dict[str, int]:
        """
        Fetch results for pending predictions and update the database.
        Returns counts of updated, not_found, and still_pending.
        """
        pending = self.db.get_pending()
        if not pending:
            return {"updated": 0, "not_found": 0, "still_pending": 0}

        # Fetch recent completed fixtures
        completed = self._fetch_completed_fixtures()
        
        # Build lookup by normalized team names
        results_lookup: dict[str, dict] = {}
        for fixture in completed:
            home = fixture.get("teams", {}).get("home", {}).get("name", "")
            away = fixture.get("teams", {}).get("away", {}).get("name", "")
            date = fixture.get("fixture", {}).get("date", "")[:10]
            
            key = self._make_lookup_key(home, away, date)
            
            goals = fixture.get("goals", {})
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            if home_goals is not None and away_goals is not None:
                if home_goals > away_goals:
                    result = "home"
                elif away_goals > home_goals:
                    result = "away"
                else:
                    result = "draw"
                    
                results_lookup[key] = {
                    "result": result,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                }

        updated = 0
        not_found = 0
        still_pending = 0

        for pred in pending:
            key = self._make_lookup_key(pred.home_team, pred.away_team, pred.match_date[:10])
            
            if key in results_lookup:
                r = results_lookup[key]
                self.db.update_result(
                    pred.match_id,
                    result=r["result"],
                    home_goals=r["home_goals"],
                    away_goals=r["away_goals"],
                )
                updated += 1
            else:
                # Check if match date has passed
                still_pending += 1

        not_found = len(pending) - updated - still_pending

        return {"updated": updated, "not_found": not_found, "still_pending": still_pending}

    def _fetch_completed_fixtures(self) -> list[dict]:
        """Fetch recently completed Premier League fixtures."""
        try:
            return self.football_api.get_completed_fixtures(last_n=50)
        except Exception as e:
            print(f"Warning: Could not fetch completed fixtures: {e}")
            return []

    def _make_lookup_key(self, home: str, away: str, date: str) -> str:
        """Create normalized lookup key for matching."""
        home_norm = home.lower().replace(" ", "")[:15]
        away_norm = away.lower().replace(" ", "")[:15]
        date_norm = date.replace("-", "")
        return f"{home_norm}_{away_norm}_{date_norm}"

    def print_report(self) -> None:
        """Print a validation report to console."""
        metrics = self.db.get_metrics()

        print("\n" + "=" * 60)
        print("PREDICTION VALIDATION REPORT")
        print("=" * 60)

        print(f"\nTotal predictions: {metrics.total}")
        print(f"  Validated: {metrics.validated}")
        print(f"  Pending:   {metrics.pending}")

        if metrics.validated > 0:
            print(f"\n--- Accuracy ---")
            print(f"Market favorite accuracy: {metrics.market_accuracy}% ({metrics.market_correct}/{metrics.validated})")
            print(f"Model favorite accuracy:  {metrics.model_accuracy}% ({metrics.model_correct}/{metrics.validated})")

            if metrics.disagreements > 0:
                disagree_pct = round(metrics.model_wins_when_disagreed / metrics.disagreements * 100, 1)
                print(f"\n--- When Model Disagreed with Market ---")
                print(f"Disagreements: {metrics.disagreements}")
                print(f"Model was correct: {metrics.model_wins_when_disagreed} ({disagree_pct}%)")
        else:
            print("\nNo validated predictions yet. Run predictions, wait for matches to complete, then validate.")

        print("=" * 60)
