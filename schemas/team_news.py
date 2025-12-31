from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class PlayerAbsence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_name: str
    position: str
    reason: Literal["injury", "suspension", "rotation"]
    estimated_xg_impact: float


class TeamNews(BaseModel):
    model_config = ConfigDict(extra="forbid")

    absences: List[PlayerAbsence] = Field(default_factory=list)


class MatchTeamNews(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home: TeamNews
    away: TeamNews
