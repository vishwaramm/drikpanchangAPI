"""Pydantic schemas for the astrology API layer."""

from __future__ import annotations

from datetime import date as _date, datetime as _datetime, time as _time
from typing import Any

from pydantic import BaseModel, ConfigDict


class AstrologyBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class BirthChartPayload(AstrologyBaseModel):
    birth_datetime: _datetime | None = None
    birth_date: _date | None = None
    birth_time: _time | None = None
    timezone: float | str | None = None
    timezone_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    ayanamsa: str | float | None = "lahiri"
    ayanamsa_value: float | None = None
    house_system: str | None = "whole_sign"
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "birth_datetime": "1990-01-01T06:30:00",
                    "city": "Delhi",
                    "ayanamsa": "lahiri",
                    "house_system": "whole_sign",
                }
            ]
        },
    )


class DashasPayload(BirthChartPayload):
    max_depth: int = 2
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "birth_datetime": "1990-01-01T06:30:00",
                    "city": "Delhi",
                    "max_depth": 3,
                }
            ]
        },
    )


class DivisionalChartsPayload(BirthChartPayload):
    model_config = ConfigDict(extra="allow")


class TransitsPayload(BirthChartPayload):
    transit_datetime: _datetime | None = None
    date_time: _datetime | None = None
    date: _date | None = None
    forecast_days: int = 0
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "birth_datetime": "1990-01-01T06:30:00",
                    "city": "Delhi",
                    "transit_datetime": "2025-01-23T00:00:00",
                    "forecast_days": 2,
                }
            ]
        },
    )


class InterpretationPayload(BirthChartPayload):
    rule_pack: str | None = None
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "birth_datetime": "1990-01-01T06:30:00",
                    "city": "Delhi",
                    "rule_pack": "strict_classical",
                }
            ]
        },
    )


class CompatibilitySidePayload(BirthChartPayload):
    chart: dict[str, Any] | None = None


class CompatibilityPayload(AstrologyBaseModel):
    boy_chart: dict[str, Any] | None = None
    girl_chart: dict[str, Any] | None = None
    boy: dict[str, Any] | None = None
    girl: dict[str, Any] | None = None
    participant_a: dict[str, Any] | None = None
    participant_b: dict[str, Any] | None = None
    partner_a: dict[str, Any] | None = None
    partner_b: dict[str, Any] | None = None
    person_a: dict[str, Any] | None = None
    person_b: dict[str, Any] | None = None
    native_a: dict[str, Any] | None = None
    native_b: dict[str, Any] | None = None
    first: dict[str, Any] | None = None
    second: dict[str, Any] | None = None
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "boy_chart": {"planets": {"Moon": {"sidereal_longitude": 0.0, "sign_index": 0, "nakshatra_index": 0}}},
                    "girl_chart": {"planets": {"Moon": {"sidereal_longitude": 30.0, "sign_index": 1, "nakshatra_index": 1}}},
                }
            ]
        },
    )

    def left_birth_payload(self) -> dict[str, Any] | None:
        return next(
            (
                value
                for value in [
                    self.boy,
                    self.participant_a,
                    self.partner_a,
                    self.person_a,
                    self.native_a,
                    self.first,
                ]
                if isinstance(value, dict)
            ),
            None,
        )

    def right_birth_payload(self) -> dict[str, Any] | None:
        return next(
            (
                value
                for value in [
                    self.girl,
                    self.participant_b,
                    self.partner_b,
                    self.person_b,
                    self.native_b,
                    self.second,
                ]
                if isinstance(value, dict)
            ),
            None,
        )


class MuhurtaPayload(AstrologyBaseModel):
    date: _date | None = None
    start_date: _date | None = None
    end_date: _date | None = None
    timezone: float | str | None = None
    timezone_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    activity_type: str = "general"
    minimum_score: int = 0
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "date": "2025-01-23",
                    "latitude": 12.972,
                    "longitude": 77.594,
                    "timezone": 5.5,
                    "activity_type": "career",
                }
            ]
        },
    )


class PanchangPayload(AstrologyBaseModel):
    date: _date | None = None
    timezone: float | str | None = None
    timezone_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    full_name: str | None = None
    birth_date: _date | None = None
    birth_time: _time | None = None
    birth_time_unknown: bool = False
    birth_city: str | None = None
    birth_state: str | None = None
    birth_country: str | None = None
    current_city: str | None = None
    current_state: str | None = None
    current_country: str | None = None
    current_timezone_name: str | None = None
    gender: str | None = None
    relationship_status: str | None = None
    main_question: str | None = None
    preferred_language: str | None = None
    tradition: str | None = None
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "date": "2025-01-23",
                    "latitude": 12.972,
                    "longitude": 77.594,
                    "timezone": 5.5,
                    "full_name": "Anika Sharma",
                    "birth_city": "Delhi",
                    "birth_country": "India",
                    "current_city": "New York",
                    "current_country": "USA",
                    "timezone_name": "America/New_York",
                }
            ]
        },
    )


class AstrologyMetaPayload(AstrologyBaseModel):
    version: str | None = None
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "version": "v1",
                }
            ]
        },
    )
