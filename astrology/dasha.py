"""Vimshottari dasha calculations."""

from __future__ import annotations

import datetime as _dt

from .constants import NAKSHATRA_NAMES, VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_YEARS
from .utils import (
    AVERAGE_SOLAR_YEAR_DAYS,
    normalize_angle,
    parse_birth_datetime,
    localize_datetime,
    year_fraction_to_timedelta,
)
from .locations import resolve_city
from .core.base import AstrologyEngine

NAKSHATRA_SPAN = 360.0 / 27.0
DASHA_LEVEL_NAMES = ["mahadasha", "antardasha", "pratyantardasha", "sookshma", "prana"]


def _sequence_index_for_nakshatra(nakshatra_index: int) -> int:
    return nakshatra_index % len(VIMSHOTTARI_SEQUENCE)


def _period_sequence(start_lord: str):
    start_index = VIMSHOTTARI_SEQUENCE.index(start_lord)
    for offset in range(len(VIMSHOTTARI_SEQUENCE)):
        yield VIMSHOTTARI_SEQUENCE[(start_index + offset) % len(VIMSHOTTARI_SEQUENCE)]


def _build_period(start: _dt.datetime, lord: str, years: float, birth_dt: _dt.datetime, depth: int, max_depth: int):
    duration = year_fraction_to_timedelta(years)
    end = start + duration
    level_name = DASHA_LEVEL_NAMES[depth] if depth < len(DASHA_LEVEL_NAMES) else f"level_{depth + 1}"
    node = {
        "lord": lord,
        "level": depth + 1,
        "level_name": level_name,
        "duration_years": years,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "active_at_birth": start <= birth_dt < end,
        "elapsed_at_birth_years": max(0.0, (birth_dt - start).total_seconds() / (AVERAGE_SOLAR_YEAR_DAYS * 86400.0)),
        "balance_at_birth_years": max(0.0, (end - birth_dt).total_seconds() / (AVERAGE_SOLAR_YEAR_DAYS * 86400.0)),
    }
    if depth < max_depth:
        children = []
        child_start = start
        for sub_lord in _period_sequence(lord):
            sub_years = years * VIMSHOTTARI_YEARS[sub_lord] / 120.0
            child = _build_period(child_start, sub_lord, sub_years, birth_dt, depth + 1, max_depth)
            children.append(child)
            child_start = _dt.datetime.fromisoformat(child["end"])
            if depth >= 1 and child["active_at_birth"]:
                # Deeper levels expand only the active chain to keep the tree size bounded.
                break
        node["children"] = children
    return node


def _cycle_start_from_birth(birth_dt: _dt.datetime, moon_nirayana_longitude: float):
    nakshatra_index = int(normalize_angle(moon_nirayana_longitude) // NAKSHATRA_SPAN)
    nakshatra_progress = (normalize_angle(moon_nirayana_longitude) % NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    start_lord = VIMSHOTTARI_SEQUENCE[_sequence_index_for_nakshatra(nakshatra_index)]
    current_years = VIMSHOTTARI_YEARS[start_lord]
    elapsed_years = current_years * nakshatra_progress
    cycle_start = birth_dt - year_fraction_to_timedelta(elapsed_years)
    cycle_end = cycle_start
    for lord in _period_sequence(start_lord):
        cycle_end += year_fraction_to_timedelta(VIMSHOTTARI_YEARS[lord])
    return {
        "nakshatra_index": nakshatra_index,
        "nakshatra_name": NAKSHATRA_NAMES[nakshatra_index],
        "start_lord": start_lord,
        "elapsed_years": elapsed_years,
        "remaining_years": current_years - elapsed_years,
        "cycle_start": cycle_start,
    }


class VimshottariDashaEngine(AstrologyEngine):
    def __init__(self, birth_chart_engine=None):
        from .birth_chart import DEFAULT_BIRTH_CHART_ENGINE

        self.birth_chart_engine = birth_chart_engine or DEFAULT_BIRTH_CHART_ENGINE

    def calculate(self, payload: dict, chart: dict | None = None, max_depth: int = 2):
        dt, _tzinfo = parse_birth_datetime(payload)
        resolved_city = None
        if payload.get("city"):
            resolved_city = resolve_city(
                str(payload.get("city")), state=str(payload.get("state", "")), country=str(payload.get("country", ""))
            )
        timezone_source = next(
            (
                value
                for value in [
                    payload.get("timezone"),
                    payload.get("timezone_name"),
                    resolved_city["timezone_name"] if resolved_city else None,
                    _tzinfo,
                ]
                if value is not None
            ),
            None,
        )
        if timezone_source is None:
            raise ValueError("timezone is required when birth_datetime is naive")
        local_dt = localize_datetime(dt, timezone_source)

        if chart and chart.get("planets") and chart["planets"].get("Moon"):
            moon_nirayana = chart["planets"]["Moon"]["sidereal_longitude"]
        else:
            chart = self.birth_chart_engine.calculate(payload)
            moon_nirayana = chart["planets"]["Moon"]["sidereal_longitude"]

        cycle = _cycle_start_from_birth(local_dt, moon_nirayana)
        cycle_start = cycle["cycle_start"]

        mahadashas = []
        current_start = cycle_start
        for lord in _period_sequence(cycle["start_lord"]):
            years = VIMSHOTTARI_YEARS[lord]
            period = _build_period(current_start, lord, years, local_dt, 0, max_depth)
            mahadashas.append(period)
            current_start = _dt.datetime.fromisoformat(period["end"])

        current_period = next((period for period in mahadashas if period["active_at_birth"]), None)
        if current_period is None:
            current_period = mahadashas[0]

        levels = {
            name: ("included" if depth <= max_depth else "excluded")
            for depth, name in enumerate(DASHA_LEVEL_NAMES)
        }

        return {
            "birth_datetime": local_dt.isoformat(),
            "nakshatra": cycle["nakshatra_name"],
            "nakshatra_index": cycle["nakshatra_index"] + 1,
            "moon_nirayana_longitude": moon_nirayana,
            "mahadasha_lord_at_birth": cycle["start_lord"],
            "dasha_balance": {
                "elapsed_years": cycle["elapsed_years"],
                "remaining_years": cycle["remaining_years"],
            },
            "cycle_start": cycle_start.isoformat(),
            "cycle_end": mahadashas[-1]["end"] if mahadashas else cycle_start.isoformat(),
            "mahadashas": mahadashas,
            "current_period": current_period,
            "levels": levels,
        }


DEFAULT_VIMSHOTTARI_DASHA_ENGINE = VimshottariDashaEngine()


def calculate_vimshottari_dasha(payload: dict, chart: dict | None = None, max_depth: int = 2):
    return DEFAULT_VIMSHOTTARI_DASHA_ENGINE.calculate(payload, chart=chart, max_depth=max_depth)
