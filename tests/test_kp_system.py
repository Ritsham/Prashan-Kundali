import unittest
from unittest.mock import MagicMock
from app.astrology.kp_system import get_kp_lords, calculate_placidus_cusps, build_kp_significators

class TestKPSystem(unittest.TestCase):
    def test_get_kp_lords(self):
        # 0 degrees Aries
        lords = get_kp_lords(0.0)
        self.assertEqual(lords["sign_lord"], "Mars")
        self.assertEqual(lords["star_lord"], "Ketu")
        self.assertEqual(lords["sub_lord"], "Ketu")
        
        # 42.0 degrees (Taurus, Rohini)
        lords = get_kp_lords(42.0)
        self.assertEqual(lords["sign_lord"], "Venus")
        self.assertEqual(lords["star_lord"], "Moon")
        self.assertEqual(lords["sub_lord"], "Rahu")
        
    def test_build_kp_significators(self):
        planets = [
            {"name": "Sun", "sign_lord": "Mars", "star_lord": "Ketu", "sub_lord": "Venus"},
            {"name": "Moon", "sign_lord": "Venus", "star_lord": "Moon", "sub_lord": "Rahu"},
        ]
        cusps = [
            {"house": 1, "longitude": 10.0, "sign_lord": "Mars", "star_lord": "Ketu", "sub_lord": "Ketu"},
            {"house": 2, "longitude": 40.0, "sign_lord": "Venus", "star_lord": "Sun", "sub_lord": "Venus"},
        ]
        
        # We need planets to have house occupation. Since we don't calculate it fully in the mock,
        # we just test if the function runs without errors and produces valid structures.
        kp_data = build_kp_significators(planets, cusps)
        
        self.assertIn("cusps", kp_data)
        self.assertIn("house_occupants", kp_data)
        self.assertIn("planet_significators", kp_data)
        self.assertEqual(len(kp_data["cusps"]), 2)
