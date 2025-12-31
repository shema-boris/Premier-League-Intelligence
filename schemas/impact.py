from pydantic import BaseModel, ConfigDict, Field


class ExpectedGoalsAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home_xg_delta: float
    away_xg_delta: float


class AdjustedProbabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home: float = Field(..., ge=0.0, le=1.0)
    draw: float = Field(..., ge=0.0, le=1.0)
    away: float = Field(..., ge=0.0, le=1.0)
