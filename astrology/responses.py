"""Typed response models for the astrology API."""

from __future__ import annotations

from datetime import date as _date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AstrologyResponseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class NamedIndexModel(AstrologyResponseModel):
    index: int
    name: str


class AspectModel(AstrologyResponseModel):
    target: str
    aspect: str
    type: str
    sign_distance: int
    orb: float


class CombustionModel(AstrologyResponseModel):
    is_combust: bool
    orb: float | None = None
    distance_from_sun: float | None = None


class PlanetPlacementModel(AstrologyResponseModel):
    longitude: float
    sign_index: int
    sign: str
    degree_in_sign: float
    degree: float | None = None
    nakshatra_index: int | None = None
    nakshatra: str | None = None
    nakshatra_number: int | None = None
    pada: int | None = None
    dignity: str | None = None
    combustion: CombustionModel | dict[str, Any] | None = None
    retrograde: bool | None = None
    house: int | None = None
    latitude: float | None = None
    distance: float | None = None
    speed_longitude: float | None = None


class BirthChartInputModel(AstrologyResponseModel):
    birth_datetime: str
    birth_datetime_utc: str | None = None
    timezone: float | str | None = None
    timezone_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    ayanamsa: str | None = None
    ayanamsa_value: float | None = None
    house_system: str | None = None


class LocationContextModel(AstrologyResponseModel):
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    timezone_name: str | None = None
    timezone: float | str | None = None
    resolved_city: dict[str, Any] | None = None


class HouseSystemModel(AstrologyResponseModel):
    system: str
    ascendant_longitude: float
    cusps: list[float] = Field(default_factory=list)
    ascmc: list[float] = Field(default_factory=list)


class BirthChartSummaryModel(AstrologyResponseModel):
    chart_type: str
    location_based: bool
    planet_count: int


class BirthChartResponse(AstrologyResponseModel):
    input: BirthChartInputModel
    julian_day_ut: float
    location: LocationContextModel
    ascendant: PlanetPlacementModel | None = None
    houses: HouseSystemModel | None = None
    planets: dict[str, PlanetPlacementModel]
    aspects: list[AspectModel] = Field(default_factory=list)
    summary: BirthChartSummaryModel
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "summary": {"chart_type": "sidereal", "location_based": True, "planet_count": 9},
                }
            ]
        },
    )


class DashaBalanceModel(AstrologyResponseModel):
    elapsed_years: float
    remaining_years: float


class DashaPeriodModel(AstrologyResponseModel):
    lord: str
    level: int
    level_name: str
    duration_years: float
    start: str
    end: str
    active_at_birth: bool
    elapsed_at_birth_years: float
    balance_at_birth_years: float
    children: list["DashaPeriodModel"] = Field(default_factory=list)


class DashaTimelineModel(AstrologyResponseModel):
    birth_datetime: str
    nakshatra: str
    nakshatra_index: int
    moon_nirayana_longitude: float
    mahadasha_lord_at_birth: str
    dasha_balance: DashaBalanceModel
    cycle_start: str
    cycle_end: str
    mahadashas: list[DashaPeriodModel]
    current_period: DashaPeriodModel
    levels: dict[str, str]
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "mahadasha_lord_at_birth": "Mars",
                    "levels": {"mahadasha": "included", "antardasha": "included", "pratyantardasha": "included"},
                }
            ]
        },
    )


class DashasResponse(AstrologyResponseModel):
    birth_chart: BirthChartResponse
    dashas: DashaTimelineModel
    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"dashas": {"mahadasha_lord_at_birth": "Mars"}}]})


class DivisionalPlacementModel(AstrologyResponseModel):
    source_longitude: float
    sign_index: int
    sign: str
    degree_in_sign: float
    varga_type: str
    varga_sign_index: int | None = None
    varga_sign: str | None = None
    segment_index: int
    segment_lord: str | None = None


class DivisionalChartModel(AstrologyResponseModel):
    name: str
    divisor: int
    method: str
    ascendant: DivisionalPlacementModel | None = None
    placements: dict[str, DivisionalPlacementModel]
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "name": "D9",
                    "divisor": 9,
                    "method": "navamsa",
                }
            ]
        },
    )


class DivisionalChartsResponse(AstrologyResponseModel):
    source: dict[str, Any]
    vargas: dict[str, DivisionalChartModel]
    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"source": {"chart_type": "sidereal"}}]})


class TransitInputModel(AstrologyResponseModel):
    transit_datetime: str
    transit_datetime_utc: str


class TransitPlacementModel(AstrologyResponseModel):
    longitude: float
    sign_index: int
    retrograde: bool | None = None
    sidereal_longitude: float
    latitude: float | None = None
    distance: float | None = None
    speed_longitude: float | None = None


class TransitChartModel(AstrologyResponseModel):
    input: TransitInputModel
    planets: dict[str, TransitPlacementModel]


class TransitHitModel(AstrologyResponseModel):
    transit_planet: str
    natal_planet: str
    aspect: str
    sign_distance: int
    orb: float


class TransitSummaryModel(AstrologyResponseModel):
    planet: str
    sign: int
    natal_hits: list[dict[str, Any]]


class TransitForecastModel(AstrologyResponseModel):
    date: str
    transit_datetime: str
    aspect_hit_count: int
    conjunction_count: int
    score: float
    top_hits: list[dict[str, Any]] = Field(default_factory=list)
    timed_windows: list["TransitWindowModel"] = Field(default_factory=list)
    dominant_themes: list[str] = Field(default_factory=list)
    events: list["TransitEventModel"] = Field(default_factory=list)
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "date": "2025-01-24",
                    "score": 30.0,
                    "timed_windows": [],
                }
            ]
        },
    )


class TransitWindowModel(AstrologyResponseModel):
    start: str
    end: str
    aspect_hit_count: int
    conjunction_count: int
    score: float
    peak_score: float
    top_hits: list[dict[str, Any]] = Field(default_factory=list)
    dominant_themes: list[str] = Field(default_factory=list)


class TransitEventModel(AstrologyResponseModel):
    planet: str
    event_type: str
    start: str
    end: str
    approx_time: str
    from_sign: str
    to_sign: str
    retrograde_state: str
    themes: list[str] = Field(default_factory=list)
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "planet": "Saturn",
                    "event_type": "ingress",
                    "approx_time": "2025-01-23T00:19:55.312500+05:30",
                }
            ]
        },
    )


class TransitsResponse(AstrologyResponseModel):
    transit_chart: TransitChartModel
    natal_chart: BirthChartResponse
    aspect_hits: list[TransitHitModel]
    summaries: list[TransitSummaryModel]
    events: list[TransitEventModel] = Field(default_factory=list)
    forecast: list[TransitForecastModel] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"forecast": [], "events": []}]})


class RuleMatchModel(AstrologyResponseModel):
    rule_id: str
    category: str
    title: str
    source: str
    score: int


class InterpretationModel(AstrologyResponseModel):
    matches: list[RuleMatchModel]
    themes: dict[str, Any]
    summary: dict[str, Any]
    sources: list[str]


class InterpretationResponse(AstrologyResponseModel):
    birth_chart: BirthChartResponse
    interpretation: InterpretationModel
    rule_pack: str
    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"rule_pack": "default_traditional"}]})


class KutaScoreModel(AstrologyResponseModel):
    name: str
    score: float
    max_score: float
    source: str
    notes: dict[str, Any]


class CompatibilityAnalysisModel(AstrologyResponseModel):
    total_gunas: float
    max_gunas: float
    grade: str
    bhakoot_favorable: bool
    nadi_favorable: bool
    kutas: list[KutaScoreModel]
    source_labels: list[str]
    doshas: dict[str, Any] = Field(default_factory=dict)
    mitigations: list[dict[str, Any]] = Field(default_factory=list)
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "grade": "very_good",
                    "total_gunas": 28.5,
                    "bhakoot_favorable": True,
                    "nadi_favorable": True,
                }
            ]
        },
    )


class CompatibilityResponse(AstrologyResponseModel):
    boy_chart: BirthChartResponse
    girl_chart: BirthChartResponse
    compatibility: CompatibilityAnalysisModel
    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"compatibility": {"grade": "very_good", "doshas": {"mangal": {"boy": False, "girl": False}}}}]})


class ScoreComponentModel(AstrologyResponseModel):
    name: str
    score: int
    max_score: int
    source: str
    notes: dict[str, Any]


class ScoreSummaryModel(AstrologyResponseModel):
    total: int
    max: int
    normalized: float
    components: list[ScoreComponentModel | dict[str, Any]]
    recommendations: list[str]


class TimeWindowModel(AstrologyResponseModel):
    start: str
    end: str
    source: str


class MuhurtaPanchangModel(AstrologyResponseModel):
    tithi: NamedIndexModel
    nakshatra: NamedIndexModel
    yoga: NamedIndexModel
    karana: NamedIndexModel
    sunrise: list[int]
    sunset: list[int]
    day_duration: list[int]


class MuhurtaDaySummaryModel(AstrologyResponseModel):
    is_favorable: bool
    activity_type: str
    midday_bonus: int
    profile: str | None = None


class MuhurtaDayResultModel(AstrologyResponseModel):
    date: str
    weekday_index: int
    weekday: str
    panchang: MuhurtaPanchangModel
    score: ScoreSummaryModel
    windows: dict[str, TimeWindowModel]
    avoid_windows: list[str]
    summary: MuhurtaDaySummaryModel


class MuhurtaInputModel(AstrologyResponseModel):
    date: _date | None = None
    start_date: _date | None = None
    end_date: _date | None = None
    activity_type: str
    minimum_score: int
    latitude: float | None = None
    longitude: float | None = None
    timezone: float | str | None = None
    timezone_name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class MuhurtaSummaryModel(AstrologyResponseModel):
    count: int
    best_score: int | None = None
    activity_type: str


class MuhurtaResponse(AstrologyResponseModel):
    input: MuhurtaInputModel
    results: list[MuhurtaDayResultModel]
    best_dates: list[MuhurtaDayResultModel]
    summary: MuhurtaSummaryModel
    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"summary": {"activity_type": "career"}}]})


class GuidanceItemModel(AstrologyResponseModel):
    label: str
    value: str
    status: str
    explanation: str


class GuidanceSectionModel(AstrologyResponseModel):
    id: str
    title: str
    shortDescription: str
    importance: str
    items: list[GuidanceItemModel]
    notes: list[str] = Field(default_factory=list)
    disclaimer: list[str] = Field(default_factory=list)
    cta: dict[str, Any] | None = None


class PersonalPanchangSummaryModel(AstrologyResponseModel):
    fullName: str
    birthDetails: str
    currentLocation: str
    todaySnapshot: str
    janmaNakshatra: str
    janmaRashi: str
    lagna: str
    nameLetters: str
    note: str


class PersonalPanchangGuidanceModel(AstrologyResponseModel):
    summary: PersonalPanchangSummaryModel
    sections: list[GuidanceSectionModel]
    analysis: dict[str, Any]
    generatedAtIso: str


class PanchangInputModel(AstrologyResponseModel):
    date: _date
    latitude: float
    longitude: float
    timezone: float
    timezone_name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    full_name: str | None = None
    birth_date: _date | None = None
    birth_time: str | None = None
    birth_time_unknown: bool | None = None
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


class PanchangDayModel(AstrologyResponseModel):
    Tithi: list[Any] | Any
    Nakshatra: list[Any] | Any
    Yoga: list[Any] | Any
    karana: list[Any] | Any
    Vaara: int | Any
    Sunrise: list[Any] | Any | None = None
    Sunset: list[Any] | Any | None = None
    day_duration: list[Any] | Any | None = Field(default=None, alias="Day Duration")


class PanchangResponse(AstrologyResponseModel):
    input: PanchangInputModel
    panchang: PanchangDayModel | dict[str, Any]
    guidance: PersonalPanchangGuidanceModel | None = None
    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [{"panchang": {"Vaara": 4}}]})


class AstrologyMetaResponse(AstrologyResponseModel):
    api_version: str
    selected_service_version: str
    engine_class: str
    available_versions: list[str]
    available_rule_packs: list[str]
    supported_endpoints: list[str]
    supported_dasha_levels: list[str]
    supported_vargas: list[str]
    supported_house_systems: list[str]
    supported_ayanamsas: list[str]
    cache_backend: str
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "api_version": "v1",
                    "selected_service_version": "v1",
                    "engine_class": "AstrologyService",
                    "available_versions": ["v1"],
                    "available_rule_packs": ["default_traditional", "strict_classical"],
                    "supported_endpoints": ["/birth-chart", "/dashas", "/divisional-charts"],
                    "supported_dasha_levels": ["mahadasha", "antardasha", "pratyantardasha", "sookshma", "prana"],
                    "supported_vargas": ["D1", "D2", "D3", "D4", "D7", "D9", "D10", "D12", "D16", "D20", "D24", "D30", "D60"],
                    "supported_house_systems": ["whole_sign"],
                    "supported_ayanamsas": ["lahiri"],
                    "cache_backend": "AstrologyResultCache",
                }
            ]
        },
    )


DashaPeriodModel.model_rebuild()
DashaTimelineModel.model_rebuild()
