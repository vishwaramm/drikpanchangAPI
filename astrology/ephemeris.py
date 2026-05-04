"""Swiss Ephemeris wrappers."""

from __future__ import annotations

from functools import lru_cache
from threading import RLock

from .constants import PLANET_TO_SWE_NAME
from .utils import normalize_angle

_LOCK = RLock()
_SWE = None


def get_swe():
    global _SWE
    if _SWE is not None:
        return _SWE
    import swisseph as swe  # type: ignore

    _SWE = swe
    return swe


def _sidereal_mode(swe, ayanamsa: str, ayanamsa_value: float | None = None):
    mode = str(ayanamsa or "lahiri").strip().lower()
    if mode in {"user", "custom", "ayanamsa"}:
        sid_mode = getattr(swe, "SIDM_USER", None)
        if sid_mode is None:
            raise ValueError("Swiss Ephemeris user ayanamsa mode is unavailable")
        if ayanamsa_value is None:
            raise ValueError("ayanamsa_value is required when ayanamsa='user'")
        swe.set_sid_mode(sid_mode, 0.0, float(ayanamsa_value))
        return

    mode_map = {
        "lahiri": getattr(swe, "SIDM_LAHIRI", None),
        "krishnamurti": getattr(swe, "SIDM_KRISHNAMURTI", None),
        "kp": getattr(swe, "SIDM_KRISHNAMURTI", None),
        "raman": getattr(swe, "SIDM_RAMAN", None),
        "fagan": getattr(swe, "SIDM_FAGAN_BRADLEY", None),
        "fagan_bradley": getattr(swe, "SIDM_FAGAN_BRADLEY", None),
        "lahiri_icrc": getattr(swe, "SIDM_LAHIRI_ICRC", None),
    }
    sid_mode = mode_map.get(mode)
    if sid_mode is None:
        sid_mode = getattr(swe, "SIDM_LAHIRI", None)
    if sid_mode is None:
        raise ValueError(f"unsupported ayanamsa '{ayanamsa}'")
    swe.set_sid_mode(sid_mode)


def _planet_id(swe, planet_name: str) -> int:
    planet_key = PLANET_TO_SWE_NAME.get(planet_name)
    if planet_key is None:
        raise ValueError(f"unsupported planet '{planet_name}'")
    return getattr(swe, planet_key)


@lru_cache(maxsize=4096)
def _calculate_planet_cached(jd_ut: float, planet_name: str, ayanamsa: str, ayanamsa_value: float | None):
    swe = get_swe()
    with _LOCK:
        _sidereal_mode(swe, ayanamsa, ayanamsa_value)
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
        xx, _ = swe.calc_ut(jd_ut, _planet_id(swe, planet_name), flags)
    longitude = normalize_angle(xx[0])
    speed = xx[3] if len(xx) > 3 else 0.0
    return {
        "longitude": longitude,
        "latitude": xx[1],
        "distance": xx[2],
        "speed_longitude": speed,
        "retrograde": speed < 0,
    }


def planet_position(jd_ut: float, planet_name: str, ayanamsa: str = "lahiri", ayanamsa_value: float | None = None):
    return _calculate_planet_cached(float(jd_ut), planet_name, ayanamsa, ayanamsa_value)


def moon_position(jd_ut: float, ayanamsa: str = "lahiri", ayanamsa_value: float | None = None):
    return planet_position(jd_ut, "Moon", ayanamsa, ayanamsa_value)


def ascendant_and_houses(
    jd_ut: float,
    latitude: float,
    longitude: float,
    ayanamsa: str = "lahiri",
    ayanamsa_value: float | None = None,
    house_system: str = "whole_sign",
):
    swe = get_swe()
    with _LOCK:
        _sidereal_mode(swe, ayanamsa, ayanamsa_value)
        if house_system == "whole_sign":
            # We still compute the ascendant degree from Swiss Ephemeris and derive houses separately.
            cusps, ascmc = swe.houses_ex(float(jd_ut), float(latitude), float(longitude), b"P", swe.FLG_SIDEREAL)
        else:
            system = house_system.encode("ascii")[:1]
            cusps, ascmc = swe.houses_ex(float(jd_ut), float(latitude), float(longitude), system, swe.FLG_SIDEREAL)
    return {
        "cusps": list(cusps),
        "ascmc": list(ascmc),
        "ascendant_longitude": normalize_angle(ascmc[0]),
    }


def julian_day_from_datetime(utc_datetime) -> float:
    swe = get_swe()
    decimal_hour = (
        utc_datetime.hour
        + utc_datetime.minute / 60.0
        + utc_datetime.second / 3600.0
        + utc_datetime.microsecond / 3_600_000_000.0
    )
    return swe.julday(utc_datetime.year, utc_datetime.month, utc_datetime.day, decimal_hour)

