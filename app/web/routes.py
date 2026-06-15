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
        response = await client.get(path, headers={"X-API-Key": settings.api_key})
    if response.status_code != 200:
        return {"detail": response.json().get("detail", "Unable to load data.")}
    return response.json()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    payload = await _fetch_internal_json(request, "/api/matches/live")
    groups_payload = await _fetch_internal_json(request, "/api/world-cup/groups")
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
        },
    )


@router.get("/matches", response_class=HTMLResponse)
async def matches(request: Request, date: str | None = None) -> HTMLResponse:
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


@router.get("/world-cup/groups", response_class=HTMLResponse)
async def world_cup_groups(request: Request) -> HTMLResponse:
    payload = await _fetch_internal_json(request, "/api/world-cup/groups")
    return templates.TemplateResponse(
        request,
        "world_cup_groups.html",
        {
            "groups": payload.get("groups", []),
            "count": payload.get("count", 0),
            "groups_title": payload.get("title", "World Cup Groups"),
            "error": payload.get("detail"),
            "page_title": "World Cup Groups",
        },
    )
