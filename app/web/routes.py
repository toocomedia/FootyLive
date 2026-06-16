from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["web"])


def _format_match_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value

    formatted = parsed.strftime("%d %b %Y, %H:%M UTC")
    return formatted.replace(" 0", " ")


async def _fetch_internal_json(request: Request, path: str) -> dict[str, Any]:
    settings = get_settings()
    transport = httpx.ASGITransport(app=request.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
        response = await client.get(path)
    if response.status_code != 200:
        return {"detail": response.json().get("detail", "Unable to load data.")}
    return response.json()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    from app.config import SUPPORTED_LEAGUES
    payload = await _fetch_internal_json(request, "/api/matches/live")
    groups_payload = await _fetch_internal_json(request, "/api/leagues/fifa.world/standings")
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "matches": payload.get("matches", []),
            "count": payload.get("count", 0),
            "error": payload.get("detail"),
            "groups": groups_payload.get("groups", []),
            "groups_title": groups_payload.get("title", "World Cup Groups"),
            "groups_error": groups_payload.get("detail"),
            "page_title": "Live Matches",
            "supported_leagues": SUPPORTED_LEAGUES,
        },
    )


@router.get("/matches", response_class=HTMLResponse)
async def matches(request: Request, date: str | None = None) -> HTMLResponse:
    from app.config import SUPPORTED_LEAGUES
    today_date = datetime.now().date()
    
    if date:
        try:
            current_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            current_date = today_date
        payload = await _fetch_internal_json(request, f"/api/matches/by-date?date={current_date}")
        if current_date == today_date:
            page_title = "Today's Matches"
        else:
            page_title = f"Matches on {current_date.strftime('%d %b %Y')}"
    else:
        payload = await _fetch_internal_json(request, "/api/matches/today")
        current_date = today_date
        page_title = "Today's Matches"
        
    date_str = current_date.strftime("%Y-%m-%d")
    
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)
    
    if current_date == today_date:
        display_date_text = "Today"
    elif current_date == today_date - timedelta(days=1):
        display_date_text = "Yesterday"
    elif current_date == today_date + timedelta(days=1):
        display_date_text = "Tomorrow"
    else:
        display_date_text = current_date.strftime("%d %b %Y")
    
    matches_list = payload.get("matches", [])
    for match in matches_list:
        if isinstance(match, dict):
            match["kickoff_time_formatted"] = _format_match_time(match.get("kickoff_time"))
            
    return templates.TemplateResponse(
        request,
        "matches.html",
        {
            "matches": matches_list,
            "count": payload.get("count", 0),
            "error": payload.get("detail"),
            "page_title": page_title,
            "selected_date": date_str,
            "display_date_text": display_date_text,
            "today_date": today_date.strftime("%Y-%m-%d"),
            "prev_date": prev_date.strftime("%Y-%m-%d"),
            "next_date": next_date.strftime("%Y-%m-%d"),
            "supported_leagues": SUPPORTED_LEAGUES,
        },
    )


@router.get("/matches/{match_id}", response_class=HTMLResponse)
async def match_detail(request: Request, match_id: str) -> HTMLResponse:
    payload = await _fetch_internal_json(request, f"/api/matches/{match_id}")
    if payload.get("id"):
        payload["kickoff_time_formatted"] = _format_match_time(payload.get("kickoff_time"))
    return templates.TemplateResponse(
        request,
        "match_detail.html",
        {
            "match": payload if payload.get("id") else None,
            "error": payload.get("detail"),
            "page_title": "Match Detail",
        },
    )


@router.get("/teams/search", response_class=HTMLResponse)
async def team_search(request: Request, q: str = "") -> HTMLResponse:
    payload = {"teams": [], "count": 0}
    if q.strip():
        payload = await _fetch_internal_json(request, f"/api/search/teams?q={q}")
    return templates.TemplateResponse(
        request,
        "team_search.html",
        {
            "teams": payload.get("teams", []),
            "count": payload.get("count", 0),
            "query": q,
            "error": payload.get("detail"),
            "page_title": "Team Search",
        },
    )








@router.get("/leagues", response_class=HTMLResponse)
async def leagues_index(request: Request) -> HTMLResponse:
    from app.config import SUPPORTED_LEAGUES
    
    international = ["fifa.world", "uefa.euro", "conmebol.america", "caf.nations", "afc.asian"]
    continental = ["uefa.champions", "uefa.europa"]
    domestic_leagues = ["eng.1", "esp.1", "ita.1", "ger.1", "fra.1"]
    domestic_cups = ["eng.fa", "esp.copa_del_rey", "ita.coppa_italia", "ger.dfb_pokal", "fra.coupe_de_france"]

    groups = [
        ("International Tournaments", {k: SUPPORTED_LEAGUES[k] for k in international if k in SUPPORTED_LEAGUES}),
        ("Continental Clubs", {k: SUPPORTED_LEAGUES[k] for k in continental if k in SUPPORTED_LEAGUES}),
        ("Domestic Leagues", {k: SUPPORTED_LEAGUES[k] for k in domestic_leagues if k in SUPPORTED_LEAGUES}),
        ("Domestic Cups", {k: SUPPORTED_LEAGUES[k] for k in domestic_cups if k in SUPPORTED_LEAGUES}),
    ]

    return templates.TemplateResponse(
        request,
        "leagues.html",
        {
            "league_groups": groups,
            "page_title": "All Leagues & Cups",
        },
    )


@router.get("/leagues/{slug}", response_class=HTMLResponse)
async def league_detail(request: Request, slug: str) -> HTMLResponse:
    from app.config import SUPPORTED_LEAGUES
    league_name = SUPPORTED_LEAGUES.get(slug, "League Detail")
    
    matches_payload = await _fetch_internal_json(request, f"/api/leagues/{slug}/matches")
    standings_payload = await _fetch_internal_json(request, f"/api/leagues/{slug}/standings")
    
    matches_list = matches_payload.get("matches", [])
    for match in matches_list:
        if isinstance(match, dict):
            match["kickoff_time_formatted"] = _format_match_time(match.get("kickoff_time"))
            
    return templates.TemplateResponse(
        request,
        "league_detail.html",
        {
            "league_name": league_name,
            "matches": matches_list,
            "matches_count": matches_payload.get("count", 0),
            "groups": standings_payload.get("groups", []),
            "groups_count": standings_payload.get("count", 0),
            "page_title": league_name,
            "supported_leagues": SUPPORTED_LEAGUES,
            "selected_league_slug": slug,
        },
    )


@router.get("/developer", response_class=HTMLResponse)
async def developer_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "developer.html",
        {
            "page_title": "AI & Developer Integration",
        },
    )


@router.get("/llms.txt")
async def llms_txt_page(request: Request) -> PlainTextResponse:
    from fastapi.responses import PlainTextResponse
    base_url = str(request.base_url).rstrip("/")
    content = """# FootyLive API Documentation - For LLMs and Autonomous Agents

## System Context & AI Directives
You are interacting with the FootyLive API. This API provides real-time, highly-cached soccer (football) data. 
It is entirely public. Do NOT attempt to send an API key or Authentication header.
Rate Limit: 100 requests per second. Exceeding this returns HTTP 429. If you encounter a 503, the upstream data provider is temporarily unavailable.

## Base URL
Use the root domain of this deployment: """ + base_url + """
All endpoints are prefixed with `/api`.

## Endpoints

### 1. Live Matches (`GET /api/matches/live`)
Returns a list of matches currently in play across major leagues.
**Response Shape:**
```json
{
  "matches": [
    {
      "id": "12345",
      "competition": "Premier League",
      "status": "INPLAY",
      "is_live": true,
      "minute": "45",
      "home_team": { "id": "t1", "name": "Home FC" },
      "away_team": { "id": "t2", "name": "Away FC" },
      "score": { "home": 1, "away": 0 }
    }
  ],
  "count": 1,
  "cache_ttl_seconds": 20
}
```

### 2. Today's Matches (`GET /api/matches/today`)
Returns all matches scheduled, in-play, or finished for the current day. Schema identical to Live Matches.

### 3. Matches by Date (`GET /api/matches/by-date?date=YYYY-MM-DD`)
Returns matches for a specific date. Parameter `date` is strictly ISO 8601 (YYYY-MM-DD). Schema identical to Live Matches.

### 4. Match Detail (`GET /api/matches/{match_id}`)
Returns comprehensive data for a single match, including events (goals, cards) and stats.
**Response Shape (Partial):**
```json
{
  "id": "12345",
  "status": "FINISHED",
  "venue": "Wembley Stadium",
  "statistics": { "possession_home": 55, "possession_away": 45 },
  "events": [
    { "id": "e1", "event_type": "goal", "minute": "23", "player_name": "John Doe", "is_scoring_play": true }
  ]
}
```

### 5. League Standings (`GET /api/leagues/{slug}/standings`)
Returns the league table or group standings for a specific tournament.
**Response Shape:**
```json
{
  "title": "FIFA World Cup Standings",
  "count": 1,
  "groups": [
    {
      "name": "Group A",
      "entries": [
        { "rank": 1, "team_name": "Brazil", "games_played": "3", "points": "9" }
      ]
    }
  ]
}
```

### 6. Search Teams (`GET /api/search/teams?q={query}`)
Search for a team by string query. Returns a list of matched teams.

## Supported Leagues (Slugs)
Pass these exactly as `{slug}` when requesting standings:
- `eng.1`: Premier League
- `esp.1`: LALIGA
- `ita.1`: Serie A
- `ger.1`: Bundesliga
- `fra.1`: Ligue 1
- `uefa.champions`: Champions League
- `uefa.europa`: Europa League
- `fifa.world`: World Cup
- `uefa.euro`: European Championship
- `conmebol.america`: Copa América
- `caf.nations`: Africa Cup of Nations
- `afc.asian`: Asian Cup
- `eng.fa`: FA Cup
- `esp.copa_del_rey`: Copa del Rey
- `ita.coppa_italia`: Coppa Italia
- `ger.dfb_pokal`: DFB-Pokal
- `fra.coupe_de_france`: Coupe de France
"""
    return PlainTextResponse(content)

