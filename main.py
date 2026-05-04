"""Primary FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from astrology.api.v1 import router as astrology_router
from legacy_http import router as legacy_router

app = FastAPI(title="Drik Panchang Astrology API", version="1.0.0")
app.include_router(astrology_router)
app.include_router(legacy_router)


@app.get("/health")
def health():
    return {"status": "ok"}
