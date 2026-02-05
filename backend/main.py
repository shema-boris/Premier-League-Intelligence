from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from crew.crew_config import run_offline_pipeline
from dotenv import load_dotenv
from schemas.match import Match
from schemas.odds import RawOdds
from schemas.report import MarketAnalysisReport
from schemas.team_news import MatchTeamNews, TeamNews
from validation.database import PredictionDB


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
    from data_sources import OddsAPIClient

    print("Fetching live data from APIs...")

    odds_client = OddsAPIClient.from_env()
    matches_with_odds = odds_client.get_all_upcoming_matches()

    if not matches_with_odds:
        print("No upcoming matches with odds found.")
        return None

    first = matches_with_odds[0]
    match, raw_odds, team_news = _convert_api_match(first)

    print(f"Found match: {match.home_team} vs {match.away_team}")
    print(f"Odds: H={raw_odds.home_win}, D={raw_odds.draw}, A={raw_odds.away_win}")
    print(f"Kickoff: {match.kickoff_utc}")

    return match, raw_odds, team_news


def _convert_api_match(api_match: dict) -> tuple[Match, RawOdds, MatchTeamNews]:
    """Convert API match data to our schemas."""
    home_team = api_match["home_team"]
    away_team = api_match["away_team"]
    raw_odds = api_match["odds"]

    kickoff_str = api_match.get("kickoff_utc", "")
    if kickoff_str:
        kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
    else:
        kickoff = datetime.now(timezone.utc)

    match = Match(
        league="Premier League",
        home_team=home_team,
        away_team=away_team,
        kickoff_utc=kickoff,
    )

    team_news = MatchTeamNews(home=TeamNews(absences=[]), away=TeamNews(absences=[]))
    return match, raw_odds, team_news


def _load_all_live_matches() -> list[tuple[Match, RawOdds, MatchTeamNews]]:
    """Load all upcoming matches from APIs."""
    from data_sources import OddsAPIClient

    print("Fetching all upcoming matches...")

    odds_client = OddsAPIClient.from_env()
    matches_with_odds = odds_client.get_all_upcoming_matches()

    print(f"Found {len(matches_with_odds)} matches with odds")

    results = []
    for api_match in matches_with_odds:
        match, raw_odds, team_news = _convert_api_match(api_match)
        results.append((match, raw_odds, team_news))

    return results


def _render_multi_match_summary(reports: list[MarketAnalysisReport]) -> str:
    """Render a summary table of all analyzed matches."""
    lines: list[str] = []
    lines.append("# Premier League Matchweek Analysis")
    lines.append("")
    lines.append(f"_Analyzed {len(reports)} matches_")
    lines.append("")
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| Match | Market Favorite | Prob | Model Favorite | Prob |")
    lines.append("|-------|-----------------|------|----------------|------|")

    for report in reports:
        # Extract teams from match_summary
        parts = report.match_summary.split(" — ")
        match_name = parts[1] if len(parts) > 1 else report.match_summary

        mkt = report.market_favorite
        mdl = report.model_favorite

        mkt_label = mkt.label if mkt.outcome != "draw" else "Draw"
        mdl_label = mdl.label if mdl.outcome != "draw" else "Draw"

        lines.append(
            f"| {match_name} | {mkt_label} | {mkt.probability:.1%} | {mdl_label} | {mdl.probability:.1%} |"
        )

    lines.append("")
    lines.append("## Biggest Market-Model Discrepancies")
    lines.append("")

    # Collect all discrepancies with match context
    all_discrepancies = []
    for report in reports:
        parts = report.match_summary.split(" — ")
        match_name = parts[1] if len(parts) > 1 else report.match_summary
        for d in report.discrepancies:
            all_discrepancies.append((match_name, d))

    # Sort by absolute delta
    all_discrepancies.sort(key=lambda x: abs(x[1].delta), reverse=True)

    lines.append("| Match | Outcome | Market P | Model P | Delta |")
    lines.append("|-------|---------|----------|---------|-------|")
    for match_name, d in all_discrepancies[:10]:
        lines.append(
            f"| {match_name} | {d.outcome} | {d.market_probability:.1%} | {d.model_probability:.1%} | {d.delta:+.1%} |"
        )

    lines.append("")
    lines.append("_Note: This is a descriptive analysis only. No betting recommendations._")
    return "\n".join(lines)


def _save_prediction(db: PredictionDB, match: Match, raw_odds: RawOdds, report: MarketAnalysisReport) -> None:
    """Save prediction to database for future validation."""
    db.save_prediction(
        home_team=match.home_team,
        away_team=match.away_team,
        match_date=match.kickoff_utc.isoformat(),
        market_favorite=report.market_favorite.label,
        market_favorite_prob=report.market_favorite.probability,
        model_favorite=report.model_favorite.label,
        model_favorite_prob=report.model_favorite.probability,
        home_prob=report.discrepancies[0].model_probability if report.discrepancies else 0,
        draw_prob=report.discrepancies[1].model_probability if len(report.discrepancies) > 1 else 0,
        away_prob=report.discrepancies[2].model_probability if len(report.discrepancies) > 2 else 0,
        home_odds=raw_odds.home_win,
        draw_odds=raw_odds.draw,
        away_odds=raw_odds.away_win,
    )


def main() -> None:
    load_dotenv()

    live_mode = os.getenv("LIVE_DATA", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    multi_mode = os.getenv("MULTI_MATCH", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    offline_mode = os.getenv("OFFLINE_MODE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    validate_mode = os.getenv("VALIDATE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    db = PredictionDB()

    # Validation mode: check predictions against results
    if validate_mode:
        from validation.backtest import BacktestRunner
        print("PHASE 4.3 — VALIDATION mode")
        print("=" * 60)
        runner = BacktestRunner(db)
        results = runner.validate_pending()
        print(f"Updated: {results['updated']} | Still pending: {results['still_pending']}")
        runner.print_report()
        return

    # Multi-match mode: analyze all upcoming matches
    if multi_mode and live_mode:
        print("PHASE 4.2 — MULTI-MATCH mode (analyzing all upcoming matches)")
        print("=" * 60)

        all_matches = _load_all_live_matches()
        if not all_matches:
            print("No matches found. Exiting.")
            return

        print(f"\nAnalyzing {len(all_matches)} matches...\n")
        print("=" * 60)

        reports: list[MarketAnalysisReport] = []
        for i, (match, raw_odds, team_news) in enumerate(all_matches, 1):
            print(f"[{i}/{len(all_matches)}] {match.home_team} vs {match.away_team}")
            report = run_offline_pipeline(
                match=match, raw_odds=raw_odds, team_news=team_news, verbose=False
            )
            reports.append(report)
            _save_prediction(db, match, raw_odds, report)

        print("\n" + "=" * 60)
        print("\nMATCHWEEK SUMMARY")
        print(_render_multi_match_summary(reports))
        print("\nMULTI-MATCH ANALYSIS COMPLETE")
        return

    # Single match mode
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
            print("OFFLINE deterministic pipeline (mock data only)")
        else:
            print("Deterministic pipeline (mock data)")
        match, raw_odds, team_news = _load_mock_data(data_dir)

    print("=" * 50)

    report = run_offline_pipeline(match=match, raw_odds=raw_odds, team_news=team_news)
    
    if live_mode:
        _save_prediction(db, match, raw_odds, report)
        print("\n[Prediction saved to database]")

    markdown = _render_report_markdown(report)
    print("\n\nFINAL REPORT (Markdown)")
    print(markdown)
    print("\nANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
