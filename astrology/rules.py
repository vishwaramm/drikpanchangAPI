"""Interpretation and rule engine.

The rule set is intentionally data-driven. For each rule we store a source label
so we can trace which definitions are based on Drik Panchang and which ones use
common classical practice or best judgment where a published threshold is not
available.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from .constants import SIGN_NAMES
from .utils import angular_distance, normalize_angle, sign_index_from_longitude, whole_sign_house_number

MANGAL_DOSHA_HOUSES = {1, 2, 4, 7, 8, 12}
KALASARPA_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
KENDRA_HOUSES = {1, 4, 7, 10}


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    category: str
    title: str
    source: str
    evaluator: Callable[[dict], bool]
    base_score: int = 5
    priority: int = 0
    cancels: tuple[str, ...] = ()


class RuleCatalog(ABC):
    """Container for a swappable set of rules."""

    @abstractmethod
    def get_rules(self) -> list[RuleDefinition]:
        raise NotImplementedError


class StaticRuleCatalog(RuleCatalog):
    def __init__(self, rules: list[RuleDefinition]):
        self._rules = tuple(rules)

    def get_rules(self) -> list[RuleDefinition]:
        return list(self._rules)


class RuleEngine:
    """Evaluate chart interpretation rules from an injected catalog."""

    def __init__(self, catalog: RuleCatalog | None = None):
        self.catalog = catalog or StaticRuleCatalog(DEFAULT_RULES)

    def interpret(self, chart: dict) -> dict:
        rules = self.catalog.get_rules()
        evaluations: list[tuple[RuleDefinition, bool]] = []
        matches = []
        themes = {}
        matched_by_id: dict[str, RuleDefinition] = {}
        for rule in rules:
            matched = bool(rule.evaluator(chart))
            evaluations.append((rule, matched))
            if matched:
                matched_by_id[rule.rule_id] = rule

        suppressed: set[str] = set()
        for rule, matched in evaluations:
            if not matched:
                continue
            for target_rule_id in rule.cancels:
                target = matched_by_id.get(target_rule_id)
                if target is not None and target.priority <= rule.priority:
                    suppressed.add(target_rule_id)

        for rule in rules:
            if rule.rule_id not in matched_by_id or rule.rule_id in suppressed:
                continue
            matches.append(
                {
                    "rule_id": rule.rule_id,
                    "category": rule.category,
                    "title": rule.title,
                    "source": rule.source,
                    "score": rule.base_score,
                }
            )
            theme = themes.setdefault(rule.category, {"score": 0, "rules": []})
            theme["score"] += rule.base_score
            theme["rules"].append(rule.rule_id)

        if chart.get("ascendant"):
            asc = chart["ascendant"]
            themes.setdefault("identity", {"score": 0, "rules": []})["notes"] = {
                "ascendant_sign": asc.get("sign"),
            }

        return {
            "matches": matches,
            "suppressed": sorted(suppressed),
            "themes": themes,
            "summary": {
                "match_count": len(matches),
                "suppressed_count": len(suppressed),
                "categories": sorted(themes.keys()),
            },
            "sources": sorted({rule.source for rule in rules}),
        }

    def with_catalog(self, catalog: RuleCatalog) -> "RuleEngine":
        return RuleEngine(catalog)


def _planet(chart: dict, name: str):
    return chart.get("planets", {}).get(name)


def _sign_index_from_ascendant(chart: dict) -> int | None:
    ascendant = chart.get("ascendant") or {}
    if "sign_index" in ascendant and ascendant["sign_index"] is not None:
        return int(ascendant["sign_index"])
    sign = ascendant.get("sign")
    if isinstance(sign, str) and sign in SIGN_NAMES:
        return SIGN_NAMES.index(sign)
    return None


def _house_planets(chart: dict, house_number: int) -> list[str]:
    return [name for name, planet in chart.get("planets", {}).items() if planet.get("house") == house_number]


def _reference_house(chart: dict, reference_planet: str, target_planet: str) -> int | None:
    if reference_planet == "ascendant":
        ref_sign_index = _sign_index_from_ascendant(chart)
        tgt = _planet(chart, target_planet)
        if ref_sign_index is None or not tgt:
            return None
        return whole_sign_house_number(ref_sign_index, tgt["sign_index"])

    ref = _planet(chart, reference_planet)
    tgt = _planet(chart, target_planet)
    if not ref or not tgt:
        return None
    return whole_sign_house_number(ref["sign_index"], tgt["sign_index"])


def _conjunction(chart: dict, a: str, b: str, orb: float) -> bool:
    pa = _planet(chart, a)
    pb = _planet(chart, b)
    if not pa or not pb:
        return False
    return angular_distance(pa["sidereal_longitude"], pb["sidereal_longitude"]) <= orb


def _is_combust(chart: dict, planet_name: str) -> bool:
    planet = _planet(chart, planet_name)
    if not planet:
        return False
    combustion = planet.get("combustion")
    if isinstance(combustion, dict):
        return bool(combustion.get("is_combust"))
    return bool(combustion)


def _gajakesari(chart: dict) -> bool:
    moon = _planet(chart, "Moon")
    jupiter = _planet(chart, "Jupiter")
    if not moon or not jupiter:
        return False
    return whole_sign_house_number(moon["sign_index"], jupiter["sign_index"]) in {1, 4, 7, 10}


def _gajakesari_cancellation(chart: dict) -> bool:
    moon = _planet(chart, "Moon")
    jupiter = _planet(chart, "Jupiter")
    if not moon or not jupiter:
        return False
    if moon.get("dignity") == "debilitated" or jupiter.get("dignity") == "debilitated":
        return True
    if moon.get("house") in {6, 8, 12} or jupiter.get("house") in {6, 8, 12}:
        return True
    if _is_combust(chart, "Jupiter"):
        return True
    return False


def _budhaditya(chart: dict) -> bool:
    # Drik Panchang describes Budhaditya Yoga as Mercury combining with Sun.
    # The orb threshold is not stated on the page, so we use a conservative 10°.
    return _conjunction(chart, "Sun", "Mercury", 10.0)


def _budhaditya_cancellation(chart: dict) -> bool:
    mercury = _planet(chart, "Mercury")
    if not mercury:
        return False
    if mercury.get("dignity") == "debilitated":
        return True
    if _is_combust(chart, "Mercury"):
        return True
    if mercury.get("house") in {6, 8, 12}:
        return True
    return False


def _mangal_dosha(chart: dict) -> bool:
    # Drik Panchang checks Lagna, Moon and Venus charts.
    # We treat a chart as Manglik if Mars falls in a classic Mangal Dosha house
    # from any of those three reference points.
    return any(
        _reference_house(chart, reference, "Mars") in MANGAL_DOSHA_HOUSES
        for reference in ("ascendant", "Moon", "Venus")
    )


def _chandra_mangala(chart: dict) -> bool:
    # Classical usage treats Moon-Mars association as the core signal.
    return _conjunction(chart, "Moon", "Mars", 8.0)


def _chandra_mangala_cancellation(chart: dict) -> bool:
    moon = _planet(chart, "Moon")
    mars = _planet(chart, "Mars")
    if not moon or not mars:
        return False
    if moon.get("dignity") == "debilitated" or mars.get("dignity") == "debilitated":
        return True
    if moon.get("house") in {6, 8, 12} or mars.get("house") in {6, 8, 12}:
        return True
    if _is_combust(chart, "Mars"):
        return True
    return False


def _mangal_dosha_cancellation(chart: dict) -> bool:
    mars = _planet(chart, "Mars")
    if not mars:
        return False
    if mars.get("dignity") not in {"own", "exalted"}:
        return False
    return mars.get("house") in KENDRA_HOUSES


def _mangal_dosha_strengthened(chart: dict) -> bool:
    mars = _planet(chart, "Mars")
    if not mars:
        return False
    if mars.get("dignity") not in {"own", "exalted"}:
        return False
    return mars.get("house") in {1, 4, 7, 10}


def _planet_in_kendra_and_dignified(chart: dict, planet_name: str) -> bool:
    planet = _planet(chart, planet_name)
    if not planet:
        return False
    if planet.get("house") not in KENDRA_HOUSES:
        return False
    return planet.get("dignity") in {"own", "exalted"}


def _mahapurusha_cancellation(chart: dict, planet_name: str) -> bool:
    planet = _planet(chart, planet_name)
    if not planet:
        return False
    if planet.get("dignity") == "debilitated":
        return True
    if _is_combust(chart, planet_name):
        return True
    if planet.get("house") in {6, 8, 12}:
        return True
    return False


def _kalasarpa(chart: dict) -> bool:
    # Drik Panchang defines Kala Sarpa when all seven planets are on one side
    # of the Rahu-Ketu axis. Partial Kala Sarpa is intentionally not counted.
    rahu = _planet(chart, "Rahu")
    ketu = _planet(chart, "Ketu")
    if not rahu or not ketu:
        return False

    rahu_long = normalize_angle(rahu["sidereal_longitude"])
    ketu_long = normalize_angle(ketu["sidereal_longitude"])
    if abs(((ketu_long - rahu_long) % 360.0) - 180.0) > 0.1:
        return False

    offsets = []
    for planet_name in KALASARPA_PLANETS:
        planet = _planet(chart, planet_name)
        if not planet:
            return False
        offset = (normalize_angle(planet["sidereal_longitude"]) - rahu_long) % 360.0
        if offset == 0.0 or offset == 180.0:
            continue
        offsets.append(offset)

    if not offsets:
        return False
    return all(0.0 < offset < 180.0 for offset in offsets) or all(180.0 < offset < 360.0 for offset in offsets)


def _kalasarpa_cancellation(chart: dict) -> bool:
    moon = _planet(chart, "Moon")
    jupiter = _planet(chart, "Jupiter")
    if not moon or not jupiter:
        return False
    if moon.get("dignity") in {"own", "exalted"} and moon.get("house") in KENDRA_HOUSES:
        return True
    if jupiter.get("dignity") in {"own", "exalted"} and jupiter.get("house") in KENDRA_HOUSES:
        return True
    return False


def _career_strength(chart: dict) -> bool:
    return any(
        chart.get("planets", {}).get(name, {}).get("house") in {1, 4, 7, 10} or name in _house_planets(chart, 10)
        for name in ("Sun", "Saturn", "Jupiter")
    )


def _finance_strength(chart: dict) -> bool:
    return bool({"Jupiter", "Venus", "Mercury"} & set(_house_planets(chart, 2) + _house_planets(chart, 11)))


def _education_strength(chart: dict) -> bool:
    return bool({"Mercury", "Jupiter"} & set(_house_planets(chart, 4) + _house_planets(chart, 5)))


def _marriage_strength(chart: dict) -> bool:
    return bool({"Venus", "Moon", "Jupiter"} & set(_house_planets(chart, 7)))


def _relocation_strength(chart: dict) -> bool:
    return bool({"Rahu", "Ketu"} & set(_house_planets(chart, 4) + _house_planets(chart, 12)))


def _mahapurusha_rule(planet_name: str) -> Callable[[dict], bool]:
    return lambda chart: _planet_in_kendra_and_dignified(chart, planet_name)


def _mahapurusha_cancellation_rule(planet_name: str) -> Callable[[dict], bool]:
    return lambda chart: _mahapurusha_cancellation(chart, planet_name)


DEFAULT_RULES = [
    RuleDefinition(
        "gajakesari_yoga",
        "yoga",
        "Gaja Kesari Yoga",
        "drikpanchang/common classical practice",
        _gajakesari,
        8,
    ),
    RuleDefinition(
        "gajakesari_cancellation",
        "yoga",
        "Gaja Kesari Cancellation",
        "classical/traditional",
        _gajakesari_cancellation,
        0,
        9,
        ("gajakesari_yoga",),
    ),
    RuleDefinition(
        "budhaditya_yoga",
        "yoga",
        "Budhaditya Yoga",
        "drikpanchang",
        _budhaditya,
        6,
    ),
    RuleDefinition(
        "budhaditya_cancellation",
        "yoga",
        "Budhaditya Cancellation",
        "classical/traditional",
        _budhaditya_cancellation,
        0,
        9,
        ("budhaditya_yoga",),
    ),
    RuleDefinition(
        "mangal_dosha",
        "dosha",
        "Mangal Dosha",
        "drikpanchang",
        _mangal_dosha,
        7,
        5,
        (),
    ),
    RuleDefinition(
        "mangal_dosha_cancellation",
        "dosha",
        "Mangal Dosha Cancellation",
        "classical/traditional",
        _mangal_dosha_cancellation,
        0,
        10,
        ("mangal_dosha",),
    ),
    RuleDefinition(
        "mangal_dosha_strengthened",
        "dosha",
        "Mangal Dosha Strengthened",
        "classical/traditional",
        _mangal_dosha_strengthened,
        0,
        11,
        ("mangal_dosha",),
    ),
    RuleDefinition(
        "kalasarpa_yoga",
        "dosha",
        "Kalasarpa Yoga",
        "drikpanchang",
        _kalasarpa,
        8,
        4,
    ),
    RuleDefinition(
        "kalasarpa_cancellation",
        "dosha",
        "Kalasarpa Cancellation",
        "classical/traditional",
        _kalasarpa_cancellation,
        0,
        9,
        ("kalasarpa_yoga",),
    ),
    RuleDefinition(
        "chandra_mangala_yoga",
        "yoga",
        "Chandra Mangala Yoga",
        "classical/traditional",
        _chandra_mangala,
        5,
        3,
    ),
    RuleDefinition(
        "chandra_mangala_cancellation",
        "yoga",
        "Chandra Mangala Cancellation",
        "classical/traditional",
        _chandra_mangala_cancellation,
        0,
        8,
        ("chandra_mangala_yoga",),
    ),
    RuleDefinition(
        "ruchaka_yoga",
        "yoga",
        "Ruchaka Yoga",
        "classical/traditional",
        _mahapurusha_rule("Mars"),
        8,
        4,
    ),
    RuleDefinition(
        "ruchaka_cancellation",
        "yoga",
        "Ruchaka Cancellation",
        "classical/traditional",
        _mahapurusha_cancellation_rule("Mars"),
        0,
        8,
        ("ruchaka_yoga",),
    ),
    RuleDefinition(
        "bhadra_yoga",
        "yoga",
        "Bhadra Yoga",
        "classical/traditional",
        _mahapurusha_rule("Mercury"),
        8,
        4,
    ),
    RuleDefinition(
        "bhadra_cancellation",
        "yoga",
        "Bhadra Cancellation",
        "classical/traditional",
        _mahapurusha_cancellation_rule("Mercury"),
        0,
        8,
        ("bhadra_yoga",),
    ),
    RuleDefinition(
        "hamsa_yoga",
        "yoga",
        "Hamsa Yoga",
        "classical/traditional",
        _mahapurusha_rule("Jupiter"),
        8,
        4,
    ),
    RuleDefinition(
        "hamsa_cancellation",
        "yoga",
        "Hamsa Cancellation",
        "classical/traditional",
        _mahapurusha_cancellation_rule("Jupiter"),
        0,
        8,
        ("hamsa_yoga",),
    ),
    RuleDefinition(
        "malavya_yoga",
        "yoga",
        "Malavya Yoga",
        "classical/traditional",
        _mahapurusha_rule("Venus"),
        8,
        4,
    ),
    RuleDefinition(
        "malavya_cancellation",
        "yoga",
        "Malavya Cancellation",
        "classical/traditional",
        _mahapurusha_cancellation_rule("Venus"),
        0,
        8,
        ("malavya_yoga",),
    ),
    RuleDefinition(
        "sasa_yoga",
        "yoga",
        "Sasa Yoga",
        "classical/traditional",
        _mahapurusha_rule("Saturn"),
        8,
        4,
    ),
    RuleDefinition(
        "sasa_cancellation",
        "yoga",
        "Sasa Cancellation",
        "classical/traditional",
        _mahapurusha_cancellation_rule("Saturn"),
        0,
        8,
        ("sasa_yoga",),
    ),
    RuleDefinition(
        "career_strength",
        "career",
        "Career Signal",
        "best_judgment",
        _career_strength,
        7,
        1,
    ),
    RuleDefinition(
        "finance_strength",
        "finance",
        "Finance Signal",
        "best_judgment",
        _finance_strength,
        6,
        1,
    ),
    RuleDefinition(
        "marriage_strength",
        "marriage",
        "Marriage Signal",
        "best_judgment",
        _marriage_strength,
        6,
        1,
    ),
    RuleDefinition(
        "education_strength",
        "education",
        "Education Signal",
        "best_judgment",
        _education_strength,
        6,
        1,
    ),
    RuleDefinition(
        "relocation_strength",
        "relocation",
        "Relocation Signal",
        "best_judgment",
        _relocation_strength,
        5,
        1,
    ),
]


DEFAULT_RULE_CATALOG = StaticRuleCatalog(DEFAULT_RULES)
DEFAULT_RULE_ENGINE = RuleEngine(DEFAULT_RULE_CATALOG)


def interpret_chart(chart: dict, rules: list[RuleDefinition] | None = None, engine: RuleEngine | None = None) -> dict:
    if engine is not None:
        return engine.interpret(chart)
    if rules is not None:
        return RuleEngine(StaticRuleCatalog(rules)).interpret(chart)
    return DEFAULT_RULE_ENGINE.interpret(chart)
