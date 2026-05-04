"""Muhurta scoring and filtering engine."""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .core.base import AstrologyEngine
from .locations import resolve_city, timezone_offset_hours_for_datetime

BASE_DIR = Path(__file__).resolve().parent.parent
SANSKRIT_NAMES_PATH = BASE_DIR / "drik-panchanga" / "sanskrit_names.json"

TITHI_FAVORABLE = {2, 3, 5, 7, 10, 11, 13, 17, 18, 20, 22, 25, 26, 28}
NAKSHATRA_FAVORABLE = {
    4,   # Rohini
    5,   # Mrigashirsha
    7,   # Punarvasu
    8,   # Pushya
    12,  # Uttara Phalguni
    13,  # Hasta
    15,  # Swati
    17,  # Anuradha
    21,  # Uttara Ashadha
    22,  # Shravana
    23,  # Dhanishta
    27,  # Revati
}
YOGA_FAVORABLE = {
    2, 3, 4, 8, 12, 16, 18, 20, 21, 22, 23, 24, 25, 26
}
KARANA_FAVORABLE = {2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55}
WEEKDAY_WEIGHTS = {
    0: 0,
    1: 1,
    2: -1,
    3: 2,
    4: 3,
    5: 2,
    6: -2,
}
RAHU_KALAM_SEGMENT = {0: 8, 1: 2, 2: 7, 3: 5, 4: 6, 5: 4, 6: 3}
YAMAGANDA_SEGMENT = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 7, 6: 6}
GULIKA_SEGMENT = {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}


@dataclass(frozen=True)
class MuhurtaScore:
    name: str
    score: int
    max_score: int
    source: str
    notes: dict


@dataclass(frozen=True)
class MuhurtaProfile:
    name: str
    preferred_weekdays: set[int] = frozenset()
    preferred_tithis: set[int] = frozenset()
    preferred_nakshatras: set[int] = frozenset()
    preferred_yogas: set[int] = frozenset()
    weekday_weight: int = 1
    tithi_weight: int = 1
    nakshatra_weight: int = 1
    yoga_weight: int = 1
    karana_weight: int = 1
    avoid_weekdays: set[int] = frozenset()
    avoid_tithis: set[int] = frozenset()
    avoid_nakshatras: set[int] = frozenset()
    avoid_yogas: set[int] = frozenset()
    avoid_karanas: set[int] = frozenset()


MUHURTA_PROFILES: dict[str, MuhurtaProfile] = {
    "general": MuhurtaProfile(
        name="general",
        preferred_weekdays=frozenset({1, 3, 4, 5}),
        preferred_tithis=frozenset(TITHI_FAVORABLE),
        preferred_nakshatras=frozenset(NAKSHATRA_FAVORABLE),
        preferred_yogas=frozenset(YOGA_FAVORABLE),
        weekday_weight=1,
        tithi_weight=1,
        nakshatra_weight=1,
        yoga_weight=1,
        karana_weight=1,
        avoid_weekdays=frozenset({0, 6}),
        avoid_tithis=frozenset({4, 9, 14, 30}),
        avoid_nakshatras=frozenset({1, 6, 9, 19}),
        avoid_yogas=frozenset({1, 6, 7, 9, 10, 11, 13, 14, 15, 17, 19}),
        avoid_karanas=frozenset({1, 8, 15, 22, 29, 36, 43, 50, 57}),
    ),
    "career": MuhurtaProfile(
        name="career",
        preferred_weekdays=frozenset({1, 3, 4, 5}),
        preferred_nakshatras=frozenset({8, 12, 13, 17, 21, 22, 23}),
        weekday_weight=2,
        tithi_weight=1,
        nakshatra_weight=2,
        yoga_weight=1,
        karana_weight=1,
        avoid_weekdays=frozenset({2, 6}),
        avoid_tithis=frozenset({4, 8, 9, 14, 15, 30}),
        avoid_nakshatras=frozenset({1, 6, 9, 19}),
        avoid_yogas=frozenset({1, 6, 7, 9, 10, 11, 13, 14, 15, 17, 19}),
    ),
    "marriage": MuhurtaProfile(
        name="marriage",
        preferred_weekdays=frozenset({5}),
        preferred_tithis=frozenset(TITHI_FAVORABLE),
        preferred_nakshatras=frozenset({2, 4, 7, 8, 12, 13, 15, 17, 21, 22, 27}),
        weekday_weight=2,
        tithi_weight=2,
        nakshatra_weight=1,
        yoga_weight=1,
        karana_weight=1,
        avoid_weekdays=frozenset({2, 6}),
        avoid_tithis=frozenset({4, 8, 9, 14, 15, 30}),
        avoid_nakshatras=frozenset({1, 6, 9, 19}),
        avoid_yogas=frozenset({1, 6, 7, 9, 10, 11, 13, 14, 15, 17, 19}),
    ),
    "travel": MuhurtaProfile(
        name="travel",
        preferred_weekdays=frozenset({1, 3, 4, 5}),
        preferred_yogas=frozenset(YOGA_FAVORABLE),
        weekday_weight=1,
        tithi_weight=1,
        nakshatra_weight=1,
        yoga_weight=2,
        karana_weight=1,
        avoid_tithis=frozenset({4, 8, 9, 14, 15, 30}),
        avoid_nakshatras=frozenset({6, 9, 19}),
        avoid_yogas=frozenset({1, 6, 7, 10, 14, 19}),
    ),
    "education": MuhurtaProfile(
        name="education",
        preferred_weekdays=frozenset({1, 3, 4}),
        preferred_nakshatras=frozenset({5, 7, 8, 12, 13, 17, 21, 22, 27}),
        weekday_weight=2,
        tithi_weight=1,
        nakshatra_weight=2,
        yoga_weight=1,
        karana_weight=1,
        avoid_weekdays=frozenset({0, 2, 6}),
        avoid_tithis=frozenset({4, 8, 9, 14, 15, 30}),
        avoid_nakshatras=frozenset({1, 6, 9, 19}),
        avoid_yogas=frozenset({1, 6, 7, 10, 14, 19}),
    ),
    "finance": MuhurtaProfile(
        name="finance",
        preferred_weekdays=frozenset({1, 3, 4, 5}),
        preferred_tithis=frozenset({2, 3, 5, 10, 11, 13, 17, 18, 20, 22, 25, 26}),
        weekday_weight=1,
        tithi_weight=2,
        nakshatra_weight=1,
        yoga_weight=1,
        karana_weight=1,
        avoid_weekdays=frozenset({0, 2, 6}),
        avoid_tithis=frozenset({4, 8, 9, 14, 15, 30}),
        avoid_nakshatras=frozenset({1, 6, 9, 19}),
        avoid_yogas=frozenset({1, 6, 7, 10, 14, 19}),
    ),
}


def _load_names() -> dict[str, dict[str, str]]:
    with SANSKRIT_NAMES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


SANSKRIT_NAMES = _load_names()


def _component_name(component: str, index: int) -> str:
    mapping = SANSKRIT_NAMES[component]
    return mapping.get(str(index), str(index))


def _extract_point(values, index: int) -> int:
    if isinstance(values, (list, tuple)) and values:
        return int(values[0])
    if isinstance(values, dict):
        for key in ("index", "value", "number", "id"):
            if key in values:
                return int(values[key])
    return int(index)


def _minutes_from_hms(value) -> int:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        hours, minutes, seconds = value[:3]
        return int(hours) * 60 + int(minutes) + (1 if int(seconds) >= 30 else 0)
    if isinstance(value, dict):
        return _minutes_from_hms([value.get("hours", 0), value.get("minutes", 0), value.get("seconds", 0)])
    return 0


def _minutes_to_hms(total_minutes: int) -> list[int]:
    total_minutes = max(0, int(total_minutes))
    return [total_minutes // 60, total_minutes % 60, 0]


def _time_from_minutes(date: _dt.date, minutes: float, tzinfo: _dt.tzinfo | None = None) -> str:
    base = _dt.datetime.combine(date, _dt.time.min, tzinfo=tzinfo)
    return (base + _dt.timedelta(minutes=minutes)).time().isoformat(timespec="minutes")


def _segment_windows(date: _dt.date, sunrise: list[int], sunset: list[int], segment_index: int) -> tuple[str, str]:
    start_minutes = _minutes_from_hms(sunrise)
    end_minutes = _minutes_from_hms(sunset)
    day_duration = max(1, end_minutes - start_minutes)
    segment_length = day_duration / 8.0
    window_start = start_minutes + segment_length * (segment_index - 1)
    window_end = window_start + segment_length
    return _time_from_minutes(date, window_start), _time_from_minutes(date, window_end)


def _abhijit_window(date: _dt.date, sunrise: list[int], sunset: list[int]) -> tuple[str, str]:
    start_minutes = _minutes_from_hms(sunrise)
    end_minutes = _minutes_from_hms(sunset)
    day_duration = max(1, end_minutes - start_minutes)
    midday = start_minutes + (day_duration / 2.0)
    span = max(12.0, day_duration / 15.0)
    return _time_from_minutes(date, midday - span / 2.0), _time_from_minutes(date, midday + span / 2.0)


def _activity_bonus(activity_type: str, weekday: int, tithi: int, nakshatra: int, yoga: int) -> int:
    activity_type = activity_type.lower()
    bonus = 0
    if activity_type in {"general", "default"}:
        return bonus

    if activity_type == "career":
        if weekday in {1, 3, 4, 5}:
            bonus += 2
        if nakshatra in {8, 12, 13, 17, 21, 22, 23}:
            bonus += 1
    elif activity_type == "marriage":
        if weekday == 5:
            bonus += 2
        if tithi in {2, 3, 5, 7, 10, 11, 13, 17, 18, 20, 22, 25, 26, 28}:
            bonus += 1
    elif activity_type == "travel":
        if weekday in {1, 3, 4, 5}:
            bonus += 1
        if yoga in {2, 3, 4, 8, 12, 16, 18, 20, 21, 22, 23, 24, 25, 26}:
            bonus += 1
    elif activity_type == "education":
        if weekday in {1, 3, 4}:
            bonus += 2
        if nakshatra in {5, 7, 8, 12, 13, 17, 21, 22, 27}:
            bonus += 1
    elif activity_type == "finance":
        if weekday in {1, 3, 4, 5}:
            bonus += 1
        if tithi in {2, 3, 5, 10, 11, 13, 17, 18, 20, 22, 25, 26}:
            bonus += 1
    return bonus


def _profile_bonus(profile: MuhurtaProfile, weekday: int, tithi: int, nakshatra: int, yoga: int, karana: int) -> int:
    bonus = 0
    if weekday in profile.preferred_weekdays:
        bonus += profile.weekday_weight
    if tithi in profile.preferred_tithis:
        bonus += profile.tithi_weight
    if nakshatra in profile.preferred_nakshatras:
        bonus += profile.nakshatra_weight
    if yoga in profile.preferred_yogas:
        bonus += profile.yoga_weight
    if weekday in profile.avoid_weekdays:
        bonus -= max(1, profile.weekday_weight)
    if tithi in profile.avoid_tithis:
        bonus -= max(1, profile.tithi_weight)
    if nakshatra in profile.avoid_nakshatras:
        bonus -= max(1, profile.nakshatra_weight)
    if yoga in profile.avoid_yogas:
        bonus -= max(1, profile.yoga_weight)
    if karana in profile.avoid_karanas:
        bonus -= max(1, profile.karana_weight)
    return bonus


class MuhurtaEngine(AstrologyEngine):
    def __init__(self, panchang_provider: Callable[[_dt.date, float, float, float], dict] | None = None):
        from legacy_panchanga import calculate_panchang

        self.panchang_provider = panchang_provider or calculate_panchang

    def _score_day(self, date: _dt.date, panchang: dict, activity_type: str = "general") -> dict:
        profile = MUHURTA_PROFILES.get(activity_type, MUHURTA_PROFILES["general"])
        tithi = int(panchang["Tithi"][0])
        nakshatra = int(panchang["Nakshatra"][0])
        yoga = int(panchang["Yoga"][0])
        karana = int(panchang["karana"][0])
        weekday = int(panchang["Vaara"])
        sunrise = panchang["Sunrise"]
        sunset = panchang["Sunset"]
        day_duration = panchang["Day Duration"]

        scores = [
            MuhurtaScore(
                name="weekday",
                score=WEEKDAY_WEIGHTS.get(weekday, 0),
                max_score=3,
                source="traditional/best_judgment",
                notes={"weekday": _component_name("varas", weekday)},
            ),
            MuhurtaScore(
                name="tithi",
                score=3 if tithi in TITHI_FAVORABLE else 0,
                max_score=3,
                source="traditional/best_judgment",
                notes={"tithi": _component_name("tithis", tithi)},
            ),
            MuhurtaScore(
                name="nakshatra",
                score=4 if nakshatra in NAKSHATRA_FAVORABLE else 1,
                max_score=4,
                source="traditional/best_judgment",
                notes={"nakshatra": _component_name("nakshatras", nakshatra)},
            ),
            MuhurtaScore(
                name="yoga",
                score=3 if yoga in YOGA_FAVORABLE else 0,
                max_score=3,
                source="traditional/best_judgment",
                notes={"yoga": _component_name("yogas", yoga)},
            ),
            MuhurtaScore(
                name="karana",
                score=2 if karana in KARANA_FAVORABLE else 0,
                max_score=2,
                source="traditional/best_judgment",
                notes={"karana": _component_name("karanas", karana)},
            ),
        ]

        activity_bonus = _activity_bonus(activity_type, weekday, tithi, nakshatra, yoga)
        profile_bonus = _profile_bonus(profile, weekday, tithi, nakshatra, yoga, karana)
        total = sum(item.score for item in scores) + activity_bonus + profile_bonus
        max_score = sum(item.max_score for item in scores) + 3 + max(0, profile.weekday_weight + profile.tithi_weight + profile.nakshatra_weight + profile.yoga_weight)
        midpoint_bonus = 2 if weekday != 3 else 0
        exclusions = []
        if weekday in profile.avoid_weekdays:
            exclusions.append("weekday")
        if tithi in profile.avoid_tithis:
            exclusions.append("tithi")
        if nakshatra in profile.avoid_nakshatras:
            exclusions.append("nakshatra")
        if yoga in profile.avoid_yogas:
            exclusions.append("yoga")
        if karana in profile.avoid_karanas:
            exclusions.append("karana")

        rahu_kalam = _segment_windows(date, sunrise, sunset, RAHU_KALAM_SEGMENT[weekday])
        yamaganda = _segment_windows(date, sunrise, sunset, YAMAGANDA_SEGMENT[weekday])
        gulika = _segment_windows(date, sunrise, sunset, GULIKA_SEGMENT[weekday])
        abhijit = _abhijit_window(date, sunrise, sunset)

        bonuses = []
        if activity_bonus > 0:
            bonuses.append(
                {
                    "name": "activity_bonus",
                    "score": activity_bonus,
                    "max_score": 3,
                    "source": "best_judgment",
                    "notes": {"activity_type": activity_type},
                }
            )
        if profile_bonus > 0:
            bonuses.append(
                {
                    "name": "profile_bonus",
                    "score": profile_bonus,
                    "max_score": max(1, profile.weekday_weight + profile.tithi_weight + profile.nakshatra_weight + profile.yoga_weight),
                    "source": "traditional/profile",
                    "notes": {"profile": profile.name},
                }
            )

        windows = {
            "abhijit": {"start": abhijit[0], "end": abhijit[1], "source": "traditional/best_judgment"},
            "rahu_kalam": {"start": rahu_kalam[0], "end": rahu_kalam[1], "source": "traditional"},
            "yamaganda": {"start": yamaganda[0], "end": yamaganda[1], "source": "traditional"},
            "gulika": {"start": gulika[0], "end": gulika[1], "source": "traditional"},
        }
        recommendations = []
        if weekday != 3:
            recommendations.append("abhijit")
        if total >= (max_score * 0.7):
            recommendations.append("general")

        return {
            "date": date.isoformat(),
            "weekday_index": weekday,
            "weekday": _component_name("varas", weekday),
            "panchang": {
                "tithi": {"index": tithi, "name": _component_name("tithis", tithi)},
                "nakshatra": {"index": nakshatra, "name": _component_name("nakshatras", nakshatra)},
                "yoga": {"index": yoga, "name": _component_name("yogas", yoga)},
                "karana": {"index": karana, "name": _component_name("karanas", karana)},
                "sunrise": sunrise,
                "sunset": sunset,
                "day_duration": day_duration,
            },
            "score": {
                "total": total,
                "max": max_score,
                "normalized": round(total / max_score, 3) if max_score else 0.0,
                "components": [
                    {
                        "name": item.name,
                        "score": item.score,
                        "max_score": item.max_score,
                        "source": item.source,
                        "notes": item.notes,
                    }
                    for item in scores
                ] + bonuses,
                "recommendations": recommendations,
            },
            "windows": windows,
            "avoid_windows": ["rahu_kalam", "yamaganda", "gulika"],
            "summary": {
                "is_favorable": total >= 10,
                "activity_type": activity_type,
                "midday_bonus": midpoint_bonus,
                "profile": profile.name,
                "exclusions": sorted(set(exclusions)),
                "strictly_recommended": not exclusions and total >= 10,
            },
        }

    def calculate(self, payload: dict) -> dict:
        date_value = payload.get("date")
        start_date_value = payload.get("start_date")
        end_date_value = payload.get("end_date")
        activity_type = str(payload.get("activity_type", "general")).strip().lower()
        minimum_score = int(payload.get("minimum_score", 0))

        if date_value:
            dates = [_dt.date.fromisoformat(str(date_value))]
        elif start_date_value and end_date_value:
            start_date = _dt.date.fromisoformat(str(start_date_value))
            end_date = _dt.date.fromisoformat(str(end_date_value))
            if end_date < start_date:
                raise ValueError("end_date must be on or after start_date")
            dates = [start_date + _dt.timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]
        else:
            raise ValueError("date or start_date and end_date are required")

        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        city = payload.get("city")
        state = str(payload.get("state", ""))
        country = str(payload.get("country", ""))

        resolved_city = None
        if (latitude is None or longitude is None) and city:
            resolved_city = resolve_city(str(city), state=state, country=country)
            latitude = resolved_city["latitude"]
            longitude = resolved_city["longitude"]

        results = []
        for date in dates:
            timezone_source = payload.get("timezone")
            if timezone_source is None:
                timezone_name = payload.get("timezone_name") or (resolved_city["timezone_name"] if resolved_city else None)
                if timezone_name is None:
                    raise ValueError("timezone or timezone_name is required")
                timezone_source = timezone_offset_hours_for_datetime(_dt.datetime.combine(date, _dt.time.min), str(timezone_name))

            panchang = self.panchang_provider(date, float(latitude), float(longitude), float(timezone_source))
            day_result = self._score_day(date, panchang, activity_type=activity_type)
            if day_result["score"]["total"] >= minimum_score:
                results.append(day_result)

        results.sort(key=lambda item: item["score"]["total"], reverse=True)
        return {
            "input": {
                "date": date_value,
                "start_date": start_date_value,
                "end_date": end_date_value,
                "activity_type": activity_type,
                "minimum_score": minimum_score,
                "latitude": float(latitude) if latitude is not None else None,
                "longitude": float(longitude) if longitude is not None else None,
                "timezone": float(payload.get("timezone")) if payload.get("timezone") is not None else None,
                "timezone_name": payload.get("timezone_name") or (resolved_city["timezone_name"] if resolved_city else None),
                "city": city,
                "state": state or None,
                "country": country or None,
            },
            "results": results,
            "best_dates": results[:5],
            "summary": {
                "count": len(results),
                "best_score": results[0]["score"]["total"] if results else None,
                "activity_type": activity_type,
            },
        }


DEFAULT_MUHURTA_ENGINE = MuhurtaEngine()


def calculate_muhurta(payload: dict) -> dict:
    return DEFAULT_MUHURTA_ENGINE.calculate(payload)
