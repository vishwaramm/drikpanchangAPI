"""Ashta-Kuta compatibility engine."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import PLANET_FRIENDS
from .core.base import AstrologyEngine


SIGN_VARNA = {
    0: "kshatriya",
    1: "vaishya",
    2: "shudra",
    3: "brahmin",
    4: "kshatriya",
    5: "vaishya",
    6: "kshatriya",
    7: "brahmin",
    8: "kshatriya",
    9: "vaishya",
    10: "shudra",
    11: "brahmin",
}

SIGN_LORD = {
    0: "Mars",
    1: "Venus",
    2: "Mercury",
    3: "Moon",
    4: "Sun",
    5: "Mercury",
    6: "Venus",
    7: "Mars",
    8: "Jupiter",
    9: "Saturn",
    10: "Saturn",
    11: "Jupiter",
}

VASHYA_GROUP = {
    0: "quadruped",
    1: "quadruped",
    2: "human",
    3: "human",
    4: "vanchar",
    5: "human",
    6: "human",
    7: "keet",
    8: "jalchar",
    9: "quadruped",
    10: "human",
    11: "jalchar",
}

NAKSHATRA_GANA = [
    "deva",
    "manushya",
    "rakshasa",
    "deva",
    "deva",
    "deva",
    "deva",
    "deva",
    "deva",
    "rakshasa",
    "manushya",
    "deva",
    "deva",
    "rakshasa",
    "rakshasa",
    "rakshasa",
    "deva",
    "rakshasa",
    "rakshasa",
    "manushya",
    "manushya",
    "deva",
    "manushya",
    "rakshasa",
    "deva",
    "deva",
    "deva",
]

NAKSHATRA_NADI = [
    "aadi",
    "madhya",
    "antya",
    "aadi",
    "aadi",
    "aadi",
    "aadi",
    "aadi",
    "aadi",
    "madhya",
    "madhya",
    "madhya",
    "madhya",
    "madhya",
    "madhya",
    "madhya",
    "aadi",
    "madhya",
    "aadi",
    "madhya",
    "aadi",
    "aadi",
    "antya",
    "antya",
    "antya",
    "antya",
    "antya",
]

NAKSHATRA_YONI = [
    "horse",
    "elephant",
    "sheep",
    "serpent",
    "serpent",
    "dog",
    "cat",
    "sheep",
    "cat",
    "rat",
    "rat",
    "cow",
    "buffalo",
    "tiger",
    "buffalo",
    "tiger",
    "deer",
    "deer",
    "dog",
    "monkey",
    "mongoose",
    "monkey",
    "lion",
    "lion",
    "horse",
    "elephant",
    "cow",
]

YONI_ENEMIES = {
    frozenset({"cow", "tiger"}),
    frozenset({"elephant", "lion"}),
    frozenset({"horse", "buffalo"}),
    frozenset({"dog", "hare"}),
    frozenset({"serpent", "mongoose"}),
    frozenset({"monkey", "goat"}),
    frozenset({"cat", "rat"}),
}

GANA_RELATIONSHIP = {
    ("deva", "deva"): 6,
    ("manushya", "manushya"): 6,
    ("rakshasa", "rakshasa"): 6,
    ("deva", "manushya"): 4,
    ("manushya", "deva"): 4,
    ("deva", "rakshasa"): 1,
    ("rakshasa", "deva"): 1,
    ("manushya", "rakshasa"): 2,
    ("rakshasa", "manushya"): 2,
}

VARNA_RANK = {
    "shudra": 0,
    "vaishya": 1,
    "kshatriya": 2,
    "brahmin": 3,
}

NADI_POINTS = 8
MANGAL_DOSHA_HOUSES = {1, 2, 4, 7, 8, 12}


@dataclass(frozen=True)
class KutaScore:
    name: str
    score: float
    max_score: float
    source: str
    notes: dict


def _moon_sign_index(chart: dict) -> int:
    moon = chart["planets"]["Moon"]
    return int(moon["sign_index"])


def _moon_nakshatra_index(chart: dict) -> int:
    moon = chart["planets"]["Moon"]
    return int(moon["nakshatra_index"])


def _sign_varna(sign_index: int) -> str:
    return SIGN_VARNA[sign_index]


def _sign_group(sign_index: int, degree: float) -> str:
    if sign_index in {4}:
        return "vanchar"
    if sign_index in {7}:
        return "keet"
    if sign_index in {2, 3, 5, 10, 11}:
        return "human"
    if sign_index in {0, 1, 9}:
        if sign_index == 9:
            return "quadruped" if degree < 15.0 else "jalchar"
        return "quadruped"
    if sign_index == 6:
        return "quadruped" if degree < 15.0 else "human"
    if sign_index == 8:
        return "jalchar"
    return VASHYA_GROUP[sign_index]


def _varna_score(boy_sign_index: int, girl_sign_index: int) -> KutaScore:
    boy = _sign_varna(boy_sign_index)
    girl = _sign_varna(girl_sign_index)
    if VARNA_RANK[boy] >= VARNA_RANK[girl]:
        score = 1.0
    else:
        score = 0.0
    return KutaScore(
        name="Varna",
        score=score,
        max_score=1.0,
        source="drikpanchang",
        notes={"boy_varna": boy, "girl_varna": girl},
    )


def _vashya_score(boy_sign_index: int, boy_degree: float, girl_sign_index: int, girl_degree: float) -> KutaScore:
    boy = _sign_group(boy_sign_index, boy_degree)
    girl = _sign_group(girl_sign_index, girl_degree)
    if boy == girl:
        score = 2.0
    elif frozenset({boy, girl}) in {frozenset({"human", "quadruped"}), frozenset({"human", "jalchar"})}:
        score = 1.5
    elif frozenset({boy, girl}) in {frozenset({"quadruped", "jalchar"}), frozenset({"human", "vanchar"})}:
        score = 1.0
    else:
        score = 0.5
    return KutaScore(
        name="Vashya",
        score=score,
        max_score=2.0,
        source="drikpanchang/traditional",
        notes={"boy_group": boy, "girl_group": girl},
    )


def _tara_count(source_nakshatra: int, target_nakshatra: int) -> int:
    return ((target_nakshatra - source_nakshatra) % 27) + 1


def _tara_is_favorable(count: int) -> bool:
    return count % 2 == 0


def _tara_score(boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
    forward = _tara_count(boy_nakshatra, girl_nakshatra)
    reverse = _tara_count(girl_nakshatra, boy_nakshatra)
    forward_ok = _tara_is_favorable(forward)
    reverse_ok = _tara_is_favorable(reverse)
    score = 3.0 if forward_ok and reverse_ok else 1.5 if forward_ok or reverse_ok else 0.0
    return KutaScore(
        name="Tara",
        score=score,
        max_score=3.0,
        source="traditional/best_judgment",
        notes={"forward_count": forward, "reverse_count": reverse},
    )


def _yoni_score(boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
    boy = NAKSHATRA_YONI[boy_nakshatra]
    girl = NAKSHATRA_YONI[girl_nakshatra]
    if boy == girl:
        score = 4.0
    elif frozenset({boy, girl}) in YONI_ENEMIES:
        score = 0.0
    else:
        score = 2.0
    return KutaScore(
        name="Yoni",
        score=score,
        max_score=4.0,
        source="traditional/best_judgment",
        notes={"boy_yoni": boy, "girl_yoni": girl},
    )


def _graha_maitri_score(boy_sign_index: int, girl_sign_index: int) -> KutaScore:
    boy_lord = SIGN_LORD[boy_sign_index]
    girl_lord = SIGN_LORD[girl_sign_index]
    if boy_lord == girl_lord:
        score = 5.0
        relation = "same"
    else:
        boy_friends = PLANET_FRIENDS[boy_lord]
        girl_friends = PLANET_FRIENDS[girl_lord]
        if girl_lord in boy_friends["friends"] and boy_lord in girl_friends["friends"]:
            score = 5.0
            relation = "mutual_friend"
        elif girl_lord in boy_friends["friends"] or boy_lord in girl_friends["friends"]:
            score = 4.0
            relation = "friend"
        elif girl_lord in boy_friends["neutral"] or boy_lord in girl_friends["neutral"]:
            score = 3.0
            relation = "neutral"
        else:
            score = 0.0
            relation = "enemy"
    return KutaScore(
        name="Graha Maitri",
        score=score,
        max_score=5.0,
        source="classical/traditional",
        notes={"boy_lord": boy_lord, "girl_lord": girl_lord, "relation": relation},
    )


def _reference_house(chart: dict, reference_planet: str, target_planet: str) -> int | None:
    if reference_planet == "ascendant":
        ref_sign_index = int(chart.get("ascendant", {}).get("sign_index", chart.get("ascendant", {}).get("sign_index", 0) or 0))
        tgt = chart.get("planets", {}).get(target_planet)
        if tgt is None:
            return None
        return ((int(tgt["sign_index"]) - ref_sign_index) % 12) + 1

    ref = chart.get("planets", {}).get(reference_planet)
    tgt = chart.get("planets", {}).get(target_planet)
    if ref is None or tgt is None:
        return None
    return ((int(tgt["sign_index"]) - int(ref["sign_index"])) % 12) + 1


def _mangal_dosha(chart: dict) -> bool:
    return any(
        _reference_house(chart, reference, "Mars") in MANGAL_DOSHA_HOUSES
        for reference in ("ascendant", "Moon", "Venus")
    )


def _mangal_dosha_cancellation(chart: dict) -> bool:
    mars = chart.get("planets", {}).get("Mars")
    if not mars:
        return False
    if mars.get("dignity") not in {"own", "exalted"}:
        return False
    return mars.get("house") in {1, 4, 7, 10}


def _mangal_dosha_strengthened(chart: dict) -> bool:
    mars = chart.get("planets", {}).get("Mars")
    if not mars:
        return False
    if mars.get("dignity") not in {"own", "exalted"}:
        return False
    return mars.get("house") in {1, 4, 7, 10}


def _gana_score(boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
    boy = NAKSHATRA_GANA[boy_nakshatra]
    girl = NAKSHATRA_GANA[girl_nakshatra]
    score = float(GANA_RELATIONSHIP.get((boy, girl), 0))
    return KutaScore(
        name="Gana",
        score=score,
        max_score=6.0,
        source="traditional/best_judgment",
        notes={"boy_gana": boy, "girl_gana": girl},
    )


def _bhakoot_score(boy_sign_index: int, girl_sign_index: int) -> KutaScore:
    distance = (girl_sign_index - boy_sign_index) % 12
    pair = frozenset({distance, (12 - distance) % 12})
    dosha_pairs = {frozenset({2, 10}), frozenset({5, 7}), frozenset({6, 8})}
    score = 0.0 if pair in dosha_pairs else 7.0
    return KutaScore(
        name="Bhakoot",
        score=score,
        max_score=7.0,
        source="traditional/best_judgment",
        notes={"sign_distance": distance},
    )


def _nadi_score(boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
    boy = NAKSHATRA_NADI[boy_nakshatra]
    girl = NAKSHATRA_NADI[girl_nakshatra]
    score = 0.0 if boy == girl else float(NADI_POINTS)
    return KutaScore(
        name="Nadi",
        score=score,
        max_score=8.0,
        source="traditional/best_judgment",
        notes={"boy_nadi": boy, "girl_nadi": girl},
    )


def _mangal_dosha_details(chart: dict) -> dict:
    mars = chart.get("planets", {}).get("Mars") or {}
    return {
        "active": _mangal_dosha(chart),
        "mitigated": _mangal_dosha_cancellation(chart) or _mangal_dosha_strengthened(chart),
        "house_from_ascendant": _reference_house(chart, "ascendant", "Mars"),
        "house_from_moon": _reference_house(chart, "Moon", "Mars"),
        "house_from_venus": _reference_house(chart, "Venus", "Mars"),
        "dignity": mars.get("dignity"),
        "house": mars.get("house"),
    }


def _compatibility_dosha_breakdown(boy_chart: dict, girl_chart: dict, bhakoot_ok: bool, nadi_ok: bool) -> tuple[dict, list[dict]]:
    boy_mangal = _mangal_dosha_details(boy_chart)
    girl_mangal = _mangal_dosha_details(girl_chart)
    boy_dosha = bool(boy_mangal["active"])
    girl_dosha = bool(girl_mangal["active"])
    both_active = boy_dosha and girl_dosha
    either_active = boy_dosha or girl_dosha

    mitigations: list[dict] = []
    if both_active:
        mitigations.append(
            {
                "name": "mangal_balance",
                "title": "Balanced Manglik pairing",
                "severity": "info",
                "details": {
                    "boy_manglik": True,
                    "girl_manglik": True,
                    "note": "Both partners carry Manglik influence, so the dosha is considered balanced rather than one-sided.",
                },
            }
        )
    elif either_active:
        mitigations.append(
            {
                "name": "mangal_mitigation",
                "title": "Manglik mitigation needed",
                "severity": "warning",
                "details": {
                    "boy_manglik": boy_dosha,
                    "girl_manglik": girl_dosha,
                    "boy_mitigated": bool(boy_mangal["mitigated"]),
                    "girl_mitigated": bool(girl_mangal["mitigated"]),
                },
            }
        )

    if not bhakoot_ok:
        mitigations.append(
            {
                "name": "bhakoot_remediation",
                "title": "Bhakoot dosha present",
                "severity": "warning",
                "details": {
                    "note": "The sign-distance pattern is traditionally considered challenging.",
                },
            }
        )

    if not nadi_ok:
        mitigations.append(
            {
                "name": "nadi_remediation",
                "title": "Nadi dosha present",
                "severity": "critical",
                "details": {
                    "note": "Same Nadi pairing is traditionally avoided in matchmaking.",
                },
            }
        )

    doshas = {
        "mangal": {
            "boy": boy_dosha,
            "girl": girl_dosha,
            "matched": both_active,
            "mitigated": bool(boy_mangal["mitigated"]) and bool(girl_mangal["mitigated"]),
            "concern": either_active and not both_active,
            "notes": {
                "boy": boy_mangal,
                "girl": girl_mangal,
            },
        },
        "bhakoot": {
            "favorable": bhakoot_ok,
            "concern": not bhakoot_ok,
            "notes": {
                "sign_distance": abs((girl_chart["planets"]["Moon"]["sign_index"] - boy_chart["planets"]["Moon"]["sign_index"]) % 12),
            },
        },
        "nadi": {
            "favorable": nadi_ok,
            "concern": not nadi_ok,
            "notes": {
                "boy_nadi": NAKSHATRA_NADI[int(boy_chart["planets"]["Moon"]["nakshatra_index"])],
                "girl_nadi": NAKSHATRA_NADI[int(girl_chart["planets"]["Moon"]["nakshatra_index"])],
            },
        },
    }
    return doshas, mitigations


def _grade(total: float, bhakoot_ok: bool, nadi_ok: bool) -> str:
    if not nadi_ok and total >= 28:
        return "inauspicious"
    if bhakoot_ok:
        if total >= 31:
            return "excellent"
        if total >= 21:
            return "very_good"
        if total >= 17:
            return "middling"
        return "inauspicious"
    if total >= 30:
        return "very_good"
    if total >= 21:
        return "middling"
    return "inauspicious"


class AshtakutaCompatibilityEngine(AstrologyEngine):
    def calculate(self, payload: dict, boy_chart: dict | None = None, girl_chart: dict | None = None) -> dict:
        if boy_chart is None:
            boy_chart = payload.get("boy_chart") if isinstance(payload, dict) else None
        if girl_chart is None:
            girl_chart = payload.get("girl_chart") if isinstance(payload, dict) else None
        if not isinstance(boy_chart, dict) or not isinstance(girl_chart, dict):
            raise ValueError("boy_chart and girl_chart are required")
        return self.calculate_from_charts(boy_chart, girl_chart)

    def varna_score(self, boy_sign_index: int, girl_sign_index: int) -> KutaScore:
        return _varna_score(boy_sign_index, girl_sign_index)

    def vashya_score(self, boy_sign_index: int, boy_degree: float, girl_sign_index: int, girl_degree: float) -> KutaScore:
        return _vashya_score(boy_sign_index, boy_degree, girl_sign_index, girl_degree)

    def tara_score(self, boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
        return _tara_score(boy_nakshatra, girl_nakshatra)

    def yoni_score(self, boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
        return _yoni_score(boy_nakshatra, girl_nakshatra)

    def graha_maitri_score(self, boy_sign_index: int, girl_sign_index: int) -> KutaScore:
        return _graha_maitri_score(boy_sign_index, girl_sign_index)

    def gana_score(self, boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
        return _gana_score(boy_nakshatra, girl_nakshatra)

    def bhakoot_score(self, boy_sign_index: int, girl_sign_index: int) -> KutaScore:
        return _bhakoot_score(boy_sign_index, girl_sign_index)

    def nadi_score(self, boy_nakshatra: int, girl_nakshatra: int) -> KutaScore:
        return _nadi_score(boy_nakshatra, girl_nakshatra)

    def calculate_from_charts(self, boy_chart: dict, girl_chart: dict) -> dict:
        boy_moon = boy_chart["planets"]["Moon"]
        girl_moon = girl_chart["planets"]["Moon"]

        boy_sign_index = int(boy_moon["sign_index"])
        girl_sign_index = int(girl_moon["sign_index"])
        boy_degree = float(boy_moon["degree_in_sign"])
        girl_degree = float(girl_moon["degree_in_sign"])
        boy_nakshatra = int(boy_moon["nakshatra_index"])
        girl_nakshatra = int(girl_moon["nakshatra_index"])

        kutas = [
            self.varna_score(boy_sign_index, girl_sign_index),
            self.vashya_score(boy_sign_index, boy_degree, girl_sign_index, girl_degree),
            self.tara_score(boy_nakshatra, girl_nakshatra),
            self.yoni_score(boy_nakshatra, girl_nakshatra),
            self.graha_maitri_score(boy_sign_index, girl_sign_index),
            self.gana_score(boy_nakshatra, girl_nakshatra),
            self.bhakoot_score(boy_sign_index, girl_sign_index),
            self.nadi_score(boy_nakshatra, girl_nakshatra),
        ]
        total = sum(kuta.score for kuta in kutas)
        bhakoot_ok = kutas[6].score > 0
        nadi_ok = kutas[7].score > 0
        doshas, mitigations = _compatibility_dosha_breakdown(boy_chart, girl_chart, bhakoot_ok, nadi_ok)
        return {
            "total_gunas": total,
            "max_gunas": 36.0,
            "grade": _grade(total, bhakoot_ok, nadi_ok),
            "bhakoot_favorable": bhakoot_ok,
            "nadi_favorable": nadi_ok,
            "doshas": doshas,
            "mitigations": mitigations,
            "kutas": [
                {
                    "name": kuta.name,
                    "score": kuta.score,
                    "max_score": kuta.max_score,
                    "source": kuta.source,
                    "notes": kuta.notes,
                }
                for kuta in kutas
            ],
            "source_labels": sorted({kuta.source for kuta in kutas}),
        }


DEFAULT_COMPATIBILITY_ENGINE = AshtakutaCompatibilityEngine()


def calculate_ashtakuta_from_charts(boy_chart: dict, girl_chart: dict) -> dict:
    return DEFAULT_COMPATIBILITY_ENGINE.calculate_from_charts(boy_chart, girl_chart)
