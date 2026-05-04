"""Birth chart engine."""

from __future__ import annotations

import datetime as _dt

from .constants import COMBUSTION_ORBS, PLANET_ORDER, PLANETARY_LORDSHIPS, EXALTATION_SIGNS, DEBILITATION_SIGNS, MOOLATRIKONA_SIGNS, PLANET_FRIENDS, VEDIC_ASPECTS
from .ephemeris import ascendant_and_houses, julian_day_from_datetime, moon_position, planet_position
from .locations import resolve_city, timezone_offset_hours_for_datetime
from .utils import (
    angular_distance,
    coerce_ayanamsa,
    degree_in_sign,
    localize_datetime,
    nakshatra_position,
    normalize_angle,
    parse_birth_datetime,
    parse_fixed_or_iana_timezone,
    sign_index_from_longitude,
    sign_modality,
    sign_name_from_index,
    whole_sign_house_number,
    zodiac_position,
)
from .core.base import AstrologyEngine


class BirthChartEngine(AstrologyEngine):
    def planet_dignity(self, planet_name: str, sign_index: int) -> str:
        if planet_name in {"Rahu", "Ketu"}:
            return "shadow"
        if MOOLATRIKONA_SIGNS.get(planet_name) == sign_index:
            return "moolatrikona"
        if EXALTATION_SIGNS.get(planet_name) == sign_index:
            return "exalted"
        if DEBILITATION_SIGNS.get(planet_name) == sign_index:
            return "debilitated"
        lordships = PLANETARY_LORDSHIPS.get(planet_name, [])
        if sign_index in lordships:
            return "own"
        friend_lords = {
            "Sun": {0, 4, 7},
            "Moon": {0, 4, 7},
            "Mars": {0, 3, 4, 7, 8, 11},
            "Mercury": {0, 1, 2, 3, 4, 7, 8, 11},
            "Jupiter": {0, 3, 4, 7, 8, 11},
            "Venus": {1, 2, 3, 4, 6, 7, 9, 10, 11},
            "Saturn": {1, 2, 3, 6, 9, 10, 11},
        }.get(planet_name, set())
        if sign_index in friend_lords:
            return "friendly"
        return "neutral"

    def combustion_status(self, planet_name: str, planet_longitude: float, sun_longitude: float) -> dict:
        orb = COMBUSTION_ORBS.get(planet_name)
        if orb is None:
            return {"is_combust": False, "orb": None, "distance_from_sun": angular_distance(planet_longitude, sun_longitude)}
        distance = angular_distance(planet_longitude, sun_longitude)
        return {"is_combust": distance <= orb, "orb": orb, "distance_from_sun": distance}

    def aspect_hints(self, planet_name: str, source_longitude: float, target_planets: dict[str, dict]) -> list[dict]:
        aspects = []
        for target_name, target in target_planets.items():
            if target_name == planet_name:
                continue
            diff = (sign_index_from_longitude(target["sidereal_longitude"]) - sign_index_from_longitude(source_longitude)) % 12
            aspect_degrees = VEDIC_ASPECTS.get(planet_name, [7])
            for aspect_distance in aspect_degrees:
                if diff == aspect_distance % 12:
                    aspects.append(
                        {
                            "target": target_name,
                            "aspect": f"{aspect_distance}th",
                            "type": "sign_aspect",
                            "sign_distance": diff,
                            "orb": 0.0,
                        }
                    )
        return aspects

    def build_location_context(self, payload: dict, birth_datetime_local: _dt.datetime) -> dict:
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        city = payload.get("city")
        state = payload.get("state", "")
        country = payload.get("country", "")

        resolved_city = None
        resolved_timezone_name = None
        if (latitude is None or longitude is None) and city:
            resolved_city = resolve_city(str(city), state=str(state), country=str(country))
            latitude = resolved_city["latitude"]
            longitude = resolved_city["longitude"]
            resolved_timezone_name = resolved_city["timezone_name"]

        timezone_name = payload.get("timezone_name") or resolved_timezone_name
        timezone_value = payload.get("timezone")
        if timezone_value is None and resolved_timezone_name:
            timezone_value = timezone_offset_hours_for_datetime(birth_datetime_local, resolved_timezone_name)

        return {
            "latitude": float(latitude) if latitude is not None else None,
            "longitude": float(longitude) if longitude is not None else None,
            "city": resolved_city["city"] if resolved_city else city,
            "state": state or None,
            "country": country or (resolved_city.get("country") if resolved_city else None),
            "timezone_name": timezone_name,
            "timezone": timezone_value,
            "resolved_city": resolved_city,
        }

    def calculate(self, payload: dict) -> dict:
        dt, tzinfo = parse_birth_datetime(payload)
        pre_resolved_city = None
        if (payload.get("latitude") is None or payload.get("longitude") is None) and payload.get("city"):
            pre_resolved_city = resolve_city(
                str(payload.get("city")), state=str(payload.get("state", "")), country=str(payload.get("country", ""))
            )

        timezone_source = next(
            (
                value
                for value in [
                    payload.get("timezone"),
                    payload.get("timezone_name"),
                    pre_resolved_city["timezone_name"] if pre_resolved_city else None,
                    tzinfo,
                ]
                if value is not None
            ),
            None,
        )
        if tzinfo is None and timezone_source is None:
            raise ValueError("timezone is required when birth_datetime is naive")

        local_dt = localize_datetime(dt, timezone_source)
        utc_dt = local_dt.astimezone(_dt.timezone.utc)
        ayanamsa, ayanamsa_value = coerce_ayanamsa(payload)
        jd_ut = julian_day_from_datetime(utc_dt)

        location = self.build_location_context(payload, local_dt)
        latitude = location["latitude"]
        longitude = location["longitude"]
        house_system = str(payload.get("house_system", "whole_sign")).strip().lower()

        planets: dict[str, dict] = {}
        for planet_name in PLANET_ORDER:
            if planet_name == "Ketu":
                continue
            positions = planet_position(jd_ut, planet_name, ayanamsa, ayanamsa_value)
            sidereal = zodiac_position(positions["longitude"])
            nakshatra = nakshatra_position(positions["longitude"])
            planets[planet_name] = {
                **positions,
                **sidereal,
                **nakshatra,
                "dignity": self.planet_dignity(planet_name, sidereal["sign_index"]),
                "combustion": None,
                "house": None,
            }

        if "Sun" in planets:
            sun_longitude = planets["Sun"]["sidereal_longitude"] if "sidereal_longitude" in planets["Sun"] else planets["Sun"]["longitude"]
        else:
            sun_longitude = planet_position(jd_ut, "Sun", ayanamsa, ayanamsa_value)["longitude"]

        for planet_name, planet in planets.items():
            planet["sidereal_longitude"] = planet["longitude"]
            planet["combustion"] = self.combustion_status(planet_name, planet["sidereal_longitude"], sun_longitude)
            planet["retrograde"] = bool(planet["retrograde"])

        rahu = planet_position(jd_ut, "Rahu", ayanamsa, ayanamsa_value)
        ketu_longitude = normalize_angle(rahu["longitude"] + 180.0)
        planets["Rahu"] = {
            **rahu,
            **zodiac_position(rahu["longitude"]),
            **nakshatra_position(rahu["longitude"]),
            "sidereal_longitude": rahu["longitude"],
            "dignity": self.planet_dignity("Rahu", sign_index_from_longitude(rahu["longitude"])),
            "combustion": self.combustion_status("Rahu", rahu["longitude"], sun_longitude),
            "retrograde": bool(rahu["retrograde"]),
            "house": None,
        }
        planets["Ketu"] = {
            "longitude": ketu_longitude,
            "sidereal_longitude": ketu_longitude,
            **zodiac_position(ketu_longitude),
            **nakshatra_position(ketu_longitude),
            "speed_longitude": -rahu["speed_longitude"],
            "retrograde": bool(rahu["retrograde"]),
            "distance": None,
            "dignity": self.planet_dignity("Ketu", sign_index_from_longitude(ketu_longitude)),
            "combustion": self.combustion_status("Ketu", ketu_longitude, sun_longitude),
            "house": None,
        }

        ascendant = None
        houses = None
        if latitude is not None and longitude is not None:
            house_data = ascendant_and_houses(jd_ut, latitude, longitude, ayanamsa, ayanamsa_value, house_system)
            asc_long = house_data["ascendant_longitude"]
            ascendant = {
                "longitude": asc_long,
                **zodiac_position(asc_long),
                **nakshatra_position(asc_long),
            }
            houses = {
                "system": house_system,
                "ascendant_longitude": asc_long,
                "cusps": house_data["cusps"],
                "ascmc": house_data["ascmc"],
            }
            asc_sign_index = ascendant["sign_index"]
            for planet in planets.values():
                planet["house"] = whole_sign_house_number(asc_sign_index, planet["sign_index"])

        aspects = []
        for planet_name, planet in planets.items():
            aspects.extend(self.aspect_hints(planet_name, planet["sidereal_longitude"], planets))

        return {
            "input": {
                "birth_datetime": local_dt.isoformat(),
                "birth_datetime_utc": utc_dt.isoformat(),
                "timezone": location["timezone"],
                "timezone_name": location["timezone_name"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "ayanamsa": ayanamsa,
                "ayanamsa_value": ayanamsa_value,
                "house_system": house_system,
            },
            "julian_day_ut": jd_ut,
            "location": location,
            "ascendant": ascendant,
            "houses": houses,
            "planets": planets,
            "aspects": aspects,
            "summary": {
                "chart_type": "sidereal",
                "location_based": latitude is not None and longitude is not None,
                "planet_count": len(planets),
            },
        }


DEFAULT_BIRTH_CHART_ENGINE = BirthChartEngine()


def calculate_birth_chart(payload: dict) -> dict:
    return DEFAULT_BIRTH_CHART_ENGINE.calculate(payload)
