from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request

from app.dependencies import get_match_service, require_api_key
from app.exceptions import UpstreamUnavailableError
from app.schemas.matches import (
    ErrorResponse,
    MatchDetail,
    MatchListResponse,
    TeamSearchResponse,
    WorldCupGroupsResponse,
)
from app.services.match_service import MatchService

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/keys/generate")
def generate_api_key(request: Request) -> dict[str, str]:
    import uuid
    import secrets
    from datetime import datetime, timedelta, timezone
    from app.db import get_active_key_for_ip, insert_key
    
    ip = request.client.host if request.client else "unknown"
    
    existing_key = get_active_key_for_ip(ip)
    if existing_key:
        return {"api_key": existing_key}
    
    raw_uuid = str(uuid.uuid4()).replace("-", "")
    suffix = secrets.token_hex(3)
    new_key = f"footy_{raw_uuid}_{suffix}"
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=90)
    insert_key(new_key, ip, expires_at)
    
    return {"api_key": new_key}


@router.get(
    "/matches/live",
    response_model=MatchListResponse,
    responses={503: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
    summary="Get Live Matches (Major Leagues)",
    description="Returns live matches for major leagues and cups.",
)
def live_matches(service: MatchService = Depends(get_match_service)) -> MatchListResponse:
    try:
        matches = service.get_live_matches()
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return MatchListResponse(
        matches=matches,
        count=len(matches),
        cache_ttl_seconds=service.cache_ttl_seconds,
    )


@router.get(
    "/matches/today",
    response_model=MatchListResponse,
    responses={503: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
    summary="Get Today's Matches (Major Leagues)",
    description="Returns today's matches for major leagues and cups.",
)
def today_matches(service: MatchService = Depends(get_match_service)) -> MatchListResponse:
    try:
        matches = service.get_today_matches()
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return MatchListResponse(
        matches=matches,
        count=len(matches),
        cache_ttl_seconds=service.cache_ttl_seconds,
    )


@router.get(
    "/matches/by-date",
    response_model=MatchListResponse,
    responses={503: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
    summary="Get Matches by Date (Major Leagues)",
    description="Returns matches for major leagues and cups on a specific date.",
)
def matches_by_date(
    date_value: date = Query(alias="date"),
    service: MatchService = Depends(get_match_service),
) -> MatchListResponse:
    try:
        matches = service.get_matches_by_date(date_value)
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return MatchListResponse(
        matches=matches,
        count=len(matches),
        cache_ttl_seconds=service.cache_ttl_seconds,
    )


@router.get(
    "/matches/{match_id}",
    response_model=MatchDetail,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
)
def match_detail(match_id: str, service: MatchService = Depends(get_match_service)) -> MatchDetail:
    try:
        match = service.get_match_detail(match_id)
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    return match


@router.get(
    "/search/teams",
    response_model=TeamSearchResponse,
    responses={503: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
)
def search_teams(
    q: str = Query(min_length=1),
    service: MatchService = Depends(get_match_service),
) -> TeamSearchResponse:
    try:
        teams = service.search_teams(q)
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return TeamSearchResponse(teams=teams, count=len(teams))





@router.get(
    "/leagues/{slug}/standings",
    response_model=WorldCupGroupsResponse,
    responses={503: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
    summary="Get League Standings",
    description="Returns the standings table for a specific league.",
)
def league_standings(slug: str, service: MatchService = Depends(get_match_service)) -> WorldCupGroupsResponse:
    try:
        return service.get_league_standings(slug)
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get(
    "/leagues/{slug}/matches",
    response_model=MatchListResponse,
    responses={503: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
    summary="Get League Matches",
    description="Returns matches for a specific league.",
)
def league_matches(slug: str, service: MatchService = Depends(get_match_service)) -> MatchListResponse:
    try:
        matches = service.get_league_matches(slug)
    except UpstreamUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return MatchListResponse(
        matches=matches,
        count=len(matches),
        cache_ttl_seconds=service.cache_ttl_seconds,
    )
