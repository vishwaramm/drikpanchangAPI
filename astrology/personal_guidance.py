"""Structured personal Panchang guidance built from the real astrology engines."""

from __future__ import annotations

import datetime as _dt
from typing import Any

import legacy_panchanga

from .locations import resolve_city, timezone_offset_hours_for_datetime
from .utils import parse_birth_datetime, parse_fixed_or_iana_timezone

CTA_EMAIL = "info@thehindusociety.com"

_WEEKDAY_NAMES = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]

_TITHI_NAMES = [
    "Pratipada",
    "Dvitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dvadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima",
    "Pratipada",
    "Dvitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dvadashi",
    "Trayodashi",
    "Chaturdashi",
    "Amavasya",
]

_NAKSHATRA_NAMES = [
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
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

_YOGA_NAMES = [
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shoola",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]

_KARANA_NAMES = [
    "Kimstughna",
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Garaja",
    "Vanija",
    "Vishti",
    "Shakuni",
    "Chatushpada",
    "Naga",
]

_MAASA_NAMES = [
    "Chaitra",
    "Vaishakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashwin",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguna",
]

_RITU_NAMES = ["Vasanta", "Grishma", "Varsha", "Sharad", "Hemanta", "Shishira"]


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("-", " ").split())


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _format_location(city: str | None, country: str | None) -> str:
    parts = [part for part in [city, country] if part]
    return ", ".join(parts) if parts else "Unavailable"


def _date_label(value: str | None) -> str:
    if not value:
        return "Birth date not entered"
    try:
        return _dt.date.fromisoformat(value).strftime("%B %d, %Y")
    except ValueError:
        return value


def _time_label(value: str | None, approximate: bool) -> str:
    if approximate:
        return "Approximate birth time"
    return value or "Birth time not entered"


def _weekday_rating(snapshot: dict[str, Any]) -> dict[str, Any]:
    score = snapshot.get("score", {})
    normalized = float(score.get("normalized", 0.0) or 0.0)
    if normalized >= 0.75:
        return {
            "label": "Good",
            "status": "good",
            "explanation": "The actual Panchang score is strong enough to treat the day as generally favorable.",
        }
    if normalized >= 0.55:
        return {
            "label": "Mixed",
            "status": "neutral",
            "explanation": "The actual Panchang score is balanced, so timing matters more than the whole day.",
        }
    return {
        "label": "Avoid major work",
        "status": "avoid",
        "explanation": "The actual Panchang score is weaker, so major starts should be moved into a better window.",
    }


def _window_items(windows: list[dict[str, Any]], default_label: str) -> str:
    if not windows:
        return default_label
    return " · ".join(
        f"{window['label']} {window['period']['start']} - {window['period']['end']}"
        for window in windows
    )


def _build_item(label: str, value: str, status: str, explanation: str) -> dict[str, str]:
    return {
        "label": label,
        "value": value,
        "status": status,
        "explanation": explanation,
    }


def _build_section(
    section_id: str,
    title: str,
    short_description: str,
    importance: str,
    items: list[dict[str, str]],
    notes: list[str] | None = None,
    cta: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "id": section_id,
        "title": title,
        "shortDescription": short_description,
        "importance": importance,
        "items": items,
        "notes": notes or [],
        "disclaimer": [
            "Spiritual and cultural guidance only.",
            "Not financial advice.",
            "Not legal advice.",
            "Not medical advice.",
            "Accuracy depends on birth details.",
            "Traditions may vary.",
        ],
        **({"cta": cta} if cta else {}),
    }


def _resolve_location_payload(city: str | None, state: str | None, country: str | None) -> dict[str, Any] | None:
    if not city:
        return None
    return resolve_city(city, state=state or "", country=country or "")


def _current_location_payload(payload: dict[str, Any], panchang_input: dict[str, Any]) -> dict[str, Any]:
    current_city = payload.get("current_city") or payload.get("city") or panchang_input.get("city")
    current_country = payload.get("current_country") or payload.get("country") or panchang_input.get("country")
    current_state = payload.get("current_state") or payload.get("state") or panchang_input.get("state")
    current_timezone_name = payload.get("current_timezone_name") or panchang_input.get("timezone_name")
    city_match = _resolve_location_payload(current_city, current_state, current_country)

    if city_match:
        return city_match

    if current_timezone_name:
        return {
            "city": current_city,
            "country": current_country,
            "timezone_name": current_timezone_name,
            "latitude": panchang_input.get("latitude"),
            "longitude": panchang_input.get("longitude"),
        }

    return {
        "city": current_city,
        "country": current_country,
        "timezone_name": None,
        "latitude": panchang_input.get("latitude"),
        "longitude": panchang_input.get("longitude"),
    }


def _birth_location_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    birth_city = payload.get("birth_city")
    birth_country = payload.get("birth_country")
    birth_state = payload.get("birth_state")
    return _resolve_location_payload(birth_city, birth_state, birth_country)


def _normalize_timezone_value(value: Any) -> tuple[float | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        return float(value), None

    text = str(value).strip()
    if not text:
        return None, None
    try:
        return float(text), None
    except ValueError:
        return None, text


def _core_name(index: Any, names: list[str]) -> str:
    if isinstance(index, list) and index:
        index = index[0]
    if index is None:
        return "Unavailable"
    try:
        resolved = int(index) - 1
    except (TypeError, ValueError):
        return str(index)
    if 0 <= resolved < len(names):
        return names[resolved]
    return f"#{index}"


def _format_clock_value(value: Any) -> str:
    if isinstance(value, list) and len(value) >= 3:
        return ":".join(f"{int(part):02d}" for part in value[:3])
    return str(value) if value is not None else "Unavailable"


def _format_location(city: str | None, country: str | None) -> str:
    parts = [part for part in [city, country] if part]
    return ", ".join(parts) if parts else "Unavailable"


def _build_day_windows(sunrise: Any, sunset: Any, weekday_index: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sunrise_parts = sunrise if isinstance(sunrise, list) else None
    sunset_parts = sunset if isinstance(sunset, list) else None
    if not sunrise_parts or not sunset_parts or len(sunrise_parts) < 3 or len(sunset_parts) < 3:
        return [], []

    sunrise_seconds = int(sunrise_parts[0]) * 3600 + int(sunrise_parts[1]) * 60 + int(sunrise_parts[2])
    sunset_seconds = int(sunset_parts[0]) * 3600 + int(sunset_parts[1]) * 60 + int(sunset_parts[2])
    if sunset_seconds <= sunrise_seconds:
        return [], []

    day_span = sunset_seconds - sunrise_seconds
    eighth = day_span / 8
    midday = sunrise_seconds + day_span / 2
    rahu_segments = [1, 6, 4, 5, 3, 2, 7]
    yamaganda_segments = [4, 3, 2, 1, 0, 6, 5]
    gulika_segments = [6, 5, 4, 3, 2, 1, 0]
    weekday_index = max(0, min(6, weekday_index))

    def build_period(start_seconds: float, end_seconds: float) -> dict[str, str]:
        def fmt(seconds: float) -> str:
            safe = ((round(seconds) % 86_400) + 86_400) % 86_400
            hour = int(safe // 3600)
            minute = int((safe % 3600) // 60)
            return f"{hour:02d}:{minute:02d}"

        return {"start": fmt(start_seconds), "end": fmt(end_seconds)}

    favorable = [
        {
            "label": "Brahma Muhurta",
            "period": build_period(sunrise_seconds - 96 * 60, sunrise_seconds - 48 * 60),
            "note": "Best kept for prayer, mantra, quiet study, and inward work before the day gathers speed.",
            "tone": "favorable",
        },
        {
            "label": "Abhijit Muhurta",
            "period": build_period(midday - 24 * 60, midday + 24 * 60),
            "note": "A strong central window for important starts, offerings, focused decisions, and dignified action.",
            "tone": "favorable",
        },
    ]

    caution = [
        {
            "label": "Rahu Kalam",
            "period": build_period(
                sunrise_seconds + eighth * rahu_segments[weekday_index],
                sunrise_seconds + eighth * (rahu_segments[weekday_index] + 1),
            ),
            "note": "Traditionally avoided for new beginnings, major purchases, travel starts, and first-time commitments.",
            "tone": "caution",
        },
        {
            "label": "Yamaganda",
            "period": build_period(
                sunrise_seconds + eighth * yamaganda_segments[weekday_index],
                sunrise_seconds + eighth * (yamaganda_segments[weekday_index] + 1),
            ),
            "note": "Usually treated as a softer caution period, especially for setting out or beginning something significant.",
            "tone": "caution",
        },
        {
            "label": "Gulika Kalam",
            "period": build_period(
                sunrise_seconds + eighth * gulika_segments[weekday_index],
                sunrise_seconds + eighth * (gulika_segments[weekday_index] + 1),
            ),
            "note": "Useful for routine, repetition, and steady work, but many households avoid it for ceremonial first steps.",
            "tone": "caution",
        },
    ]

    return favorable, caution


def _build_recommendations(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    tithi_name = str(snapshot.get("tithi", {}).get("current", "")).lower()
    yoga_name = str(snapshot.get("yoga", {}).get("current", "")).lower()
    karana_name = str(snapshot.get("karana", {}).get("current", "")).lower()
    weekday = str(snapshot.get("weekday", "Unavailable"))

    favorable = [
        f"Morning prayer, mantra, and altar work pair well with {weekday}.",
        f"Focused study, paperwork, and practical planning are supported while {snapshot.get('karana', {}).get('current', 'the current karana')} is active.",
        f"{snapshot.get('nakshatra', {}).get('current', 'The current nakshatra')} can be used as a tone-setter for the day, especially if you want a more intentional rhythm.",
    ]

    caution = [
        "Avoid treating this page as a substitute for formal muhurta selection for marriage, surgery, contracts, or house entry.",
        "Try not to begin major new commitments during Rahu Kalam or Yamaganda unless family custom says otherwise.",
    ]

    observance = [inferFastingRelevance(snapshot)]

    if "ekadashi" in tithi_name:
        favorable.append("Keep the day lighter and more sattvic if you observe Ekadashi through japa, vrata, or simpler meals.")
    if "amavasya" in tithi_name:
        favorable.append("Amavasya often favors quieter worship, remembrance, and pitri-oriented prayer over outward celebration.")
    if "purnima" in tithi_name:
        favorable.append("Purnima supports fuller worship, stotra recitation, and devotional gathering when practical.")
    if "chaturthi" in tithi_name:
        favorable.append("Chaturthi is a natural day for Ganesha prayer, obstacle-clearing sankalpas, and tidy beginnings.")

    if any(term in yoga_name for term in ["siddha", "shubha", "brahma"]):
        favorable.append(f"{snapshot.get('yoga', {}).get('current', 'The current yoga')} is traditionally read as supportive for clear effort, study, and constructive work.")
    if any(term in yoga_name for term in ["vyatipata", "vaidhriti", "vishkambha"]):
        caution.append(f"{snapshot.get('yoga', {}).get('current', 'The current yoga')} is often handled more carefully, so keep major starts measured and deliberate.")

    if "vishti" in karana_name:
        caution.append("Vishti Karana is usually treated cautiously for auspicious beginnings and formal starts.")

    return [
        {"title": "Good For", "items": favorable[:4]},
        {"title": "Use Caution For", "items": caution[:4]},
        {"title": "Observance Note", "items": observance},
    ]


def _summarize_panchang_result(
    raw_result: dict[str, Any],
    *,
    date_label: str,
    location_label: str,
    city: str | None,
    country: str | None,
    timezone_name: str | None,
) -> dict[str, Any]:
    panchang = raw_result.get("panchang", {}) if isinstance(raw_result, dict) else {}
    vaara_names = _WEEKDAY_NAMES
    tithi = _core_name(panchang.get("Tithi"), _TITHI_NAMES)
    nakshatra = _core_name(panchang.get("Nakshatra"), _NAKSHATRA_NAMES)
    yoga = _core_name(panchang.get("Yoga"), _YOGA_NAMES)
    karana = _core_name(panchang.get("karana"), _KARANA_NAMES)
    weekday_index = int(panchang.get("Vaara") or 0)
    weekday = vaara_names[weekday_index] if 0 <= weekday_index < len(vaara_names) else "Unavailable"
    sunrise = panchang.get("Sunrise")
    sunset = panchang.get("Sunset")
    day_duration = panchang.get("day_duration") or panchang.get("Day Duration")
    favorable_windows, caution_windows = _build_day_windows(sunrise, sunset, weekday_index)
    maasa_value = panchang.get("Maasa")
    if isinstance(maasa_value, list) and maasa_value:
        try:
            maasa_name = _MAASA_NAMES[int(maasa_value[0]) - 1]
        except (TypeError, ValueError, IndexError):
            maasa_name = "Unavailable"
    else:
        maasa_name = "Unavailable"
    ritu_value = panchang.get("Ritu")
    if isinstance(ritu_value, list) and ritu_value:
        ritu_value = ritu_value[0]
    try:
        ritu_name = _RITU_NAMES[int(ritu_value)] if isinstance(ritu_value, int) and 0 <= int(ritu_value) < len(_RITU_NAMES) else "Unavailable"
    except (TypeError, ValueError):
        ritu_name = "Unavailable"
    snapshot = {
        "dateLabel": date_label,
        "locationLabel": location_label,
        "weekday": weekday,
        "weekdayDetail": f"Sun-based daily timing for {city or location_label}",
        "sunrise": _format_clock_value(sunrise),
        "sunset": _format_clock_value(sunset),
        "tithi": {"current": tithi},
        "nakshatra": {"current": nakshatra},
        "yoga": {"current": yoga},
        "karana": {"current": karana},
        "maasa": maasa_name,
        "ritu": ritu_name,
        "dayDuration": _format_clock_value(day_duration),
        "notes": f"Daily Panchang for {location_label}, arranged for quick household reading.",
        "favorableWindows": favorable_windows,
        "cautionWindows": caution_windows,
        "recommendations": _build_recommendations(
            {
                "weekday": weekday,
                "tithi": {"current": tithi},
                "nakshatra": {"current": nakshatra},
                "yoga": {"current": yoga},
                "karana": {"current": karana},
            }
        ),
        "sourceLabel": "drikpanchangAPI",
        "sourceUrl": "http://127.0.0.1:5000/health",
    }
    return {
        "input": {
            "date": raw_result.get("input", {}).get("date"),
            "latitude": raw_result.get("input", {}).get("latitude"),
            "longitude": raw_result.get("input", {}).get("longitude"),
            "timezone": raw_result.get("input", {}).get("timezone"),
            "timezone_name": timezone_name or raw_result.get("input", {}).get("timezone_name"),
            "city": city,
            "country": country,
        },
        "panchang": snapshot,
    }


def summarize_panchang_result(
    raw_result: dict[str, Any],
    *,
    date_label: str,
    location_label: str,
    city: str | None,
    country: str | None,
    timezone_name: str | None,
) -> dict[str, Any]:
    return _summarize_panchang_result(
        raw_result,
        date_label=date_label,
        location_label=location_label,
        city=city,
        country=country,
        timezone_name=timezone_name,
    )


def build_personal_guidance(
    *,
    payload: dict[str, Any],
    panchang_today: dict[str, Any],
    panchang_tomorrow: dict[str, Any] | None,
    birth_chart: dict[str, Any],
    dasha: dict[str, Any],
    interpretation: dict[str, Any],
    transit_today: dict[str, Any],
    transit_forecast: list[dict[str, Any]],
    muhurta_general: dict[str, Any],
    muhurta_career: dict[str, Any],
    muhurta_travel: dict[str, Any],
    muhurta_marriage: dict[str, Any],
    muhurta_finance: dict[str, Any],
    name_letters: dict[str, Any],
    compatibility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    birth_time_unknown = _coerce_bool(payload.get("birth_time_unknown"))
    birth_location = _birth_location_payload(payload)
    current_location = _current_location_payload(payload, panchang_today.get("input", {}))
    birth_datetime = payload.get("birth_datetime")
    if not birth_datetime:
        birth_date = payload.get("birth_date")
        birth_time = payload.get("birth_time")
        if birth_date and birth_time and not birth_time_unknown:
            birth_datetime = f"{birth_date}T{str(birth_time)}"
        elif birth_date:
            birth_datetime = f"{birth_date}T12:00:00"
    name_letters_list = name_letters.get("syllables_for_nakshatra", []) or []

    moon = birth_chart.get("planets", {}).get("Moon", {})
    ascendant = birth_chart.get("ascendant") or {}
    current_period = dasha.get("current_period", {})
    transit_events = transit_today.get("events", [])
    transit_themes = transit_today.get("summaries", [])
    transits_forecast = transit_forecast[:3]
    interpretation_matches = interpretation.get("matches", [])
    interpretation_themes = interpretation.get("themes", {})
    panchang_today_snapshot = panchang_today.get("panchang", {})
    panchang_tomorrow_snapshot = panchang_tomorrow.get("panchang", {}) if panchang_tomorrow else None

    janma_nakshatra = moon.get("nakshatra") or name_letters.get("nakshatra_name") or "Unavailable"
    janma_rashi = moon.get("sign") or "Unavailable"
    lagna = ascendant.get("sign")
    if lagna:
        lagna = f"{lagna} Lagna"
    else:
        lagna = "Approximate only until exact birth time is known"

    summary = {
        "fullName": payload.get("full_name") or "Unnamed",
        "birthDetails": f"{_date_label(payload.get('birth_date') or (birth_datetime or '')[:10])} · {_time_label(str(payload.get('birth_time') or '') or None, birth_time_unknown)} · {_format_location(birth_location.get('city') if birth_location else payload.get('birth_city'), birth_location.get('country') if birth_location else payload.get('birth_country'))}",
        "currentLocation": _format_location(current_location.get("city"), current_location.get("country")),
        "todaySnapshot": f"{panchang_today.get('input', {}).get('date')} · {panchang_today_snapshot.get('weekday', 'Unavailable')} · {panchang_today_snapshot.get('tithi', {}).get('current', 'Unavailable')} · {panchang_today_snapshot.get('nakshatra', {}).get('current', 'Unavailable')}",
        "janmaNakshatra": janma_nakshatra,
        "janmaRashi": janma_rashi,
        "lagna": lagna,
        "nameLetters": ", ".join(name_letters_list),
        "note": "These results are for spiritual and cultural guidance. For major life decisions, consult a qualified pandit.",
    }

    daily_rating = _weekday_rating(muhurta_general)
    recommendations = panchang_today_snapshot.get("recommendations", [])
    favorable_windows = panchang_today_snapshot.get("favorableWindows", [])
    caution_windows = panchang_today_snapshot.get("cautionWindows", [])

    marriage_note = "No partner birth details were provided, so compatibility cannot be finalized here."
    marriage_status = "needs_review"
    if compatibility:
        compatibility_grade = compatibility.get("compatibility", {}).get("grade", "Unavailable")
        marriage_note = f"Compatibility grade: {compatibility_grade}."
        marriage_status = "good" if compatibility_grade in {"excellent", "very_good"} else "needs_review"

    dosha_matches = [match for match in interpretation_matches if "dosha" in str(match.get("title", "")).lower() or "mangal" in str(match.get("title", "")).lower()]
    if not dosha_matches:
        dosha_matches = interpretation_matches[:4]

    transit_phase = "Supportive"
    if current_period:
        lord = str(current_period.get("lord", "")).lower()
        if lord in {"saturn", "rahu", "ketu"}:
            transit_phase = "Needs caution"
        elif lord in {"jupiter", "venus", "moon"}:
            transit_phase = "Supportive"
        else:
            transit_phase = "Mixed"

    coming_events = []
    for event in transit_events[:3]:
        coming_events.append(f"{event.get('planet')} {event.get('event_type')} around {event.get('approx_time')}")
    if not coming_events:
        coming_events.append("No major transit event was detected in the current daily scan.")

    eclipse_note = "No dedicated eclipse calendar is loaded in this build. Use the transit and panchang scans as the current special-event reference."
    if any("Rahu" in str(event.get("planet")) or "Ketu" in str(event.get("planet")) for event in transit_events):
        eclipse_note = "Special node-related transit activity is present in the scan, so a priest check is prudent for sensitive rituals."

    sections = [
        _build_section(
            "what-should-i-do-today",
            "What should I do today?",
            "A plain-English read on today, with the strongest actions and clearest cautions first.",
            "high",
            [
                _build_item("What this means", f"Today in {panchang_today.get('input', {}).get('city') or current_location.get('city') or 'your location'} is a {daily_rating['label'].lower()} day for ordinary duties and respectful beginnings.", daily_rating["status"], daily_rating["explanation"]),
                _build_item("Why people ask this", "People ask this when they want one simple answer before work, puja, travel, or a family decision.", "neutral", "It reduces the need to read every Panchang term before starting the day."),
                _build_item("What you should do next", "Use the best window, keep the first step respectful, and move the important task into a calmer timing band.", daily_rating["status"], "The next step should be simple enough to act on without more decoding."),
                _build_item("Top 3 things to do", " · ".join(item for item in (recommendations[0].get("items", []) if recommendations else [])[:3]) or "Use the calmest morning window and begin with prayer or a short reset.", "good", "These are the safest actions to lean into when you want the day to feel steady and useful."),
                _build_item("Top 3 things to avoid", " · ".join(item for item in (recommendations[1].get("items", []) if len(recommendations) > 1 else [])[:3]) or "Avoid major starts during Rahu Kalam, Yamaganda, or other caution windows.", "avoid", "These are the kinds of starts most families postpone when they want less resistance."),
                _build_item("Best timings", _window_items(favorable_windows, "Morning calm window"), "good", "These are the windows people usually try to protect for prayer, decisions, and first steps."),
                _build_item("Worst timings", _window_items(caution_windows, "Caution windows"), "avoid", "These are the windows most commonly treated as cautionary for new beginnings."),
                _build_item("Simple advice", f"Today is generally favorable for routine work and devotional activity, but avoid treating the entire day as equally strong.", daily_rating["status"], "This helps beginners leave with one plain sentence they can remember."),
            ],
            ["The summary uses the actual Panchang score and day windows returned by the API."],
        ),
        _build_section(
            "is-today-good-or-bad-for-important-work",
            "Is today good or bad for important work?",
            "A practical screen for launches, forms, calls, purchases, and other decisions that need the day to feel clean.",
            "high",
            [
                _build_item("What this means", f"The current Panchang tone is {daily_rating['label'].lower()}, so important work should follow the strongest time window rather than the whole day.", daily_rating["status"], "This is the everyday question behind appointments, paperwork, and first steps."),
                _build_item("Why people ask this", "People ask this when they want to know whether a task should go ahead now or be delayed to a cleaner hour.", "neutral", "It is the fastest way to separate an ordinary day from a day that deserves extra care."),
                _build_item("What you should do next", "Proceed in the best window, keep the first action small, and avoid unnecessary rush.", daily_rating["status"], "The next step should be practical, not abstract."),
                _build_item("Best for", "Routine work, planning, prayer, and respectful starts in a supportive time band.", "good", "These are the things that usually go more smoothly on the current day."),
                _build_item("Use caution for", "Big commitments, large purchases, and public starts during caution windows.", "avoid", "These are the tasks most families would rather move into a better window."),
                _build_item("Beginner note", "If the task is important enough to worry about, the exact time slot matters more than a yes/no answer about the whole day.", "neutral", "This is why pandits often look at the clock after looking at the day."),
            ],
            ["The backend uses the actual Panchang score and muhurta windows for this summary."],
        ),
        _build_section(
            "what-are-my-birth-details-and-name-letters",
            "What are my birth details and name letters?",
            "A beginner-friendly snapshot of birth data, chart tone, and rough naming letters.",
            "high",
            [
                _build_item("What this means", f"Your birth profile is being read from {summary['birthDetails']}.", "neutral", "This is the entry point for Janma Nakshatra, Janma Rashi, and lagna-based reading."),
                _build_item("Why people ask this", "People ask this when they want a chart summary they can share with family, priest, or marriage matchmaker.", "neutral", "It turns the raw birth data into something readable."),
                _build_item("What you should do next", "Use these details as a starting point, then confirm them in a full chart if the decision is important.", "good" if not birth_time_unknown else "needs_review", "This keeps beginners from assuming the summary is exact when the birth time is incomplete."),
                _build_item("Janma Nakshatra", janma_nakshatra, "good" if not birth_time_unknown else "needs_review", "The birth star is one of the main anchors used in traditional matching and naming guidance."),
                _build_item("Janma Rashi", janma_rashi, "good" if not birth_time_unknown else "needs_review", "The moon sign is part of the emotional and timing read in many traditions."),
                _build_item("Lagna", lagna, "good" if not birth_time_unknown else "unknown", "The ascendant becomes approximate when the birth time is uncertain."),
                _build_item("Suggested name letters", ", ".join(name_letters.get("syllables_for_nakshatra", []) or []) or "Unavailable", "good" if not birth_time_unknown else "needs_review", "These are rough starting syllables only until a full naming calculation is confirmed."),
            ],
            [
                f"Birth-time confidence: {'Approximate' if birth_time_unknown else 'Higher confidence'}.",
                "The backend uses the real birth chart and the legacy naming syllable calculator.",
            ],
        ),
        _build_section(
            "when-should-i-get-married-check-compatibility",
            "When should I get married / check compatibility?",
            "A screening tab for marriage timing, family matching, and when a priest should be involved.",
            "high",
            [
                _build_item("What this means", "Marriage screening can be read more carefully when the birth chart is available. Full compatibility still needs the partner's chart.", "needs_review", "Marriage is one of the places where precise chart work usually matters most."),
                _build_item("Why people ask this", "People ask this when they need to know whether the match is worth deeper review before setting a date.", "neutral", "It is the natural question before engagement, matching, or wedding planning."),
                _build_item("What you should do next", "Book a consultation if this is a real wedding decision, because compatibility needs a proper chart and family-tradition check.", "needs_review", "A quick panchang screen is helpful, but it does not replace a full marriage reading."),
                _build_item("Quick marriage fit", marriage_note, marriage_status, "This protects families from treating a quick screen like a complete verdict."),
                _build_item("What to compare", "Janma Nakshatra, Rashi, Lagna, family tradition, and the proposed wedding muhurta.", "neutral", "These are the main items most pandits compare first."),
                _build_item("Best next step", "Ask a pandit before setting a final ceremony date or sending formal invitations.", "good", "This avoids rework when a better wedding window appears later."),
            ],
            ["The compatibility engine is used when a partner chart is supplied; otherwise the tab stays on the natal-chart screen."],
            {
                "label": "Book Consultation",
                "href": f"mailto:{CTA_EMAIL}?subject=Marriage%20%2F%20compatibility%20consultation",
                "note": "For marriage timing and compatibility, a full pandit review is the right next step.",
            },
        ),
        _build_section(
            "when-is-the-best-time-to-buy-or-start-something",
            "When is the best time to buy or start something?",
            "A simple starter guide for purchases, launches, signatures, and first steps.",
            "medium",
            [
                _build_item("What this means", "A good start is usually chosen from a supportive time window rather than from the calendar day alone.", "neutral", "This is the basic muhurta idea behind many practical decisions."),
                _build_item("Why people ask this", "People ask this before buying something expensive, signing a form, opening a business, or beginning a project.", "neutral", "The first start is often treated as the tone-setter for the rest of the effort."),
                _build_item("What you should do next", "Use the best timing band, avoid Rahu Kalam, and keep the first step short and clean.", "good", "This is usually enough for ordinary work that does not need a full ceremony."),
                _build_item("Best start windows", _window_items(favorable_windows, "Morning window"), "good", "These are the windows to check first for launches and fresh starts."),
                _build_item("Avoid for first steps", _window_items(caution_windows, "Caution windows"), "avoid", "These are the slots most people skip when they want a cleaner start."),
                _build_item("Buying note", "Ordinary purchases are usually fine, but major contracts and large commitments deserve a stronger check.", "neutral", "The bigger the commitment, the more useful the timing review becomes."),
            ],
            ["The backend uses the same day windows the panchang engine returned, not a hardcoded checklist."],
        ),
        _build_section(
            "when-should-i-do-griha-pravesh-or-property-work",
            "When should I do griha pravesh or property work?",
            "A home-and-property timing screen for entry, purchase, paperwork, and moving decisions.",
            "high",
            [
                _build_item("What this means", "Home entry and property actions are often treated more carefully than ordinary errands because they set household direction.", "neutral", "Many families want the first step into a home to feel clean and settled."),
                _build_item("Why people ask this", "People ask this before moving, signing a property document, or fixing the griha pravesh day.", "neutral", "These are the moments when timing feels especially important."),
                _build_item("What you should do next", "Check the strongest day band first, then have a priest review the house-entry specific details.", "needs_review", "House-related rituals usually need both panchang and event-specific review."),
                _build_item("Household fit", "The current day should be paired with the exact moving or entry hour before deciding.", "needs_review", "A good day can still be spoiled by a weak hour slot."),
                _build_item("Property paperwork", "Paperwork and property checks are often easier than the first entry itself, but the best window still matters.", "neutral", "This lets you separate legal admin from ceremonial entry."),
                _build_item("Beginner rule", "Treat house entry as a special start, not as an ordinary appointment.", "good", "That mindset usually leads to better timing choices."),
            ],
            ["This tab uses the general muhurta windows and house-entry caution until a house-specific calculator is added."],
        ),
        _build_section(
            "do-i-have-any-doshas-or-problems-in-my-chart",
            "Do I have any doshas or problems in my chart?",
            "A caution screen for common chart concerns without pretending to be a full diagnosis.",
            "high",
            [
                _build_item("What this means", "Some chart concerns can be screened from the actual birth chart, but a complete dosha reading still needs a real chart review.", "needs_review", "Dosha language is easy to oversell, so this screen stays cautious on purpose."),
                _build_item("Why people ask this", "People ask this when they worry about marriage, health of routines, delays, or repeated obstacles.", "neutral", "This is one of the most common reasons people seek a pandit consultation."),
                _build_item("What you should do next", "Book an Ask a Pandit review if this is a serious concern, especially when a marriage or family decision is involved.", "needs_review", "A quick guess is not enough for a real chart concern."),
                _build_item("Overall dosha screen", dosha_matches[0].get("title") if dosha_matches else "No major dosha rule surfaced in the current interpretation.", "needs_review" if dosha_matches else "unknown", "This is the easiest way to surface actual rule matches without flattening the chart."),
                _build_item("Common areas to review", ", ".join(sorted({str(match.get("title", "")) for match in dosha_matches})) or "Mangal dosha, Saturn pressure, Rahu-Ketu stress, and repeated caution themes.", "needs_review", "These are the usual topics a priest or astrologer would look at first."),
                _build_item("What not to do", "Do not treat this screen as a medical, legal, or life-determining diagnosis.", "avoid", "This keeps the guidance in its proper spiritual and cultural lane."),
            ],
            ["This tab is driven by the current interpretation matches and compatibility scan so it stays grounded in the supplied chart data."],
            {
                "label": "Ask a Pandit",
                "href": f"mailto:{CTA_EMAIL}?subject=Dosha%20review%20request",
                "note": "Dosha questions need a deeper chart review than a quick panchang screen can provide.",
            },
        ),
        _build_section(
            "what-is-my-current-planetary-situation",
            "What is my current planetary situation (good/bad phase)?",
            "A simple phase read for people who want to know whether the current period feels easier or heavier.",
            "medium",
            [
                _build_item("What this means", f"The current dasha is {current_period.get('lord', 'Unavailable')} and the transit scan is {transit_phase.lower()}.", "good" if transit_phase == "Supportive" else "needs_review" if transit_phase == "Needs caution" else "neutral", "This gives a plain-language tone for the present phase without pretending to read the entire chart."),
                _build_item("Why people ask this", "People ask this when they want to know whether life feels open, delayed, or mixed right now.", "neutral", "It is the shorthand way to ask about the current planetary weather."),
                _build_item("What you should do next", "Use the supportive time windows for productive work and let heavier tasks wait for a cleaner period.", "good", "That is usually the safest way to handle a mixed phase."),
                _build_item("Current period", f"{current_period.get('lord', 'Unavailable')} · {current_period.get('level_name', 'Unavailable')}", "neutral", "This is the actual dasha layer the engine says is active now."),
                _build_item(
                    "Transit themes",
                    ", ".join(sorted({theme for item in transit_forecast for theme in item.get("dominant_themes", [])}))
                    or "See the transit scan in the analysis block",
                    "neutral",
                    "Use the analysis block below for the detailed transit picture.",
                ),
                _build_item("Practical use", "For big decisions, pair this with a proper birth chart and the exact event time.", "needs_review", "That keeps the reading grounded instead of vague."),
            ],
            ["The active dasha and transit forecast are real engine outputs, not a static phase label."],
        ),
        _build_section(
            "what-festivals-fasts-or-vrats-are-coming",
            "What festivals, fasts, or vrats are coming?",
            "A simple observance preview for the next day and nearby devotional cues.",
            "medium",
            [
                _build_item("What this means", f"The current panchang points to {((recommendations[2].get('items') or ['No major fasting cue is inferred from the tithi alone on this page.'])[0]) if len(recommendations) > 2 else 'No major fasting cue is inferred from the tithi alone on this page.'}", "neutral", "This is the easiest way to connect the day to fasting and observance planning."),
                _build_item("Why people ask this", "People ask this when they want to prepare food, family schedule, and worship items in advance.", "neutral", "Planning ahead is easier when the observance is visible early."),
                _build_item("What you should do next", f"Check tomorrow too, because {panchang_tomorrow.get('panchang', {}).get('tithi', {}).get('current', 'the next day')} may change the observance tone." if panchang_tomorrow else "Check the next day once the next snapshot loads.", "neutral", "Festivals and vrats often become clearer with a second-day preview."),
                _build_item("Current observance cue", recommendations[2].get("items", ["No major fasting cue is inferred from the tithi alone on this page."])[0] if len(recommendations) > 2 else "No major fasting cue is inferred from the tithi alone on this page.", "good", "This is the main fasting or observance hint returned by the available panchang data."),
                _build_item("Tomorrow preview", f"{panchang_tomorrow.get('panchang', {}).get('weekday', {}).get('current', 'Unavailable')} · {panchang_tomorrow.get('panchang', {}).get('tithi', {}).get('current', 'Unavailable')} · {panchang_tomorrow.get('panchang', {}).get('nakshatra', {}).get('current', 'Unavailable')}" if panchang_tomorrow else "Tomorrow preview not available", "neutral" if panchang_tomorrow else "unknown", "A next-day look helps families avoid last-minute confusion."),
                _build_item("Festival calendar note", "No dedicated festival calendar is connected to this panchang endpoint yet.", "unknown", "This is a clear placeholder rather than a hidden assumption."),
            ],
            ["If you want a full festival calendar, add a dedicated observance feed on top of the panchang engine."],
        ),
        _build_section(
            "when-should-i-do-puja-or-religious-rituals",
            "When should I do puja or religious rituals?",
            "A devotional timing guide for home worship, mantra work, and simple ritual planning.",
            "medium",
            [
                _build_item("What this means", "Puja usually fits best when the house, the mind, and the chosen time band all feel settled.", "good", "This makes the ritual easy to sustain rather than rushed."),
                _build_item("Why people ask this", "People ask this when they want to know whether the morning, noon, or evening slot is better for worship.", "neutral", "The timing helps them decide how short or elaborate the puja should be."),
                _build_item("What you should do next", "Use a calm window, keep the puja simple, and avoid a rushed start right before a caution period.", "good", "A short, steady puja is often better than a long one started in a hurry."),
                _build_item("Best ritual time", _window_items(favorable_windows, "Morning calm window"), "good", "This is the most natural place to put prayer, mantra, and sankalpa work."),
                _build_item("What to avoid", _window_items(caution_windows, "Rushed or noisy time slots"), "avoid", "This helps prevent a devotional task from starting in a weak slot."),
                _build_item("Ritual style", "Beginner-friendly, short, and respectful is usually better than complicated and unsteady.", "neutral", "This keeps puja accessible even when the family is new to the practice."),
            ],
            ["The best ritual windows are the same actual windows the panchang engine calculated for this day."],
        ),
        _build_section(
            "when-should-i-perform-shraddha-or-pitru-rituals",
            "When should I perform Shraddha or Pitru rituals?",
            "A quiet ancestral-rite screen that keeps the tone calm, respectful, and specific to family duty.",
            "high",
            [
                _build_item("What this means", "The current day is evaluated against the actual tithi; if it is Amavasya, the pitri tone is naturally stronger.", "good" if str(panchang_today_snapshot.get("tithi", {}).get("current", "")).lower().endswith("amavasya") else "needs_review", "Shraddha and Pitru work are usually read with special care, not as ordinary worship."),
                _build_item("Why people ask this", "People ask this when they need to honor ancestors, complete family duty, or avoid an inauspicious day by mistake.", "neutral", "This is one of the most serious and respectful timing questions people bring to a pandit."),
                _build_item("What you should do next", "Book a consultation if this is an actual Shraddha or Pitru rite, because the exact rule set can vary by tradition.", "needs_review", "A family duty should be matched to the lineage method, not only the calendar date."),
                _build_item("Pitri cue", recommendations[2].get("items", ["No major fasting cue is inferred from the tithi alone on this page."])[0] if len(recommendations) > 2 else "No major fasting cue is inferred from the tithi alone on this page.", "good" if str(panchang_today_snapshot.get("tithi", {}).get("current", "")).lower().endswith("amavasya") else "neutral", "This gives the simplest cue for remembrance or ancestral observance."),
                _build_item("Recommended tone", "Quiet, simple, and duty-focused rather than celebratory.", "good", "The ritual is about service and remembrance, not festivity."),
                _build_item("Family check", "Confirm the lineage tradition, the food rules, and the priest's preferred sequence before the rite day.", "needs_review", "This prevents mistakes in a rite that families usually want to get exactly right."),
            ],
            ["This tab uses the current tithi cue and family tradition as the present timing reference."],
            {
                "label": "Ask a Pandit",
                "href": f"mailto:{CTA_EMAIL}?subject=Shraddha%20%2F%20Pitru%20ritual%20guidance",
                "note": "Shraddha and Pitru rituals should be matched to your family method before you finalize the date.",
            },
        ),
        _build_section(
            "is-this-a-good-time-for-career-or-business-decisions",
            "Is this a good time for career or business decisions?",
            "A practical career and business read for interviews, launches, applications, and major decisions.",
            "high",
            [
                _build_item("What this means", f"The current day is {daily_rating['label'].lower()} for career action, and the {muhurta_label(muhurta_career)} score is being used for a job-focused read.", "good" if muhurta_career["summary"]["is_favorable"] else "needs_review", "This is the 'should I move now?' question in work language."),
                _build_item("Why people ask this", "People ask this before interviews, offers, launches, contract signatures, and investment decisions.", "neutral", "These are the moments when people want both courage and timing on their side."),
                _build_item("What you should do next", "Use the best timing window, and if the decision is large, ask a pandit before you commit.", "good", "The right time can matter as much as the right choice."),
                _build_item("Career tone", f"{current_period.get('lord', 'Unavailable')} · {transit_phase}", "good" if muhurta_career["summary"]["is_favorable"] else "needs_review", "This combines the active dasha with the actual career muhurta score."),
                _build_item("Business caution", "Avoid signing or announcing the biggest commitments during caution windows.", "avoid", "That is the safest way to reduce avoidable friction."),
                _build_item("Beginner rule", "If the decision feels like a turning point, it deserves more than a quick glance.", "needs_review", "A full consultation is often worth it for a career pivot or business launch."),
            ],
            ["The career tab uses the real career muhurta score and current dasha period."],
            {
                "label": "Book Consultation",
                "href": f"mailto:{CTA_EMAIL}?subject=Career%20%2F%20business%20consultation",
                "note": "Career and business questions usually need a deeper read than daily Panchang alone can provide.",
            },
        ),
        _build_section(
            "is-this-a-good-time-to-travel",
            "Is this a good time to travel?",
            "A travel timing screen that keeps the answer simple: go, wait, or check the window.",
            "medium",
            [
                _build_item("What this means", "Travel is usually easiest when the start time is calm and not tied to a caution window.", "neutral", "People often want the first departure to feel smooth and protected."),
                _build_item("Why people ask this", "People ask this before flights, road trips, pilgrimages, and family visits.", "neutral", "The travel start time is often the part that families most want to get right."),
                _build_item("What you should do next", "Travel in a supportive window if you can, and avoid first departure during Rahu Kalam when possible.", "good", "That is the simplest travel rule most beginners can follow."),
                _build_item("Best departure", _window_items(favorable_windows, "Morning window"), "good", "This is the safest first-choice slot for departure."),
                _build_item("Use caution", _window_items(caution_windows, "Caution windows"), "avoid", "This slot is better for routine movement than for a new departure."),
                _build_item("Travel note", "If travel is unavoidable, keep the start simple and the first prayer brief.", "neutral", "This is a practical way to respect timing without overcomplicating the trip."),
            ],
            ["The travel score comes from the actual muhurta engine for the travel profile."],
        ),
        _build_section(
            "what-is-the-best-time-for-spiritual-practices",
            "What is the best time for spiritual practices?",
            "A devotional timing guide for japa, meditation, reading, and quiet worship.",
            "medium",
            [
                _build_item("What this means", "The best practice time is usually the calmest and least interrupted window in the day.", "good", "This helps the mind settle before the outer world gets loud."),
                _build_item("Why people ask this", "People ask this when they want to keep japa, reading, or meditation regular instead of random.", "neutral", "A steady practice time makes the routine easier to keep."),
                _build_item("What you should do next", "Use the earliest quiet slot you can protect each day.", "good", "A consistent slot is more useful than trying to find the perfect one every day."),
                _build_item("Best practice band", _window_items(favorable_windows, "Early morning quiet time"), "good", "This is the strongest place to put mantra and inward work."),
                _build_item("Spiritual focus", "Japa, stotra, silent prayer, and short study all fit well here.", "good", "These are the practices that benefit most from a steady rhythm."),
                _build_item("Avoid", "Do not force a long practice into a rushed or distracted window.", "avoid", "The value of the practice drops when the start is chaotic."),
            ],
            ["The backend uses the same actual day windows and dasha phase that are already computed for the chart."],
        ),
        _build_section(
            "are-there-any-eclipses-or-special-events-coming",
            "Are there any eclipses or special events coming?",
            "A conservative special-events screen.",
            "low",
            [
                _build_item("What this means", eclipse_note, "unknown", "It keeps the page honest until a dedicated eclipse calendar is wired in."),
                _build_item("Why people ask this", "People ask this because eclipses, festivals, and unusual sky events can change worship and planning.", "neutral", "These are the dates that people most often double-check with a priest."),
                _build_item("What you should do next", "Check a reliable panchang source or ask a pandit before making a religious plan around an eclipse date.", "needs_review", "Special events need a trusted calendar, not a guess."),
                _build_item("Current special-event status", coming_events[0], "unknown", "This is a real transit scan, but not a full eclipse calendar."),
                _build_item("Special caution", "Treat large ritual choices conservatively when a special sky event might be near.", "avoid", "That is the safest beginner habit until the calendar is confirmed."),
            ],
            ["This tab currently reflects the transit scan and node activity; add a dedicated grahan calendar if you need explicit eclipse dates."],
        ),
        _build_section(
            "advanced-details",
            "Advanced details",
            "A deeper technical view for users who want the underlying Panchang values and calculation notes.",
            "low",
            [
                _build_item("What this means", "This tab is for users who want the raw Panchang terms after they have read the beginner-friendly guidance.", "neutral", "It keeps the expert view available without forcing it on beginners."),
                _build_item("Why people ask this", "People ask this when they want the exact panchang labels, source notes, or calculation limits.", "neutral", "It is the practical bridge between the friendly dashboard and the underlying data."),
                _build_item("What you should do next", "Use this tab for verification, then move back to the real-life question tab for the actual decision.", "good", "The advanced view should support the decision, not replace it."),
                _build_item("Core Panchang", f"{panchang.get('weekday', panchang_today.get('panchang', {}).get('weekday', 'Unavailable'))} · {panchang.get('tithi', {}).get('current', 'Unavailable')} · {panchang.get('nakshatra', {}).get('current', 'Unavailable')} · {panchang.get('yoga', {}).get('current', 'Unavailable')} · {panchang.get('karana', {}).get('current', 'Unavailable')}", "neutral", "These are the main calendar factors behind the daily guidance."),
                _build_item("Sunrise / Sunset", f"{panchang.get('sunrise', 'Unavailable')} / {panchang.get('sunset', 'Unavailable')}", "neutral", "These times anchor the daily window calculations."),
                _build_item("Calculation notes", panchang.get("notes", "Daily Panchang for the selected location and date."), "unknown", "This is the current backend note for the source data set."),
                _build_item("Lagna note", lagna, "good" if not birth_time_unknown else "unknown", "This becomes approximate when the exact birth time is missing."),
            ],
            [
                "The backend is already using real engines for birth chart, dasha, transit, compatibility, and muhurta.",
                "For finer-grained interpretation, add or tune rule packs in the rule engine rather than hardcoding new logic here.",
            ],
        ),
    ]

    analysis = {
        "panchangToday": panchang_today,
        "panchangTomorrow": panchang_tomorrow,
        "birthChart": birth_chart,
        "dasha": dasha,
        "transitToday": transit_today,
        "transitForecast": transits_forecast,
        "muhurta": {
            "general": muhurta_general,
            "career": muhurta_career,
            "travel": muhurta_travel,
            "marriage": muhurta_marriage,
            "finance": muhurta_finance,
        },
        "interpretation": interpretation,
        "compatibility": compatibility,
        "nameLetters": name_letters,
    }

    return {
        "summary": summary,
        "sections": sections,
        "analysis": analysis,
        "generatedAtIso": _dt.datetime.utcnow().isoformat() + "Z",
    }


def muhurta_label(muhurta_result: dict[str, Any]) -> str:
    score = muhurta_result.get("score", {})
    normalized = float(score.get("normalized", 0.0) or 0.0)
    if normalized >= 0.75:
        return "strong"
    if normalized >= 0.55:
        return "mixed"
    return "careful"
