"""Client for The Odds API - fetches live betting odds."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from schemas.odds import RawOdds


@dataclass(frozen=True, slots=True)
class OddsAPIClient:
    """Fetch live 1X2 odds from The Odds API.
    
    API docs: https://the-odds-api.com/liveapi/guides/v4/
    Free tier: 500 requests/month
    """

    api_key: str
    base_url: str = "https://api.the-odds-api.com/v4"

    @classmethod
    def from_env(cls) -> "OddsAPIClient":
        """Create client from ODDS_API_KEY environment variable."""
        api_key = os.getenv("ODDS_API_KEY")
        if not api_key:
            raise ValueError("ODDS_API_KEY environment variable not set")
        return cls(api_key=api_key)

    def get_premier_league_odds(self) -> list[dict[str, Any]]:
        """Fetch upcoming Premier League match odds.
        
        Returns a list of matches with odds from multiple bookmakers.
        """
        url = f"{self.base_url}/sports/soccer_epl/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "uk",
            "markets": "h2h",  # 1X2 (head-to-head)
            "oddsFormat": "decimal",
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_odds_for_match(
        self, home_team: str, away_team: str
    ) -> RawOdds | None:
        """Get 1X2 odds for a specific match by team names.
        
        Returns RawOdds if match found, None otherwise.
        Uses the first available bookmaker's odds.
        """
        matches = self.get_premier_league_odds()

        for match in matches:
            # Match by team names (case-insensitive partial match)
            api_home = match.get("home_team", "").lower()
            api_away = match.get("away_team", "").lower()

            if (
                home_team.lower() in api_home or api_home in home_team.lower()
            ) and (
                away_team.lower() in api_away or api_away in away_team.lower()
            ):
                return self._extract_odds(match)

        return None

    def get_all_upcoming_matches(self) -> list[dict[str, Any]]:
        """Get all upcoming Premier League matches with odds.
        
        Returns list of dicts with: home_team, away_team, kickoff_utc, odds
        """
        matches = self.get_premier_league_odds()
        result = []

        for match in matches:
            odds = self._extract_odds(match)
            if odds:
                result.append({
                    "home_team": match.get("home_team"),
                    "away_team": match.get("away_team"),
                    "kickoff_utc": match.get("commence_time"),
                    "odds": odds,
                })

        return result

    def _extract_odds(self, match: dict[str, Any]) -> RawOdds | None:
        """Extract RawOdds from a match object.
        
        Uses the first bookmaker with valid h2h odds.
        """
        bookmakers = match.get("bookmakers", [])
        if not bookmakers:
            return None

        for bookmaker in bookmakers:
            markets = bookmaker.get("markets", [])
            for market in markets:
                if market.get("key") == "h2h":
                    outcomes = market.get("outcomes", [])
                    odds_map = {o["name"]: o["price"] for o in outcomes}

                    home_team = match.get("home_team")
                    away_team = match.get("away_team")

                    home_win = odds_map.get(home_team)
                    draw = odds_map.get("Draw")
                    away_win = odds_map.get(away_team)

                    if home_win and draw and away_win:
                        return RawOdds(
                            home_win=home_win,
                            draw=draw,
                            away_win=away_win,
                        )

        return None
