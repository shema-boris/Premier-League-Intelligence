from __future__ import annotations

from dataclasses import dataclass

from schemas.team_news import MatchTeamNews, TeamNews


@dataclass(frozen=True, slots=True)
class TeamNewsAgent:
    """Validate and summarize mock team news.

    Phase 2 is intentionally simple:
    - No scraping
    - No NLP
    - No inference

    This agent primarily exists to enforce a clean schema contract for future ingestion.
    """

    @staticmethod
    def validate(team_news: MatchTeamNews) -> MatchTeamNews:
        # The input is already a Pydantic object, but re-validating via model_dump()
        # ensures strict schema compliance even if callers pass a subclass.
        return MatchTeamNews.model_validate(team_news.model_dump())

    @staticmethod
    def total_xg_impact(team_news: TeamNews) -> float:
        return float(sum(a.estimated_xg_impact for a in team_news.absences))

    @staticmethod
    def total_match_xg_impact(team_news: MatchTeamNews) -> tuple[float, float]:
        """Return (home_total, away_total)."""

        return (
            TeamNewsAgent.total_xg_impact(team_news.home),
            TeamNewsAgent.total_xg_impact(team_news.away),
        )
