"""Transit / gochar calculations."""

from __future__ import annotations

import datetime as _dt

from .constants import PLANET_ORDER, VEDIC_ASPECTS
from .ephemeris import planet_position
from .utils import angular_distance, normalize_angle, parse_birth_datetime, localize_datetime, year_fraction_to_timedelta, sign_index_from_longitude, sign_name_from_index
from .core.base import AstrologyEngine


PLANET_THEMES = {
    "Sun": {"identity", "authority"},
    "Moon": {"mind", "home"},
    "Mars": {"action", "conflict"},
    "Mercury": {"communication", "learning"},
    "Jupiter": {"growth", "wisdom"},
    "Venus": {"relationships", "comfort"},
    "Saturn": {"duty", "delay"},
    "Rahu": {"amplification", "disruption"},
    "Ketu": {"detachment", "spirituality"},
}

TRANSIT_EVENT_SCAN_MINUTES = 5


def _transit_hits(transit_chart: dict, natal_chart: dict) -> list[dict]:
    hits = []
    natal_planets = natal_chart.get("planets", {})
    for transit_name, transit_planet in transit_chart.get("planets", {}).items():
        for natal_name, natal_planet in natal_planets.items():
            if transit_name == natal_name:
                continue
            diff = (sign_index_from_longitude(natal_planet["sidereal_longitude"]) - sign_index_from_longitude(transit_planet["sidereal_longitude"])) % 12
            for aspect in VEDIC_ASPECTS.get(transit_name, [7]):
                if diff == aspect % 12:
                    hits.append(
                        {
                            "transit_planet": transit_name,
                            "natal_planet": natal_name,
                            "aspect": f"{aspect}th",
                            "sign_distance": diff,
                            "orb": 0.0,
                        }
                    )
    return hits


def _themes_for_hits(hits: list[dict]) -> list[str]:
    themes: set[str] = set()
    for hit in hits:
        themes.update(PLANET_THEMES.get(hit["transit_planet"], set()))
        themes.update(PLANET_THEMES.get(hit["natal_planet"], set()))
        if hit["aspect"] == "7th":
            themes.add("relationship")
        if hit["aspect"] in {"4th", "10th"}:
            themes.add("kendra_activation")
    return sorted(themes)


def _planet_state_at(point: _dt.datetime, natal_chart: dict, snapshot_builder, planet_name: str):
    snapshot = snapshot_builder(point, natal_chart)
    planets = snapshot.get("transit_chart", {}).get("planets", {})
    planet = planets.get(planet_name)
    if not planet:
        return None
    sign_index = planet.get("sign_index")
    retrograde = bool(planet.get("retrograde"))
    return {
        "sign_index": int(sign_index) if sign_index is not None else None,
        "retrograde": retrograde,
    }


def _refine_transition(
    left: _dt.datetime,
    right: _dt.datetime,
    natal_chart: dict,
    snapshot_builder,
    planet_name: str,
    left_state: dict,
    right_state: dict,
) -> _dt.datetime:
    low = left
    high = right
    low_state = dict(left_state)
    high_state = dict(right_state)
    for _ in range(16):
        if (high - low).total_seconds() <= 10:
            break
        mid = low + (high - low) / 2
        mid_state = _planet_state_at(mid, natal_chart, snapshot_builder, planet_name)
        if mid_state is None:
            break
        if mid_state == low_state:
            low = mid
            low_state = mid_state
        else:
            high = mid
            high_state = mid_state
    return low + (high - low) / 2


def _build_transit_snapshot(transit_local: _dt.datetime, natal_chart: dict) -> dict:
    transit_utc = transit_local.astimezone(_dt.timezone.utc)
    jd_ut = transit_utc.timestamp() / 86400.0 + 2440587.5
    ayanamsa = natal_chart.get("input", {}).get("ayanamsa", "lahiri")
    ayanamsa_value = natal_chart.get("input", {}).get("ayanamsa_value")

    planets = {}
    for planet_name in PLANET_ORDER:
        if planet_name == "Ketu":
            continue
        positions = planet_position(jd_ut, planet_name, ayanamsa, ayanamsa_value)
        planets[planet_name] = {
            **positions,
            "sidereal_longitude": positions["longitude"],
            "sign_index": sign_index_from_longitude(positions["longitude"]),
        }

    rahu = planet_position(jd_ut, "Rahu", ayanamsa, ayanamsa_value)
    planets["Rahu"] = {**rahu, "sidereal_longitude": rahu["longitude"], "sign_index": sign_index_from_longitude(rahu["longitude"])}
    ketu_longitude = normalize_angle(rahu["longitude"] + 180.0)
    planets["Ketu"] = {
        "longitude": ketu_longitude,
        "sidereal_longitude": ketu_longitude,
        "sign_index": sign_index_from_longitude(ketu_longitude),
        "retrograde": bool(rahu["retrograde"]),
    }

    transit_chart = {
        "input": {
            "transit_datetime": transit_local.isoformat(),
            "transit_datetime_utc": transit_utc.isoformat(),
        },
        "planets": planets,
    }
    hits = _transit_hits(transit_chart, natal_chart)
    summaries = []
    for transit_name, transit_planet in planets.items():
        natal_aspects = []
        for natal_name, natal_planet in natal_chart.get("planets", {}).items():
            distance = angular_distance(transit_planet["sidereal_longitude"], natal_planet["sidereal_longitude"])
            if distance <= 5.0:
                natal_aspects.append(
                    {
                        "natal_planet": natal_name,
                        "distance_deg": distance,
                        "conjunction": distance <= 1.0,
                    }
                )
        summaries.append(
            {
                "planet": transit_name,
                "sign": transit_planet["sign_index"],
                "natal_hits": natal_aspects,
            }
        )
    return {"transit_chart": transit_chart, "aspect_hits": hits, "summaries": summaries}


def _build_timed_windows(transit_local: _dt.datetime, natal_chart: dict, snapshot_builder=None) -> list[dict]:
    snapshot_builder = snapshot_builder or _build_transit_snapshot
    windows: list[dict] = []
    current: dict | None = None

    for hour in range(24):
        point = transit_local + _dt.timedelta(hours=hour)
        snapshot = snapshot_builder(point, natal_chart)
        top_hits = sorted(
            snapshot["aspect_hits"],
            key=lambda item: (item["transit_planet"], item["natal_planet"], item["aspect"]),
        )[:3]
        if not top_hits:
            if current is not None:
                windows.append(
                    {
                        "start": current["start"].isoformat(),
                        "end": current["end"].isoformat(),
                        "aspect_hit_count": current["aspect_hit_count"],
                        "conjunction_count": current["conjunction_count"],
                        "score": round(current["score_total"] / max(1, current["samples"]), 3),
                        "peak_score": round(current["peak_score"], 3),
                        "top_hits": current["top_hits"],
                        "dominant_themes": sorted(current["themes"]),
                    }
                )
                current = None
            continue

        signature = tuple((item["transit_planet"], item["natal_planet"], item["aspect"]) for item in top_hits)
        score = float(len(snapshot["aspect_hits"]) * 2 + sum(len(item["natal_hits"]) for item in snapshot["summaries"]))
        themes = set(_themes_for_hits(top_hits))

        if current and current["signature"] == signature and current["end"] == point:
            current["end"] = point + _dt.timedelta(hours=1)
            current["aspect_hit_count"] += len(snapshot["aspect_hits"])
            current["conjunction_count"] += sum(len(item["natal_hits"]) for item in snapshot["summaries"])
            current["score_total"] += score
            current["peak_score"] = max(current["peak_score"], score)
            current["samples"] += 1
            current["themes"].update(themes)
            current["top_hits"] = top_hits
        else:
            if current is not None:
                windows.append(
                    {
                        "start": current["start"].isoformat(),
                        "end": current["end"].isoformat(),
                        "aspect_hit_count": current["aspect_hit_count"],
                        "conjunction_count": current["conjunction_count"],
                        "score": round(current["score_total"] / max(1, current["samples"]), 3),
                        "peak_score": round(current["peak_score"], 3),
                        "top_hits": current["top_hits"],
                        "dominant_themes": sorted(current["themes"]),
                    }
                )
            current = {
                "signature": signature,
                "start": point,
                "end": point + _dt.timedelta(hours=1),
                "aspect_hit_count": len(snapshot["aspect_hits"]),
                "conjunction_count": sum(len(item["natal_hits"]) for item in snapshot["summaries"]),
                "score_total": score,
                "peak_score": score,
                "samples": 1,
                "themes": themes,
                "top_hits": top_hits,
            }

    if current is not None:
        windows.append(
            {
                "start": current["start"].isoformat(),
                "end": current["end"].isoformat(),
                "aspect_hit_count": current["aspect_hit_count"],
                "conjunction_count": current["conjunction_count"],
                "score": round(current["score_total"] / max(1, current["samples"]), 3),
                "peak_score": round(current["peak_score"], 3),
                "top_hits": current["top_hits"],
                "dominant_themes": sorted(current["themes"]),
            }
        )

    return windows


def _build_transit_events(transit_local: _dt.datetime, natal_chart: dict, snapshot_builder=None) -> list[dict]:
    snapshot_builder = snapshot_builder or _build_transit_snapshot
    samples: list[tuple[_dt.datetime, dict]] = []
    for step in range((24 * 60 // TRANSIT_EVENT_SCAN_MINUTES) + 1):
        point = transit_local + _dt.timedelta(minutes=TRANSIT_EVENT_SCAN_MINUTES * step)
        snapshot = snapshot_builder(point, natal_chart)
        transit_planets = snapshot.get("transit_chart", {}).get("planets", {})
        planet_state = {
            name: {
                "sign_index": planet.get("sign_index"),
                "retrograde": bool(planet.get("retrograde")),
            }
            for name, planet in transit_planets.items()
        }
        samples.append((point, planet_state))

    events: list[dict] = []
    for idx in range(1, len(samples)):
        prev_point, prev_state = samples[idx - 1]
        curr_point, curr_state = samples[idx]
        for planet_name in sorted(curr_state):
            previous = prev_state.get(planet_name)
            current = curr_state.get(planet_name)
            if not previous or not current:
                continue
            if previous["sign_index"] != current["sign_index"]:
                approx_time = _refine_transition(prev_point, curr_point, natal_chart, snapshot_builder, planet_name, previous, current)
                events.append(
                    {
                        "planet": planet_name,
                        "event_type": "ingress",
                        "start": prev_point.isoformat(),
                        "end": curr_point.isoformat(),
                        "approx_time": approx_time.isoformat(),
                        "from_sign": sign_name_from_index(int(previous["sign_index"])),
                        "to_sign": sign_name_from_index(int(current["sign_index"])),
                        "retrograde_state": "retrograde" if current["retrograde"] else "direct",
                        "themes": sorted(PLANET_THEMES.get(planet_name, set()) | {"ingress"}),
                    }
                )
            if previous["retrograde"] != current["retrograde"]:
                approx_time = _refine_transition(prev_point, curr_point, natal_chart, snapshot_builder, planet_name, previous, current)
                events.append(
                    {
                        "planet": planet_name,
                        "event_type": "station_retrograde" if current["retrograde"] else "station_direct",
                        "start": prev_point.isoformat(),
                        "end": curr_point.isoformat(),
                        "approx_time": approx_time.isoformat(),
                        "from_sign": sign_name_from_index(int(current["sign_index"])),
                        "to_sign": sign_name_from_index(int(current["sign_index"])),
                        "retrograde_state": "retrograde" if current["retrograde"] else "direct",
                        "themes": sorted(PLANET_THEMES.get(planet_name, set()) | {"station"}),
                    }
                )

    events.sort(key=lambda item: (item["approx_time"], item["planet"], item["event_type"]))
    return events


class TransitEngine(AstrologyEngine):
    def __init__(self, birth_chart_engine=None, snapshot_builder=None):
        from .birth_chart import DEFAULT_BIRTH_CHART_ENGINE

        self.birth_chart_engine = birth_chart_engine or DEFAULT_BIRTH_CHART_ENGINE
        self.snapshot_builder = snapshot_builder or _build_transit_snapshot

    def calculate(self, payload: dict, natal_chart: dict | None = None):
        natal_chart = natal_chart or self.birth_chart_engine.calculate(payload)
        transit_dt, _tzinfo = parse_birth_datetime(
            {
                "birth_datetime": payload.get("transit_datetime") or payload.get("date_time") or payload.get("date"),
                "timezone": payload.get("timezone") or natal_chart.get("input", {}).get("timezone"),
            }
        )
        transit_local = localize_datetime(
            transit_dt,
            payload.get("timezone") or payload.get("timezone_name") or natal_chart.get("input", {}).get("timezone"),
        )
        snapshot = self.snapshot_builder(transit_local, natal_chart)
        events = _build_transit_events(transit_local, natal_chart, self.snapshot_builder)
        forecast_days = max(0, int(payload.get("forecast_days", 0) or 0))
        forecast = []
        for offset in range(1, forecast_days + 1):
            forecast_local = transit_local + _dt.timedelta(days=offset)
            forecast_snapshot = self.snapshot_builder(forecast_local, natal_chart)
            top_hits = sorted(
                forecast_snapshot["summaries"],
                key=lambda item: len(item["natal_hits"]),
                reverse=True,
            )[:3]
            aspect_hit_count = len(forecast_snapshot["aspect_hits"])
            conjunction_count = sum(len(item["natal_hits"]) for item in forecast_snapshot["summaries"])
            timed_windows = _build_timed_windows(forecast_local, natal_chart, self.snapshot_builder)
            forecast_events = _build_transit_events(forecast_local, natal_chart, self.snapshot_builder)
            forecast.append(
                {
                    "date": forecast_local.date().isoformat(),
                    "transit_datetime": forecast_local.isoformat(),
                    "aspect_hit_count": aspect_hit_count,
                    "conjunction_count": conjunction_count,
                    "score": float(aspect_hit_count * 2 + conjunction_count),
                    "top_hits": top_hits,
                    "timed_windows": timed_windows,
                    "dominant_themes": sorted({theme for window in timed_windows for theme in window["dominant_themes"]})[:6],
                    "events": forecast_events,
                }
            )

        return {
            "transit_chart": snapshot["transit_chart"],
            "natal_chart": natal_chart,
            "aspect_hits": snapshot["aspect_hits"],
            "summaries": snapshot["summaries"],
            "events": events,
            "forecast": forecast,
        }


DEFAULT_TRANSIT_ENGINE = TransitEngine()


def calculate_transits(payload: dict, natal_chart: dict | None = None):
    return DEFAULT_TRANSIT_ENGINE.calculate(payload, natal_chart=natal_chart)
