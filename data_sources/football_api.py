"""Client for API-Football - fetches fixtures and injuries."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from schemas.match import Match
from schemas.team_news import MatchTeamNews, PlayerAbsence, TeamNews


# Premier League ID in API-Football
PREMIER_LEAGUE_ID = 39
# Current season (Premier League uses starting year, e.g., 2024 for 2024-2025)
CURRENT_SEASON = 2024


@dataclass(frozen=True, slots=True)
class FootballAPIClient:
    """Fetch fixtures and injuries from API-Football.
    
    API docs: https://www.api-football.com/documentation-v3
    Free tier: 100 requests/day
    """

    api_key: str
    base_url: str = "https://v3.football.api-sports.io"

    @classmethod
    def from_env(cls) -> "FootballAPIClient":
        """Create client from FOOTBALL_API_KEY environment variable."""
        api_key = os.getenv("FOOTBALL_API_KEY")
        if not api_key:
            raise ValueError("FOOTBALL_API_KEY environment variable not set")
        return cls(api_key=api_key)

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make authenticated GET request to API-Football."""
        headers = {
            "x-apisports-key": self.api_key,
        }
        url = f"{self.base_url}/{endpoint}"

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_upcoming_fixtures(self, next_n: int = 10) -> list[dict[str, Any]]:
        """Get next N upcoming Premier League fixtures.
        
        Returns raw API response with fixture details.
        Uses date range query (free-tier compatible).
        """
        from datetime import timedelta

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        future = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")

        data = self._get("fixtures", params={
            "league": PREMIER_LEAGUE_ID,
            "season": CURRENT_SEASON,
            "from": today,
            "to": future,
        })

        fixtures = data.get("response", [])
        # Sort by date and limit
        fixtures.sort(key=lambda f: f.get("fixture", {}).get("date", ""))
        return fixtures[:next_n]

    def get_fixtures_by_round(self, round_name: str) -> list[dict[str, Any]]:
        """Get fixtures for a specific round/matchweek.
        
        round_name example: "Regular Season - 20"
        """
        data = self._get("fixtures", params={
            "league": PREMIER_LEAGUE_ID,
            "season": CURRENT_SEASON,
            "round": round_name,
        })
        return data.get("response", [])

    def get_current_round(self) -> str | None:
        """Get the current round/matchweek name."""
        data = self._get("fixtures/rounds", params={
            "league": PREMIER_LEAGUE_ID,
            "season": CURRENT_SEASON,
            "current": "true",
        })
        rounds = data.get("response", [])
        return rounds[0] if rounds else None

    def get_team_injuries(self, team_id: int) -> list[dict[str, Any]]:
        """Get current injuries for a team."""
        data = self._get("injuries", params={
            "league": PREMIER_LEAGUE_ID,
            "season": CURRENT_SEASON,
            "team": team_id,
        })
        return data.get("response", [])

    def get_fixture_injuries(self, fixture_id: int) -> list[dict[str, Any]]:
        """Get injuries for a specific fixture."""
        data = self._get("injuries", params={
            "fixture": fixture_id,
        })
        return data.get("response", [])

    def fixture_to_match(self, fixture: dict[str, Any]) -> Match:
        """Convert API fixture to our Match schema."""
        teams = fixture.get("fixture", {})
        fixture_info = fixture.get("fixture", {})
        teams_info = fixture.get("teams", {})
        league_info = fixture.get("league", {})

        kickoff_str = fixture_info.get("date", "")
        if kickoff_str:
            kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
        else:
            kickoff = datetime.now(timezone.utc)

        return Match(
            league=league_info.get("name", "Premier League"),
            home_team=teams_info.get("home", {}).get("name", "Unknown"),
            away_team=teams_info.get("away", {}).get("name", "Unknown"),
            kickoff_utc=kickoff,
        )

    def get_match_team_news(self, fixture: dict[str, Any]) -> MatchTeamNews:
        """Get team news (injuries) for a fixture.
        
        Fetches injuries for both teams and converts to MatchTeamNews schema.
        """
        fixture_id = fixture.get("fixture", {}).get("id")
        teams_info = fixture.get("teams", {})
        home_team_id = teams_info.get("home", {}).get("id")
        away_team_id = teams_info.get("away", {}).get("id")

        home_absences: list[PlayerAbsence] = []
        away_absences: list[PlayerAbsence] = []

        # Try fixture-specific injuries first
        if fixture_id:
            injuries = self.get_fixture_injuries(fixture_id)
            for injury in injuries:
                absence = self._injury_to_absence(injury)
                if absence:
                    team_id = injury.get("team", {}).get("id")
                    if team_id == home_team_id:
                        home_absences.append(absence)
                    elif team_id == away_team_id:
                        away_absences.append(absence)

        # If no fixture injuries, try team injuries
        if not home_absences and home_team_id:
            for injury in self.get_team_injuries(home_team_id):
                absence = self._injury_to_absence(injury)
                if absence:
                    home_absences.append(absence)

        if not away_absences and away_team_id:
            for injury in self.get_team_injuries(away_team_id):
                absence = self._injury_to_absence(injury)
                if absence:
                    away_absences.append(absence)

        return MatchTeamNews(
            home=TeamNews(absences=home_absences),
            away=TeamNews(absences=away_absences),
        )

    def _injury_to_absence(self, injury: dict[str, Any]) -> PlayerAbsence | None:
        """Convert API injury record to PlayerAbsence schema."""
        player = injury.get("player", {})
        player_name = player.get("name")
        if not player_name:
            return None

        # Map position from API (or default to "Unknown")
        position = player.get("position", "MF")
        # Simplify position to 2-letter code
        pos_map = {
            "Goalkeeper": "GK",
            "Defender": "DF",
            "Midfielder": "MF",
            "Attacker": "ST",
        }
        position = pos_map.get(position, position[:2].upper() if position else "MF")

        # Determine reason
        reason_text = injury.get("player", {}).get("reason", "").lower()
        if "suspend" in reason_text or "red card" in reason_text:
            reason = "suspension"
        elif "rotation" in reason_text or "rest" in reason_text:
            reason = "rotation"
        else:
            reason = "injury"

        # Estimate xG impact based on position
        # This is a simple heuristic - attackers have more impact than defenders
        xg_impact_map = {
            "ST": -0.15,
            "RW": -0.10,
            "LW": -0.10,
            "CF": -0.12,
            "MF": -0.05,
            "AM": -0.08,
            "CM": -0.05,
            "DM": -0.04,
            "DF": -0.03,
            "CB": -0.03,
            "LB": -0.03,
            "RB": -0.03,
            "GK": -0.02,
        }
        estimated_xg_impact = xg_impact_map.get(position, -0.05)

        return PlayerAbsence(
            player_name=player_name,
            position=position,
            reason=reason,
            estimated_xg_impact=estimated_xg_impact,
        )

    def get_upcoming_matches_with_news(self, next_n: int = 10) -> list[dict[str, Any]]:
        """Get upcoming matches with team news (injuries).
        
        Returns list of dicts with: match (Match), team_news (MatchTeamNews), fixture_id
        """
        fixtures = self.get_upcoming_fixtures(next_n)
        result = []

        for fixture in fixtures:
            match = self.fixture_to_match(fixture)
            team_news = self.get_match_team_news(fixture)
            fixture_id = fixture.get("fixture", {}).get("id")

            result.append({
                "match": match,
                "team_news": team_news,
                "fixture_id": fixture_id,
            })

        return result
