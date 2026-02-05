from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Match(BaseModel):
    model_config = ConfigDict(extra="forbid")

    league: str = Field(default="Premier League")
    home_team: str
    away_team: str
    kickoff_utc: datetime
