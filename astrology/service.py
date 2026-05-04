"""High-level service entrypoints for the API layer."""

from __future__ import annotations

import datetime as _dt
from typing import Any

import legacy_panchanga

from .cache import AstrologyResultCache
from .birth_chart import DEFAULT_BIRTH_CHART_ENGINE, BirthChartEngine
from .compatibility import DEFAULT_COMPATIBILITY_ENGINE, AshtakutaCompatibilityEngine
from .dasha import DEFAULT_VIMSHOTTARI_DASHA_ENGINE, VimshottariDashaEngine
from .divisional import DEFAULT_DIVISIONAL_CHART_ENGINE, DivisionalChartEngine
from .muhurta import DEFAULT_MUHURTA_ENGINE, MuhurtaEngine
from .panchang import DEFAULT_PANCHANG_ENGINE, PanchangEngine
from .locations import resolve_city, timezone_offset_hours_for_datetime
from .rules import DEFAULT_RULE_ENGINE, RuleEngine, interpret_chart
from .rulepacks import DEFAULT_RULE_PACK, DEFAULT_RULE_PACK_REGISTRY, RulePack, RulePackRegistry
from .personal_guidance import build_personal_guidance, summarize_panchang_result
from .utils import parse_birth_datetime, parse_fixed_or_iana_timezone
from .transit import DEFAULT_TRANSIT_ENGINE, TransitEngine


class AstrologyService:
    """Framework-agnostic facade for the astrology engine.

    The service is intentionally small and composed of injectable engines so
    callers can swap the rule catalog or replace an implementation without
    touching HTTP code or chart calculations.
    """

    def __init__(
        self,
        birth_chart_engine: BirthChartEngine | None = None,
        dasha_engine: VimshottariDashaEngine | None = None,
        divisional_engine: DivisionalChartEngine | None = None,
        transit_engine: TransitEngine | None = None,
        compatibility_engine: AshtakutaCompatibilityEngine | None = None,
        muhurta_engine: MuhurtaEngine | None = None,
        panchang_engine: PanchangEngine | None = None,
        rule_engine: RuleEngine | None = None,
        rule_pack: RulePack | None = None,
        rule_pack_registry: RulePackRegistry | None = None,
        cache: AstrologyResultCache | None = None,
    ):
        self.birth_chart_engine = birth_chart_engine or DEFAULT_BIRTH_CHART_ENGINE
        self.dasha_engine = dasha_engine or DEFAULT_VIMSHOTTARI_DASHA_ENGINE
        self.divisional_engine = divisional_engine or DEFAULT_DIVISIONAL_CHART_ENGINE
        self.transit_engine = transit_engine or DEFAULT_TRANSIT_ENGINE
        self.compatibility_engine = compatibility_engine or DEFAULT_COMPATIBILITY_ENGINE
        self.muhurta_engine = muhurta_engine or DEFAULT_MUHURTA_ENGINE
        self.panchang_engine = panchang_engine or DEFAULT_PANCHANG_ENGINE
        self.rule_pack = rule_pack or DEFAULT_RULE_PACK
        self.rule_pack_registry = rule_pack_registry or DEFAULT_RULE_PACK_REGISTRY
        self.rule_engine = rule_engine or RuleEngine(self.rule_pack.catalog)
        self.cache = cache or AstrologyResultCache()

    def _normalize_timezone(self, payload: dict[str, Any]) -> tuple[float | None, str | None]:
        timezone_value = payload.get("timezone")
        timezone_name = payload.get("timezone_name")

        if isinstance(timezone_value, (int, float)):
            return float(timezone_value), timezone_name

        if isinstance(timezone_value, str):
            text = timezone_value.strip()
            if text:
                try:
                    return float(text), timezone_name
                except ValueError:
                    timezone_name = timezone_name or text

        return None, timezone_name

    def _coerce_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _resolve_city_payload(self, city: str | None, state: str | None, country: str | None) -> dict[str, Any] | None:
        if not city:
            return None
        return resolve_city(str(city), state=str(state or ""), country=str(country or ""))

    def _current_location(self, payload: dict[str, Any]) -> dict[str, Any]:
        current_city = payload.get("current_city") or payload.get("city")
        current_state = payload.get("current_state") or payload.get("state")
        current_country = payload.get("current_country") or payload.get("country")
        current_timezone_name = payload.get("current_timezone_name") or payload.get("timezone_name")
        resolved = self._resolve_city_payload(current_city, current_state, current_country)
        if resolved:
            return {
                "city": resolved["city"],
                "state": resolved.get("state"),
                "country": resolved.get("country"),
                "latitude": resolved.get("latitude"),
                "longitude": resolved.get("longitude"),
                "timezone_name": resolved.get("timezone_name"),
            }
        return {
            "city": current_city,
            "state": current_state,
            "country": current_country,
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "timezone_name": current_timezone_name,
        }

    def _birth_location(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._resolve_city_payload(payload.get("birth_city"), payload.get("birth_state"), payload.get("birth_country"))

    def _date_for_timezone(self, payload: dict[str, Any], timezone_name: str | None, timezone_value: float | None) -> _dt.date:
        if timezone_name:
            tzinfo = parse_fixed_or_iana_timezone(timezone_name)
            return _dt.datetime.now(tzinfo).date()
        if timezone_value is not None:
            tzinfo = parse_fixed_or_iana_timezone(timezone_value)
            return _dt.datetime.now(tzinfo).date()
        return _dt.datetime.utcnow().date()

    def _current_transit_datetime(self, timezone_name: str | None, timezone_value: float | None) -> _dt.datetime:
        if timezone_name:
            return _dt.datetime.now(parse_fixed_or_iana_timezone(timezone_name))
        if timezone_value is not None:
            return _dt.datetime.now(parse_fixed_or_iana_timezone(timezone_value))
        return _dt.datetime.now(_dt.timezone.utc)

    def _build_birth_payload(self, payload: dict[str, Any], birth_location: dict[str, Any] | None, timezone_name: str | None, timezone_value: float | None) -> dict[str, Any]:
        birth_date = payload.get("birth_date")
        birth_time_unknown = self._coerce_bool(payload.get("birth_time_unknown"))
        birth_time = payload.get("birth_time")
        birth_datetime = payload.get("birth_datetime")
        if not birth_datetime and birth_date:
            if birth_time and not birth_time_unknown:
                birth_datetime = f"{birth_date}T{str(birth_time)}"
            else:
                birth_datetime = f"{birth_date}T12:00:00"

        result: dict[str, Any] = {
            "birth_datetime": birth_datetime,
            "birth_date": birth_date,
            "birth_time": birth_time,
            "timezone": timezone_value if timezone_value is not None else None,
            "timezone_name": timezone_name,
            "latitude": payload.get("birth_latitude") or (birth_location or {}).get("latitude"),
            "longitude": payload.get("birth_longitude") or (birth_location or {}).get("longitude"),
            "city": (birth_location or {}).get("city") or payload.get("birth_city"),
            "state": (birth_location or {}).get("state") or payload.get("birth_state"),
            "country": (birth_location or {}).get("country") or payload.get("birth_country"),
        }
        return {key: value for key, value in result.items() if value is not None}

    def _build_name_letters_payload(self, payload: dict[str, Any], birth_location: dict[str, Any] | None, birth_payload: dict[str, Any]) -> dict[str, Any]:
        derived = {
            "birth_datetime": birth_payload.get("birth_datetime"),
            "timezone": birth_payload.get("timezone"),
            "timezone_name": birth_payload.get("timezone_name"),
            "latitude": birth_payload.get("latitude"),
            "longitude": birth_payload.get("longitude"),
            "city": birth_payload.get("city"),
            "state": birth_payload.get("state"),
            "country": birth_payload.get("country"),
        }
        if birth_location and birth_location.get("city") and not derived.get("latitude") and not derived.get("longitude"):
            derived["city"] = birth_location.get("city")
            derived["state"] = birth_location.get("state")
            derived["country"] = birth_location.get("country")
        if derived.get("timezone") is None and derived.get("timezone_name") and derived.get("birth_datetime"):
            try:
                birth_dt, _ = parse_birth_datetime(
                    {
                        "birth_datetime": derived["birth_datetime"],
                        "timezone_name": derived["timezone_name"],
                    }
                )
                derived["timezone"] = timezone_offset_hours_for_datetime(birth_dt, str(derived["timezone_name"]))
            except ValueError:
                pass
        return {key: value for key, value in derived.items() if value is not None}

    def _build_muhurta_payload(
        self,
        payload: dict[str, Any],
        current_location: dict[str, Any],
        date_value: _dt.date,
        timezone_name: str | None,
        timezone_value: float | None,
        activity_type: str,
    ) -> dict[str, Any]:
        resolved = {
            "date": date_value.isoformat(),
            "activity_type": activity_type,
            "latitude": current_location.get("latitude"),
            "longitude": current_location.get("longitude"),
            "timezone": timezone_value if timezone_value is not None else None,
            "timezone_name": timezone_name or current_location.get("timezone_name"),
            "city": current_location.get("city") or payload.get("current_city") or payload.get("city"),
            "state": current_location.get("state") or payload.get("current_state") or payload.get("state"),
            "country": current_location.get("country") or payload.get("current_country") or payload.get("country"),
            "minimum_score": 0,
        }
        return {key: value for key, value in resolved.items() if value is not None}

    def _cached(self, namespace: str, payload: dict, builder):
        return self.cache.cached(namespace, payload, builder)

    def build_birth_chart(self, payload: dict) -> dict:
        return self._cached("birth_chart", payload, lambda: self.birth_chart_engine.calculate(payload))

    def build_dashas(self, payload: dict) -> dict:
        return self._cached(
            "dashas",
            payload,
            lambda: {
                "birth_chart": self.build_birth_chart(payload),
                "dashas": self.dasha_engine.calculate(payload, chart=self.build_birth_chart(payload)),
            },
        )

    def build_divisional_charts(self, payload: dict) -> dict:
        return self._cached(
            "divisional_charts",
            payload,
            lambda: {
                "birth_chart": self.build_birth_chart(payload),
                "divisional_charts": self.divisional_engine.calculate(self.build_birth_chart(payload)),
            },
        )

    def build_transits(self, payload: dict) -> dict:
        return self._cached(
            "transits",
            payload,
            lambda: self.transit_engine.calculate(payload, natal_chart=self.build_birth_chart(payload)),
        )

    def build_interpretation(self, payload: dict) -> dict:
        requested_pack = payload.get("rule_pack")

        def _build() -> dict:
            chart = self.build_birth_chart(payload)
            if requested_pack:
                try:
                    rule_pack = self.rule_pack_registry.get(str(requested_pack))
                except KeyError as exc:
                    raise ValueError(str(exc))
                rule_engine = RuleEngine(rule_pack.catalog)
            else:
                rule_engine = self.rule_engine
            return {
                "birth_chart": chart,
                "interpretation": interpret_chart(chart, engine=rule_engine),
                "rule_pack": requested_pack or self.rule_pack.name,
            }

        return self._cached("interpretation", payload, _build)

    def _chart_from_payload(self, payload: dict, chart_key: str, birth_key: str) -> dict:
        chart = payload.get(chart_key)
        if isinstance(chart, dict):
            return chart

        nested = payload.get(birth_key)
        if isinstance(nested, dict):
            return self.birth_chart_engine.calculate(nested)

        if birth_key == "boy":
            for key in ("boy", "participant_a", "partner_a", "person_a", "native_a", "first"):
                nested = payload.get(key)
                if isinstance(nested, dict):
                    return self.birth_chart_engine.calculate(nested)
        else:
            for key in ("girl", "participant_b", "partner_b", "person_b", "native_b", "second"):
                nested = payload.get(key)
                if isinstance(nested, dict):
                    return self.birth_chart_engine.calculate(nested)

        raise ValueError(f"{chart_key} or {birth_key} birth data is required")

    def build_compatibility(self, payload: dict) -> dict:
        return self._cached(
            "compatibility",
            payload,
            lambda: {
                "boy_chart": self._chart_from_payload(payload, "boy_chart", "boy"),
                "girl_chart": self._chart_from_payload(payload, "girl_chart", "girl"),
                "compatibility": self.compatibility_engine.calculate_from_charts(
                    self._chart_from_payload(payload, "boy_chart", "boy"),
                    self._chart_from_payload(payload, "girl_chart", "girl"),
                ),
            },
        )

    def build_muhurta(self, payload: dict) -> dict:
        return self._cached("muhurta", payload, lambda: self.muhurta_engine.calculate(payload))

    def build_panchang(self, payload: dict) -> dict:
        def _build() -> dict:
            normalized_payload = dict(payload)
            timezone_value, timezone_name = self._normalize_timezone(normalized_payload)
            current_location = self._current_location(normalized_payload)
            birth_location = self._birth_location(normalized_payload)
            normalized_payload["birth_time_unknown"] = self._coerce_bool(normalized_payload.get("birth_time_unknown"))

            if current_location.get("latitude") is None or current_location.get("longitude") is None:
                raise ValueError("current city could not be resolved; latitude and longitude are required")

            current_date = self._date_for_timezone(normalized_payload, current_location.get("timezone_name") or timezone_name, timezone_value)
            today_payload = {
                "date": current_date.isoformat(),
                "latitude": current_location.get("latitude"),
                "longitude": current_location.get("longitude"),
                "timezone": timezone_value if timezone_value is not None else None,
                "timezone_name": current_location.get("timezone_name") or timezone_name,
                "city": current_location.get("city"),
                "state": current_location.get("state"),
                "country": current_location.get("country"),
            }
            today_result = self.panchang_engine.calculate(today_payload)
            tomorrow_result = self.panchang_engine.calculate({**today_payload, "date": (current_date + _dt.timedelta(days=1)).isoformat()})

            today_snapshot = summarize_panchang_result(
                today_result,
                date_label=current_date.strftime("%B %d, %Y"),
                location_label=", ".join(part for part in [current_location.get("city"), current_location.get("country")] if part) or "Unavailable",
                city=current_location.get("city"),
                country=current_location.get("country"),
                timezone_name=current_location.get("timezone_name") or timezone_name,
            )
            tomorrow_snapshot = summarize_panchang_result(
                tomorrow_result,
                date_label=(current_date + _dt.timedelta(days=1)).strftime("%B %d, %Y"),
                location_label=", ".join(part for part in [current_location.get("city"), current_location.get("country")] if part) or "Unavailable",
                city=current_location.get("city"),
                country=current_location.get("country"),
                timezone_name=current_location.get("timezone_name") or timezone_name,
            )

            birth_payload = self._build_birth_payload(normalized_payload, birth_location, normalized_payload.get("timezone_name") or timezone_name, timezone_value)
            if not birth_payload.get("birth_datetime"):
                raise ValueError("birth_date is required for personal Panchang guidance")

            birth_chart = self.build_birth_chart(birth_payload)
            dasha = self.dasha_engine.calculate(birth_payload, chart=birth_chart, max_depth=2)
            interpretation = self.build_interpretation(birth_payload)
            transit_datetime = self._current_transit_datetime(current_location.get("timezone_name") or timezone_name, timezone_value)
            transit_payload = {
                "transit_datetime": transit_datetime.isoformat(),
                "timezone": timezone_value if timezone_value is not None else None,
                "timezone_name": current_location.get("timezone_name") or timezone_name,
                "latitude": current_location.get("latitude"),
                "longitude": current_location.get("longitude"),
                "city": current_location.get("city"),
                "state": current_location.get("state"),
                "country": current_location.get("country"),
                "forecast_days": 3,
            }
            transits = self.transit_engine.calculate(transit_payload, natal_chart=birth_chart)

            muhurta_general = self.muhurta_engine.calculate(self._build_muhurta_payload(normalized_payload, current_location, current_date, current_location.get("timezone_name") or timezone_name, timezone_value, "general"))
            muhurta_career = self.muhurta_engine.calculate(self._build_muhurta_payload(normalized_payload, current_location, current_date, current_location.get("timezone_name") or timezone_name, timezone_value, "career"))
            muhurta_travel = self.muhurta_engine.calculate(self._build_muhurta_payload(normalized_payload, current_location, current_date, current_location.get("timezone_name") or timezone_name, timezone_value, "travel"))
            muhurta_marriage = self.muhurta_engine.calculate(self._build_muhurta_payload(normalized_payload, current_location, current_date, current_location.get("timezone_name") or timezone_name, timezone_value, "marriage"))
            muhurta_finance = self.muhurta_engine.calculate(self._build_muhurta_payload(normalized_payload, current_location, current_date, current_location.get("timezone_name") or timezone_name, timezone_value, "finance"))

            name_letters_payload = self._build_name_letters_payload(normalized_payload, birth_location, birth_payload)
            try:
                name_letters = legacy_panchanga.get_name_letters(name_letters_payload)
            except Exception:
                if birth_location and birth_location.get("city"):
                    name_letters = legacy_panchanga.get_name_letters_by_city(
                        {
                            "birth_datetime": birth_payload["birth_datetime"],
                            "city": birth_location.get("city"),
                            "state": birth_location.get("state"),
                            "country": birth_location.get("country"),
                        }
                    )
                else:
                    name_letters = {
                        "nakshatra_name": "Unavailable",
                        "syllables_for_nakshatra": [],
                        "note": "Naming syllables could not be resolved with the supplied birth data.",
                    }

            guidance = build_personal_guidance(
                payload=normalized_payload,
                panchang_today=today_snapshot,
                panchang_tomorrow=tomorrow_snapshot,
                birth_chart=birth_chart,
                dasha=dasha,
                interpretation=interpretation.get("interpretation", {}),
                transit_today=transits,
                transit_forecast=transits.get("forecast", []),
                muhurta_general=muhurta_general,
                muhurta_career=muhurta_career,
                muhurta_travel=muhurta_travel,
                muhurta_marriage=muhurta_marriage,
                muhurta_finance=muhurta_finance,
                name_letters=name_letters,
                compatibility=None,
            )

            return {
                "input": {
                    **today_result.get("input", {}),
                    "full_name": normalized_payload.get("full_name"),
                    "birth_date": normalized_payload.get("birth_date").isoformat() if isinstance(normalized_payload.get("birth_date"), _dt.date) else normalized_payload.get("birth_date"),
                    "birth_time": normalized_payload.get("birth_time").isoformat() if isinstance(normalized_payload.get("birth_time"), _dt.time) else normalized_payload.get("birth_time"),
                    "birth_time_unknown": bool(normalized_payload.get("birth_time_unknown")),
                    "birth_city": normalized_payload.get("birth_city"),
                    "birth_state": normalized_payload.get("birth_state"),
                    "birth_country": normalized_payload.get("birth_country"),
                    "current_city": normalized_payload.get("current_city") or normalized_payload.get("city"),
                    "current_state": normalized_payload.get("current_state") or normalized_payload.get("state"),
                    "current_country": normalized_payload.get("current_country") or normalized_payload.get("country"),
                    "current_timezone_name": normalized_payload.get("current_timezone_name"),
                    "gender": normalized_payload.get("gender"),
                    "relationship_status": normalized_payload.get("relationship_status"),
                    "main_question": normalized_payload.get("main_question"),
                    "preferred_language": normalized_payload.get("preferred_language"),
                    "tradition": normalized_payload.get("tradition"),
                },
                "panchang": today_result.get("panchang", {}),
                "guidance": guidance,
                "analysis": {
                    "today": today_result,
                    "tomorrow": tomorrow_result,
                    "birth_chart": birth_chart,
                    "dasha": dasha,
                    "interpretation": interpretation,
                    "transits": transits,
                    "muhurta": {
                        "general": muhurta_general,
                        "career": muhurta_career,
                        "travel": muhurta_travel,
                        "marriage": muhurta_marriage,
                        "finance": muhurta_finance,
                    },
                    "name_letters": name_letters,
                },
            }

        return self._cached("panchang", payload, _build)

    def build_meta(self, payload: dict | None = None) -> dict:
        payload = payload or {}
        supported_vargas = list(self.divisional_engine.varga_config)
        supported_dasha_levels = ["mahadasha", "antardasha", "pratyantardasha", "sookshma", "prana"]
        supported_ayanamsas = ["lahiri", "krishnamurti", "raman", "lahiri_icrc", "user"]
        supported_endpoints = [
            "/birth-chart",
            "/dashas",
            "/divisional-charts",
            "/transits",
            "/interpretation",
            "/compatibility",
            "/muhurta",
            "/panchang",
            "/meta",
        ]
        return {
            "api_version": "v1",
            "selected_service_version": payload.get("version") or "v1",
            "engine_class": self.__class__.__name__,
            "available_versions": ["v1"],
            "available_rule_packs": self.rule_pack_registry.list(),
            "supported_endpoints": supported_endpoints,
            "supported_dasha_levels": supported_dasha_levels,
            "supported_vargas": supported_vargas,
            "supported_house_systems": ["whole_sign"],
            "supported_ayanamsas": supported_ayanamsas,
            "cache_backend": self.cache.__class__.__name__,
        }


DEFAULT_ASTROLOGY_SERVICE = AstrologyService()


def build_birth_chart(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_birth_chart(payload)


def build_dashas(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_dashas(payload)


def build_divisional_charts(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_divisional_charts(payload)


def build_transits(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_transits(payload)


def build_interpretation(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_interpretation(payload)


def build_compatibility(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_compatibility(payload)


def build_muhurta(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_muhurta(payload)


def build_panchang(payload: dict) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_panchang(payload)


def build_meta(payload: dict | None = None) -> dict:
    return DEFAULT_ASTROLOGY_SERVICE.build_meta(payload)
