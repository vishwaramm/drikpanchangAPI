"""Panchang engine wrapper around the legacy Drik Panchanga calculations."""

from __future__ import annotations

import datetime as _dt

from .core.base import AstrologyEngine
from .locations import resolve_city, timezone_offset_hours_for_datetime


class PanchangEngine(AstrologyEngine):
    def __init__(self, panchang_provider=None):
        from legacy_panchanga import calculate_panchang

        self.panchang_provider = panchang_provider or calculate_panchang

    def calculate(self, payload: dict) -> dict:
        date_value = payload.get("date")
        if not date_value:
            raise ValueError("date is required")

        date = _dt.date.fromisoformat(str(date_value))
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

        timezone_source = payload.get("timezone")
        timezone_name = payload.get("timezone_name") or (resolved_city["timezone_name"] if resolved_city else None)
        if timezone_source is None:
            if timezone_name is None:
                raise ValueError("timezone or timezone_name is required")
            timezone_source = timezone_offset_hours_for_datetime(_dt.datetime.combine(date, _dt.time.min), str(timezone_name))

        if latitude is None or longitude is None:
            raise ValueError("latitude and longitude are required")

        panchang = self.panchang_provider(date, float(latitude), float(longitude), float(timezone_source))
        return {
            "input": {
                "date": date.isoformat(),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "timezone": float(timezone_source),
                "timezone_name": timezone_name,
                "city": city,
                "state": state or None,
                "country": country or None,
            },
            "panchang": panchang,
        }


DEFAULT_PANCHANG_ENGINE = PanchangEngine()


def calculate_panchang(payload: dict) -> dict:
    return DEFAULT_PANCHANG_ENGINE.calculate(payload)
