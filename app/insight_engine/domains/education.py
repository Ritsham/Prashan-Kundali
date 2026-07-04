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


from app.insight_engine.rules.common import *

def interpret_education_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    intent = detect_education_intent(chart["question"].get("text", ""))
    target_house = 9 if intent["focus"] in {"higher_education", "research", "foreign_admission"} else 5
    target_label = "9th lord" if target_house == 9 else "5th lord"
    target_sign = (lagna_sign + target_house - 1) % 12

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    target_lord_name = SIGN_LORDS[target_sign]
    fourth_lord_name = SIGN_LORDS[(lagna_sign + 3) % 12]
    ninth_lord_name = SIGN_LORDS[(lagna_sign + 8) % 12]

    lagna_lord = planets[lagna_lord_name]
    target_lord = planets[target_lord_name]
    fourth_lord = planets[fourth_lord_name]
    ninth_lord = planets[ninth_lord_name]
    moon = planets["Moon"]
    mercury = planets["Mercury"]
    jupiter = planets["Jupiter"]

    evidence = []
    score = 0
    blockers = 0

    cognitive = cognitive_filter(lagna, moon, planets)
    evidence.append(cognitive)
    if cognitive["status"] == "blocked":
        blockers += 2
        score -= 3
    elif cognitive["status"] == "caution":
        blockers += 1
        score -= 1
    else:
        score += 1

    lord_evidence, lord_score, lord_blockers = analyze_education_lords(lagna_lord, target_lord, target_label)
    evidence.extend(lord_evidence)
    score += lord_score
    blockers += lord_blockers

    main_yoga = applying_yoga(lagna_lord, target_lord)
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Tajika yoga",
                "strong",
                f"{lagna_lord_name} and {target_lord_name} are applying by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 3
        blockers += 1
        evidence.append(
            item(
                "Tajika yoga",
                "blocked",
                f"{lagna_lord_name} and {target_lord_name} are separating by {main_yoga['aspect_name']}; the peak window may have passed.",
            )
        )
    else:
        evidence.append(item("Tajika yoga", "caution", f"No close applying yoga appears between the Lagna lord and {target_label}."))

    obstacles = education_obstacles(lagna_lord, target_lord, planets)
    score += obstacles["score"]
    blockers += obstacles["blockers"]
    evidence.extend(obstacles["evidence"])

    foundation = education_foundation(fourth_lord, ninth_lord, target_house)
    score += foundation["score"]
    blockers += foundation["blockers"]
    evidence.extend(foundation["evidence"])

    karakas = education_karakas(mercury, jupiter, moon)
    score += karakas["score"]
    blockers += karakas["blockers"]
    evidence.extend(karakas["evidence"])

    d24 = d24_dignity(chart, unique_planets(["Mercury", "Jupiter", lagna_lord_name, target_lord_name]))
    score += d24["score"]
    blockers += d24["blockers"]
    evidence.extend(d24["evidence"])

    return {
        "domain": "education",
        "title": "Education Prashna Interpretation",
        "intent": intent,
        "verdict": education_verdict_from_score(score, blockers, target_house),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": education_timing_from_yoga(main_yoga, lagna_lord, target_lord) if main_yoga["state"] == "applying" else None,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "target_house": ordinal(target_house),
            "target_lord": target_lord_name,
            "fourth_lord": fourth_lord_name,
            "ninth_lord": ninth_lord_name,
        },
        "evidence": evidence,
    }

def detect_education_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["phd", "doctorate", "research", "thesis"]):
        return {"focus": "research", "summary": "The querent is asking about research or advanced academic mastery, so the 9th house leads."}
    if any(word in text for word in ["foreign", "abroad", "visa", "overseas", "international"]):
        return {"focus": "foreign_admission", "summary": "The querent is asking about foreign admission or overseas education, so the 9th house leads."}
    if any(word in text for word in ["college", "university", "admission", "masters", "postgraduate", "degree"]):
        return {"focus": "higher_education", "summary": "The querent is asking about admission or higher education, so the 9th house leads."}
    if any(word in text for word in ["exam", "test", "rank", "clear", "pass", "interview", "competitive"]):
        return {"focus": "exam", "summary": "The querent is asking about exam success or ranking, so the 5th house leads."}
    if any(word in text for word in ["focus", "study", "learn", "memory", "concentration", "preparation"]):
        return {"focus": "study_capacity", "summary": "The querent is asking about learning capacity and preparation, so the 5th house leads with support from the 4th."}
    return {"focus": "academic_progress", "summary": "The querent is asking about general academic progress, so the 5th house leads."}

def cognitive_filter(lagna: dict, moon: dict, planets: dict[str, dict]) -> dict:
    moon_node_pressure = any(
        planet["name"] in {"Rahu", "Ketu"} and aspect_between(planet["longitude"], moon["longitude"])
        for planet in planets.values()
    )
    lagna_afflictions = [
        planet["name"]
        for planet in planets.values()
        if planet["name"] in MALEFICS and planet["house"] == 1
    ]
    if moon["house"] in HIDDEN_HOUSES and moon_node_pressure:
        return item("Cognitive filter", "blocked", f"Moon is in the {ordinal(moon['house'])} house under nodal pressure; panic or burnout is overwhelming the question.")
    if moon["house"] in HIDDEN_HOUSES:
        return item("Cognitive filter", "caution", f"Moon is in the {ordinal(moon['house'])} house, showing anxiety, distraction, or self-doubt.")
    if moon_node_pressure:
        return item("Cognitive filter", "caution", "Moon is under Rahu/Ketu pressure, so concentration may fluctuate sharply.")
    if lagna_afflictions:
        return item("Cognitive filter", "caution", f"Lagna has pressure from {', '.join(lagna_afflictions)}, so academic stress is visible.")
    return item("Cognitive filter", "clear", f"Lagna is {lagna['sign']} and Moon is in the {ordinal(moon['house'])} house; the student's mind is readable.")

def analyze_education_lords(lagna_lord: dict, target_lord: dict, target_label: str) -> tuple[list[dict], int, int]:
    evidence = []
    score = 0
    blockers = 0
    for label, planet in [("Lagna lord", lagna_lord), (target_label, target_lord)]:
        if planet["house"] in SUPPORT_HOUSES:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} is in the {ordinal(planet['house'])} house, giving usable academic momentum."))
        elif planet["house"] in HIDDEN_HOUSES:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house, showing resistance, fatigue, or hidden obstacles."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} is in the {ordinal(planet['house'])} house."))
    if lagna_lord["house"] in {5, 9} or target_lord["house"] == 1:
        score += 2
        evidence.append(item("Action alignment", "strong", "The student and academic target are directly connected by house placement."))
    return evidence, score, blockers

def education_obstacles(lagna_lord: dict, target_lord: dict, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for name, meaning in [
        ("Saturn", "delay, red tape, fatigue, or slow administrative movement"),
        ("Mars", "rushing, technical mistakes, conflict, or severe competition"),
    ]:
        planet = planets[name]
        touches_path = aspect_between(planet["longitude"], lagna_lord["longitude"]) or aspect_between(planet["longitude"], target_lord["longitude"])
        if touches_path and planet["house"] in HIDDEN_HOUSES:
            score -= 2
            blockers += 1
            evidence.append(item("Disrupting factor", "blocked", f"{name} pressures the academic path from the {ordinal(planet['house'])} house: {meaning}."))
        elif touches_path:
            score -= 1
            evidence.append(item("Disrupting factor", "caution", f"{name} contacts the academic path, indicating {meaning}."))
    if not evidence:
        evidence.append(item("Disrupting factor", "neutral", "Saturn and Mars do not strongly interrupt the student-target connection."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def education_foundation(fourth_lord: dict, ninth_lord: dict, target_house: int) -> dict:
    evidence = []
    score = 0
    blockers = 0
    if fourth_lord["house"] in HIDDEN_HOUSES:
        score -= 1
        blockers += 1
        evidence.append(item("4th house", "caution", f"{fourth_lord['name']} rules study foundation and sits in the {ordinal(fourth_lord['house'])} house."))
    else:
        score += 1
        evidence.append(item("4th house", "support", f"{fourth_lord['name']} supports memory and study environment from the {ordinal(fourth_lord['house'])} house."))

    if target_house == 9:
        if ninth_lord["house"] in HIDDEN_HOUSES:
            score -= 2
            blockers += 1
            evidence.append(item("9th house", "blocked", f"{ninth_lord['name']} rules higher education and sits in the {ordinal(ninth_lord['house'])} house."))
        else:
            score += 1
            evidence.append(item("9th house", "support", f"{ninth_lord['name']} supports higher education, mentors, and institutional luck."))
    else:
        evidence.append(item("9th house", "neutral", "The 9th house is secondary for this education query."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def education_karakas(mercury: dict, jupiter: dict, moon: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (mercury, "Mercury", "logic, writing, analysis, and exam execution"),
        (jupiter, "Jupiter", "conceptual understanding and teacher guidance"),
    ]:
        if planet["retrograde"] or planet["house"] in HIDDEN_HOUSES:
            score -= 1
            blockers += 1 if planet["house"] in HIDDEN_HOUSES else 0
            reason = "retrograde" if planet["retrograde"] else f"in the {ordinal(planet['house'])} house"
            evidence.append(item(label, "caution", f"{label} is {reason}, weakening {meaning}."))
        else:
            score += 1
            evidence.append(item(label, "support", f"{label} supports {meaning} from the {ordinal(planet['house'])} house."))
    if moon["house"] in {1, 4, 5, 9, 10, 11}:
        score += 1
        evidence.append(item("Moon", "support", f"Moon in the {ordinal(moon['house'])} house supports attention and response speed."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d24_dignity(chart: dict, planet_names: list[str]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna_sign = varga_sign_index(chart["lagna"]["longitude"], "D24")
    for name in planet_names:
        planet = planets[name]
        sign = varga_sign_index(planet["longitude"], "D24")
        house = whole_sign_house(sign * 30.0, lagna_sign)
        if DEBILITATION_SIGNS.get(name) == sign:
            score -= 2
            blockers += 1
            evidence.append(item("D24 dignity", "blocked", f"{name} is debilitated in D24 {SIGNS[sign]}, weakening learning depth."))
        elif EXALTATION_SIGNS.get(name) == sign or SIGN_LORDS[sign] == name:
            score += 1
            evidence.append(item("D24 dignity", "support", f"{name} is strong in D24 {SIGNS[sign]}, supporting mastery."))
        elif house in HIDDEN_HOUSES:
            score -= 1
            evidence.append(item("D24 dignity", "caution", f"{name} falls in the D24 {ordinal(house)} house, so sustained study needs discipline."))
        else:
            evidence.append(item("D24 dignity", "neutral", f"{name} falls in D24 {SIGNS[sign]}, house {house}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def education_verdict_from_score(score: int, blockers: int, target_house: int) -> dict:
    target = "higher education/admission" if target_house == 9 else "exam or academic target"
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": f"The {target} is not clearly promised now; stress, delay, or weak execution dominates."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": f"The {target} is strongly supported if the student acts with focus while the chart is active."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": f"The {target} is possible, but it needs disciplined preparation and careful handling of obstacles."}
    return {"level": "uncertain", "summary": "The chart is mixed; ability is present, but opportunity and execution are not fully aligned."}

def education_timing_from_yoga(yoga: dict, first: dict, second: dict) -> dict:
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9}:
        unit = "days to weeks"
    elif sign_index in {2, 5, 8, 11}:
        unit = "weeks to months"
    else:
        unit = "months, with sustained effort"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the timing seed for result/admission movement, read as {unit}.",
    }

