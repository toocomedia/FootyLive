from app.config import get_settings


def test_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_key_is_required(client):
    response = client.get("/api/matches/live")
    assert response.status_code == 401


def test_live_matches_success(client):
    settings = get_settings()
    response = client.get("/api/matches/live", headers={"X-API-Key": settings.api_key})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["matches"][0]["home_team"]["name"] == "Home FC"


def test_today_matches_success(client):
    settings = get_settings()
    response = client.get("/api/matches/today", headers={"X-API-Key": settings.api_key})

    assert response.status_code == 200
    assert response.json()["matches"][0]["status"] == "SCHEDULED"


def test_matches_by_date_success(client):
    settings = get_settings()
    response = client.get("/api/matches/by-date?date=2026-06-14", headers={"X-API-Key": settings.api_key})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["matches"][0]["kickoff_time"].startswith("2026-06-14")


def test_match_detail_not_found(client):
    settings = get_settings()
    response = client.get("/api/matches/404", headers={"X-API-Key": settings.api_key})
    assert response.status_code == 404


def test_world_cup_groups_success(client):
    settings = get_settings()
    response = client.get("/api/world-cup/groups", headers={"X-API-Key": settings.api_key})

    assert response.status_code == 200
    assert response.json()["groups"][0]["name"] == "Group A"


def test_index_page_renders_live_matches(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "live match" in response.text
    assert "Home FC" in response.text
    assert "Away FC" in response.text
