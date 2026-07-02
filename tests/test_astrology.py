import unittest
import os
from datetime import datetime, timezone

from app.astrology.constants import SIGNS
from app.astrology.divisional import VARGA_ORDER, build_all_divisional_charts, navamsa_sign_index, varga_sign_index
from app.services import answer_generator
from app.services.answer_generator import api_keys_for, llm_context_payload, provider_order
from app.services.chart_calculator import calculate_prashna_chart
from app.astrology.vimshottari import subperiods, vimshottari_from_moon
from app.astrology.zodiac import nakshatra_for, whole_sign_house, zodiac_point


def restore_env(name: str, value) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class AstrologyCalculationTests(unittest.TestCase):
    def test_answer_generator_supports_multiple_provider_keys(self):
        original_keys = os.environ.get("OPENAI_API_KEYS")
        original_key = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_API_KEYS"] = "key-a, key-b"
            os.environ["OPENAI_API_KEY"] = "key-c"
            self.assertEqual(api_keys_for("OPENAI"), ["key-a", "key-b", "key-c"])
        finally:
            restore_env("OPENAI_API_KEYS", original_keys)
            restore_env("OPENAI_API_KEY", original_key)

    def test_answer_generator_loads_local_env_once(self):
        self.assertTrue(hasattr(answer_generator, "load_local_env"))

    def test_provider_order_supports_openrouter_and_cerebras_fallbacks(self):
        saved = {
            name: os.environ.get(name)
            for name in [
                "PRASHNA_LLM_PROVIDER",
                "PRASHNA_LLM_FALLBACK_PROVIDERS",
                "OPENROUTER_API_KEYS",
                "CEREBRAS_API_KEYS",
                "GROQ_API_KEYS",
                "OPENAI_API_KEYS",
                "GEMINI_API_KEYS",
                "GOOGLE_API_KEYS",
            ]
        }
        try:
            for name in saved:
                os.environ.pop(name, None)
            os.environ["PRASHNA_LLM_PROVIDER"] = "groq"
            os.environ["PRASHNA_LLM_FALLBACK_PROVIDERS"] = "openrouter,cerebras,groq"
            os.environ["GROQ_API_KEYS"] = "gsk-test"
            os.environ["OPENROUTER_API_KEYS"] = "sk-or-v1-test-a,sk-or-v1-test-b"
            os.environ["CEREBRAS_API_KEYS"] = "csk-test"
            self.assertEqual(provider_order(), ["groq", "openrouter", "cerebras"])
            self.assertEqual(api_keys_for("OPENROUTER"), ["sk-or-v1-test-a", "sk-or-v1-test-b"])
            self.assertEqual(api_keys_for("CEREBRAS"), ["csk-test"])
        finally:
            for name, value in saved.items():
                restore_env(name, value)

    def test_llm_context_payload_defaults_to_compact_precomputed_context(self):
        original_mode = os.environ.get("PRASHNA_LLM_CONTEXT_MODE")
        try:
            os.environ.pop("PRASHNA_LLM_CONTEXT_MODE", None)
            chart = {
                "question": {
                    "name": "Test",
                    "text": "Will this investment give profit?",
                    "asked_at_local": "2026-06-28T17:30:00+05:30",
                    "place_name": "Delhi",
                    "timezone": "Asia/Kolkata",
                },
                "lagna": {"sign": "Libra", "formatted_degree": "10°00'", "nakshatra": "Swati", "pada": 2},
                "planets": [
                    {"name": "Moon", "sign": "Taurus", "house": 8, "formatted_degree": "12°00'", "nakshatra": "Rohini", "pada": 1, "retrograde": False, "sign_index": 1, "longitude": 42.0},
                    {"name": "Jupiter", "sign": "Cancer", "house": 10, "formatted_degree": "3°00'", "nakshatra": "Pushya", "pada": 1, "retrograde": False, "sign_index": 3, "longitude": 93.0},
                    {"name": "Venus", "sign": "Libra", "house": 1, "formatted_degree": "5°00'", "nakshatra": "Chitra", "pada": 4, "retrograde": False, "sign_index": 6, "longitude": 185.0},
                ],
                "dashas": {"current_mahadasha": {"lord": "Venus"}, "current_antardasha": {"lord": "Jupiter"}},
                "divisional_charts": {"D1": {"Libra": ["Asc", "Venus"], "Taurus": ["Moon"], "Cancer": ["Jupiter"]}},
            }
            interpretation = {
                "domain": "wealth",
                "score": 3,
                "confidence": "Medium",
                "intent": {"focus": "speculation"},
                "key_lords": {"lagna_lord": "Venus", "eleventh_lord": "Jupiter"},
                "verdict": {"summary": "Profit is possible but leakage needs control."},
                "evidence": [
                    {"label": "Gain support", "status": "support", "text": "Jupiter supports gains from the 10th house."},
                    {"label": "Risk warning", "status": "caution", "text": "Moon in the 8th house shows volatility."},
                ],
            }
            payload = llm_context_payload(chart, interpretation)
            self.assertIn("precalculated_judgment", payload)
            self.assertIn("essential_chart_facts", payload)
            self.assertIn("causal_summary", payload["precalculated_judgment"])
            self.assertIn("probability_estimate", payload["precalculated_judgment"])
            self.assertIn("clear_recommendation", payload["precalculated_judgment"])
            self.assertIn("house_role_map", payload["essential_chart_facts"])
            self.assertIn("precomputed_interpretation_blueprint", payload)
            self.assertIn("executive_summary_thesis", payload["precomputed_interpretation_blueprint"])
            self.assertIn("astrological_analysis_plan", payload["precomputed_interpretation_blueprint"])
            self.assertIn("practical_interpretation_plan", payload["precomputed_interpretation_blueprint"])
            self.assertIn("timing_plan", payload["precomputed_interpretation_blueprint"])
            self.assertIn("final_verdict_plan", payload["precomputed_interpretation_blueprint"])
            self.assertIn("probability_estimate", payload["precomputed_interpretation_blueprint"]["final_verdict_plan"])
            self.assertIn("clear_recommendation", payload["precomputed_interpretation_blueprint"]["final_verdict_plan"])
            self.assertIn("explanation_support", payload)
            self.assertIn("vocabulary_variation", payload["explanation_support"])
            self.assertIn("clarity_rewrites", payload["explanation_support"])
            self.assertIn("closing_prompt", payload["explanation_support"])
            self.assertIn("causal_evidence_notes", payload["ranked_evidence"])
            self.assertIn("dasha_synthesis", payload["timing"])
            self.assertIn("practical_window", payload["timing"]["dasha_synthesis"])
            self.assertIn("answer_contract", payload["practical_synthesis_targets"])
            self.assertIn("first_three_lines", payload["practical_synthesis_targets"]["answer_contract"])
            self.assertIn("probability_rule", payload["practical_synthesis_targets"]["answer_contract"])
            self.assertEqual(payload["practical_synthesis_targets"]["section_contract"]["target_total_words"], "1000-1200")
            self.assertEqual(payload["practical_synthesis_targets"]["section_contract"]["minimum_total_words"], 1000)
            self.assertNotIn("planetary_facts", payload)
            self.assertNotIn("divisional_charts", payload)
        finally:
            restore_env("PRASHNA_LLM_CONTEXT_MODE", original_mode)

    def test_llm_context_payload_full_mode_keeps_legacy_debug_payload(self):
        original_mode = os.environ.get("PRASHNA_LLM_CONTEXT_MODE")
        try:
            os.environ["PRASHNA_LLM_CONTEXT_MODE"] = "full"
            chart = {
                "question": {"text": "Will career improve?", "name": "Test"},
                "lagna": {},
                "planets": [],
                "dashas": {},
                "divisional_charts": {},
            }
            interpretation = {"domain": "job_career", "evidence": [], "verdict": {}}
            payload = llm_context_payload(chart, interpretation)
            self.assertIn("planetary_facts", payload)
            self.assertIn("divisional_charts", payload)
        finally:
            restore_env("PRASHNA_LLM_CONTEXT_MODE", original_mode)

    def test_zodiac_point_maps_sign_and_degree(self):
        point = zodiac_point(42.5)
        self.assertEqual(point.sign, "Taurus")
        self.assertEqual(point.degree_in_sign, 12.5)

    def test_nakshatra_and_pada_boundaries(self):
        self.assertEqual(nakshatra_for(0)["name"], "Ashwini")
        self.assertEqual(nakshatra_for(0)["pada"], 1)
        self.assertEqual(nakshatra_for(13.3334)["name"], "Bharani")
        self.assertEqual(nakshatra_for(13.3334)["pada"], 1)

    def test_whole_sign_house_from_lagna(self):
        self.assertEqual(whole_sign_house(10, 0), 1)
        self.assertEqual(whole_sign_house(40, 0), 2)
        self.assertEqual(whole_sign_house(350, 0), 12)
        self.assertEqual(whole_sign_house(10, 6), 7)

    def test_navamsa_sign_rules(self):
        self.assertEqual(navamsa_sign_index(0), 0)
        self.assertEqual(navamsa_sign_index(29.9), 8)
        self.assertEqual(navamsa_sign_index(30), 9)
        self.assertEqual(navamsa_sign_index(60), 6)

    def test_requested_divisional_charts_are_built(self):
        planets = [{"name": "Sun", "longitude": 10}, {"name": "Moon", "longitude": 48}]
        charts = build_all_divisional_charts(planets, {"longitude": 12})
        self.assertEqual(list(charts.keys()), VARGA_ORDER)
        for chart in charts.values():
            self.assertEqual(set(chart.keys()), set(SIGNS))
            self.assertEqual(sum(len(items) for items in chart.values()), 3)

    def test_trimsamsha_uses_unequal_odd_even_spans(self):
        self.assertEqual(varga_sign_index(4.9, "D30"), 0)
        self.assertEqual(varga_sign_index(6, "D30"), 10)
        self.assertEqual(varga_sign_index(48, "D30"), 11)
        self.assertEqual(varga_sign_index(56, "D30"), 7)

    def test_chart_response_includes_all_requested_vargas_and_domain(self):
        chart = calculate_prashna_chart(
            question="Will career improve?",
            name="Test",
            asked_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="job_career",
            question_subdomain="",
        )
        self.assertEqual(list(chart["divisional_charts"].keys()), VARGA_ORDER)
        self.assertEqual(chart["question"]["domain"], "job_career")
        self.assertEqual(chart["question"]["subdomain"], "")
        self.assertIn("D6", chart["divisional_charts"])
        self.assertNotIn("transit", chart)
        self.assertNotIn("interpretation", chart)

    def test_marriage_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will I marry the person I love?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="marriage",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "marriage")
        self.assertEqual(interpretation["intent"]["focus"], "specific_partner")
        self.assertIn("verdict", interpretation)
        self.assertIn("lagna_lord", interpretation["key_lords"])
        self.assertGreaterEqual(len(interpretation["evidence"]), 8)
        self.assertIn("answer", interpretation)
        self.assertEqual(interpretation["answer"]["mode"], "local")
        self.assertIn("Direct Answer", interpretation["answer"]["text"])

    def test_education_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will I clear this competitive exam?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="education",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "education")
        self.assertEqual(interpretation["intent"]["focus"], "exam")
        self.assertEqual(interpretation["key_lords"]["target_house"], "5th")
        self.assertIn("target_lord", interpretation["key_lords"])
        self.assertTrue(any(item["label"] == "D24 dignity" for item in interpretation["evidence"]))

    def test_wealth_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will this stock market investment give profit?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="wealth",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "wealth")
        self.assertEqual(interpretation["intent"]["focus"], "speculation")
        self.assertIn("second_lord", interpretation["key_lords"])
        self.assertIn("eleventh_lord", interpretation["key_lords"])
        self.assertTrue(any(item["label"] == "D4 stability" for item in interpretation["evidence"]))

    def test_child_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will we conceive a child soon?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="child",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "child")
        self.assertEqual(interpretation["intent"]["focus"], "conception")
        self.assertIn("fifth_lord", interpretation["key_lords"])
        self.assertIn("ninth_lord", interpretation["key_lords"])
        self.assertTrue(any(item["label"] == "D7 stability" for item in interpretation["evidence"]))

    def test_illness_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will I recover from this illness soon?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="illness",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "illness")
        self.assertEqual(interpretation["intent"]["focus"], "recovery")
        self.assertIn("sixth_lord", interpretation["key_lords"])
        self.assertIn("tenth_lord", interpretation["key_lords"])
        self.assertTrue(any(item["label"] == "D6 hidden source" for item in interpretation["evidence"]))
        self.assertTrue(any(item["label"] == "Medical note" for item in interpretation["evidence"]))

    def test_foreign_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will my visa get approved for relocation abroad?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="foreign",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "foreign")
        self.assertEqual(interpretation["intent"]["focus"], "visa")
        self.assertIn("twelfth_lord", interpretation["key_lords"])
        self.assertIn("target_lord", interpretation["key_lords"])
        self.assertTrue(any(item["label"] == "D4 residence" for item in interpretation["evidence"]))

    def test_government_job_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will I clear the government job exam and get appointment?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="job_career",
            question_subdomain="government",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "job_career")
        self.assertEqual(interpretation["subdomain"], "government")
        self.assertEqual(interpretation["intent"]["focus"], "competitive_exam")
        self.assertIn("tenth_lord", interpretation["key_lords"])
        self.assertIn("sixth_lord", interpretation["key_lords"])
        self.assertTrue(any(item["label"] == "D10 career" for item in interpretation["evidence"]))

    def test_private_job_prashna_includes_structured_interpretation(self):
        chart = calculate_prashna_chart(
            question="Will I clear the HR interview and get the offer letter?",
            name="Test",
            asked_at_utc=datetime(2026, 6, 28, 12, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            question_domain="job_career",
            question_subdomain="private",
        )
        interpretation = chart["interpretation"]
        self.assertEqual(interpretation["domain"], "job_career")
        self.assertEqual(interpretation["subdomain"], "private")
        self.assertEqual(interpretation["intent"]["focus"], "offer")
        self.assertIn("seventh_lord", interpretation["key_lords"])
        self.assertIn("eleventh_lord", interpretation["key_lords"])
        self.assertTrue(any(item["label"] == "D10 corporate" for item in interpretation["evidence"]))

    def test_lagna_chart_includes_current_transit(self):
        chart = calculate_prashna_chart(
            question="",
            name="Test",
            asked_at_utc=datetime(1990, 1, 1, 6, 30, tzinfo=timezone.utc),
            latitude=28.6139,
            longitude=77.209,
            place_name="Delhi",
            chart_type="lagna",
            gender="male",
        )
        self.assertIn("transit", chart)
        self.assertEqual(chart["transit"]["house_reference"], "birth_lagna")
        self.assertEqual(len(chart["transit"]["planets"]), 9)
        self.assertEqual(set(chart["transit"]["chart"].keys()), set(SIGNS))
        self.assertIn("calculated_at_utc", chart["transit"])

    def test_vimshottari_starts_from_moon_nakshatra_lord(self):
        dasha = vimshottari_from_moon(0, datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(dasha["current_mahadasha"]["lord"], "Ketu")
        self.assertEqual(dasha["current_antardasha"]["lord"], "Ketu")
        self.assertEqual(dasha["current_prana"]["lord"], "Ketu")
        self.assertEqual(dasha["current_mahadasha"]["balance_years"], 7)

    def test_subperiods_start_from_selected_parent_lord(self):
        start = datetime(2030, 3, 1, tzinfo=timezone.utc)
        saturn_children = subperiods("Saturn", start, 19, ["Saturn"])
        self.assertEqual(saturn_children[0]["path"], ["Saturn", "Saturn"])
        self.assertEqual(saturn_children[1]["path"], ["Saturn", "Mercury"])
        self.assertEqual(len(saturn_children), 9)


if __name__ == "__main__":
    unittest.main()
