from __future__ import annotations

from app.astrology.constants import SIGNS
from app.astrology.divisional import varga_sign_index
from app.astrology.zodiac import normalize_degrees, whole_sign_house


SIGN_LORDS = {
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

EXALTATION_SIGNS = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 9,
    "Mercury": 5,
    "Jupiter": 3,
    "Venus": 11,
    "Saturn": 6,
}

DEBILITATION_SIGNS = {
    "Sun": 6,
    "Moon": 7,
    "Mars": 3,
    "Mercury": 11,
    "Jupiter": 9,
    "Venus": 5,
    "Saturn": 0,
}

MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}
HIDDEN_HOUSES = {6, 8, 12}
SUPPORT_HOUSES = {1, 4, 5, 7, 9, 10, 11}
FAVORABLE_ASPECTS = {0, 60, 120}
ASPECT_ORB = 6.0
FRUITFUL_SIGNS = {3, 7, 11}
BARREN_SIGNS = {0, 2, 4, 5}


from app.insight_engine.rules.common import (
    ASPECT_ORB, BARREN_SIGNS, BENEFICS, DEBILITATION_SIGNS,
    EXALTATION_SIGNS, FAVORABLE_ASPECTS, FRUITFUL_SIGNS,
    HIDDEN_HOUSES, MALEFICS, SIGN_LORDS, SUPPORT_HOUSES,
    planet_strength_score, applying_yoga, aspect_between,
    aspect_gap, aspect_name, confidence_label, gap_is_widening,
    item, ordinal, timing_from_yoga, unique_planets,
    verdict_from_score,
)
from app.insight_engine.domains.marriage import interpret_marriage_prashna
from app.insight_engine.domains.education import interpret_education_prashna
from app.insight_engine.domains.wealth import interpret_wealth_prashna
from app.insight_engine.domains.child import interpret_child_prashna
from app.insight_engine.domains.illness import interpret_illness_prashna
from app.insight_engine.domains.foreign import interpret_foreign_prashna
from app.insight_engine.domains.career import (
    interpret_government_job_prashna,
    interpret_private_job_prashna,
)


def build_interpretation(chart: dict) -> dict | None:
    if chart.get("meta", {}).get("chart_type") != "prashna":
        return None
    domain, subdomain = normalized_question_domain(chart)
    if domain == "marriage":
        return interpret_marriage_prashna(chart)
    if domain == "education":
        return interpret_education_prashna(chart)
    if domain == "wealth":
        return interpret_wealth_prashna(chart)
    if domain == "child":
        return interpret_child_prashna(chart)
    if domain == "illness":
        return interpret_illness_prashna(chart)
    if domain == "foreign":
        return interpret_foreign_prashna(chart)
    if domain == "job_career" and subdomain == "government":
        return interpret_government_job_prashna(chart)
    if domain == "job_career" and subdomain == "private":
        return interpret_private_job_prashna(chart)
    return interpret_general_prashna(chart, domain)

def normalized_question_domain(chart: dict) -> tuple[str, str]:
    question = chart.get("question", {})
    domain = (question.get("domain") or "").strip()
    subdomain = (question.get("subdomain") or "").strip()
    text = question.get("text", "")
    if not domain:
        domain = infer_question_domain(text)
    if domain == "job_career" and not subdomain:
        subdomain = infer_job_subdomain(text)
    return domain, subdomain

def infer_question_domain(question: str) -> str:
    text = question.lower()
    keyword_domains = [
        ("marriage", ["marriage", "marry", "wedding", "spouse", "husband", "wife", "relationship", "love", "partner"]),
        ("education", ["exam", "study", "education", "college", "school", "admission", "degree", "marks", "research", "phd"]),
        ("wealth", ["money", "wealth", "income", "salary", "profit", "loss", "loan", "property", "fund", "payment", "investment"]),
        ("child", ["child", "baby", "pregnancy", "pregnant", "conceive", "conception", "progeny"]),
        ("illness", ["health", "illness", "disease", "recover", "recovery", "doctor", "medicine", "surgery", "pain", "fever"]),
        ("foreign", ["foreign", "abroad", "visa", "travel", "journey", "relocate", "relocation", "passport", "immigration"]),
        ("job_career", ["job", "career", "work", "interview", "promotion", "business", "government", "private", "office"]),
    ]
    for domain, keywords in keyword_domains:
        if any(keyword in text for keyword in keywords):
            return domain
    return "general"

def infer_job_subdomain(question: str) -> str:
    text = question.lower()
    if any(word in text for word in ["government", "govt", "sarkari", "state job", "civil service", "public sector"]):
        return "government"
    if any(word in text for word in ["private", "company", "corporate", "startup", "interview", "offer", "package"]):
        return "private"
    return ""

def interpret_general_prashna(chart: dict, domain: str = "general") -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    lagna_lord_name = SIGN_LORDS[lagna_sign]
    fourth_lord_name = SIGN_LORDS[(lagna_sign + 3) % 12]
    seventh_lord_name = SIGN_LORDS[(lagna_sign + 6) % 12]
    tenth_lord_name = SIGN_LORDS[(lagna_sign + 9) % 12]
    eleventh_lord_name = SIGN_LORDS[(lagna_sign + 10) % 12]

    lagna_lord = planets[lagna_lord_name]
    fourth_lord = planets[fourth_lord_name]
    seventh_lord = planets[seventh_lord_name]
    tenth_lord = planets[tenth_lord_name]
    eleventh_lord = planets[eleventh_lord_name]
    moon = planets["Moon"]

    evidence = []
    score = 0
    blockers = 0
    intent = detect_general_intent(chart["question"].get("text", ""), domain)

    authenticity = authenticity_check(lagna, moon, planets)
    evidence.append(authenticity)
    if authenticity["status"] == "blocked":
        score -= 3
        blockers += 2
    elif authenticity["status"] == "caution":
        score -= 1
        blockers += 1
    else:
        score += 1

    readiness = general_readiness(lagna_lord, moon)
    score += readiness["score"]
    blockers += readiness["blockers"]
    evidence.extend(readiness["evidence"])

    outcome = general_outcome_support(fourth_lord, tenth_lord, eleventh_lord)
    score += outcome["score"]
    blockers += outcome["blockers"]
    evidence.extend(outcome["evidence"])

    main_yoga = best_general_yoga(lagna_lord, moon, [eleventh_lord, tenth_lord, fourth_lord, seventh_lord])
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Main Prashna yoga",
                "strong",
                f"{main_yoga['source']} applies to {main_yoga['target']} by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees; the matter is moving toward manifestation.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 3
        blockers += 1
        evidence.append(
            item(
                "Main Prashna yoga",
                "blocked",
                f"{main_yoga['source']} separates from {main_yoga['target']} by {main_yoga['aspect_name']}; the strongest opening may be passing or needs renewed effort.",
            )
        )
    else:
        evidence.append(item("Main Prashna yoga", "caution", "No close applying Tajika yoga connects the querent with fulfilment, action, conclusion, or the other party."))

    obstacles = general_obstacles(lagna_lord, moon, planets)
    score += obstacles["score"]
    blockers += obstacles["blockers"]
    evidence.extend(obstacles["evidence"])

    return {
        "domain": domain or "general",
        "title": "General Prashna Interpretation",
        "intent": intent,
        "verdict": general_verdict_from_score(score, blockers),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": timing_from_yoga(main_yoga, main_yoga.get("source_planet"), main_yoga.get("target_planet")) if main_yoga["state"] == "applying" else None,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "fourth_lord": fourth_lord_name,
            "seventh_lord": seventh_lord_name,
            "tenth_lord": tenth_lord_name,
            "eleventh_lord": eleventh_lord_name,
        },
        "evidence": evidence,
    }

def best_general_yoga(lagna_lord: dict, moon: dict, targets: list[dict]) -> dict:
    candidates = []
    for target in targets:
        for source, source_label in [(lagna_lord, lagna_lord["name"]), (moon, "Moon")]:
            if source["name"] == target["name"]:
                continue
            yoga = applying_yoga(source, target)
            if yoga["state"] != "none":
                candidates.append({**yoga, "source": source_label, "source_planet": source, "target": target["name"], "target_planet": target})
    if not candidates:
        return {"state": "none"}
    applying = [candidate for candidate in candidates if candidate["state"] == "applying"]
    pool = applying or candidates
    return sorted(pool, key=lambda item: item["degree_gap"])[0]

def general_obstacles(lagna_lord: dict, moon: dict, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for name in ["Saturn", "Mars", "Rahu", "Ketu"]:
        planet = planets[name]
        touches_querent = aspect_between(planet["longitude"], lagna_lord["longitude"]) or aspect_between(planet["longitude"], moon["longitude"])
        if touches_querent and planet["house"] in HIDDEN_HOUSES:
            score -= 2
            blockers += 1
            evidence.append(item("Obstacle pressure", "blocked", f"{name} pressures the querent/Moon from the {ordinal(planet['house'])} house, showing hidden resistance or delay."))
        elif touches_querent:
            score -= 1
            evidence.append(item("Obstacle pressure", "caution", f"{name} contacts the querent/Moon, so effort must be steady and not impulsive."))
    if not evidence:
        score += 1
        evidence.append(item("Obstacle pressure", "support", "Major malefics do not closely block the querent or Moon, so the matter has room to proceed."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def general_verdict_from_score(score: int, blockers: int) -> dict:
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": "The answer leans negative or delayed right now; obstacles, hidden pressure, or weak fulfilment dominate the chart."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": "The answer leans strongly positive; the chart shows readiness, action, and fulfilment working together."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": "The matter can work, but it needs correct action, patience, and attention to the pressure points shown in the chart."}
    return {"level": "uncertain", "summary": "The chart is mixed; the desire is visible, but the result is not fully secured yet."}

