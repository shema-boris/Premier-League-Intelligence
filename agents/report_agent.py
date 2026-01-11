from __future__ import annotations

from dataclasses import dataclass

from schemas.discrepancy import MarketDiscrepancy
from schemas.impact import AdjustedProbabilities
from schemas.match import Match
from schemas.odds import ImpliedProbabilities
from schemas.report import MarketAnalysisReport, OutcomeFavorite
from schemas.team_news import MatchTeamNews, PlayerAbsence


@dataclass(frozen=True, slots=True)
class ReportWriterAgent:
    """Write a neutral, recruiter-facing market intelligence memo.

    Hard constraints:
    - No betting recommendations
    - No advice
    - Descriptive only
    """

    @staticmethod
    def write(
        match: Match,
        implied: ImpliedProbabilities,
        adjusted: AdjustedProbabilities,
        team_news: MatchTeamNews,
        discrepancies: list[MarketDiscrepancy],
    ) -> MarketAnalysisReport:
        match_summary = (
            f"{match.league} — {match.home_team} vs {match.away_team} — "
            f"Kickoff (UTC): {match.kickoff_utc.isoformat()}"
        )

        market_favorite = ReportWriterAgent._favorite_from_probabilities(
            match=match,
            home=implied.home,
            draw=implied.draw,
            away=implied.away,
        )
        model_favorite = ReportWriterAgent._favorite_from_probabilities(
            match=match,
            home=adjusted.home,
            draw=adjusted.draw,
            away=adjusted.away,
        )

        key_team_news = ReportWriterAgent._format_team_news(team_news)
        conclusion = ReportWriterAgent._format_conclusion(discrepancies)

        return MarketAnalysisReport(
            match_summary=match_summary,
            market_favorite=market_favorite,
            model_favorite=model_favorite,
            key_team_news=key_team_news,
            discrepancies=discrepancies,
            conclusion=conclusion,
        )

    @staticmethod
    def _favorite_from_probabilities(
        *,
        match: Match,
        home: float,
        draw: float,
        away: float,
    ) -> OutcomeFavorite:
        options = {
            "home": (home, match.home_team),
            "draw": (draw, "Draw"),
            "away": (away, match.away_team),
        }
        outcome, (probability, label) = max(options.items(), key=lambda kv: kv[1][0])
        return OutcomeFavorite(outcome=outcome, label=label, probability=probability)

    @staticmethod
    def _format_team_news(team_news: MatchTeamNews) -> str:
        def fmt_absence(a: PlayerAbsence) -> str:
            sign = "+" if a.estimated_xg_impact > 0 else ""
            return (
                f"- {a.player_name} ({a.position}) — {a.reason}; "
                f"estimated_xg_impact: {sign}{a.estimated_xg_impact:.2f}"
            )

        home_total = sum(a.estimated_xg_impact for a in team_news.home.absences)
        away_total = sum(a.estimated_xg_impact for a in team_news.away.absences)

        lines: list[str] = []
        lines.append("Home team absences:")
        if team_news.home.absences:
            lines.extend(fmt_absence(a) for a in team_news.home.absences)
        else:
            lines.append("- None reported")
        lines.append(f"Home total estimated_xg_impact: {home_total:+.2f}")
        lines.append("")

        lines.append("Away team absences:")
        if team_news.away.absences:
            lines.extend(fmt_absence(a) for a in team_news.away.absences)
        else:
            lines.append("- None reported")
        lines.append(f"Away total estimated_xg_impact: {away_total:+.2f}")

        return "\n".join(lines)

    @staticmethod
    def _format_conclusion(discrepancies: list[MarketDiscrepancy]) -> str:
        if not discrepancies:
            return "No discrepancy items were generated."

        top = discrepancies[0]
        direction = "higher" if top.delta > 0 else "lower"
        return (
            "Summary: The largest market-to-model misalignment is observed in the "
            f"'{top.outcome}' outcome. The model probability is {direction} than the market "
            f"by {abs(top.delta):.3f} (absolute probability points)."
        )
