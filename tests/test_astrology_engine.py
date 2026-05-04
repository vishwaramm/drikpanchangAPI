import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile

from astrology.birth_chart import calculate_birth_chart
from astrology.engines.birth_chart import DEFAULT_BIRTH_CHART_ENGINE
from astrology.engines.panchang import DEFAULT_PANCHANG_ENGINE
from astrology.core.base import AstrologyEngine
from astrology.core.cache import AstrologyResultCache, FileAstrologyResultCache, canonical_payload
from astrology.api.v1 import router as astrology_v1_router
from astrology.http import create_router
from astrology.core.birth_chart import calculate_birth_chart as core_calculate_birth_chart
from astrology.services.astrology_service import DEFAULT_ASTROLOGY_SERVICE as SERVICE_FROM_NAMESPACE
from astrology.registry import AstrologyEngineRegistry
from astrology.responses import BirthChartResponse, CompatibilityResponse, DashasResponse, PanchangResponse
from astrology.rulepacks import DEFAULT_RULE_PACK_REGISTRY
from astrology.service import AstrologyService, build_compatibility, build_meta, build_muhurta, build_panchang
from astrology.transit import TransitEngine
from astrology.dasha import calculate_vimshottari_dasha
from astrology.divisional import calculate_divisional_charts
from astrology.rules import RuleDefinition, RuleEngine, StaticRuleCatalog, interpret_chart
from astrology.utils import parse_birth_datetime, whole_sign_house_number
from fastapi import FastAPI
from fastapi.testclient import TestClient
from main import app


def sample_birth_chart_response(extra: dict | None = None) -> dict:
    payload = {
        "input": {
            "birth_datetime": "2024-01-01T00:00:00+05:30",
            "birth_datetime_utc": "2023-12-31T18:30:00+00:00",
            "timezone": 5.5,
            "timezone_name": "Asia/Kolkata",
            "latitude": 12.972,
            "longitude": 77.594,
            "ayanamsa": "lahiri",
            "ayanamsa_value": None,
            "house_system": "whole_sign",
        },
        "julian_day_ut": 2460310.2708333335,
        "location": {
            "latitude": 12.972,
            "longitude": 77.594,
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India",
            "timezone_name": "Asia/Kolkata",
            "timezone": 5.5,
            "resolved_city": None,
        },
        "ascendant": None,
        "houses": None,
        "planets": {},
        "aspects": [],
        "summary": {"chart_type": "sidereal", "location_based": True, "planet_count": 0},
    }
    if extra:
        payload.update(extra)
    return payload


def sample_compatibility_response(extra: dict | None = None) -> dict:
    payload = {
        "boy_chart": sample_birth_chart_response(),
        "girl_chart": sample_birth_chart_response(),
        "compatibility": {
            "total_gunas": 0.0,
            "max_gunas": 36.0,
            "grade": "inauspicious",
            "bhakoot_favorable": False,
            "nadi_favorable": False,
            "kutas": [],
            "source_labels": [],
        },
    }
    if extra:
        payload.update(extra)
    return payload


def sample_muhurta_response(extra: dict | None = None) -> dict:
    payload = {
        "input": {
            "date": "2025-01-23",
            "start_date": None,
            "end_date": None,
            "activity_type": "career",
            "minimum_score": 0,
            "latitude": 12.972,
            "longitude": 77.594,
            "timezone": 5.5,
            "timezone_name": "Asia/Kolkata",
            "city": None,
            "state": None,
            "country": None,
        },
        "results": [],
        "best_dates": [],
        "summary": {"count": 0, "best_score": None, "activity_type": "career"},
    }
    if extra:
        payload.update(extra)
    return payload


def sample_panchang_response(extra: dict | None = None) -> dict:
    payload = {
        "input": {
            "date": "2025-01-23",
            "latitude": 12.972,
            "longitude": 77.594,
            "timezone": 5.5,
            "timezone_name": "Asia/Kolkata",
            "city": None,
            "state": None,
            "country": None,
        },
        "panchang": {"Tithi": [1, [0, 0, 0]], "Vaara": 4},
    }
    if extra:
        payload.update(extra)
    return payload


class UtilityTests(unittest.TestCase):
    def test_parse_birth_datetime_with_timezone(self):
        dt, tzinfo = parse_birth_datetime(
            {
                "birth_date": "1990-01-01",
                "birth_time": "06:30",
                "timezone": 5.5,
            }
        )
        self.assertEqual(dt.isoformat(), "1990-01-01T06:30:00")
        self.assertIsNotNone(tzinfo)

    def test_whole_sign_house_number(self):
        self.assertEqual(whole_sign_house_number(0, 0), 1)
        self.assertEqual(whole_sign_house_number(0, 3), 4)
        self.assertEqual(whole_sign_house_number(10, 0), 3)


class DashaTests(unittest.TestCase):
    def test_vimshottari_dasha_uses_moon_longitude_from_chart(self):
        chart = {
            "planets": {
                "Moon": {"sidereal_longitude": 0.0},
            }
        }
        result = calculate_vimshottari_dasha(
            {"birth_datetime": "2024-01-01T00:00:00", "timezone": 5.5},
            chart=chart,
            max_depth=1,
        )
        self.assertEqual(result["mahadasha_lord_at_birth"], "Ketu")
        self.assertEqual(result["nakshatra"], "Ashwini")
        self.assertAlmostEqual(result["dasha_balance"]["remaining_years"], 7.0, places=6)

    def test_vimshottari_dasha_exposes_deeper_levels_when_requested(self):
        chart = {"planets": {"Moon": {"sidereal_longitude": 0.0}}}
        result = calculate_vimshottari_dasha(
            {"birth_datetime": "2024-01-01T00:00:00", "timezone": 5.5},
            chart=chart,
            max_depth=4,
        )
        self.assertEqual(result["levels"]["sookshma"], "included")
        self.assertEqual(result["levels"]["prana"], "included")
        self.assertEqual(
            result["mahadashas"][0]["children"][0]["children"][0]["children"][0]["children"][0]["level_name"],
            "prana",
        )

    def test_vimshottari_dasha_boundary_case(self):
        chart = {"planets": {"Moon": {"sidereal_longitude": 0.0}}}
        result = calculate_vimshottari_dasha(
            {"birth_datetime": "2024-01-01T00:00:00", "timezone": 5.5},
            chart=chart,
            max_depth=3,
        )
        self.assertEqual(result["mahadasha_lord_at_birth"], "Ketu")
        self.assertAlmostEqual(result["dasha_balance"]["remaining_years"], 7.0, places=6)


class DivisionalTests(unittest.TestCase):
    def test_divisional_chart_structure(self):
        chart = {
            "planets": {
                "Sun": {"sidereal_longitude": 2.0},
                "Moon": {"sidereal_longitude": 45.0},
            },
            "ascendant": {"longitude": 123.0, "sign": "Leo"},
        }
        result = calculate_divisional_charts(chart)
        self.assertIn("D1", result["vargas"])
        self.assertIn("D9", result["vargas"])
        self.assertEqual(result["vargas"]["D1"]["placements"]["Sun"]["sign"], "Aries")
        self.assertEqual(result["vargas"]["D30"]["placements"]["Sun"]["segment_lord"], "Mars")

    def test_divisional_extended_snapshot(self):
        chart = {
            "planets": {
                "Sun": {"sidereal_longitude": 12.0},
                "Moon": {"sidereal_longitude": 101.0},
                "Mars": {"sidereal_longitude": 217.0},
                "Mercury": {"sidereal_longitude": 289.0},
                "Jupiter": {"sidereal_longitude": 333.0},
                "Venus": {"sidereal_longitude": 44.0},
                "Saturn": {"sidereal_longitude": 155.0},
            },
            "ascendant": {"longitude": 44.0, "sign": "Taurus"},
        }
        result = calculate_divisional_charts(chart)
        self.assertEqual(result["vargas"]["D2"]["ascendant"]["varga_sign"], "Leo")
        self.assertEqual(result["vargas"]["D7"]["placements"]["Moon"]["varga_sign"], "Virgo")
        self.assertEqual(result["vargas"]["D20"]["placements"]["Saturn"]["varga_sign"], "Pisces")
        self.assertEqual(result["vargas"]["D60"]["placements"]["Venus"]["segment_index"], 8)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_legacy_panchang_validation_still_works(self):
        response = self.client.get("/api/v1/panchang")
        self.assertEqual(response.status_code, 400)
        self.assertIn("date is required", response.json()["detail"])

    def test_new_birth_chart_route_is_registered(self):
        with patch("astrology.http.DEFAULT_ASTROLOGY_SERVICE.build_birth_chart", return_value=sample_birth_chart_response({"ok": True})):
            response = self.client.get("/api/v1/astrology/birth-chart?birth_datetime=2024-01-01T00:00:00&timezone=5.5")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_compatibility_route_is_registered(self):
        with patch("astrology.http.DEFAULT_ASTROLOGY_SERVICE.build_compatibility", return_value=sample_compatibility_response({"ok": True})):
            response = self.client.post(
                "/api/v1/astrology/compatibility",
                json={
                    "boy_chart": {"planets": {"Moon": {"sidereal_longitude": 0.0, "sign_index": 0, "degree_in_sign": 0.0, "nakshatra_index": 0}}},
                    "girl_chart": {"planets": {"Moon": {"sidereal_longitude": 30.0, "sign_index": 1, "degree_in_sign": 0.0, "nakshatra_index": 1}}},
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_muhurta_route_is_registered(self):
        with patch("astrology.http.DEFAULT_ASTROLOGY_SERVICE.build_muhurta", return_value=sample_muhurta_response({"ok": True})):
            response = self.client.get(
                "/api/v1/astrology/muhurta?date=2025-01-23&latitude=12.972&longitude=77.594&timezone=5.5"
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_panchang_route_is_registered(self):
        with patch("astrology.http.DEFAULT_ASTROLOGY_SERVICE.build_panchang", return_value=sample_panchang_response({"ok": True})):
            response = self.client.get(
                "/api/v1/astrology/panchang?date=2025-01-23&latitude=12.972&longitude=77.594&timezone=5.5"
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_meta_route_returns_capabilities(self):
        response = self.client.get("/api/v1/astrology/meta?version=v1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], "v1")
        self.assertIn("default_traditional", body["available_rule_packs"])
        self.assertIn("D60", body["supported_vargas"])

    def test_birth_chart_route_validates_payload(self):
        response = self.client.post(
            "/api/v1/astrology/birth-chart",
            json={"birth_datetime": "not-a-datetime", "timezone": 5.5},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("birth_datetime", str(response.json()["detail"]))

    def test_build_meta_service_surface(self):
        meta = build_meta({"version": "v1"})
        self.assertEqual(meta["api_version"], "v1")
        self.assertEqual(meta["selected_service_version"], "v1")
        self.assertIn("strict_classical", meta["available_rule_packs"])
        self.assertIn("/birth-chart", meta["supported_endpoints"])


class BirthChartTests(unittest.TestCase):
    def test_city_based_birth_chart_resolves_timezone(self):
        chart = calculate_birth_chart(
            {
                "birth_datetime": "1990-01-01T06:30:00",
                "city": "Delhi",
            }
        )
        self.assertEqual(chart["location"]["city"], "Delhi")
        self.assertEqual(chart["input"]["timezone_name"], "Asia/Kolkata")
        self.assertIsNotNone(chart["ascendant"])


class RuleTests(unittest.TestCase):
    def test_budhaditya_and_gajakesari_rules(self):
        chart = {
            "planets": {
                "Sun": {"sidereal_longitude": 15.0, "sign_index": 0, "house": 1},
                "Mercury": {"sidereal_longitude": 19.0, "sign_index": 0, "house": 1},
                "Moon": {"sidereal_longitude": 90.0, "sign_index": 3, "house": 4},
                "Jupiter": {"sidereal_longitude": 180.0, "sign_index": 6, "house": 7},
                "Mars": {"sidereal_longitude": 210.0, "sign_index": 7, "house": 8},
                "Venus": {"sidereal_longitude": 240.0, "sign_index": 8, "house": 9},
                "Saturn": {"sidereal_longitude": 270.0, "sign_index": 9, "house": 10},
                "Rahu": {"sidereal_longitude": 300.0, "sign_index": 10, "house": 11},
                "Ketu": {"sidereal_longitude": 120.0, "sign_index": 4, "house": 5},
            },
            "ascendant": {"sign": "Aries"},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("budhaditya_yoga", rule_ids)
        self.assertIn("gajakesari_yoga", rule_ids)

    def test_budhaditya_and_gajakesari_cancellations(self):
        chart = {
            "planets": {
                "Sun": {"sidereal_longitude": 15.0, "sign_index": 0, "house": 1},
                "Mercury": {
                    "sidereal_longitude": 19.0,
                    "sign_index": 0,
                    "house": 1,
                    "combustion": {"is_combust": True},
                    "dignity": "debilitated",
                },
                "Moon": {"sidereal_longitude": 0.0, "sign_index": 0, "house": 1},
                "Jupiter": {
                    "sidereal_longitude": 90.0,
                    "sign_index": 3,
                    "house": 4,
                    "combustion": {"is_combust": True},
                },
                "Mars": {"sidereal_longitude": 210.0, "sign_index": 7, "house": 8},
                "Venus": {"sidereal_longitude": 240.0, "sign_index": 8, "house": 9},
                "Saturn": {"sidereal_longitude": 270.0, "sign_index": 9, "house": 10},
                "Rahu": {"sidereal_longitude": 300.0, "sign_index": 10, "house": 11},
                "Ketu": {"sidereal_longitude": 120.0, "sign_index": 4, "house": 5},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("budhaditya_cancellation", rule_ids)
        self.assertIn("gajakesari_cancellation", rule_ids)
        self.assertNotIn("budhaditya_yoga", rule_ids)
        self.assertNotIn("gajakesari_yoga", rule_ids)
        self.assertIn("budhaditya_yoga", interpretation["suppressed"])
        self.assertIn("gajakesari_yoga", interpretation["suppressed"])

    def test_chandra_mangala_and_kalasarpa_cancellations(self):
        chart = {
            "planets": {
                "Moon": {
                    "sidereal_longitude": 80.0,
                    "sign_index": 0,
                    "house": 1,
                    "dignity": "own",
                },
                "Mars": {
                    "sidereal_longitude": 85.0,
                    "sign_index": 0,
                    "house": 1,
                    "dignity": "debilitated",
                    "combustion": {"is_combust": True},
                },
                "Jupiter": {
                    "sidereal_longitude": 110.0,
                    "sign_index": 3,
                    "house": 4,
                    "dignity": "exalted",
                },
                "Sun": {"sidereal_longitude": 70.0, "sign_index": 2, "house": 3},
                "Mercury": {"sidereal_longitude": 100.0, "sign_index": 3, "house": 4},
                "Venus": {"sidereal_longitude": 120.0, "sign_index": 4, "house": 5},
                "Saturn": {"sidereal_longitude": 130.0, "sign_index": 4, "house": 5},
                "Rahu": {"sidereal_longitude": 60.0, "sign_index": 2, "house": 3},
                "Ketu": {"sidereal_longitude": 240.0, "sign_index": 8, "house": 9},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("chandra_mangala_cancellation", rule_ids)
        self.assertIn("kalasarpa_cancellation", rule_ids)
        self.assertNotIn("chandra_mangala_yoga", rule_ids)
        self.assertNotIn("kalasarpa_yoga", rule_ids)
        self.assertIn("chandra_mangala_yoga", interpretation["suppressed"])
        self.assertIn("kalasarpa_yoga", interpretation["suppressed"])

    def test_mahapurusha_cancellations(self):
        chart = {
            "planets": {
                "Sun": {"sidereal_longitude": 5.0, "sign_index": 0, "house": 1},
                "Mercury": {
                    "sidereal_longitude": 25.0,
                    "sign_index": 0,
                    "house": 1,
                    "dignity": "debilitated",
                },
                "Moon": {"sidereal_longitude": 95.0, "sign_index": 3, "house": 4},
                "Jupiter": {
                    "sidereal_longitude": 105.0,
                    "sign_index": 3,
                    "house": 4,
                    "dignity": "debilitated",
                    "combustion": {"is_combust": True},
                },
                "Mars": {
                    "sidereal_longitude": 205.0,
                    "sign_index": 6,
                    "house": 7,
                    "dignity": "debilitated",
                },
                "Venus": {
                    "sidereal_longitude": 245.0,
                    "sign_index": 8,
                    "house": 9,
                    "dignity": "debilitated",
                },
                "Saturn": {
                    "sidereal_longitude": 290.0,
                    "sign_index": 9,
                    "house": 10,
                    "dignity": "debilitated",
                },
                "Rahu": {"sidereal_longitude": 45.0, "sign_index": 1, "house": 2},
                "Ketu": {"sidereal_longitude": 225.0, "sign_index": 7, "house": 8},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        for base_rule in {"ruchaka_yoga", "bhadra_yoga", "hamsa_yoga", "malavya_yoga", "sasa_yoga"}:
            self.assertNotIn(base_rule, rule_ids)
        for cancellation_rule in {"ruchaka_cancellation", "bhadra_cancellation", "hamsa_cancellation", "malavya_cancellation", "sasa_cancellation"}:
            self.assertIn(cancellation_rule, rule_ids)

    def test_manglik_rule(self):
        chart = {
            "planets": {
                "Sun": {"sidereal_longitude": 10.0, "sign_index": 0, "house": 1},
                "Moon": {"sidereal_longitude": 20.0, "sign_index": 0, "house": 1},
                "Mars": {"sidereal_longitude": 25.0, "sign_index": 0, "house": 1},
                "Mercury": {"sidereal_longitude": 30.0, "sign_index": 1, "house": 2},
                "Jupiter": {"sidereal_longitude": 35.0, "sign_index": 1, "house": 2},
                "Venus": {"sidereal_longitude": 40.0, "sign_index": 1, "house": 2},
                "Saturn": {"sidereal_longitude": 45.0, "sign_index": 1, "house": 2},
                "Rahu": {"sidereal_longitude": 60.0, "sign_index": 2, "house": 3},
                "Ketu": {"sidereal_longitude": 240.0, "sign_index": 8, "house": 9},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("mangal_dosha", rule_ids)

    def test_manglik_cancellation_suppresses_dosha(self):
        chart = {
            "planets": {
                "Mars": {"sidereal_longitude": 5.0, "sign_index": 0, "house": 1, "dignity": "own"},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("mangal_dosha_cancellation", rule_ids)
        self.assertNotIn("mangal_dosha", rule_ids)
        self.assertIn("mangal_dosha", interpretation["suppressed"])

    def test_manglik_strengthened_cancels_dosha(self):
        chart = {
            "planets": {
                "Mars": {"sidereal_longitude": 5.0, "sign_index": 0, "house": 1, "dignity": "own"},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("mangal_dosha_strengthened", rule_ids)
        self.assertNotIn("mangal_dosha", rule_ids)

    def test_kalasarpa_rule(self):
        chart = {
            "planets": {
                "Sun": {"sidereal_longitude": 70.0, "sign_index": 2, "house": 3},
                "Moon": {"sidereal_longitude": 80.0, "sign_index": 2, "house": 3},
                "Mars": {"sidereal_longitude": 90.0, "sign_index": 3, "house": 4},
                "Mercury": {"sidereal_longitude": 100.0, "sign_index": 3, "house": 4},
                "Jupiter": {"sidereal_longitude": 110.0, "sign_index": 3, "house": 4},
                "Venus": {"sidereal_longitude": 120.0, "sign_index": 4, "house": 5},
                "Saturn": {"sidereal_longitude": 130.0, "sign_index": 4, "house": 5},
                "Rahu": {"sidereal_longitude": 60.0, "sign_index": 2, "house": 3},
                "Ketu": {"sidereal_longitude": 240.0, "sign_index": 8, "house": 9},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("kalasarpa_yoga", rule_ids)

    def test_mahapurusha_rule(self):
        chart = {
            "planets": {
                "Mars": {"sidereal_longitude": 5.0, "sign_index": 0, "house": 1, "dignity": "own"},
            },
            "ascendant": {"sign": "Aries", "sign_index": 0},
        }
        interpretation = interpret_chart(chart)
        rule_ids = {item["rule_id"] for item in interpretation["matches"]}
        self.assertIn("ruchaka_yoga", rule_ids)


class CompatibilityTests(unittest.TestCase):
    def test_ashtakuta_scoring_from_charts(self):
        boy_chart = {
            "planets": {
                "Moon": {
                    "sidereal_longitude": 0.0,
                    "sign_index": 0,
                    "degree_in_sign": 0.0,
                    "nakshatra_index": 0,
                }
            }
        }
        girl_chart = {
            "planets": {
                "Moon": {
                    "sidereal_longitude": 30.0,
                    "sign_index": 1,
                    "degree_in_sign": 0.0,
                    "nakshatra_index": 1,
                }
            }
        }
        result = build_compatibility({"boy_chart": boy_chart, "girl_chart": girl_chart})
        self.assertIn("compatibility", result)
        self.assertEqual(result["compatibility"]["max_gunas"], 36.0)
        self.assertGreaterEqual(result["compatibility"]["total_gunas"], 0.0)


class MuhurtaTests(unittest.TestCase):
    def test_build_muhurta_with_mock_provider(self):
        def provider(date, latitude, longitude, timezone):
            return {
                "Tithi": [11, [0, 0, 0]],
                "Nakshatra": [8, [0, 0, 0]],
                "Yoga": [21, [0, 0, 0]],
                "karana": [7],
                "Vaara": 4,
                "Sunrise": [6, 0, 0],
                "Sunset": [18, 0, 0],
                "Day Duration": [12, 0, 0],
            }

        from astrology.muhurta import MuhurtaEngine

        engine = MuhurtaEngine(panchang_provider=provider)
        result = engine.calculate(
            {
                "date": "2025-01-23",
                "latitude": 12.972,
                "longitude": 77.594,
                "timezone": 5.5,
                "activity_type": "career",
            }
        )
        self.assertEqual(result["summary"]["count"], 1)
        self.assertIn("windows", result["results"][0])
        self.assertGreater(result["results"][0]["score"]["total"], 0)
        self.assertEqual(result["results"][0]["summary"]["profile"], "career")


class PanchangTests(unittest.TestCase):
    def test_build_panchang_with_mock_provider(self):
        def provider(date, latitude, longitude, timezone):
            return {
                "Tithi": [11, [0, 0, 0]],
                "Nakshatra": [8, [0, 0, 0]],
                "Yoga": [21, [0, 0, 0]],
                "karana": [7],
                "Vaara": 4,
                "Sunrise": [6, 0, 0],
                "Sunset": [18, 0, 0],
                "Day Duration": [12, 0, 0],
            }

        from astrology.panchang import PanchangEngine

        engine = PanchangEngine(panchang_provider=provider)
        result = engine.calculate(
            {
                "date": "2025-01-23",
                "latitude": 12.972,
                "longitude": 77.594,
                "timezone": 5.5,
            }
        )
        self.assertEqual(result["input"]["date"], "2025-01-23")
        self.assertEqual(result["panchang"]["Tithi"][0], 11)


class TransitTests(unittest.TestCase):
    def test_transit_forecast_is_generated(self):
        class FakeBirthChartEngine:
            def calculate(self, payload: dict) -> dict:
                return {
                    "input": {
                        "birth_datetime": "2024-01-01T00:00:00+05:30",
                        "birth_datetime_utc": "2023-12-31T18:30:00+00:00",
                        "timezone": 5.5,
                        "timezone_name": "Asia/Kolkata",
                        "latitude": 12.972,
                        "longitude": 77.594,
                        "ayanamsa": "lahiri",
                        "ayanamsa_value": None,
                        "house_system": "whole_sign",
                    },
                    "planets": {
                        "Moon": {"sidereal_longitude": 0.0, "sign_index": 0},
                        "Sun": {"sidereal_longitude": 30.0, "sign_index": 1},
                    },
                }

        engine = TransitEngine(birth_chart_engine=FakeBirthChartEngine())
        result = engine.calculate({"transit_datetime": "2025-01-23T00:00:00", "timezone": 5.5, "forecast_days": 2})

        self.assertEqual(len(result["forecast"]), 2)
        self.assertIn("score", result["forecast"][0])
        self.assertIn("aspect_hit_count", result["forecast"][0])

    def test_transit_events_are_generated(self):
        class FakeBirthChartEngine:
            def calculate(self, payload: dict) -> dict:
                return {
                    "input": {
                        "birth_datetime": "2024-01-01T00:00:00+05:30",
                        "birth_datetime_utc": "2023-12-31T18:30:00+00:00",
                        "timezone": 5.5,
                        "timezone_name": "Asia/Kolkata",
                        "latitude": 12.972,
                        "longitude": 77.594,
                        "ayanamsa": "lahiri",
                        "ayanamsa_value": None,
                        "house_system": "whole_sign",
                    },
                    "planets": {
                        "Moon": {"sidereal_longitude": 0.0, "sign_index": 0},
                        "Sun": {"sidereal_longitude": 30.0, "sign_index": 1},
                    },
                }

        def snapshot_builder(transit_local, natal_chart):
            minute = transit_local.minute
            if minute < 30:
                saturn_sign = 9
                saturn_retro = True
            else:
                saturn_sign = 10
                saturn_retro = False
            return {
                "transit_chart": {
                    "input": {"transit_datetime": transit_local.isoformat()},
                    "planets": {
                        "Saturn": {
                            "sign_index": saturn_sign,
                            "retrograde": saturn_retro,
                            "sidereal_longitude": float(saturn_sign * 30),
                        },
                        "Jupiter": {
                            "sign_index": 7,
                            "retrograde": False,
                            "sidereal_longitude": 210.0,
                        },
                    },
                },
                "aspect_hits": [],
                "summaries": [],
            }

        engine = TransitEngine(birth_chart_engine=FakeBirthChartEngine(), snapshot_builder=snapshot_builder)
        result = engine.calculate({"transit_datetime": "2025-01-23T00:00:00", "timezone": 5.5, "forecast_days": 1})

        self.assertTrue(result["events"])
        event_types = {item["event_type"] for item in result["events"]}
        self.assertIn("ingress", event_types)
        self.assertIn("station_direct", event_types)
        self.assertIn("events", result["forecast"][0])
        self.assertEqual(result["events"][0]["approx_time"], "2025-01-23T00:29:55.312500+05:30")

    def test_transit_timed_windows_are_generated(self):
        class FakeBirthChartEngine:
            def calculate(self, payload: dict) -> dict:
                return {
                    "input": {
                        "birth_datetime": "2024-01-01T00:00:00+05:30",
                        "birth_datetime_utc": "2023-12-31T18:30:00+00:00",
                        "timezone": 5.5,
                        "timezone_name": "Asia/Kolkata",
                        "latitude": 12.972,
                        "longitude": 77.594,
                        "ayanamsa": "lahiri",
                        "ayanamsa_value": None,
                        "house_system": "whole_sign",
                    },
                    "planets": {
                        "Moon": {"sidereal_longitude": 0.0, "sign_index": 0},
                        "Sun": {"sidereal_longitude": 30.0, "sign_index": 1},
                    },
                }

        def snapshot_builder(transit_local, natal_chart):
            hour = transit_local.hour
            if hour in {9, 10, 11}:
                hits = [
                    {
                        "transit_planet": "Jupiter",
                        "natal_planet": "Moon",
                        "aspect": "7th",
                        "sign_distance": 7,
                        "orb": 0.0,
                    }
                ]
            elif hour in {15}:
                hits = [
                    {
                        "transit_planet": "Mars",
                        "natal_planet": "Sun",
                        "aspect": "4th",
                        "sign_distance": 4,
                        "orb": 0.0,
                    }
                ]
            else:
                hits = []
            return {
                "transit_chart": {
                    "input": {"transit_datetime": transit_local.isoformat()},
                    "planets": {
                        "Saturn": {
                            "sign_index": 9 if transit_local.hour < 12 else 10,
                            "retrograde": transit_local.hour < 12,
                            "sidereal_longitude": float((9 if transit_local.hour < 12 else 10) * 30),
                        },
                        "Jupiter": {
                            "sign_index": 7,
                            "retrograde": False,
                            "sidereal_longitude": 210.0,
                        },
                    },
                },
                "aspect_hits": hits,
                "summaries": [
                    {"planet": item["transit_planet"], "sign": 0, "natal_hits": [{"natal_planet": item["natal_planet"], "distance_deg": 0.0, "conjunction": False}]}
                    for item in hits
                ],
            }

        engine = TransitEngine(birth_chart_engine=FakeBirthChartEngine(), snapshot_builder=snapshot_builder)
        result = engine.calculate({"transit_datetime": "2025-01-23T00:00:00", "timezone": 5.5, "forecast_days": 1})

        self.assertEqual(len(result["forecast"]), 1)
        self.assertGreaterEqual(len(result["forecast"][0]["timed_windows"]), 1)
        self.assertIn("dominant_themes", result["forecast"][0]["timed_windows"][0])
        self.assertIn("identity", result["forecast"][0]["dominant_themes"])


class RuleEngineSwapTests(unittest.TestCase):
    def test_custom_rule_catalog_is_injectable(self):
        chart = {"planets": {}, "ascendant": {"sign": "Aries"}}

        custom_rule = RuleDefinition(
            rule_id="custom_rule",
            category="custom",
            title="Custom Rule",
            source="test",
            evaluator=lambda current_chart: bool(current_chart.get("ascendant")),
            base_score=99,
        )
        engine = RuleEngine(StaticRuleCatalog([custom_rule]))
        result = interpret_chart(chart, engine=engine)

        self.assertEqual(result["summary"]["match_count"], 1)
        self.assertEqual(result["matches"][0]["rule_id"], "custom_rule")
        self.assertIn("custom", result["themes"])

    def test_rule_pack_selection_is_available_on_interpretation(self):
        class FakeBirthChartEngine:
            def calculate(self, payload: dict) -> dict:
                return {"planets": {}, "ascendant": {"sign": "Aries"}}

        service = AstrologyService(birth_chart_engine=FakeBirthChartEngine())
        result = service.build_interpretation({"birth_datetime": "2024-01-01T00:00:00", "timezone": 5.5, "rule_pack": "life_themes"})

        self.assertEqual(result["rule_pack"], "life_themes")


class CacheTests(unittest.TestCase):
    def test_service_caches_repeated_birth_chart_requests(self):
        class CountingBirthEngine:
            def __init__(self):
                self.calls = 0

            def calculate(self, payload: dict) -> dict:
                self.calls += 1
                return {"payload": payload, "call_number": self.calls}

        birth_engine = CountingBirthEngine()
        cache = AstrologyResultCache()
        service = AstrologyService(birth_chart_engine=birth_engine, cache=cache)
        payload = {"birth_datetime": "2024-01-01T00:00:00", "timezone": 5.5}

        first = service.build_birth_chart(payload)
        second = service.build_birth_chart(payload)

        self.assertEqual(first, second)
        self.assertEqual(birth_engine.calls, 1)
        self.assertEqual(canonical_payload(payload), canonical_payload(dict(payload)))

    def test_file_cache_persists_between_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_one = FileAstrologyResultCache(Path(tmpdir))
            payload = {"a": 1, "b": [2, 3]}
            cache_one.set("sample", payload, {"value": 42})
            cache_two = FileAstrologyResultCache(Path(tmpdir))
            self.assertEqual(cache_two.get("sample", payload), {"value": 42})


class RegistryTests(unittest.TestCase):
    def test_registry_returns_default_and_custom_versions(self):
        registry = AstrologyEngineRegistry()
        self.assertIsNotNone(registry.get())
        self.assertIn("v1", registry.versions())

    def test_rule_pack_registry_returns_default_pack(self):
        pack = DEFAULT_RULE_PACK_REGISTRY.get()
        self.assertEqual(pack.name, "default_traditional")
        self.assertTrue(pack.source_tags)
        self.assertIn("classical_core", DEFAULT_RULE_PACK_REGISTRY.list())
        self.assertIn("life_themes", DEFAULT_RULE_PACK_REGISTRY.list())
        self.assertIn("strict_classical", DEFAULT_RULE_PACK_REGISTRY.list())
        self.assertIn("extended_interpretive", DEFAULT_RULE_PACK_REGISTRY.list())


class ImportPathTests(unittest.TestCase):
    def test_engine_and_api_submodule_imports_work(self):
        self.assertIsNotNone(DEFAULT_BIRTH_CHART_ENGINE)
        self.assertIsNotNone(DEFAULT_PANCHANG_ENGINE)
        self.assertEqual(astrology_v1_router.prefix, "/api/v1/astrology")
        self.assertIsNotNone(SERVICE_FROM_NAMESPACE)

    def test_response_models_are_importable(self):
        self.assertIn("input", BirthChartResponse.model_fields)
        self.assertIn("planets", BirthChartResponse.model_fields)
        self.assertIn("birth_chart", DashasResponse.model_fields)
        self.assertIn("compatibility", CompatibilityResponse.model_fields)
        self.assertIn("input", PanchangResponse.model_fields)

    def test_core_namespace_imports_work(self):
        self.assertEqual(core_calculate_birth_chart, calculate_birth_chart)
        self.assertIsInstance(DEFAULT_BIRTH_CHART_ENGINE, AstrologyEngine)


class RegistryRoutingTests(unittest.TestCase):
    def test_router_can_resolve_versioned_service_from_registry(self):
        class AltService(AstrologyService):
            def build_birth_chart(self, payload: dict) -> dict:
                return sample_birth_chart_response({"service": "alt", "payload": payload})

        registry = AstrologyEngineRegistry()
        registry.register("alt", AltService())
        app = FastAPI()
        app.include_router(create_router(registry=registry))
        client = TestClient(app)

        response = client.get(
            "/api/v1/astrology/birth-chart?birth_datetime=2024-01-01T00:00:00&timezone=5.5&version=alt"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["service"], "alt")


if __name__ == "__main__":
    unittest.main()
