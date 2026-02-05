from pydantic import BaseModel, ConfigDict, Field


class RawOdds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home_win: float = Field(..., gt=1.0)
    draw: float = Field(..., gt=1.0)
    away_win: float = Field(..., gt=1.0)


class ImpliedProbabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home: float = Field(..., ge=0.0, le=1.0)
    draw: float = Field(..., ge=0.0, le=1.0)
    away: float = Field(..., ge=0.0, le=1.0)
    overround: float = Field(..., ge=0.0)
