from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

from .discrepancy import MarketDiscrepancy


class OutcomeFavorite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["home", "draw", "away"]
    label: str
    probability: float = Field(ge=0.0, le=1.0)


class MarketAnalysisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_summary: str
    market_favorite: OutcomeFavorite
    model_favorite: OutcomeFavorite
    key_team_news: str
    discrepancies: List[MarketDiscrepancy] = Field(default_factory=list)
    conclusion: str
