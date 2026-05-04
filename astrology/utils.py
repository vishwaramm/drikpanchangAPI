"""Pure utility helpers for chart calculations."""

from __future__ import annotations

import datetime as _dt
from dataclasses import asdict, is_dataclass
from zoneinfo import ZoneInfo

from .constants import NAKSHATRA_NAMES, SIGN_NAMES

NAKSHATRA_SPAN = 360.0 / 27.0
PAADA_SPAN = 360.0 / 108.0
AVERAGE_SOLAR_YEAR_DAYS = 365.2425


def normalize_angle(value: float) -> float:
    return value % 360.0


def sign_index_from_longitude(longitude: float) -> int:
    return int(normalize_angle(longitude) // 30.0)


def sign_name_from_index(index: int) -> str:
    return SIGN_NAMES[index % 12]


def degree_in_sign(longitude: float) -> float:
    return normalize_angle(longitude) % 30.0


def zodiac_position(longitude: float) -> dict:
    sign_index = sign_index_from_longitude(longitude)
    degree = degree_in_sign(longitude)
    return {
        "sign_index": sign_index,
        "sign": sign_name_from_index(sign_index),
        "degree_in_sign": degree,
        "degree": normalize_angle(longitude),
    }


def nakshatra_position(longitude: float) -> dict:
    normalized = normalize_angle(longitude)
    nakshatra_index = int(normalized // NAKSHATRA_SPAN)
    if nakshatra_index > 26:
        nakshatra_index = 26
    pada = int(normalized // PAADA_SPAN) % 4 + 1
    return {
        "nakshatra_index": nakshatra_index,
        "nakshatra": NAKSHATRA_NAMES[nakshatra_index],
        "nakshatra_number": nakshatra_index + 1,
        "pada": pada,
    }


def sign_modality(sign_index: int) -> str:
    remainder = sign_index % 3
    if remainder == 0:
        return "movable"
    if remainder == 1:
        return "fixed"
    return "dual"


def angular_distance(a: float, b: float) -> float:
    diff = abs(normalize_angle(a) - normalize_angle(b))
    return min(diff, 360.0 - diff)


def signed_arc(a: float, b: float) -> float:
    """Signed smallest arc from a to b in degrees."""
    diff = normalize_angle(b) - normalize_angle(a)
    if diff > 180.0:
        diff -= 360.0
    if diff < -180.0:
        diff += 360.0
    return diff


def whole_sign_house_number(ascendant_sign_index: int, planet_sign_index: int) -> int:
    return ((planet_sign_index - ascendant_sign_index) % 12) + 1


def to_iso(dt: _dt.datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def jsonable(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, _dt.time):
        return value.isoformat()
    return value


def year_fraction_to_timedelta(years: float) -> _dt.timedelta:
    return _dt.timedelta(days=years * AVERAGE_SOLAR_YEAR_DAYS)


def parse_fixed_or_iana_timezone(value) -> _dt.tzinfo:
    if value is None:
        raise ValueError("timezone is required")
    if isinstance(value, _dt.tzinfo):
        return value
    if isinstance(value, (int, float)):
        return _dt.timezone(_dt.timedelta(hours=float(value)))
    text = str(value).strip()
    try:
        return _dt.timezone(_dt.timedelta(hours=float(text)))
    except ValueError:
        return ZoneInfo(text)


def localize_datetime(dt: _dt.datetime, timezone_value) -> _dt.datetime:
    tz = parse_fixed_or_iana_timezone(timezone_value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def datetime_to_utc(dt: _dt.datetime, timezone_value=None) -> _dt.datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(_dt.timezone.utc)
    if timezone_value is None:
        raise ValueError("timezone is required for naive datetimes")
    return localize_datetime(dt, timezone_value).astimezone(_dt.timezone.utc)


def parse_birth_datetime(payload: dict) -> tuple[_dt.datetime, _dt.tzinfo | None]:
    value = payload.get("birth_datetime")
    if value:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            dt = _dt.datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(
                "invalid birth_datetime format. Use ISO-8601 or YYYY-MM-DD HH:MM[:SS]"
            ) from exc
        tzinfo = dt.tzinfo
        if tzinfo is None and payload.get("timezone") is not None:
            tzinfo = parse_fixed_or_iana_timezone(payload["timezone"])
        return dt, tzinfo

    birth_date = payload.get("birth_date")
    birth_time = payload.get("birth_time")
    if not birth_date or not birth_time:
        raise ValueError("birth_datetime or birth_date and birth_time are required")

    if "T" in str(birth_time):
        raise ValueError("birth_time should be a time value, not a datetime")

    try:
        date_obj = _dt.date.fromisoformat(str(birth_date))
    except ValueError as exc:
        raise ValueError("invalid birth_date format. Use YYYY-MM-DD") from exc

    try:
        time_obj = _dt.time.fromisoformat(str(birth_time))
    except ValueError as exc:
        raise ValueError("invalid birth_time format. Use HH:MM[:SS]") from exc

    dt = _dt.datetime.combine(date_obj, time_obj)
    tzinfo = parse_fixed_or_iana_timezone(payload["timezone"]) if payload.get("timezone") is not None else None
    return dt, tzinfo


def coerce_ayanamsa(payload: dict) -> tuple[str, float | None]:
    value = payload.get("ayanamsa", "lahiri")
    numeric = payload.get("ayanamsa_value")
    if isinstance(value, (int, float)):
        return "user", float(value)
    return str(value), float(numeric) if numeric is not None else None

