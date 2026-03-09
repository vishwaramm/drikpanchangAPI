import datetime
import csv
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any, Callable, Dict, List

DRIK_PANCHANGA_PATH = Path(__file__).resolve().parent / "drik-panchanga"
if str(DRIK_PANCHANGA_PATH) not in sys.path:
    sys.path.append(str(DRIK_PANCHANGA_PATH))

import panchanga
import swisseph as swe

NAKSHATRA_NAMES = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashirsha",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

NAKSHATRA_PADA_SYLLABLES = {
    "Ashwini": ["Chu", "Che", "Cho", "La"],
    "Bharani": ["Li", "Lu", "Le", "Lo"],
    "Krittika": ["A", "I", "U", "E"],
    "Rohini": ["O", "Va", "Vi", "Vu"],
    "Mrigashirsha": ["Ve", "Vo", "Ka", "Ki"],
    "Ardra": ["Ku", "Gha", "Na", "Cha"],
    "Punarvasu": ["Ke", "Ko", "Ha", "Hi"],
    "Pushya": ["Hu", "He", "Ho", "Da"],
    "Ashlesha": ["Di", "Du", "De", "Do"],
    "Magha": ["Ma", "Mi", "Mu", "Me"],
    "Purva Phalguni": ["Mo", "Ta", "Ti", "Tu"],
    "Uttara Phalguni": ["Te", "To", "Pa", "Pi"],
    "Hasta": ["Pu", "Sha", "Na", "Tha"],
    "Chitra": ["Pe", "Po", "Ra", "Ri"],
    "Swati": ["Ru", "Re", "Ro", "Ta"],
    "Vishakha": ["Ti", "Tu", "Te", "To"],
    "Anuradha": ["Na", "Ni", "Nu", "Ne"],
    "Jyeshtha": ["No", "Ya", "Yi", "Yu"],
    "Mula": ["Ye", "Yo", "Bha", "Bhi"],
    "Purva Ashadha": ["Bhu", "Dha", "Pha", "Dha"],
    "Uttara Ashadha": ["Bhe", "Bho", "Ja", "Ji"],
    "Shravana": ["Ju", "Je", "Jo", "Khi"],
    "Dhanishta": ["Ga", "Gi", "Gu", "Ge"],
    "Shatabhisha": ["Go", "Sa", "Si", "Su"],
    "Purva Bhadrapada": ["Se", "So", "Da", "Di"],
    "Uttara Bhadrapada": ["Du", "Tha", "Jha", "Da"],
    "Revati": ["De", "Do", "Cha", "Chi"],
}

CITIES_CSV_PATH = DRIK_PANCHANGA_PATH / "cities.csv"
_CITIES_INDEX: Dict[str, List[Dict[str, Any]]] = {}

CONTEXT_TOKEN_ALIASES = {
    "trinidad": ["port_of_spain", "port", "spain", "trinidad", "tobago"],
    "tobago": ["port_of_spain", "port", "spain", "trinidad", "tobago"],
}


def parse_date(value: str) -> datetime.date:
    """Parse supported date formats into a date object."""
    if not value:
        raise ValueError("date is required")

    formats = ("%Y-%m-%d", "%d-%m-%Y", "%d%m%Y")
    for fmt in formats:
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    raise ValueError("invalid date format. Use YYYY-MM-DD, DD-MM-YYYY, or DDMMYYYY")


def parse_datetime(value: str) -> datetime.datetime:
    """Parse supported datetime formats into a datetime object."""
    if not value:
        raise ValueError("birth_datetime is required")

    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        pass

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d%m%Y %H:%M:%S",
        "%d%m%Y %H:%M",
    )
    for fmt in formats:
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(
        "invalid birth_datetime format. Use ISO-8601, YYYY-MM-DD HH:MM[:SS], or DD-MM-YYYY HH:MM[:SS]"
    )


def _normalize_city_name(name: str) -> str:
    return " ".join(name.strip().lower().replace("-", " ").split())


def _load_cities_index():
    global _CITIES_INDEX
    if _CITIES_INDEX:
        return

    if not CITIES_CSV_PATH.exists():
        raise ValueError("cities.csv not found in drik-panchanga folder")

    index: Dict[str, List[Dict[str, Any]]] = {}
    with CITIES_CSV_PATH.open("r", encoding="utf-8") as city_file:
        reader = csv.reader(city_file, delimiter=":")
        for row in reader:
            if len(row) != 4:
                continue
            city_name, latitude, longitude, timezone_name = row
            key = _normalize_city_name(city_name)
            index.setdefault(key, []).append(
                {
                    "city": city_name,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                    "timezone_name": timezone_name,
                }
            )

    _CITIES_INDEX = index


def _timezone_offset_hours_for_datetime(
    birth_datetime: datetime.datetime, timezone_name: str
) -> float:
    tz = ZoneInfo(timezone_name)
    if birth_datetime.tzinfo is None:
        localized = birth_datetime.replace(tzinfo=tz)
    else:
        localized = birth_datetime.astimezone(tz)

    offset = localized.utcoffset()
    if offset is None:
        raise ValueError(f"could not determine UTC offset for timezone '{timezone_name}'")

    return offset.total_seconds() / 3600.0


def _resolve_city_entry(city: str, state: str = "", country: str = ""):
    _load_cities_index()
    if not city:
        raise ValueError("city is required")

    context_tokens = " ".join([state or "", country or ""]).lower().replace(",", " ").split()
    expanded_context_tokens = set(context_tokens)
    for token in list(context_tokens):
        aliases = CONTEXT_TOKEN_ALIASES.get(token, [])
        for alias in aliases:
            expanded_context_tokens.add(alias.lower())

    key = _normalize_city_name(city)
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

        sample = [
            {
                "city": entry["city"],
                "timezone_name": entry["timezone_name"],
                "latitude": entry["latitude"],
                "longitude": entry["longitude"],
            }
            for entry in partial_matches[:5]
        ]
        raise ValueError({"message": f"multiple partial matches found for city '{city}'", "matches": sample})

    if len(candidates) == 1:
        return candidates[0]

    if context_tokens:
        scored = []
        for candidate in candidates:
            haystack = f"{candidate['city']} {candidate['timezone_name']}".lower()
            score = sum(1 for token in expanded_context_tokens if token in haystack)
            scored.append((score, candidate))
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored[0][0] > 0 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
            return scored[0][1]

    sample = [
        {
            "city": entry["city"],
            "timezone_name": entry["timezone_name"],
            "latitude": entry["latitude"],
            "longitude": entry["longitude"],
        }
        for entry in candidates[:5]
    ]
    raise ValueError(
        {
            "message": f"multiple matches found for city '{city}'. add state or country to disambiguate",
            "matches": sample,
        }
    )


def _jd_from_birth_datetime_payload(payload: Dict[str, Any]):
    birth_datetime = parse_datetime(str(payload.get("birth_datetime", "")))

    if birth_datetime.tzinfo is None:
        if payload.get("timezone") is None:
            raise ValueError("timezone is required for birth_datetime without UTC offset")
        timezone = float(payload["timezone"])
        utc_datetime = birth_datetime - datetime.timedelta(hours=timezone)
    else:
        utc_datetime = birth_datetime.astimezone(datetime.timezone.utc)
        timezone = float(payload.get("timezone", 0.0))

    decimal_hour = (
        utc_datetime.hour
        + utc_datetime.minute / 60.0
        + utc_datetime.second / 3600.0
        + utc_datetime.microsecond / 3_600_000_000.0
    )
    jd = swe.julday(utc_datetime.year, utc_datetime.month, utc_datetime.day, decimal_hour)
    return jd, timezone


def _jd_from_payload(payload: Dict[str, Any]) -> float:
    if "jd" in payload and payload["jd"] is not None:
        return float(payload["jd"])

    date = parse_date(str(payload.get("date", "")))
    return panchanga.gregorian_to_jd(date)


def _place_from_payload(payload: Dict[str, Any]):
    required = ("latitude", "longitude", "timezone")
    missing = [field for field in required if payload.get(field) is None]
    if missing:
        raise ValueError(f"missing required place field(s): {', '.join(missing)}")

    return panchanga.Place(
        latitude=float(payload["latitude"]),
        longitude=float(payload["longitude"]),
        timezone=float(payload["timezone"]),
    )


def _float_list(payload: Dict[str, Any], field: str):
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return [float(v) for v in value]


def _int_field(payload: Dict[str, Any], field: str) -> int:
    if payload.get(field) is None:
        raise ValueError(f"{field} is required")
    return int(payload[field])


def calculate_panchang(date, latitude, longitude, timezone):
    jd = panchanga.gregorian_to_jd(date)
    place = panchanga.Place(latitude=latitude, longitude=longitude, timezone=timezone)

    tithi = panchanga.tithi(jd, place)
    nakshatra = panchanga.nakshatra(jd, place)
    yog = panchanga.yoga(jd, place)
    mas = panchanga.masa(jd, place)
    rtu = panchanga.ritu(mas[0])

    karan = panchanga.karana(jd, place)
    vara = panchanga.vaara(jd)
    sunrise = panchanga.sunrise(jd, place)[1]
    sunset = panchanga.sunset(jd, place)[1]
    kday = panchanga.ahargana(jd)
    kyear, sakayr = panchanga.elapsed_year(jd, mas[0])
    samvat = panchanga.samvatsara(jd, mas[0])
    day_dur = panchanga.day_duration(jd, place)[1]

    return {
        "Tithi": tithi,
        "karana": karan,
        "Nakshatra": nakshatra,
        "Yoga": yog,
        "Maasa": mas,
        "Ritu": rtu,
        "Vaara": vara,
        "Sunrise": sunrise,
        "Sunset": sunset,
        "Ahargana": kday,
        "Samvat": samvat,
        "Day Duration": day_dur,
        "Year": kyear,
        "Sakayr": sakayr,
    }


FUNCTION_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "to_dms": lambda p: panchanga.to_dms(float(p["deg"])),
    "unwrap_angles": lambda p: panchanga.unwrap_angles(_float_list(p, "angles")),
    "inverse_lagrange": lambda p: panchanga.inverse_lagrange(
        _float_list(p, "x"), _float_list(p, "y"), float(p["ya"])
    ),
    "gregorian_to_jd": lambda p: panchanga.gregorian_to_jd(parse_date(str(p["date"]))),
    "jd_to_gregorian": lambda p: panchanga.jd_to_gregorian(float(p["jd"])),
    "solar_longitude": lambda p: panchanga.solar_longitude(_jd_from_payload(p)),
    "lunar_longitude": lambda p: panchanga.lunar_longitude(_jd_from_payload(p)),
    "lunar_latitude": lambda p: panchanga.lunar_latitude(_jd_from_payload(p)),
    "sunrise": lambda p: panchanga.sunrise(_jd_from_payload(p), _place_from_payload(p)),
    "sunset": lambda p: panchanga.sunset(_jd_from_payload(p), _place_from_payload(p)),
    "moonrise": lambda p: panchanga.moonrise(_jd_from_payload(p), _place_from_payload(p)),
    "moonset": lambda p: panchanga.moonset(_jd_from_payload(p), _place_from_payload(p)),
    "tithi": lambda p: panchanga.tithi(_jd_from_payload(p), _place_from_payload(p)),
    "nakshatra": lambda p: panchanga.nakshatra(_jd_from_payload(p), _place_from_payload(p)),
    "yoga": lambda p: panchanga.yoga(_jd_from_payload(p), _place_from_payload(p)),
    "karana": lambda p: panchanga.karana(_jd_from_payload(p), _place_from_payload(p)),
    "vaara": lambda p: panchanga.vaara(_jd_from_payload(p)),
    "masa": lambda p: panchanga.masa(_jd_from_payload(p), _place_from_payload(p)),
    "ahargana": lambda p: panchanga.ahargana(_jd_from_payload(p)),
    "elapsed_year": lambda p: panchanga.elapsed_year(_jd_from_payload(p), _int_field(p, "maasa_num")),
    "new_moon": lambda p: panchanga.new_moon(
        _jd_from_payload(p), _int_field(p, "tithi"), int(p.get("opt", -1))
    ),
    "raasi": lambda p: panchanga.raasi(_jd_from_payload(p)),
    "lunar_phase": lambda p: panchanga.lunar_phase(_jd_from_payload(p)),
    "samvatsara": lambda p: panchanga.samvatsara(_jd_from_payload(p), _int_field(p, "maasa_num")),
    "ritu": lambda p: panchanga.ritu(_int_field(p, "masa_num")),
    "day_duration": lambda p: panchanga.day_duration(_jd_from_payload(p), _place_from_payload(p)),
}


FUNCTION_INPUTS = {
    "to_dms": ["deg"],
    "unwrap_angles": ["angles"],
    "inverse_lagrange": ["x", "y", "ya"],
    "gregorian_to_jd": ["date"],
    "jd_to_gregorian": ["jd"],
    "solar_longitude": ["jd or date"],
    "lunar_longitude": ["jd or date"],
    "lunar_latitude": ["jd or date"],
    "sunrise": ["jd or date", "latitude", "longitude", "timezone"],
    "sunset": ["jd or date", "latitude", "longitude", "timezone"],
    "moonrise": ["jd or date", "latitude", "longitude", "timezone"],
    "moonset": ["jd or date", "latitude", "longitude", "timezone"],
    "tithi": ["jd or date", "latitude", "longitude", "timezone"],
    "nakshatra": ["jd or date", "latitude", "longitude", "timezone"],
    "yoga": ["jd or date", "latitude", "longitude", "timezone"],
    "karana": ["jd or date", "latitude", "longitude", "timezone"],
    "vaara": ["jd or date"],
    "masa": ["jd or date", "latitude", "longitude", "timezone"],
    "ahargana": ["jd or date"],
    "elapsed_year": ["jd or date", "maasa_num"],
    "new_moon": ["jd or date", "tithi", "opt(optional, default -1)"],
    "raasi": ["jd or date"],
    "lunar_phase": ["jd or date"],
    "samvatsara": ["jd or date", "maasa_num"],
    "ritu": ["masa_num"],
    "day_duration": ["jd or date", "latitude", "longitude", "timezone"],
}


def call_drik_function(function_name: str, payload: Dict[str, Any]):
    function_name = function_name.strip()
    if function_name not in FUNCTION_HANDLERS:
        raise KeyError(f"unsupported function '{function_name}'")
    return FUNCTION_HANDLERS[function_name](payload)


def list_drik_functions():
    return [
        {"name": name, "inputs": FUNCTION_INPUTS.get(name, [])}
        for name in sorted(FUNCTION_HANDLERS.keys())
    ]


def get_name_letters(payload: Dict[str, Any]):
    jd, timezone = _jd_from_birth_datetime_payload(payload)

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    location_used = latitude is not None and longitude is not None

    if location_used:
        lat = float(latitude)
        lon = float(longitude)
        swe.set_topo(lon, lat, 0.0)
        moon_longitude = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_TOPOCTR)[0][0]
    else:
        moon_longitude = panchanga.lunar_longitude(jd)

    moon_nirayana = (moon_longitude - swe.get_ayanamsa_ut(jd)) % 360
    nakshatra_span = 360.0 / 27.0
    pada_span = 360.0 / 108.0

    nakshatra_index = int(moon_nirayana / nakshatra_span)
    if nakshatra_index > 26:
        nakshatra_index = 26
    nakshatra_number = nakshatra_index + 1
    nakshatra_name = NAKSHATRA_NAMES[nakshatra_index]

    pada = int(moon_nirayana / pada_span) % 4 + 1
    syllables = NAKSHATRA_PADA_SYLLABLES[nakshatra_name]
    recommended_syllable = syllables[pada - 1]

    return {
        "birth_datetime": payload.get("birth_datetime"),
        "timezone": timezone,
        "location_used": location_used,
        "latitude": float(latitude) if latitude is not None else None,
        "longitude": float(longitude) if longitude is not None else None,
        "julian_day_ut": jd,
        "moon_nirayana_longitude": moon_nirayana,
        "nakshatra_number": nakshatra_number,
        "nakshatra_name": nakshatra_name,
        "pada": pada,
        "recommended_syllable": recommended_syllable,
        "syllables_for_nakshatra": syllables,
        "note": "Naming syllables can vary by regional/language tradition.",
    }


def get_name_letters_by_city(payload: Dict[str, Any]):
    city_input = str(payload.get("city", "")).strip()
    state = str(payload.get("state", "")).strip()
    country = str(payload.get("country", "")).strip()

    if not city_input:
        raise ValueError("city is required")

    if "," in city_input:
        parts = [part.strip() for part in city_input.split(",") if part.strip()]
        if parts:
            city_input = parts[0]
        if len(parts) >= 2 and not state:
            state = parts[1]
        if len(parts) >= 3 and not country:
            country = parts[2]

    city_entry = _resolve_city_entry(city_input, state=state, country=country)
    birth_datetime = parse_datetime(str(payload.get("birth_datetime", "")))
    timezone_hours = _timezone_offset_hours_for_datetime(
        birth_datetime, city_entry["timezone_name"]
    )

    derived_payload = dict(payload)
    derived_payload["timezone"] = timezone_hours
    derived_payload["latitude"] = city_entry["latitude"]
    derived_payload["longitude"] = city_entry["longitude"]

    result = get_name_letters(derived_payload)
    result["resolved_city"] = city_entry["city"]
    result["resolved_timezone_name"] = city_entry["timezone_name"]
    result["input_city"] = payload.get("city")
    result["input_state"] = payload.get("state")
    result["input_country"] = payload.get("country")
    return result
