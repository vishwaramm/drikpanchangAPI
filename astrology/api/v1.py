"""Versioned v1 router for the astrology API."""

from __future__ import annotations

from ..http import create_router

router = create_router(version="v1")

__all__ = ["router", "create_router"]

