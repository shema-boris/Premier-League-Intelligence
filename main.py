from __future__ import annotations

import json
from pathlib import Path

from agents.discrepancy_agent import DiscrepancyAnalysisAgent
from agents.impact_agent import ImpactModelingAgent
from agents.odds_agent import OddsAgent
from agents.report_agent import ReportWriterAgent
from agents.team_news_agent import TeamNewsAgent
from schemas.match import Match
from schemas.odds import RawOdds
from schemas.team_news import MatchTeamNews


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    print("PHASE 2 — Single-threaded analytical pipeline (No CrewAI)")

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"

    match = Match.model_validate(_load_json(data_dir / "mock_match.json"))

    odds_payload = _load_json(data_dir / "mock_odds.json")
    raw_odds = RawOdds.model_validate(odds_payload["raw_odds"])

    team_news = MatchTeamNews.model_validate(_load_json(data_dir / "mock_team_news.json"))

    implied = OddsAgent.implied_probabilities(raw_odds)
    validated_team_news = TeamNewsAgent.validate(team_news)
    xg_adj, adjusted = ImpactModelingAgent.model(implied, validated_team_news)
    discrepancies = DiscrepancyAnalysisAgent.analyze(implied, adjusted)
    report = ReportWriterAgent.write(match, validated_team_news, discrepancies)

    print("\n[1] Raw Odds")
    print(raw_odds.model_dump_json(indent=2))

    print("\n[2] Market Implied Probabilities (normalized; overround reported separately)")
    print(implied.model_dump_json(indent=2))

    print("\n[3] Team News (validated)")
    print(validated_team_news.model_dump_json(indent=2))

    print("\n[4] Expected Goals Adjustment")
    print(xg_adj.model_dump_json(indent=2))

    print("\n[5] Adjusted Probabilities (team-news interpretability layer)")
    print(adjusted.model_dump_json(indent=2))

    print("\n[6] Market Discrepancies (sorted by absolute delta)")
    print(json.dumps([d.model_dump() for d in discrepancies], indent=2))

    print("\n[7] Market Analysis Report (schema) — NO RECOMMENDATIONS")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
