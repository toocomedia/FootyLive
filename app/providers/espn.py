from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.assets.flags import cache_flag
from app.exceptions import UpstreamUnavailableError


class EspnSoccerProvider:
    source_name = "espn"
    base_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all"
    world_cup_standings_url = "https://site.web.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

    def __init__(self, request_timeout_seconds: int = 10) -> None:
        self.request_timeout_seconds = request_timeout_seconds
        self._client = httpx.Client(
            timeout=self.request_timeout_seconds,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, text/plain, */*",
            },
            follow_redirects=True,
        )

    def get_live_matches(self) -> list[dict[str, Any]]:
        events = self._get_scoreboard_events()
        live_events = [
            event
            for event in events
            if self._competition(event).get("status", {}).get("type", {}).get("state") == "in"
        ]
        return [self._normalize_scoreboard_event(event) for event in live_events]

    def get_today_matches(self) -> list[dict[str, Any]]:
        events = self._get_scoreboard_events()
        return [self._normalize_scoreboard_event(event) for event in events]

    def get_matches_by_date(self, match_date: date) -> list[dict[str, Any]]:
        events = self._get_scoreboard_events(match_date=match_date)
        return [self._normalize_scoreboard_event(event) for event in events]

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        payload = self._get_json(f"/summary?event={match_id}", allow_not_found=True)
        header = payload.get("header")
        if not isinstance(header, dict):
            return None
        return self._normalize_summary(payload)

    def search_teams(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = self.get_today_matches()
        unique: dict[str, dict[str, Any]] = {}
        for match in matches:
            for team_key in ("home_team", "away_team"):
                team = match[team_key]
                if query_lower in team["name"].lower():
                    unique[team["id"]] = {
                        "id": team["id"],
                        "name": team["name"],
                        "competition": match.get("competition"),
                    }
        return list(unique.values())

    def get_world_cup_groups(self) -> dict[str, Any]:
        payload = self._get_absolute_json(self.world_cup_standings_url)
        children = payload.get("children")
        if not isinstance(children, list) or not children:
            raise UpstreamUnavailableError("ESPN did not return any World Cup group standings.")

        ordered_groups = [self._normalize_group(group) for group in children if isinstance(group, dict)]
        ordered_groups.sort(key=lambda item: item["name"])
        return {
            "title": payload.get("name") or "FIFA World Cup Standings",
            "groups": ordered_groups,
            "count": len(ordered_groups),
        }

    def _get_scoreboard_events(self, match_date: date | None = None) -> list[dict[str, Any]]:
        path = "/scoreboard"
        if match_date is not None:
            path = f"{path}?dates={match_date.strftime('%Y%m%d')}"
        payload = self._get_json(path)
        events = payload.get("events")
        if not isinstance(events, list):
            raise UpstreamUnavailableError("ESPN returned an unexpected events payload.")
        return events

    def _get_json(self, path: str, allow_not_found: bool = False) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        return self._get_absolute_json(url, allow_not_found=allow_not_found)

    def _get_absolute_json(self, url: str, allow_not_found: bool = False) -> dict[str, Any]:
        try:
            response = self._client.get(url)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError("Failed to fetch data from ESPN soccer.") from exc

        if allow_not_found and response.status_code == 404:
            return {}
        if response.status_code >= 400:
            raise UpstreamUnavailableError(f"ESPN soccer returned HTTP {response.status_code}.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamUnavailableError("ESPN soccer returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise UpstreamUnavailableError("ESPN soccer returned an unexpected response format.")
        return payload

    def close(self) -> None:
        self._client.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _normalize_scoreboard_event(self, event: dict[str, Any]) -> dict[str, Any]:
        competition = self._competition(event)
        return self._normalize_common(event_id=str(event.get("id")), competition=competition)

    def _normalize_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        header = payload.get("header", {})
        competition = self._competition(header)
        normalized = self._normalize_common(event_id=str(header.get("id")), competition=competition)
        normalized["events"] = self._extract_key_events(payload.get("keyEvents"))
        return normalized

    def _normalize_common(self, event_id: str, competition: dict[str, Any]) -> dict[str, Any]:
        competitors = competition.get("competitors", [])
        home = self._find_competitor(competitors, "home")
        away = self._find_competitor(competitors, "away")
        status = competition.get("status", {})
        status_type = status.get("type", {})
        venue = competition.get("venue", {})
        notes = competition.get("notes")
        first_note = notes[0] if isinstance(notes, list) and notes else {}

        home_score = self._safe_int(home.get("score"))
        away_score = self._safe_int(away.get("score"))
        state = status_type.get("state")

        return {
            "id": event_id,
            "source": self.source_name,
            "competition": competition.get("league", {}).get("name")
            or competition.get("series", {}).get("fullName")
            or first_note.get("headline")
            or competition.get("altGameNote")
            or None,
            "status": status_type.get("description") or status_type.get("detail") or "Unknown",
            "status_type": state,
            "is_live": state == "in",
            "is_finished": state == "post",
            "result": self._result_label(home_score, away_score, state),
            "kickoff_time": competition.get("date") or competition.get("startDate"),
            "minute": status.get("displayClock") or status_type.get("shortDetail"),
            "home_team": self._normalize_team(home),
            "away_team": self._normalize_team(away),
            "score": {"home": home_score, "away": away_score},
            "venue": venue.get("fullName"),
            "referee": None,
            "home_score_display": home.get("score"),
            "away_score_display": away.get("score"),
            "statistics": self._extract_statistics(home, away),
        }

    def _normalize_group(self, group: dict[str, Any], fallback_name: str | None = None) -> dict[str, Any]:
        standings = group.get("standings", {})
        entries = standings.get("entries", [])
        return {
            "name": group.get("name") or group.get("abbreviation") or standings.get("name") or fallback_name or "Group",
            "entries": [self._normalize_group_entry(entry) for entry in entries if isinstance(entry, dict)],
        }

    def _normalize_group_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        stats = self._stats_map(entry.get("stats", []))
        rank = self._safe_int(stats.get("rank"))
        team_value = entry.get("team", "Unknown Team")
        team_id = (
            str(team_value.get("id"))
            if isinstance(team_value, dict) and team_value.get("id") is not None
            else str(entry.get("id", "unknown"))
        )
        team_name = (
            team_value.get("displayName")
            or team_value.get("shortDisplayName")
            or team_value.get("name")
            or "Unknown Team"
            if isinstance(team_value, dict)
            else str(team_value)
        )
        return {
            "rank": rank,
            "team_id": team_id,
            "team_name": str(team_name),
            "flag_path": cache_flag(team_id, self._entry_logo_url(entry), team_name=str(team_name)),
            "games_played": stats.get("gamesplayed"),
            "wins": stats.get("wins"),
            "draws": stats.get("ties"),
            "losses": stats.get("losses"),
            "goal_difference": stats.get("pointdifferential"),
            "points": stats.get("points"),
        }

    @staticmethod
    def _competition(payload: dict[str, Any]) -> dict[str, Any]:
        competitions = payload.get("competitions")
        if not isinstance(competitions, list) or not competitions:
            raise UpstreamUnavailableError("ESPN response did not include competitions.")
        competition = competitions[0]
        if not isinstance(competition, dict):
            raise UpstreamUnavailableError("ESPN returned an unexpected competition payload.")
        return competition

    @staticmethod
    def _find_competitor(competitors: list[dict[str, Any]], home_away: str) -> dict[str, Any]:
        for competitor in competitors:
            if competitor.get("homeAway") == home_away:
                return competitor
        return {}

    @staticmethod
    def _normalize_team(competitor: dict[str, Any]) -> dict[str, str]:
        team = competitor.get("team", {})
        team_id = str(team.get("id", competitor.get("id", "unknown")))
        team_name = str(
                team.get("displayName")
                or team.get("shortDisplayName")
                or team.get("name")
                or "Unknown Team"
            )
        return {
            "id": team_id,
            "name": team_name,
            "flag_path": cache_flag(team_id, EspnSoccerProvider._team_logo_url(team), team_name=team_name),
        }

    @staticmethod
    def _extract_statistics(home: dict[str, Any], away: dict[str, Any]) -> dict[str, str]:
        stats: dict[str, str] = {}
        for side, competitor in (("home", home), ("away", away)):
            for stat in competitor.get("statistics", []):
                name = stat.get("name")
                value = stat.get("displayValue")
                if name and value is not None:
                    stats[f"{side}_{name}"] = str(value)
        return stats

    @staticmethod
    def _stats_map(stats: list[dict[str, Any]]) -> dict[str, str]:
        values: dict[str, str] = {}
        for stat in stats:
            stat_type = stat.get("type")
            display_value = stat.get("displayValue")
            if stat_type and display_value is not None:
                values[str(stat_type).lower()] = str(display_value)
        return values

    @staticmethod
    def _extract_key_events(key_events: Any) -> list[dict[str, Any]]:
        if not isinstance(key_events, list):
            return []

        interesting_types = {
            "goal",
            "own-goal",
            "penalty---scored",
            "yellow-card",
            "red-card",
            "second-yellow-red-card",
        }
        events: list[dict[str, Any]] = []
        for event in key_events:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", {}).get("type") or "")
            is_scoring_play = bool(event.get("scoringPlay"))
            if not is_scoring_play and event_type not in interesting_types:
                continue

            participants = event.get("participants")
            first_participant = participants[0] if isinstance(participants, list) and participants else {}
            athlete = first_participant.get("athlete", {}) if isinstance(first_participant, dict) else {}
            team = event.get("team", {}) if isinstance(event.get("team"), dict) else {}
            clock = event.get("clock", {}) if isinstance(event.get("clock"), dict) else {}
            event_label = str(event.get("type", {}).get("text") or event_type.replace("-", " ").title() or "Event")

            events.append(
                {
                    "id": str(event.get("id", "")),
                    "event_type": event_type or "event",
                    "label": event_label,
                    "icon_path": EspnSoccerProvider._event_icon_path(event_type, is_scoring_play),
                    "minute": clock.get("displayValue"),
                    "team_id": str(team.get("id")) if team.get("id") is not None else None,
                    "team_name": team.get("displayName"),
                    "player_name": athlete.get("displayName"),
                    "text": event.get("shortText") or event.get("text"),
                    "is_scoring_play": is_scoring_play,
                }
            )
        return events

    @staticmethod
    def _event_icon_path(event_type: str, is_scoring_play: bool) -> str:
        if is_scoring_play or event_type in {"goal", "own-goal", "penalty---scored"}:
            return "/static/icons/goal.svg"
        if event_type == "yellow-card":
            return "/static/icons/yellow-card.svg"
        if event_type in {"red-card", "second-yellow-red-card"}:
            return "/static/icons/red-card.svg"
        return "/static/icons/event.svg"

    @staticmethod
    def _team_logo_url(team: dict[str, Any]) -> str | None:
        logos = team.get("logos")
        if isinstance(logos, list) and logos:
            first = logos[0]
            if isinstance(first, dict) and first.get("href"):
                return str(first["href"])
        if team.get("logo"):
            return str(team["logo"])
        return None

    @staticmethod
    def _entry_logo_url(entry: dict[str, Any]) -> str | None:
        team = entry.get("team")
        if isinstance(team, dict):
            team_logo = EspnSoccerProvider._team_logo_url(team)
            if team_logo:
                return team_logo
        logos = entry.get("logo")
        if isinstance(logos, list) and logos:
            first = logos[0]
            if isinstance(first, dict) and first.get("href"):
                return str(first["href"])
        return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _result_label(home_score: int | None, away_score: int | None, state: Any) -> str | None:
        if state != "post" or home_score is None or away_score is None:
            return None
        if home_score > away_score:
            return "home_win"
        if away_score > home_score:
            return "away_win"
        return "draw"
