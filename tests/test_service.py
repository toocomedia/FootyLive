import pytest

from datetime import date

from app.exceptions import UpstreamUnavailableError
from app.services.match_service import MatchService


def build_match(match_id: str = "1"):
    return {
        "id": match_id,
        "source": "espn",
        "competition": "Premier League",
        "status": "INPLAY",
        "status_type": "in",
        "is_live": True,
        "is_finished": False,
        "result": None,
        "kickoff_time": "2026-06-15T18:00:00+00:00",
        "minute": "67",
        "home_team": {"id": "home-1", "name": "Home FC"},
        "away_team": {"id": "away-1", "name": "Away FC"},
        "score": {"home": 2, "away": 1},
        "venue": None,
        "referee": None,
        "statistics": {},
    }


class ProviderStub:
    def __init__(self):
        self.calls = 0
        self.fail_after_cache = False
        self.always_fail = False

    def get_live_matches(self):
        self.calls += 1
        if self.always_fail:
            raise UpstreamUnavailableError("upstream failed")
        if self.fail_after_cache and self.calls > 1:
            raise UpstreamUnavailableError("upstream failed")
        return [build_match()]

    def get_today_matches(self):
        return [build_match("2")]

    def get_matches_by_date(self, match_date: date):
        return [
            {
                **build_match("3"),
                "kickoff_time": f"{match_date.isoformat()}T18:00:00+00:00",
                "status": "SCHEDULED",
                "status_type": "pre",
                "is_live": False,
                "is_finished": False,
                "result": None,
                "minute": None,
            }
        ]

    def get_match(self, match_id: str):
        return build_match(match_id)

    def search_teams(self, query: str):
        return [{"id": "home-1", "name": "Home FC", "competition": "Premier League"}]

    def get_world_cup_groups(self):
        return {
            "title": "FIFA World Cup Standings",
            "count": 1,
            "groups": [
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
        }


def test_service_caches_live_matches():
    provider = ProviderStub()
    service = MatchService(provider=provider, cache_ttl_seconds=20)

    first = service.get_live_matches()
    second = service.get_live_matches()

    assert len(first) == 1
    assert len(second) == 1
    assert provider.calls == 1


def test_service_returns_stale_cache_on_upstream_failure():
    provider = ProviderStub()
    service = MatchService(provider=provider, cache_ttl_seconds=20)

    service.get_live_matches()
    provider.fail_after_cache = True
    service.cache._entries["matches:live"].expires_at = service.cache._entries["matches:live"].expires_at.replace(year=2000)

    matches = service.get_live_matches()
    assert len(matches) == 1


def test_service_raises_when_no_cache_and_upstream_fails():
    provider = ProviderStub()
    provider.always_fail = True
    service = MatchService(provider=provider, cache_ttl_seconds=20)

    with pytest.raises(UpstreamUnavailableError):
        service.get_live_matches()


def test_service_search_teams_empty_query():
    provider = ProviderStub()
    service = MatchService(provider=provider, cache_ttl_seconds=20)

    assert service.search_teams("   ") == []


def test_service_world_cup_groups():
    provider = ProviderStub()
    service = MatchService(provider=provider, cache_ttl_seconds=20)

    groups = service.get_world_cup_groups()
    assert groups.count == 1
    assert groups.groups[0].name == "Group A"


def test_service_get_matches_by_date():
    provider = ProviderStub()
    service = MatchService(provider=provider, cache_ttl_seconds=20)

    matches = service.get_matches_by_date(date(2026, 6, 14))

    assert len(matches) == 1
    assert matches[0].kickoff_time.startswith("2026-06-14")
