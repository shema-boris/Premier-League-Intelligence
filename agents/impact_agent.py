from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from schemas.impact import AdjustedProbabilities, ExpectedGoalsAdjustment
from schemas.odds import ImpliedProbabilities
from schemas.team_news import MatchTeamNews


@dataclass(frozen=True, slots=True)
class ImpactModelingAgent:
    """Create an interpretable probability adjustment layer driven by team news.

    This is not intended to be predictive. It converts absence-level xG impacts into a
    simple directional probability shift.

    Modeling assumptions (explicit):
    - Team xG delta is the sum of `estimated_xg_impact` across absences.
    - Net xG delta is (home_xg_delta - away_xg_delta).
    - Net xG delta shifts home-vs-away win probability linearly.
    - Home advantage is assumed to be implicit in the market baseline; it is not added.
    - Output probabilities are clipped to be non-negative and re-normalized.

    Notes:
    - The linear coefficient is intentionally small and capped to avoid extreme moves.
    """

    # Premier League-specific simplification:
    # In a relatively efficient top league, team-news driven moves are typically modest.
    # We cap the shift to keep the output interpretability-focused.
    SHIFT_PER_NET_XG: ClassVar[float] = 0.15
    MAX_ABS_SHIFT: ClassVar[float] = 0.15
    EPS: ClassVar[float] = 1e-9

    @staticmethod
    def expected_goals_adjustment(team_news: MatchTeamNews) -> ExpectedGoalsAdjustment:
        home_xg_delta = float(sum(a.estimated_xg_impact for a in team_news.home.absences))
        away_xg_delta = float(sum(a.estimated_xg_impact for a in team_news.away.absences))
        return ExpectedGoalsAdjustment(home_xg_delta=home_xg_delta, away_xg_delta=away_xg_delta)

    @classmethod
    def adjusted_probabilities(
        cls,
        market: ImpliedProbabilities,
        xg_adj: ExpectedGoalsAdjustment,
    ) -> AdjustedProbabilities:
        """Adjust market probabilities using xG deltas.

        The adjustment is implemented as a home-vs-away shift with draw treated as
        a residual that is re-normalized.
        """

        net_xg = xg_adj.home_xg_delta - xg_adj.away_xg_delta
        shift = net_xg * cls.SHIFT_PER_NET_XG
        if shift > cls.MAX_ABS_SHIFT:
            shift = cls.MAX_ABS_SHIFT
        elif shift < -cls.MAX_ABS_SHIFT:
            shift = -cls.MAX_ABS_SHIFT

        home = market.home + shift
        away = market.away - shift
        draw = market.draw

        home, draw, away = cls._clip_and_normalize(home, draw, away)
        return AdjustedProbabilities(home=home, draw=draw, away=away)

    @classmethod
    def model(
        cls,
        market: ImpliedProbabilities,
        team_news: MatchTeamNews,
    ) -> tuple[ExpectedGoalsAdjustment, AdjustedProbabilities]:
        xg_adj = cls.expected_goals_adjustment(team_news)
        probs = cls.adjusted_probabilities(market, xg_adj)
        return xg_adj, probs

    @classmethod
    def _clip_and_normalize(cls, home: float, draw: float, away: float) -> tuple[float, float, float]:
        home = max(home, cls.EPS)
        draw = max(draw, cls.EPS)
        away = max(away, cls.EPS)

        s = home + draw + away
        if s <= 0.0:
            raise ValueError("Probabilities must sum to a positive value")

        return home / s, draw / s, away / s
