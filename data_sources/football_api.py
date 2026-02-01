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
# Will automatically try current season first, then fall back to previous seasons
CURRENT_SEASON = 2025
# Seasons to search (in order of priority: most recent first)
# Note: Season 2024 data shows matches from May 2025, so it has the most recent data
SEARCH_SEASONS = [2024, 2023, 2022, 2021, 2020]

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

    def get_completed_fixtures(self, last_n: int = 50) -> list[dict[str, Any]]:
        """Get recently completed Premier League fixtures with results.
        
        Uses date range query (free-tier compatible).
        """
        from datetime import timedelta

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        past = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        data = self._get("fixtures", params={
            "league": PREMIER_LEAGUE_ID,
            "season": CURRENT_SEASON,
            "from": past,
            "to": today,
            "status": "FT",  # Full Time (completed)
        })

        fixtures = data.get("response", [])
        # Sort by date descending (most recent first)
        fixtures.sort(key=lambda f: f.get("fixture", {}).get("date", ""), reverse=True)
        return fixtures[:last_n]

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

    def get_team_last_n_fixtures(self, team_id: int, n: int = 5) -> list[dict[str, Any]]:
        """Get last N completed fixtures for a team across multiple seasons.
        
        Returns fixtures sorted by date (most recent first).
        Searches across SEARCH_SEASONS until we find enough matches.
        Note: Free plan doesn't support 'last' parameter, so we use date ranges.
        """
        from datetime import timedelta
        
        all_fixtures = []
        
        # Search through seasons from most recent to oldest
        for season in SEARCH_SEASONS:
            if len(all_fixtures) >= n:
                break
            
            try:
                # Determine date range for this season
                # Premier League season runs from August to May
                season_start = f"{season}-08-01"
                season_end = f"{season + 1}-05-31"
                
                # Get completed fixtures for this season
                data = self._get("fixtures", params={
                    "team": team_id,
                    "season": season,
                    "from": season_start,
                    "to": season_end,
                    "status": "FT",
                })
                
                fixtures = data.get("response", [])
                
                # Add fixtures that aren't already in our list
                for fixture in fixtures:
                    fixture_id = fixture.get("fixture", {}).get("id")
                    if not any(f.get("fixture", {}).get("id") == fixture_id for f in all_fixtures):
                        all_fixtures.append(fixture)
                
            except Exception:
                continue
        
        # Sort by date (most recent first) and limit to N
        all_fixtures.sort(key=lambda f: f.get("fixture", {}).get("date", ""), reverse=True)
        return all_fixtures[:n]

    def get_head_to_head(self, team1_id: int, team2_id: int, last_n: int = 5) -> list[dict[str, Any]]:
        """Get last N head-to-head matches between two teams across multiple seasons.
        
        Returns fixtures sorted by date (most recent first).
        Searches across SEARCH_SEASONS to find matches.
        Note: Free plan doesn't support 'h2h' parameter, so we fetch team1's fixtures
        and filter for matches against team2.
        """
        all_fixtures = []
        
        # Search by season (Free plan compatible)
        for season in SEARCH_SEASONS:
            if len(all_fixtures) >= last_n:
                break
                
            try:
                # Get all fixtures for team1 in this season
                season_start = f"{season}-08-01"
                season_end = f"{season + 1}-05-31"
                
                data = self._get("fixtures", params={
                    "team": team1_id,
                    "season": season,
                    "league": PREMIER_LEAGUE_ID,
                    "from": season_start,
                    "to": season_end,
                })
                fixtures = data.get("response", [])
                
                # Filter for matches against team2
                for fixture in fixtures:
                    home_id = fixture.get("teams", {}).get("home", {}).get("id")
                    away_id = fixture.get("teams", {}).get("away", {}).get("id")
                    
                    # Check if this is a match between team1 and team2
                    if (home_id == team1_id and away_id == team2_id) or \
                       (home_id == team2_id and away_id == team1_id):
                        fixture_id = fixture.get("fixture", {}).get("id")
                        if not any(f.get("fixture", {}).get("id") == fixture_id for f in all_fixtures):
                            all_fixtures.append(fixture)
                
            except Exception:
                continue
        
        # Sort by date (most recent first) and limit
        all_fixtures.sort(key=lambda f: f.get("fixture", {}).get("date", ""), reverse=True)
        return all_fixtures[:last_n]

    def get_team_id_by_name(self, team_name: str) -> int | None:
        """Get team ID by searching team name.
        
        Returns first matching team ID or None.
        Note: Free plan doesn't support search parameter, so we fetch all PL teams and filter.
        """
        # Get all Premier League teams (use most recent season with data)
        for season in SEARCH_SEASONS:
            try:
                data = self._get("teams", params={
                    "league": PREMIER_LEAGUE_ID,
                    "season": season,
                })
                
                teams = data.get("response", [])
                if teams:
                    # Search for team by name (case-insensitive, partial match)
                    team_name_lower = team_name.lower()
                    for team_data in teams:
                        team = team_data.get("team", {})
                        team_full_name = team.get("name", "").lower()
                        if team_name_lower in team_full_name or team_full_name in team_name_lower:
                            return team.get("id")
                    break  # Found teams but no match, don't try other seasons
            except Exception:
                continue
        
        return None

    def get_team_logo(self, team_name: str) -> str | None:
        """Get team logo URL by team name.
        
        Returns logo URL or None if not found.
        Note: Free plan doesn't support search parameter, so we fetch all PL teams and filter.
        """
        # Get all Premier League teams (use most recent season with data)
        for season in SEARCH_SEASONS:
            try:
                data = self._get("teams", params={
                    "league": PREMIER_LEAGUE_ID,
                    "season": season,
                })
                
                teams = data.get("response", [])
                if teams:
                    # Search for team by name (case-insensitive, partial match)
                    team_name_lower = team_name.lower()
                    for team_data in teams:
                        team = team_data.get("team", {})
                        team_full_name = team.get("name", "").lower()
                        if team_name_lower in team_full_name or team_full_name in team_name_lower:
                            return team.get("logo")
                    break  # Found teams but no match, don't try other seasons
            except Exception:
                continue
        
        return None

    def get_predicted_lineup(self, team_id: int) -> dict[str, Any]:
        """Get predicted lineup based on recent matches.
        
        Returns dict with formation and players by position.
        """
        # Get last 3 matches to find common lineup
        recent_fixtures = self.get_team_last_n_fixtures(team_id, n=3)
        
        if not recent_fixtures:
            return {"formation": "4-3-3", "players": []}
        
        # Get lineup from most recent match
        latest = recent_fixtures[0]
        fixture_id = latest.get("fixture", {}).get("id")
        
        if not fixture_id:
            return {"formation": "4-3-3", "players": []}
        
        # Fetch lineups for the fixture
        data = self._get("fixtures/lineups", params={"fixture": fixture_id})
        lineups = data.get("response", [])
        
        # Find the lineup for our team
        team_lineup = None
        for lineup in lineups:
            if lineup.get("team", {}).get("id") == team_id:
                team_lineup = lineup
                break
        
        if not team_lineup:
            return {"formation": "4-3-3", "players": []}
        
        formation = team_lineup.get("formation", "4-3-3")
        start_xi = team_lineup.get("startXI", [])
        substitutes = team_lineup.get("substitutes", [])
        
        return {
            "formation": formation,
            "start_xi": start_xi,
            "substitutes": substitutes,
        }
