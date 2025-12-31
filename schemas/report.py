from typing import List

from pydantic import BaseModel, ConfigDict, Field

from .discrepancy import MarketDiscrepancy


class MarketAnalysisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_summary: str
    key_team_news: str
    discrepancies: List[MarketDiscrepancy] = Field(default_factory=list)
    conclusion: str
