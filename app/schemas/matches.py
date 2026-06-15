from __future__ import annotations

from pydantic import BaseModel, Field


class TeamSummary(BaseModel):
    id: str
    name: str
    flag_path: str | None = None


class ScoreSummary(BaseModel):
    home: int | None = None
    away: int | None = None


class MatchSummary(BaseModel):
    id: str
    source: str = "espn"
    competition: str | None = None
    status: str
    status_type: str | None = None
    is_live: bool = False
    is_finished: bool = False
    result: str | None = None
    kickoff_time: str | None = None
    minute: str | None = None
    home_team: TeamSummary
    away_team: TeamSummary
    score: ScoreSummary = Field(default_factory=ScoreSummary)


class MatchEvent(BaseModel):
    id: str
    event_type: str
    label: str
    icon_path: str | None = None
    minute: str | None = None
    team_id: str | None = None
    team_name: str | None = None
    player_name: str | None = None
    text: str | None = None
    is_scoring_play: bool = False


class MatchDetail(MatchSummary):
    venue: str | None = None
    referee: str | None = None
    home_score_display: str | None = None
    away_score_display: str | None = None
    statistics: dict[str, str | int | float | None] = Field(default_factory=dict)
    events: list[MatchEvent] = Field(default_factory=list)


class MatchListResponse(BaseModel):
    matches: list[MatchSummary]
    count: int
    cache_ttl_seconds: int


class TeamSearchResult(BaseModel):
    id: str
    name: str
    competition: str | None = None


class TeamSearchResponse(BaseModel):
    teams: list[TeamSearchResult]
    count: int


class GroupTableEntry(BaseModel):
    rank: int | None = None
    team_id: str
    team_name: str
    flag_path: str | None = None
    games_played: str | None = None
    wins: str | None = None
    draws: str | None = None
    losses: str | None = None
    goal_difference: str | None = None
    points: str | None = None


class GroupTable(BaseModel):
    name: str
    entries: list[GroupTableEntry]


class WorldCupGroupsResponse(BaseModel):
    title: str
    groups: list[GroupTable]
    count: int


class ErrorResponse(BaseModel):
    detail: str
