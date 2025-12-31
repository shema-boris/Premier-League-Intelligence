from __future__ import annotations

from dataclasses import dataclass

from schemas.odds import ImpliedProbabilities, RawOdds


@dataclass(frozen=True, slots=True)
class OddsAgent:
    """Convert 1X2 decimal odds into market-implied probabilities.

    Assumptions
    - Decimal odds are strictly > 1.0.
    - Raw implied probabilities are computed as 1 / odds.
    - Overround is the sum of raw implied probabilities.
    - Returned probabilities are normalized to sum to 1.
    """

    @staticmethod
    def implied_probabilities(raw_odds: RawOdds) -> ImpliedProbabilities:
        raw_home = 1.0 / raw_odds.home_win
        raw_draw = 1.0 / raw_odds.draw
        raw_away = 1.0 / raw_odds.away_win

        overround = raw_home + raw_draw + raw_away
        if overround <= 0.0:
            raise ValueError("Invalid odds: implied probability sum must be positive")

        return ImpliedProbabilities(
            home=raw_home / overround,
            draw=raw_draw / overround,
            away=raw_away / overround,
            overround=overround,
        )
