from __future__ import annotations

import json
from pathlib import Path
import unittest

from astrology.birth_chart import calculate_birth_chart
from astrology.dasha import calculate_vimshottari_dasha
from astrology.divisional import calculate_divisional_charts
from astrology.muhurta import calculate_muhurta
from astrology.service import build_compatibility
from astrology.service import build_meta
from astrology.compatibility import calculate_ashtakuta_from_charts
from astrology.rules import interpret_chart
from astrology.transit import calculate_transits
from astrology.muhurta import MuhurtaEngine
from astrology.transit import TransitEngine


FIXTURE_PATH = Path(__file__).with_name("fixtures") / "astrology_snapshots.json"


def _assert_subset(testcase: unittest.TestCase, expected, actual):
    if isinstance(expected, dict):
        testcase.assertIsInstance(actual, dict)
        for key, value in expected.items():
            testcase.assertIn(key, actual)
            _assert_subset(testcase, value, actual[key])
        return
    if isinstance(expected, list):
        testcase.assertIsInstance(actual, list)
        testcase.assertEqual(len(actual), len(expected))
        for exp_item, act_item in zip(expected, actual):
            _assert_subset(testcase, exp_item, act_item)
        return
    testcase.assertEqual(actual, expected)


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
            cls.snapshots = json.load(handle)

    def test_birth_chart_snapshot(self):
        snapshot = self.snapshots["birth"]
        actual = calculate_birth_chart(snapshot["payload"])
        projection = {
            "input": actual["input"],
            "location": actual["location"],
            "ascendant": actual["ascendant"],
            "summary": actual["summary"],
            "sun": actual["planets"]["Sun"],
            "moon": actual["planets"]["Moon"],
            "rahu": actual["planets"]["Rahu"],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_birth_chart_timezone_only_snapshot(self):
        snapshot = self.snapshots["birth_timezone"]
        actual = calculate_birth_chart(snapshot["payload"])
        projection = {
            "input": actual["input"],
            "location": actual["location"],
            "ascendant": actual["ascendant"],
            "summary": actual["summary"],
            "sun": actual["planets"]["Sun"],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_dasha_snapshot(self):
        snapshot = self.snapshots["dasha"]
        birth = calculate_birth_chart({"birth_datetime": snapshot["payload"]["birth_datetime"], "city": snapshot["payload"]["city"]})
        actual = calculate_vimshottari_dasha(snapshot["payload"], chart=birth, max_depth=snapshot["payload"]["max_depth"])
        projection = {
            "nakshatra": actual["nakshatra"],
            "mahadasha_lord_at_birth": actual["mahadasha_lord_at_birth"],
            "current_period": {"lord": actual["current_period"]["lord"], "level_name": actual["current_period"]["level_name"]},
            "levels": actual["levels"],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_dasha_edge_snapshot(self):
        snapshot = self.snapshots["dasha_edge"]
        actual = calculate_vimshottari_dasha(snapshot["payload"], chart=snapshot["chart"], max_depth=snapshot["payload"]["max_depth"])
        projection = {
            "nakshatra": actual["nakshatra"],
            "mahadasha_lord_at_birth": actual["mahadasha_lord_at_birth"],
            "dasha_balance": {
                "elapsed_years": round(actual["dasha_balance"]["elapsed_years"], 3),
                "remaining_years": round(actual["dasha_balance"]["remaining_years"], 3),
            },
            "current_period": {
                "lord": actual["current_period"]["lord"],
                "level_name": actual["current_period"]["level_name"],
            },
            "levels": actual["levels"],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_dasha_boundary_snapshot(self):
        snapshot = self.snapshots["dasha_boundary"]
        actual = calculate_vimshottari_dasha(snapshot["payload"], chart=snapshot["chart"], max_depth=snapshot["payload"]["max_depth"])
        projection = {
            "nakshatra": actual["nakshatra"],
            "mahadasha_lord_at_birth": actual["mahadasha_lord_at_birth"],
            "dasha_balance": {
                "elapsed_years": round(actual["dasha_balance"]["elapsed_years"], 3),
                "remaining_years": round(actual["dasha_balance"]["remaining_years"], 3),
            },
            "current_period": {
                "lord": actual["current_period"]["lord"],
                "level_name": actual["current_period"]["level_name"],
            },
            "levels": actual["levels"],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_divisional_snapshot(self):
        snapshot = self.snapshots["divisional"]
        actual = calculate_divisional_charts(snapshot["chart"])
        projection = {
            "source": actual["source"],
            "D1": {
                "name": actual["vargas"]["D1"]["name"],
                "placements": {
                    "Sun": actual["vargas"]["D1"]["placements"]["Sun"],
                    "Moon": actual["vargas"]["D1"]["placements"]["Moon"],
                },
            },
            "D9": {
                "name": actual["vargas"]["D9"]["name"],
                "ascendant": actual["vargas"]["D9"]["ascendant"],
            },
            "D10": {
                "name": actual["vargas"]["D10"]["name"],
                "placements": {
                    "Mercury": actual["vargas"]["D10"]["placements"]["Mercury"],
                },
            },
            "D30": {
                "name": actual["vargas"]["D30"]["name"],
                "placements": {
                    "Moon": actual["vargas"]["D30"]["placements"]["Moon"],
                },
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_divisional_secondary_snapshot(self):
        snapshot = self.snapshots["divisional_secondary"]
        actual = calculate_divisional_charts(snapshot["chart"])
        projection = {
            "source": actual["source"],
            "D2": {
                "name": actual["vargas"]["D2"]["name"],
                "ascendant": actual["vargas"]["D2"]["ascendant"],
                "placements": {
                    "Sun": actual["vargas"]["D2"]["placements"]["Sun"],
                    "Venus": actual["vargas"]["D2"]["placements"]["Venus"],
                },
            },
            "D7": {
                "name": actual["vargas"]["D7"]["name"],
                "placements": {
                    "Moon": actual["vargas"]["D7"]["placements"]["Moon"],
                    "Jupiter": actual["vargas"]["D7"]["placements"]["Jupiter"],
                },
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_divisional_extended_snapshot(self):
        snapshot = self.snapshots["divisional_extended"]
        actual = calculate_divisional_charts(snapshot["chart"])
        projection = {
            "source": actual["source"],
            "D2": {
                "name": actual["vargas"]["D2"]["name"],
                "ascendant": actual["vargas"]["D2"]["ascendant"],
            },
            "D7": {
                "name": actual["vargas"]["D7"]["name"],
                "placements": {
                    "Moon": actual["vargas"]["D7"]["placements"]["Moon"],
                    "Jupiter": actual["vargas"]["D7"]["placements"]["Jupiter"],
                },
            },
            "D20": {
                "name": actual["vargas"]["D20"]["name"],
                "placements": {
                    "Saturn": actual["vargas"]["D20"]["placements"]["Saturn"],
                },
            },
            "D60": {
                "name": actual["vargas"]["D60"]["name"],
                "placements": {
                    "Venus": actual["vargas"]["D60"]["placements"]["Venus"],
                },
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_divisional_boundary_snapshot(self):
        snapshot = self.snapshots["divisional_boundary"]
        actual = calculate_divisional_charts(snapshot["chart"])
        projection = {
            "source": actual["source"],
            "D2": {
                "name": actual["vargas"]["D2"]["name"],
                "ascendant": actual["vargas"]["D2"]["ascendant"],
            },
            "D9": {
                "name": actual["vargas"]["D9"]["name"],
                "ascendant": actual["vargas"]["D9"]["ascendant"],
            },
            "D30": {
                "name": actual["vargas"]["D30"]["name"],
                "placements": {
                    "Sun": actual["vargas"]["D30"]["placements"]["Sun"],
                    "Moon": actual["vargas"]["D30"]["placements"]["Moon"],
                    "Saturn": actual["vargas"]["D30"]["placements"]["Saturn"],
                },
            },
            "D60": {
                "name": actual["vargas"]["D60"]["name"],
                "placements": {
                    "Saturn": actual["vargas"]["D60"]["placements"]["Saturn"],
                },
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_transit_snapshot(self):
        snapshot = self.snapshots["transit"]
        birth = calculate_birth_chart({"birth_datetime": snapshot["payload"]["birth_datetime"], "city": snapshot["payload"]["city"]})
        actual = calculate_transits(snapshot["payload"], natal_chart=birth)
        projection = {
            "forecast_len": len(actual["forecast"]),
            "aspect_hit_count": len(actual["aspect_hits"]),
            "first_forecast": {
                "date": actual["forecast"][0]["date"],
                "score": actual["forecast"][0]["score"],
                "conjunction_count": actual["forecast"][0]["conjunction_count"],
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_muhurta_snapshot(self):
        snapshot = self.snapshots["muhurta"]
        actual = calculate_muhurta(snapshot["payload"])
        projection = {
            "summary": {**actual["summary"], "profile": actual["results"][0]["summary"]["profile"]},
            "first_result": actual["results"][0],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_muhurta_strict_filter_snapshot(self):
        snapshot = self.snapshots["muhurta_strict"]
        engine = MuhurtaEngine(panchang_provider=lambda date, latitude, longitude, timezone: {
            "Tithi": [11, [0, 0, 0]],
            "Nakshatra": [8, [0, 0, 0]],
            "Yoga": [21, [0, 0, 0]],
            "karana": [7],
            "Vaara": 4,
            "Sunrise": [6, 0, 0],
            "Sunset": [18, 0, 0],
            "Day Duration": [12, 0, 0],
        })
        actual = engine.calculate(snapshot["payload"])
        projection = {
            "summary": actual["summary"],
            "results": actual["results"],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_rule_cancellation_snapshot(self):
        snapshot = self.snapshots["rule_cancellation"]
        actual = interpret_chart(snapshot["payload"])
        projection = {
            "suppressed": actual["suppressed"],
            "summary": actual["summary"],
            "first_match": actual["matches"][0],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_transit_windows_snapshot(self):
        snapshot = self.snapshots["transit_windows"]

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
                saturn_sign = 9
                saturn_retro = True
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
                saturn_sign = 10
                saturn_retro = False
            else:
                hits = []
                saturn_sign = 9 if hour < 12 else 10
                saturn_retro = hour < 12
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
                "aspect_hits": hits,
                "summaries": [
                    {
                        "planet": item["transit_planet"],
                        "sign": 0,
                        "natal_hits": [
                            {
                                "natal_planet": item["natal_planet"],
                                "distance_deg": 0.0,
                                "conjunction": False,
                            }
                        ],
                    }
                    for item in hits
                ],
            }

        engine = TransitEngine(birth_chart_engine=FakeBirthChartEngine(), snapshot_builder=snapshot_builder)
        actual = engine.calculate(snapshot["payload"])
        projection = {
            "forecast_len": len(actual["forecast"]),
            "first_forecast": {
                "timed_windows_len": len(actual["forecast"][0]["timed_windows"]),
                "first_window": actual["forecast"][0]["timed_windows"][0],
                "dominant_themes": actual["forecast"][0]["dominant_themes"],
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_transit_event_boundary_snapshot(self):
        snapshot = self.snapshots["transit_event_boundary"]

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
            if transit_local.hour < 1:
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
        actual = engine.calculate(snapshot["payload"])
        projection = {
            "events_len": len(actual["events"]),
            "first_event": actual["events"][0],
            "forecast_first": {
                "date": actual["forecast"][0]["date"],
                "events_len": len(actual["forecast"][0]["events"]),
                "first_event": actual["forecast"][0]["events"][0],
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_compatibility_snapshot(self):
        snapshot = self.snapshots["compatibility"]
        actual = build_compatibility(snapshot["payload"])
        projection = {
            "total_gunas": actual["compatibility"]["total_gunas"],
            "grade": actual["compatibility"]["grade"],
            "bhakoot_favorable": actual["compatibility"]["bhakoot_favorable"],
            "nadi_favorable": actual["compatibility"]["nadi_favorable"],
            "first_kuta": {
                "name": actual["compatibility"]["kutas"][0]["name"],
                "score": actual["compatibility"]["kutas"][0]["score"],
            },
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_compatibility_dosha_snapshot(self):
        snapshot = self.snapshots["compatibility_dosha"]
        actual = calculate_ashtakuta_from_charts(snapshot["boy_chart"], snapshot["girl_chart"])
        projection = {
            "total_gunas": actual["total_gunas"],
            "grade": actual["grade"],
            "bhakoot_favorable": actual["bhakoot_favorable"],
            "nadi_favorable": actual["nadi_favorable"],
            "doshas": actual["doshas"],
            "mitigations": actual["mitigations"],
        }
        _assert_subset(self, snapshot["expected"], projection)

    def test_meta_snapshot(self):
        snapshot = self.snapshots["meta"]
        actual = build_meta(snapshot["payload"])
        projection = {
            "api_version": actual["api_version"],
            "selected_service_version": actual["selected_service_version"],
            "available_rule_packs": actual["available_rule_packs"],
            "supported_vargas": actual["supported_vargas"],
            "supported_endpoints": actual["supported_endpoints"],
        }
        _assert_subset(self, snapshot["expected"], projection)
