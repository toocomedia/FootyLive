import app.providers.espn as espn_module
from app.exceptions import UpstreamUnavailableError
from app.providers.espn import EspnSoccerProvider


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses):
        self.responses = responses

    def get(self, url):
        for suffix, response in self.responses.items():
            if url.endswith(suffix):
                return response
        raise AssertionError(f"Unexpected URL: {url}")

    def close(self):
        return None


def test_provider_normalizes_live_match():
    espn_module.cache_flag = (
        lambda team_id, logo_url, timeout_seconds=10, team_name="": f"/static/flags/{team_id}.png" if logo_url else None
    )
    provider = EspnSoccerProvider()
    provider._client = FakeClient(
        {
            "/scoreboard": FakeResponse(
                200,
                {
                    "events": [
                        {
                            "id": 99,
                            "competitions": [
                                {
                                    "date": "2026-06-15T18:00:00Z",
                                    "status": {
                                        "displayClock": "55'",
                                        "type": {"state": "in", "description": "In Progress"},
                                    },
                                    "league": {"name": "Champions League"},
                                    "competitors": [
                                        {
                                            "homeAway": "home",
                                            "score": "1",
                                            "team": {"id": "1", "displayName": "Alpha", "logo": "https://example.com/1.png"},
                                            "statistics": [],
                                        },
                                        {
                                            "homeAway": "away",
                                            "score": "0",
                                            "team": {"id": "2", "displayName": "Beta", "logo": "https://example.com/2.png"},
                                            "statistics": [],
                                        },
                                    ],
                                }
                            ],
                        }
                    ]
                },
            ),
        }
    )

    matches = provider.get_live_matches()

    assert matches[0]["id"] == "99"
    assert matches[0]["competition"] == "Champions League"
    assert matches[0]["status_type"] == "in"
    assert matches[0]["is_live"] is True
    assert matches[0]["is_finished"] is False
    assert matches[0]["result"] is None
    assert matches[0]["score"]["home"] == 1
    assert matches[0]["home_team"]["name"] == "Alpha"
    assert matches[0]["home_team"]["flag_path"] == "/static/flags/1.png"


def test_provider_raises_on_bad_shape():
    espn_module.cache_flag = lambda team_id, logo_url, timeout_seconds=10, team_name="": None
    provider = EspnSoccerProvider()
    provider._client = FakeClient(
        {
            "/scoreboard": FakeResponse(200, {"not_events": "a list"}),
        }
    )

    try:
        provider.get_live_matches()
        assert False, "Expected UpstreamUnavailableError"
    except UpstreamUnavailableError:
        assert True


def test_provider_surfaces_challenge_error():
    espn_module.cache_flag = lambda team_id, logo_url, timeout_seconds=10, team_name="": None
    provider = EspnSoccerProvider()
    provider._client = FakeClient(
        {
            "/scoreboard": FakeResponse(
                403,
                {"error": {"code": 403, "reason": "challenge"}},
            ),
        }
    )

    try:
        provider.get_live_matches()
        assert False, "Expected UpstreamUnavailableError"
    except UpstreamUnavailableError as exc:
        assert "403" in str(exc)


def test_provider_normalizes_world_cup_groups():
    espn_module.cache_flag = (
        lambda team_id, logo_url, timeout_seconds=10, team_name="": f"/static/flags/{team_id}.png" if logo_url else None
    )
    provider = EspnSoccerProvider()
    provider._client = FakeClient(
        {
            "https://site.web.api.espn.com/apis/v2/sports/soccer/fifa.world/standings": FakeResponse(
                200,
                {
                    "name": "FIFA World Cup",
                    "children": [
                        {
                            "name": "Group H",
                            "standings": {
                                "entries": [
                                    {
                                        "id": "164",
                                        "team": {"displayName": "Spain"},
                                        "logo": [{"href": "https://example.com/spain.png"}],
                                        "stats": [
                                            {"type": "rank", "displayValue": "1"},
                                            {"type": "gamesplayed", "displayValue": "1"},
                                            {"type": "wins", "displayValue": "0"},
                                            {"type": "ties", "displayValue": "1"},
                                            {"type": "losses", "displayValue": "0"},
                                            {"type": "pointdifferential", "displayValue": "0"},
                                            {"type": "points", "displayValue": "1"},
                                        ],
                                    }
                                ]
                            },
                        }
                    ],
                },
            ),
        }
    )

    groups = provider.get_world_cup_groups()
    assert groups["count"] == 1
    assert groups["groups"][0]["name"] == "Group H"
    assert groups["groups"][0]["entries"][0]["team_name"] == "Spain"
    assert groups["groups"][0]["entries"][0]["flag_path"] == "/static/flags/164.png"


def test_provider_normalizes_match_key_events():
    espn_module.cache_flag = lambda team_id, logo_url, timeout_seconds=10, team_name="": None
    provider = EspnSoccerProvider()
    provider._client = FakeClient(
        {
            "/summary?event=88": FakeResponse(
                200,
                {
                    "header": {
                        "id": "88",
                        "competitions": [
                            {
                                "date": "2026-06-15T18:00:00Z",
                                "status": {
                                    "displayClock": "90'+1'",
                                    "type": {"state": "post", "description": "Full Time"},
                                },
                                "league": {"name": "Champions League"},
                                "competitors": [
                                    {
                                        "homeAway": "home",
                                        "score": "2",
                                        "team": {"id": "1", "displayName": "Alpha"},
                                        "statistics": [],
                                    },
                                    {
                                        "homeAway": "away",
                                        "score": "1",
                                        "team": {"id": "2", "displayName": "Beta"},
                                        "statistics": [],
                                    },
                                ],
                            }
                        ],
                    },
                    "keyEvents": [
                        {
                            "id": "900",
                            "type": {"text": "Goal", "type": "goal"},
                            "text": "Alpha scores.",
                            "clock": {"displayValue": "55'"},
                            "scoringPlay": True,
                            "team": {"id": "1", "displayName": "Alpha"},
                            "participants": [{"athlete": {"displayName": "Player One"}}],
                        },
                        {
                            "id": "901",
                            "type": {"text": "Yellow Card", "type": "yellow-card"},
                            "text": "Player Two is booked.",
                            "clock": {"displayValue": "61'"},
                            "scoringPlay": False,
                            "team": {"id": "2", "displayName": "Beta"},
                            "participants": [{"athlete": {"displayName": "Player Two"}}],
                        },
                        {
                            "id": "999",
                            "type": {"text": "Substitution", "type": "substitution"},
                            "text": "Not included.",
                            "clock": {"displayValue": "70'"},
                            "scoringPlay": False,
                        },
                    ],
                },
            ),
        }
    )

    match = provider.get_match("88")

    assert match is not None
    assert match["is_finished"] is True
    assert match["result"] == "home_win"
    assert len(match["events"]) == 2
    assert match["events"][0]["event_type"] == "goal"
    assert match["events"][0]["player_name"] == "Player One"
    assert match["events"][1]["event_type"] == "yellow-card"
    assert match["events"][1]["team_name"] == "Beta"
