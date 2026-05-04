"""Registry for swapping astrology service bundles by API version or policy."""

from __future__ import annotations

from dataclasses import dataclass, field

from .service import AstrologyService, DEFAULT_ASTROLOGY_SERVICE


@dataclass
class AstrologyEngineRegistry:
    _services: dict[str, AstrologyService] = field(default_factory=dict)
    default_version: str = "v1"

    def __post_init__(self) -> None:
        if self.default_version not in self._services:
            self._services[self.default_version] = DEFAULT_ASTROLOGY_SERVICE

    def register(self, version: str, service: AstrologyService) -> None:
        self._services[version] = service

    def get(self, version: str | None = None) -> AstrologyService:
        resolved = version or self.default_version
        if resolved not in self._services:
            raise KeyError(f"unknown astrology engine version: {resolved}")
        return self._services[resolved]

    def versions(self) -> list[str]:
        return sorted(self._services)


DEFAULT_ASTROLOGY_REGISTRY = AstrologyEngineRegistry()

