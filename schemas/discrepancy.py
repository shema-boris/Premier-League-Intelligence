from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketDiscrepancy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["home", "draw", "away"]
    market_probability: float = Field(..., ge=0.0, le=1.0)
    model_probability: float = Field(..., ge=0.0, le=1.0)
    delta: float
