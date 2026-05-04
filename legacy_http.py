"""FastAPI router for the legacy panchang and naming endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

import legacy_panchanga
from astrology.service import DEFAULT_ASTROLOGY_SERVICE

router = APIRouter(tags=["legacy"])


async def _payload_from_request(request: Request) -> dict:
    data: dict = dict(request.query_params)
    if request.method in {"POST", "PUT", "PATCH"}:
        body = await request.body()
        if body:
            parsed = json.loads(body.decode("utf-8"))
            if isinstance(parsed, dict):
                data.update(parsed)
    return data


def _detail_from_exception(exc: ValueError) -> str:
    value = exc.args[0] if exc.args else str(exc)
    if isinstance(value, dict):
        return value.get("message", str(value))
    return str(value)


@router.get("/api/v1/panchang")
async def get_panchang(request: Request):
    try:
        payload = await _payload_from_request(request)
        return DEFAULT_ASTROLOGY_SERVICE.build_panchang(payload)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing required field: {exc.args[0]}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/v1/drik/functions")
def get_available_functions():
    return {"functions": legacy_panchanga.list_drik_functions()}


@router.get("/api/v1/cities")
async def get_cities(request: Request):
    try:
        payload = await _payload_from_request(request)
        return legacy_panchanga.get_cities(str(payload.get("country", "")).strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/v1/drik/{function_name}")
@router.post("/api/v1/drik/{function_name}")
async def call_drik_function(function_name: str, request: Request):
    try:
        payload = await _payload_from_request(request)
        return {"function": function_name, "result": legacy_panchanga.call_drik_function(function_name, payload)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail_from_exception(exc))
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid payload: {exc}")


@router.get("/api/v1/naming/letters")
@router.post("/api/v1/naming/letters")
async def get_name_letters(request: Request):
    try:
        payload = await _payload_from_request(request)
        return legacy_panchanga.get_name_letters(payload)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing required field: {exc.args[0]}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/v1/naming/letters/by-city")
@router.post("/api/v1/naming/letters/by-city")
async def get_name_letters_by_city(request: Request):
    try:
        payload = await _payload_from_request(request)
        return legacy_panchanga.get_name_letters_by_city(payload)
    except ValueError as exc:
        value = exc.args[0] if exc.args else str(exc)
        if isinstance(value, dict):
            raise HTTPException(status_code=400, detail=value.get("message", "invalid city input"))
        raise HTTPException(status_code=400, detail=str(exc))
