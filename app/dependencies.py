from fastapi import Header, HTTPException, Request, status

from app.config import get_settings
from app.providers.espn import EspnSoccerProvider
from app.services.match_service import MatchService


def get_match_service(request: Request) -> MatchService:
    service = getattr(request.app.state, "match_service", None)
    if service is None:
        settings = get_settings()
        service = MatchService(
            provider=EspnSoccerProvider(request_timeout_seconds=settings.request_timeout_seconds),
            cache_ttl_seconds=settings.cache_ttl_seconds,
        )
        request.app.state.match_service = service
    return service


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
