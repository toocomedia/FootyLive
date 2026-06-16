from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_match_service
from app.main import app
from app.schemas.matches import MatchDetail, MatchSummary, TeamSearchResult, WorldCupGroupsResponse


def build_match(match_id: str = "1", status: str = "INPLAY") -> dict:
    return {
        "id": match_id,
        "source": "espn",
        "competition": "Premier League",
        "status": status,
        "kickoff_time": "2026-06-15T18:00:00+00:00",
        "minute": "67",
        "home_team": {"id": "home-1", "name": "Home FC"},
        "away_team": {"id": "away-1", "name": "Away FC"},
        "score": {"home": 2, "away": 1},
        "venue": "Main Stadium",
        "referee": "Ref Name",
        "statistics": {},
    }


class StubMatchService:
    cache_ttl_seconds = 20

    def get_live_matches(self):
        return [MatchSummary.model_validate(build_match())]

    def get_today_matches(self):
        return [MatchSummary.model_validate(build_match(match_id="2", status="SCHEDULED"))]

    def get_matches_by_date(self, match_date: date):
        return [
            MatchSummary.model_validate(
                {
                    **build_match(match_id="3", status="SCHEDULED"),
                    "kickoff_time": f"{match_date.isoformat()}T18:00:00+00:00",
                    "minute": None,
                    "is_live": False,
                    "is_finished": False,
                    "result": None,
                    "status_type": "pre",
                }
            )
        ]

    def get_match_detail(self, match_id: str):
        if match_id == "404":
            return None
        return MatchDetail.model_validate(build_match(match_id=match_id))

    def search_teams(self, query: str):
        if query.lower() == "none":
            return []
        return [TeamSearchResult(id="home-1", name="Home FC", competition="Premier League")]

    def get_league_standings(self, slug: str):
        return WorldCupGroupsResponse(
            title="FIFA World Cup Standings",
            count=1,
            groups=[
                {
                    "name": "Group A",
                    "entries": [
                        {
                            "rank": 1,
                            "team_id": "1",
                            "team_name": "Alpha",
                            "flag_path": None,
                            "games_played": "1",
                            "wins": "1",
                            "draws": "0",
                            "losses": "0",
                            "goal_difference": "2",
                            "points": "3",
                        }
                    ],
                }
            ],
        )


@pytest.fixture
def client():
    app.dependency_overrides[get_match_service] = lambda: StubMatchService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
