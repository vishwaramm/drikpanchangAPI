"""FastAPI router factory for the astrology engine."""

from __future__ import annotations

import json
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from .registry import AstrologyEngineRegistry, DEFAULT_ASTROLOGY_REGISTRY
from .schemas import (
    BirthChartPayload,
    AstrologyMetaPayload,
    CompatibilityPayload,
    DashasPayload,
    DivisionalChartsPayload,
    InterpretationPayload,
    MuhurtaPayload,
    PanchangPayload,
    TransitsPayload,
)
from .responses import (
    BirthChartResponse,
    AstrologyMetaResponse,
    CompatibilityResponse,
    DashasResponse,
    DivisionalChartsResponse,
    InterpretationResponse,
    MuhurtaResponse,
    PanchangResponse,
    TransitsResponse,
)
from .service import AstrologyService, DEFAULT_ASTROLOGY_SERVICE


@dataclass(frozen=True)
class _EndpointSpec:
    path: str
    payload_model: type
    response_model: type
    service_method: str


def _http_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


async def _payload_from_request(request: Request) -> dict:
    data: dict = dict(request.query_params)
    if request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        if body:
            parsed = json.loads(body.decode("utf-8"))
            if isinstance(parsed, dict):
                data.update(parsed)
    return data


def _validated_payload(model_cls, payload: dict) -> dict:
    try:
        return model_cls.model_validate(payload).model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors())


def _resolve_service(
    request: Request,
    default_service: AstrologyService,
    registry: AstrologyEngineRegistry | None = None,
    version: str | None = None,
) -> AstrologyService:
    if registry is None:
        return default_service
    requested_version = version or request.query_params.get("version") or request.headers.get("x-astrology-version")
    if requested_version:
        try:
            return registry.get(str(requested_version))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    return default_service


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


def _register_endpoint(router: APIRouter, spec: _EndpointSpec, service: AstrologyService, registry: AstrologyEngineRegistry, version: str | None):
    async def handler(request: Request):
        try:
            raw_payload = await _payload_from_request(request)
            payload = _validated_payload(spec.payload_model, raw_payload)
            requested_version = version or request.query_params.get("version") or request.headers.get("x-astrology-version")
            resolved_service = _resolve_service(request, service, registry, version)
            payload["version"] = requested_version or version or registry.default_version
            method = getattr(resolved_service, spec.service_method)
            return method(payload)
        except ValueError as exc:
            raise _http_error(exc)

    handler.__name__ = f"{spec.service_method}_{spec.path.strip('/').replace('/', '_')}"
    router.add_api_route(spec.path, handler, methods=["GET", "POST"], response_model=spec.response_model, tags=["astrology"])


def create_router(
    service: AstrologyService | None = None,
    registry: AstrologyEngineRegistry | None = None,
    version: str | None = None,
) -> APIRouter:
    """Build a router backed by a specific astrology service instance."""

    registry = registry or DEFAULT_ASTROLOGY_REGISTRY
    service = service or registry.get(version)
    router = APIRouter(prefix="/api/v1/astrology", tags=["astrology"])

    specs = [
        _EndpointSpec("/birth-chart", BirthChartPayload, BirthChartResponse, "build_birth_chart"),
        _EndpointSpec("/dashas", DashasPayload, DashasResponse, "build_dashas"),
        _EndpointSpec("/divisional-charts", DivisionalChartsPayload, DivisionalChartsResponse, "build_divisional_charts"),
        _EndpointSpec("/transits", TransitsPayload, TransitsResponse, "build_transits"),
        _EndpointSpec("/interpretation", InterpretationPayload, InterpretationResponse, "build_interpretation"),
        _EndpointSpec("/compatibility", CompatibilityPayload, CompatibilityResponse, "build_compatibility"),
        _EndpointSpec("/muhurta", MuhurtaPayload, MuhurtaResponse, "build_muhurta"),
        _EndpointSpec("/panchang", PanchangPayload, PanchangResponse, "build_panchang"),
        _EndpointSpec("/meta", AstrologyMetaPayload, AstrologyMetaResponse, "build_meta"),
    ]

    for spec in specs:
        _register_endpoint(router, spec, service, registry, version)

    return router


router = create_router()
