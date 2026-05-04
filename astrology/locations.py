"""City and timezone lookup helpers for astrology inputs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent
CITY_CSV_PATH = BASE_DIR / "drik-panchanga" / "cities.csv"
ISO3166_TAB_PATH = Path("/usr/share/zoneinfo/iso3166.tab")
ZONE_TAB_PATH = Path("/usr/share/zoneinfo/zone.tab")

_CITIES_INDEX: dict[str, list[dict[str, Any]]] = {}
_COUNTRY_CITY_INDEX: dict[str, list[dict[str, Any]]] = {}
_TIMEZONE_COUNTRY_INDEX: dict[str, str] = {}


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("-", " ").split())


def _load_timezone_country_index() -> None:
    global _TIMEZONE_COUNTRY_INDEX
    if _TIMEZONE_COUNTRY_INDEX:
        return
    if not ISO3166_TAB_PATH.exists() or not ZONE_TAB_PATH.exists():
        return

    country_names: dict[str, str] = {}
    with ISO3166_TAB_PATH.open("r", encoding="utf-8") as country_file:
        for line in country_file:
            if not line.strip() or line.startswith("#"):
                continue
            code, name = line.strip().split("\t", 1)
            country_names[code] = name

    timezone_country_index: dict[str, str] = {}
    with ZONE_TAB_PATH.open("r", encoding="utf-8") as zone_file:
        for line in zone_file:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            country_code, _coordinates, timezone_name = parts[:3]
            timezone_country_index[timezone_name] = country_names.get(country_code, country_code)

    _TIMEZONE_COUNTRY_INDEX = timezone_country_index


def country_from_timezone(timezone_name: str) -> str:
    _load_timezone_country_index()
    return _TIMEZONE_COUNTRY_INDEX.get(timezone_name, timezone_name.replace("_", " "))


def load_cities_index() -> None:
    global _CITIES_INDEX, _COUNTRY_CITY_INDEX
    if _CITIES_INDEX and _COUNTRY_CITY_INDEX:
        return
    if not CITY_CSV_PATH.exists():
        raise ValueError("cities.csv not found in drik-panchanga folder")

    index: dict[str, list[dict[str, Any]]] = {}
    country_index: dict[str, list[dict[str, Any]]] = {}
    with CITY_CSV_PATH.open("r", encoding="utf-8") as city_file:
        reader = csv.reader(city_file, delimiter=":")
        for row in reader:
            if len(row) != 4:
                continue
            city_name, latitude, longitude, timezone_name = row
            entry = {
                "city": city_name,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "timezone_name": timezone_name,
                "country": country_from_timezone(timezone_name),
            }
            key = _normalize(city_name)
            index.setdefault(key, []).append(entry)
            country_key = _normalize(entry["country"])
            country_index.setdefault(country_key, []).append(entry)

    _CITIES_INDEX = index
    _COUNTRY_CITY_INDEX = country_index


def resolve_city(city: str, state: str = "", country: str = "") -> dict[str, Any]:
    load_cities_index()
    if not city:
        raise ValueError("city is required")

    context_tokens = " ".join([state or "", country or ""]).lower().replace(",", " ").split()
    expanded_context_tokens = set(context_tokens)
    key = _normalize(city)
    candidates = _CITIES_INDEX.get(key, [])

    if not candidates:
        partial_matches = []
        for city_key, entries in _CITIES_INDEX.items():
            if key in city_key:
                partial_matches.extend(entries)
        if len(partial_matches) == 1:
            return partial_matches[0]
        if not partial_matches:
            raise ValueError(f"city '{city}' not found in city map")
        raise ValueError(
            {
                "message": f"multiple partial matches found for city '{city}'",
                "matches": [
                    {
                        "city": entry["city"],
                        "country": entry.get("country"),
                        "timezone_name": entry["timezone_name"],
                        "latitude": entry["latitude"],
                        "longitude": entry["longitude"],
                    }
                    for entry in partial_matches[:5]
                ],
            }
        )

    if len(candidates) == 1:
        return candidates[0]

    if context_tokens:
        scored = []
        for candidate in candidates:
            haystack = f"{candidate['city']} {candidate['timezone_name']}".lower()
            score = sum(1 for token in expanded_context_tokens if token in haystack)
            scored.append((score, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored[0][0] > 0 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
            return scored[0][1]

    raise ValueError(
        {
            "message": f"multiple matches found for city '{city}'. add state or country to disambiguate",
            "matches": [
                {
                    "city": entry["city"],
                    "timezone_name": entry["timezone_name"],
                    "latitude": entry["latitude"],
                    "longitude": entry["longitude"],
                }
                for entry in candidates[:5]
            ],
        }
    )


def timezone_offset_hours_for_datetime(birth_datetime, timezone_name: str) -> float:
    tz = ZoneInfo(timezone_name)
    if birth_datetime.tzinfo is None:
        localized = birth_datetime.replace(tzinfo=tz)
    else:
        localized = birth_datetime.astimezone(tz)
    offset = localized.utcoffset()
    if offset is None:
        raise ValueError(f"could not determine UTC offset for timezone '{timezone_name}'")
    return offset.total_seconds() / 3600.0

