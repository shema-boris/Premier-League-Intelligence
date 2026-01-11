from __future__ import annotations

import json
import os
from pathlib import Path

from crew.crew_config import build_premier_league_crew, run_offline_pipeline
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
    lines.append("_Note: This is a mock, descriptive analysis. No betting recommendations._")
    return "\n".join(lines)


def main() -> None:
    load_dotenv()
    offline_mode = os.getenv("OFFLINE_MODE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    if offline_mode:
        print("PHASE 3 — OFFLINE deterministic pipeline (no LLM; mock data only)")
    else:
        print("PHASE 3 — CrewAI orchestration (sequential; deterministic tools; mock data only)")

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"

    match = Match.model_validate(_load_json(data_dir / "mock_match.json"))

    odds_payload = _load_json(data_dir / "mock_odds.json")
    raw_odds = RawOdds.model_validate(odds_payload["raw_odds"])

    team_news = MatchTeamNews.model_validate(_load_json(data_dir / "mock_team_news.json"))

    if offline_mode:
        report = run_offline_pipeline(match=match, raw_odds=raw_odds, team_news=team_news)
    else:
        try:
            crew = build_premier_league_crew(match=match, raw_odds=raw_odds, team_news=team_news, verbose=True)
            result = crew.kickoff()

            report: MarketAnalysisReport | None = None
            if getattr(result, "pydantic", None) is not None and isinstance(result.pydantic, MarketAnalysisReport):
                report = result.pydantic
            elif getattr(result, "tasks_output", None):
                last = result.tasks_output[-1]
                if getattr(last, "pydantic", None) is not None and isinstance(last.pydantic, MarketAnalysisReport):
                    report = last.pydantic
                else:
                    report = MarketAnalysisReport.model_validate_json(last.raw)
            else:
                report = MarketAnalysisReport.model_validate_json(result.raw)
        except Exception as e:
            print("\nCrewAI/Gemini execution failed; falling back to offline deterministic pipeline.")
            print(f"Failure detail: {e}")
            report = run_offline_pipeline(match=match, raw_odds=raw_odds, team_news=team_news)

    markdown = _render_report_markdown(report)
    print("\n\nFINAL REPORT (Markdown)")
    print(markdown)
    print("\nPHASE 3 COMPLETE")


if __name__ == "__main__":
    main()
