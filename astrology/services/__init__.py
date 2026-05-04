"""Service namespace for orchestration, registry, and rule-pack composition."""

from __future__ import annotations

from ..cache import AstrologyResultCache, FileAstrologyResultCache
from ..registry import AstrologyEngineRegistry, DEFAULT_ASTROLOGY_REGISTRY
from ..rulepacks import DEFAULT_RULE_PACK, DEFAULT_RULE_PACK_REGISTRY, RulePack, RulePackRegistry
from ..service import AstrologyService, DEFAULT_ASTROLOGY_SERVICE, build_meta

__all__ = [
    "AstrologyEngineRegistry",
    "AstrologyResultCache",
    "FileAstrologyResultCache",
    "DEFAULT_ASTROLOGY_REGISTRY",
    "DEFAULT_ASTROLOGY_SERVICE",
    "DEFAULT_RULE_PACK",
    "DEFAULT_RULE_PACK_REGISTRY",
    "AstrologyService",
    "build_meta",
    "RulePack",
    "RulePackRegistry",
]
