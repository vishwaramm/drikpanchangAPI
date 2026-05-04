"""Named rule packs for swapping astrology policy bundles."""

from __future__ import annotations

from dataclasses import dataclass, field

from .rules import DEFAULT_RULES, RuleCatalog, StaticRuleCatalog


@dataclass(frozen=True)
class RulePack:
    name: str
    catalog: RuleCatalog
    description: str = ""
    source_tags: tuple[str, ...] = ()


def build_default_rule_pack() -> RulePack:
    return RulePack(
        name="default_traditional",
        catalog=StaticRuleCatalog(DEFAULT_RULES),
        description="Default mixed-source traditional rule pack",
        source_tags=("drikpanchang", "classical", "best_judgment"),
    )


def build_classical_core_rule_pack() -> RulePack:
    rules = [rule for rule in DEFAULT_RULES if rule.category in {"yoga", "dosha"} and rule.source != "best_judgment"]
    return RulePack(
        name="classical_core",
        catalog=StaticRuleCatalog(rules),
        description="Traditional yoga and dosha pack using explicit classical rules",
        source_tags=("drikpanchang", "classical"),
    )


def build_life_theme_rule_pack() -> RulePack:
    rules = [rule for rule in DEFAULT_RULES if rule.category in {"career", "finance", "marriage", "education", "relocation"}]
    return RulePack(
        name="life_themes",
        catalog=StaticRuleCatalog(rules),
        description="Lightweight interpretation pack for life-theme analysis",
        source_tags=("best_judgment",),
    )


def build_strict_classical_rule_pack() -> RulePack:
    rules = [rule for rule in DEFAULT_RULES if rule.source != "best_judgment"]
    return RulePack(
        name="strict_classical",
        catalog=StaticRuleCatalog(rules),
        description="Strict source-backed yoga and dosha pack",
        source_tags=("drikpanchang", "classical"),
    )


def build_extended_interpretive_rule_pack() -> RulePack:
    rules = list(DEFAULT_RULES)
    return RulePack(
        name="extended_interpretive",
        catalog=StaticRuleCatalog(rules),
        description="Full default pack including life-theme rules",
        source_tags=("drikpanchang", "classical", "best_judgment"),
    )


@dataclass
class RulePackRegistry:
    _packs: dict[str, RulePack] = field(default_factory=dict)
    default_pack_name: str = "default_traditional"

    def __post_init__(self) -> None:
        if self.default_pack_name not in self._packs:
            self._packs[self.default_pack_name] = build_default_rule_pack()
        for pack in (
            build_classical_core_rule_pack(),
            build_life_theme_rule_pack(),
            build_strict_classical_rule_pack(),
            build_extended_interpretive_rule_pack(),
        ):
            self._packs.setdefault(pack.name, pack)

    def register(self, pack: RulePack) -> None:
        self._packs[pack.name] = pack

    def get(self, name: str | None = None) -> RulePack:
        resolved = name or self.default_pack_name
        if resolved not in self._packs:
            raise KeyError(f"unknown rule pack: {resolved}")
        return self._packs[resolved]

    def list(self) -> list[str]:
        return sorted(self._packs)


DEFAULT_RULE_PACK = build_default_rule_pack()
DEFAULT_RULE_PACK_REGISTRY = RulePackRegistry()
