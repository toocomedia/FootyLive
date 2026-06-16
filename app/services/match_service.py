from __future__ import annotations

from datetime import date
from typing import Any

from app.cache import TTLCache
from app.exceptions import UpstreamUnavailableError
from app.providers.espn import EspnSoccerProvider
from app.schemas.matches import MatchDetail, MatchSummary, TeamSearchResult
from app.schemas.matches import GroupTable, WorldCupGroupsResponse


class MatchService:
    def __init__(self, provider: EspnSoccerProvider, cache_ttl_seconds: int) -> None:
        self.provider = provider
        self.cache = TTLCache(cache_ttl_seconds)
        self.cache_ttl_seconds = cache_ttl_seconds

    def get_live_matches(self) -> list[MatchSummary]:
        return self._cached_model_list(
            cache_key="matches:live",
            fetcher=self.provider.get_live_matches,
            model=MatchSummary,
        )

    def get_today_matches(self) -> list[MatchSummary]:
        return self._cached_model_list(
            cache_key="matches:today",
            fetcher=self.provider.get_today_matches,
            model=MatchSummary,
        )

    def get_matches_by_date(self, match_date: date) -> list[MatchSummary]:
        return self._cached_model_list(
            cache_key=f"matches:date:{match_date.isoformat()}",
            fetcher=lambda: self.provider.get_matches_by_date(match_date),
            model=MatchSummary,
        )

    def get_match_detail(self, match_id: str) -> MatchDetail | None:
        cache_key = f"match:{match_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        stale = self.cache.get_stale(cache_key)
        detail = None

        try:
            detail = self.provider.get_match(match_id)
        except UpstreamUnavailableError:
            pass

        if detail is None:
            matches = self.get_live_matches() + self.get_today_matches()
            for match in matches:
                if match.id == match_id:
                    detail = match.model_dump()
                    break

        if detail is None:
            if stale is not None:
                return stale
            return None

        fresh = MatchDetail.model_validate(detail)
        return self.cache.set(cache_key, fresh)

    def search_teams(self, query: str) -> list[TeamSearchResult]:
        if not query.strip():
            return []
        teams = self._cached_model_list(
            cache_key=f"teams:search:{query.strip().lower()}",
            fetcher=lambda: self.provider.search_teams(query),
            model=TeamSearchResult,
        )
        return teams



    def get_league_standings(self, slug: str) -> WorldCupGroupsResponse:
        cache_key = f"league:standings:{slug}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        stale = self.cache.get_stale(cache_key)
        try:
            payload = self.provider.get_league_standings(slug)
            fresh = WorldCupGroupsResponse(
                title=payload["title"],
                groups=[GroupTable.model_validate(group) for group in payload["groups"]],
                count=payload["count"],
            )
        except UpstreamUnavailableError:
            if stale is not None:
                return stale
            raise
        return self.cache.set(cache_key, fresh)

    def get_league_matches(self, slug: str) -> list[MatchSummary]:
        return self._cached_model_list(
            cache_key=f"league:matches:{slug}",
            fetcher=lambda: self.provider.get_league_matches(slug),
            model=MatchSummary,
        )

    def _cached_model_list(self, cache_key: str, fetcher: Any, model: Any) -> list[Any]:
        stale = self.cache.get_stale(cache_key)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            fresh = [model.model_validate(item) for item in fetcher()]
        except UpstreamUnavailableError:
            if stale is not None:
                return stale
            raise
        return self.cache.set(cache_key, fresh)
