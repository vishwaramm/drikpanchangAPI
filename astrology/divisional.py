"""Divisional chart engine."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import SIGN_NAMES
from .utils import degree_in_sign, normalize_angle, sign_index_from_longitude, sign_name_from_index, sign_modality
from .core.base import AstrologyEngine


@dataclass(frozen=True)
class VargaResult:
    name: str
    divisor: int
    method: str


VARGA_CONFIG = {
    "D1": VargaResult("D1", 1, "rashi"),
    "D2": VargaResult("D2", 2, "hora"),
    "D3": VargaResult("D3", 3, "drekkana"),
    "D4": VargaResult("D4", 4, "chaturthamsa"),
    "D7": VargaResult("D7", 7, "saptamsa"),
    "D9": VargaResult("D9", 9, "navamsa"),
    "D10": VargaResult("D10", 10, "dasamsa"),
    "D12": VargaResult("D12", 12, "dwadashamsa"),
    "D16": VargaResult("D16", 16, "shodashamsa"),
    "D20": VargaResult("D20", 20, "vimsamsa"),
    "D24": VargaResult("D24", 24, "siddhamsa"),
    "D30": VargaResult("D30", 30, "trimshamsa"),
    "D60": VargaResult("D60", 60, "shashtiamsa"),
}


def _next_sign_index(start_index: int, offset: int) -> int:
    return (start_index + offset) % 12


def _start_sign_for_modality(sign_index: int, divisor: int) -> int:
    modality = sign_modality(sign_index)
    if divisor == 1:
        return sign_index
    if divisor == 2:
        return 3 if sign_index % 2 == 0 else 4  # Cancer / Leo
    if divisor == 30:
        return sign_index
    if divisor == 60:
        return sign_index
    if divisor == 9:
        if modality == "movable":
            return sign_index
        if modality == "fixed":
            return _next_sign_index(sign_index, 8)
        return _next_sign_index(sign_index, 4)
    if divisor == 10:
        if modality == "movable":
            return sign_index
        if modality == "fixed":
            return _next_sign_index(sign_index, 8)
        return _next_sign_index(sign_index, 4)
    if divisor == 12:
        return sign_index
    if divisor == 16:
        if modality == "movable":
            return sign_index
        if modality == "fixed":
            return _next_sign_index(sign_index, 6)
        return _next_sign_index(sign_index, 3)
    if divisor == 20:
        if modality == "movable":
            return sign_index
        if modality == "fixed":
            return _next_sign_index(sign_index, 6)
        return _next_sign_index(sign_index, 3)
    if divisor == 24:
        if modality == "movable":
            return sign_index
        if modality == "fixed":
            return _next_sign_index(sign_index, 6)
        return _next_sign_index(sign_index, 3)
    if divisor == 7:
        if modality == "movable":
            return sign_index
        if modality == "fixed":
            return _next_sign_index(sign_index, 6)
        return _next_sign_index(sign_index, 3)
    if divisor == 4:
        if modality == "movable":
            return sign_index
        if modality == "fixed":
            return _next_sign_index(sign_index, 3)
        return _next_sign_index(sign_index, 6)
    if divisor == 3:
        if sign_index % 2 == 0:
            return sign_index
        return sign_index
    return sign_index


def _segment_index(longitude: float, divisor: int) -> int:
    return int((normalize_angle(longitude) / 30.0) * divisor) % divisor


def _varga_sign_for_longitude(longitude: float, divisor: int) -> dict:
    sign_index = sign_index_from_longitude(longitude)
    degree = degree_in_sign(longitude)
    modality = sign_modality(sign_index)

    if divisor == 1:
        varga_sign_index = sign_index
    elif divisor == 2:
        varga_sign_index = 3 if (int(degree // 15) == 0 and sign_index % 2 == 0) or (int(degree // 15) == 1 and sign_index % 2 == 1) else 4
    elif divisor == 30:
        varga_sign_index = sign_index
    elif divisor == 60:
        varga_sign_index = sign_index
    else:
        start_sign = _start_sign_for_modality(sign_index, divisor)
        segment = min(divisor - 1, int(degree / (30.0 / divisor)))
        varga_sign_index = _next_sign_index(start_sign, segment)

    if divisor in {30, 60}:
        segment = _segment_index(longitude, divisor)
        return {
            "varga_sign_index": varga_sign_index,
            "varga_sign": sign_name_from_index(varga_sign_index),
            "segment_index": segment + 1,
        }

    segment = min(divisor - 1, int(degree / (30.0 / divisor)))
    return {
        "varga_sign_index": varga_sign_index,
        "varga_sign": sign_name_from_index(varga_sign_index),
        "segment_index": segment + 1,
    }


def _placement_for_longitude(longitude: float, divisor: int) -> dict:
    base = {
        "source_longitude": normalize_angle(longitude),
        "sign_index": sign_index_from_longitude(longitude),
        "sign": sign_name_from_index(sign_index_from_longitude(longitude)),
        "degree_in_sign": degree_in_sign(longitude),
    }
    if divisor == 30:
        degree = degree_in_sign(longitude)
        if base["sign_index"] % 2 == 0:
            if degree < 5:
                lord = "Mars"
            elif degree < 10:
                lord = "Saturn"
            elif degree < 18:
                lord = "Jupiter"
            elif degree < 25:
                lord = "Mercury"
            else:
                lord = "Venus"
        else:
            if degree < 5:
                lord = "Venus"
            elif degree < 12:
                lord = "Mercury"
            elif degree < 20:
                lord = "Jupiter"
            elif degree < 25:
                lord = "Saturn"
            else:
                lord = "Mars"
        return {**base, "varga_type": "trimshamsa", "segment_lord": lord, "segment_index": int((degree // 5) + 1)}

    if divisor == 60:
        return {**base, "varga_type": "shashtiamsa", "segment_index": int((normalize_angle(longitude) / 6.0) + 1)}

    mapped = _varga_sign_for_longitude(longitude, divisor)
    return {**base, "varga_type": VARGA_CONFIG[f"D{divisor}"].method, **mapped}


class DivisionalChartEngine(AstrologyEngine):
    def __init__(self, varga_config: dict[str, VargaResult] | None = None):
        self.varga_config = varga_config or VARGA_CONFIG

    def calculate(self, chart: dict) -> dict:
        planets = chart.get("planets", {})
        ascendant = chart.get("ascendant")
        results = {}

        for varga_name, config in self.varga_config.items():
            divisor = config.divisor
            placements = {}
            for planet_name, planet in planets.items():
                placements[planet_name] = _placement_for_longitude(planet["sidereal_longitude"], divisor)
            ascendant_placement = None
            if ascendant:
                ascendant_placement = _placement_for_longitude(ascendant["longitude"], divisor)
            results[varga_name] = {
                "name": varga_name,
                "divisor": divisor,
                "method": config.method,
                "ascendant": ascendant_placement,
                "placements": placements,
            }

        return {
            "source": {
                "chart_type": "sidereal",
                "reference_sign": chart.get("ascendant", {}).get("sign") if chart.get("ascendant") else None,
            },
            "vargas": results,
        }


DEFAULT_DIVISIONAL_CHART_ENGINE = DivisionalChartEngine()


def calculate_divisional_charts(chart: dict) -> dict:
    return DEFAULT_DIVISIONAL_CHART_ENGINE.calculate(chart)
