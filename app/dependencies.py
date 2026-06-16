from fastapi import Request

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
