"""Shared base classes for astrology engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AstrologyEngine(ABC):
    """Abstract base class for swappable astrology calculators."""

    @abstractmethod
    def calculate(self, *args: Any, **kwargs: Any) -> dict:
        raise NotImplementedError

