from __future__ import annotations

from dataclasses import dataclass

from schemas.discrepancy import MarketDiscrepancy
from schemas.impact import AdjustedProbabilities
from schemas.odds import ImpliedProbabilities


@dataclass(frozen=True, slots=True)
class DiscrepancyAnalysisAgent:
    """Compare market-implied probabilities vs model-adjusted probabilities."""

    @staticmethod
    def analyze(
        market: ImpliedProbabilities,
        model: AdjustedProbabilities,
    ) -> list[MarketDiscrepancy]:
        discrepancies = [
            MarketDiscrepancy(
                outcome="home",
                market_probability=market.home,
                model_probability=model.home,
                delta=model.home - market.home,
            ),
            MarketDiscrepancy(
                outcome="draw",
                market_probability=market.draw,
                model_probability=model.draw,
                delta=model.draw - market.draw,
            ),
            MarketDiscrepancy(
                outcome="away",
                market_probability=market.away,
                model_probability=model.away,
                delta=model.away - market.away,
            ),
        ]

        discrepancies.sort(key=lambda d: abs(d.delta), reverse=True)
        return discrepancies
