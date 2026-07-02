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

def interpret_marriage_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    seventh_sign = (lagna_sign + 6) % 12
    second_sign = (lagna_sign + 1) % 12
    eleventh_sign = (lagna_sign + 10) % 12

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    seventh_lord_name = SIGN_LORDS[seventh_sign]
    second_lord_name = SIGN_LORDS[second_sign]
    eleventh_lord_name = SIGN_LORDS[eleventh_sign]

    lagna_lord = planets[lagna_lord_name]
    seventh_lord = planets[seventh_lord_name]
    second_lord = planets[second_lord_name]
    eleventh_lord = planets[eleventh_lord_name]
    moon = planets["Moon"]
    venus = planets["Venus"]
    jupiter = planets["Jupiter"]

    evidence = []
    score = 0
    blockers = 0

    intent = detect_marriage_intent(chart["question"].get("text", ""))
    authenticity = authenticity_check(lagna, moon, planets)
    evidence.append(authenticity)
    if authenticity["status"] == "blocked":
        blockers += 2
        score -= 3
    elif authenticity["status"] == "caution":
        blockers += 1
        score -= 1
    else:
        score += 1

    lord_evidence, lord_score, lord_blockers = analyze_primary_lords(lagna_lord, seventh_lord)
    evidence.extend(lord_evidence)
    score += lord_score
    blockers += lord_blockers

    main_yoga = applying_yoga(lagna_lord, seventh_lord)
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Tajika yoga",
                "strong",
                f"{lagna_lord_name} and {seventh_lord_name} are applying by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 3
        blockers += 1
        evidence.append(
            item(
                "Tajika yoga",
                "blocked",
                f"{lagna_lord_name} and {seventh_lord_name} are separating by {main_yoga['aspect_name']}; the opportunity is moving away unless another bridge forms.",
            )
        )
    else:
        evidence.append(item("Tajika yoga", "caution", "No close applying yoga appears between the Lagna lord and 7th lord."))

    moon_bridge = best_bridge(moon, [seventh_lord, eleventh_lord], {seventh_lord_name, eleventh_lord_name})
    if moon_bridge:
        score += 2
        evidence.append(
            item(
                "Moon bridge",
                "strong",
                f"Moon applies to {moon_bridge['target']} by {moon_bridge['aspect_name']}, supporting external movement toward the answer.",
            )
        )
    elif moon["house"] in HIDDEN_HOUSES:
        score -= 1
        evidence.append(item("Moon bridge", "caution", f"Moon sits in the {ordinal(moon['house'])} house, so the querent's mind is unsettled or hidden."))
    else:
        evidence.append(item("Moon bridge", "neutral", "Moon does not form a close applying bridge to the 7th or 11th lord."))

    support = house_support(second_lord, eleventh_lord)
    score += support["score"]
    blockers += support["blockers"]
    evidence.extend(support["evidence"])

    karakas = karaka_support(venus, jupiter, seventh_sign)
    score += karakas["score"]
    evidence.extend(karakas["evidence"])

    d9 = d9_dignity(chart, [lagna_lord_name, seventh_lord_name])
    score += d9["score"]
    blockers += d9["blockers"]
    evidence.extend(d9["evidence"])

    verdict = verdict_from_score(score, blockers)
    timing = timing_from_yoga(main_yoga, lagna_lord, seventh_lord) if main_yoga["state"] == "applying" else None

    return {
        "domain": "marriage",
        "title": "Marriage Prashna Interpretation",
        "intent": intent,
        "verdict": verdict,
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": timing,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "seventh_lord": seventh_lord_name,
            "second_lord": second_lord_name,
            "eleventh_lord": eleventh_lord_name,
        },
        "evidence": evidence,
    }

def detect_marriage_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["when", "date", "timing", "how long"]):
        focus = "timing"
        summary = "The querent is primarily asking when marriage may happen."
    elif any(word in text for word in ["love", "partner", "boyfriend", "girlfriend", "specific person", "person i"]):
        focus = "specific_partner"
        summary = "The querent is asking about marriage with a specific desired partner."
    elif any(word in text for word in ["delay", "obstacle", "problem", "block"]):
        focus = "obstacles"
        summary = "The querent is asking about delay or obstacles in marriage."
    else:
        focus = "promise"
        summary = "The querent is asking whether marriage is promised from this Prashna."
    return {"focus": focus, "summary": summary}

