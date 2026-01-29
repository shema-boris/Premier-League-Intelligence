from __future__ import annotations

import json
import os
from pathlib import Path

from crew.crew_config import run_offline_pipeline
from dotenv import load_dotenv
from schemas.match import Match
from schemas.odds import RawOdds
from schemas.report import MarketAnalysisReport
from schemas.team_news import MatchTeamNews


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _render_report_markdown(report: MarketAnalysisReport) -> str:
    lines: list[str] = []
    lines.append("# Premier League Market Intelligence Report")
    lines.append("")
    lines.append("## Match")
    lines.append(report.match_summary)
    lines.append("")
    lines.append("## Most likely outcomes (descriptive)")
    lines.append(
        f"Market favorite: {report.market_favorite.label} ({report.market_favorite.outcome}) — "
        f"{report.market_favorite.probability:.3f}"
    )
    lines.append(
        f"Model favorite: {report.model_favorite.label} ({report.model_favorite.outcome}) — "
        f"{report.model_favorite.probability:.3f}"
    )
    lines.append("")
    lines.append("## Most likely winner (team only; descriptive)")
    if report.market_favorite.outcome == "draw":
        lines.append(
            f"Market: Draw is the most likely outcome ({report.market_favorite.probability:.3f}); no single team favored."
        )
    else:
        lines.append(
            f"Market: {report.market_favorite.label} is the most likely winner ({report.market_favorite.probability:.3f})."
        )
    if report.model_favorite.outcome == "draw":
        lines.append(
            f"Model: Draw is the most likely outcome ({report.model_favorite.probability:.3f}); no single team favored."
        )
    else:
        lines.append(
            f"Model: {report.model_favorite.label} is the most likely winner ({report.model_favorite.probability:.3f})."
        )
    lines.append("")
    lines.append("## Key team news")
    lines.append(report.key_team_news)
    lines.append("")
    lines.append("## Market vs model discrepancies")
    lines.append("| Outcome | Market P | Model P | Delta |")
    lines.append("|---|---:|---:|---:|")
    for d in report.discrepancies:
        lines.append(
            f"| {d.outcome} | {d.market_probability:.3f} | {d.model_probability:.3f} | {d.delta:+.3f} |"
        )
    lines.append("")
    lines.append("## Conclusion")
    lines.append(report.conclusion)
    lines.append("")
    lines.append("_Note: This is a descriptive analysis only. No betting recommendations._")
    return "\n".join(lines)


def _load_mock_data(data_dir: Path) -> tuple[Match, RawOdds, MatchTeamNews]:
    """Load mock data from JSON files."""
    match = Match.model_validate(_load_json(data_dir / "mock_match.json"))
    odds_payload = _load_json(data_dir / "mock_odds.json")
    raw_odds = RawOdds.model_validate(odds_payload["raw_odds"])
    team_news = MatchTeamNews.model_validate(_load_json(data_dir / "mock_team_news.json"))
    return match, raw_odds, team_news


def _load_live_data() -> tuple[Match, RawOdds, MatchTeamNews] | None:
    """Load live data from APIs. Returns None if no upcoming matches."""
    from datetime import datetime, timezone
    from data_sources import OddsAPIClient, FootballAPIClient
    from schemas.team_news import TeamNews

    print("Fetching live data from APIs...")

    # Get upcoming matches from Odds API (primary source - always has data)
    odds_client = OddsAPIClient.from_env()
    matches_with_odds = odds_client.get_all_upcoming_matches()

    if not matches_with_odds:
        print("No upcoming matches with odds found.")
        return None

    # Use the first match
    first = matches_with_odds[0]
    home_team = first["home_team"]
    away_team = first["away_team"]
    raw_odds = first["odds"]

    print(f"Found match: {home_team} vs {away_team}")
    print(f"Odds: H={raw_odds.home_win}, D={raw_odds.draw}, A={raw_odds.away_win}")

    # Parse kickoff time
    kickoff_str = first.get("kickoff_utc", "")
    if kickoff_str:
        kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
    else:
        kickoff = datetime.now(timezone.utc)
    print(f"Kickoff: {kickoff}")

    match = Match(
        league="Premier League",
        home_team=home_team,
        away_team=away_team,
        kickoff_utc=kickoff,
    )

    # Try to get injuries from Football API (may be empty if off-season)
    team_news = MatchTeamNews(home=TeamNews(absences=[]), away=TeamNews(absences=[]))
    try:
        football_client = FootballAPIClient.from_env()
        fixtures = football_client.get_upcoming_fixtures(next_n=10)
        for fixture in fixtures:
            fx_home = fixture.get("teams", {}).get("home", {}).get("name", "")
            fx_away = fixture.get("teams", {}).get("away", {}).get("name", "")
            if (home_team.lower() in fx_home.lower() or fx_home.lower() in home_team.lower()) and \
               (away_team.lower() in fx_away.lower() or fx_away.lower() in away_team.lower()):
                team_news = football_client.get_match_team_news(fixture)
                print("Fetched injury data from Football API")
                break
    except Exception as e:
        print(f"Football API unavailable (injuries will be empty): {e}")

    return match, raw_odds, team_news


def main() -> None:
    load_dotenv()

    # Check mode: LIVE_DATA takes precedence, then OFFLINE_MODE
    live_mode = os.getenv("LIVE_DATA", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    offline_mode = os.getenv("OFFLINE_MODE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"

    if live_mode:
        print("PHASE 4 — LIVE DATA mode (fetching from APIs)")
        print("=" * 50)
        result = _load_live_data()
        if result is None:
            print("Falling back to mock data...")
            match, raw_odds, team_news = _load_mock_data(data_dir)
        else:
            match, raw_odds, team_news = result
    else:
        if offline_mode:
            print("PHASE 3 — OFFLINE deterministic pipeline (mock data only)")
        else:
            print("PHASE 3 — Deterministic pipeline (mock data)")
        match, raw_odds, team_news = _load_mock_data(data_dir)

    print("=" * 50)

    # Run the deterministic pipeline
    report = run_offline_pipeline(match=match, raw_odds=raw_odds, team_news=team_news)

    markdown = _render_report_markdown(report)
    print("\n\nFINAL REPORT (Markdown)")
    print(markdown)
    print("\nANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
