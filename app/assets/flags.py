from __future__ import annotations
import re
import unicodedata

COUNTRY_CODES = {
    "algeria": "dz",
    "argentina": "ar",
    "australia": "au",
    "austria": "at",
    "belgium": "be",
    "bosnia herzegovina": "ba",
    "brazil": "br",
    "cameroon": "cm",
    "canada": "ca",
    "cape verde": "cv",
    "colombia": "co",
    "congo dr": "cd",
    "costa rica": "cr",
    "croatia": "hr",
    "curacao": "cw",
    "czech republic": "cz",
    "czechia": "cz",
    "denmark": "dk",
    "ecuador": "ec",
    "egypt": "eg",
    "england": "gb",
    "france": "fr",
    "germany": "de",
    "ghana": "gh",
    "haiti": "ht",
    "iran": "ir",
    "iran ir": "ir",
    "iraq": "iq",
    "italy": "it",
    "ivory coast": "ci",
    "japan": "jp",
    "jordan": "jo",
    "korea republic": "kr",
    "mexico": "mx",
    "morocco": "ma",
    "netherlands": "nl",
    "new zealand": "nz",
    "nigeria": "ng",
    "norway": "no",
    "panama": "pa",
    "paraguay": "py",
    "poland": "pl",
    "portugal": "pt",
    "qatar": "qa",
    "saudi arabia": "sa",
    "scotland": "gb",
    "senegal": "sn",
    "serbia": "rs",
    "south korea": "kr",
    "spain": "es",
    "sweden": "se",
    "switzerland": "ch",
    "south africa": "za",
    "tunisia": "tn",
    "tunesia": "tn",
    "turkey": "tr",
    "turkiye": "tr",
    "united arab emirates": "ae",
    "united states": "us",
    "uruguay": "uy",
    "uzbekistan": "uz",
    "usa": "us",
    "wales": "gb",
}


def cache_flag(
    team_id: str,
    logo_url: str | None,
    timeout_seconds: int = 10,
    team_name: str = "",
) -> str | None:
    del team_id, logo_url, timeout_seconds

    code = COUNTRY_CODES.get(_normalize_country_name(team_name))
    if code:
        return f"/static/flags/{code}.svg"
    return None


def _normalize_country_name(team_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", team_name)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
