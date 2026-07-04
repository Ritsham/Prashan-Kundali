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

def interpret_foreign_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    intent = detect_foreign_intent(chart["question"].get("text", ""))
    target_house = foreign_target_house(intent["focus"])
    target_label = f"{ordinal(target_house)} lord"

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    third_lord_name = SIGN_LORDS[(lagna_sign + 2) % 12]
    fourth_lord_name = SIGN_LORDS[(lagna_sign + 3) % 12]
    seventh_lord_name = SIGN_LORDS[(lagna_sign + 6) % 12]
    ninth_lord_name = SIGN_LORDS[(lagna_sign + 8) % 12]
    twelfth_lord_name = SIGN_LORDS[(lagna_sign + 11) % 12]
    target_lord_name = {
        3: third_lord_name,
        7: seventh_lord_name,
        9: ninth_lord_name,
        12: twelfth_lord_name,
    }[target_house]

    lagna_lord = planets[lagna_lord_name]
    third_lord = planets[third_lord_name]
    fourth_lord = planets[fourth_lord_name]
    seventh_lord = planets[seventh_lord_name]
    ninth_lord = planets[ninth_lord_name]
    twelfth_lord = planets[twelfth_lord_name]
    target_lord = planets[target_lord_name]
    moon = planets["Moon"]
    rahu = planets["Rahu"]
    saturn = planets["Saturn"]
    jupiter = planets["Jupiter"]

    evidence = []
    score = 0
    blockers = 0

    root = travel_root_anchor(lagna_sign, (lagna_sign + 3) % 12, fourth_lord)
    score += root["score"]
    blockers += root["blockers"]
    evidence.extend(root["evidence"])

    bridge = travel_destination_bridge(lagna_lord, target_lord, target_label, fourth_lord, twelfth_lord, intent["focus"])
    score += bridge["score"]
    blockers += bridge["blockers"]
    evidence.extend(bridge["evidence"])

    main_yoga = best_travel_yoga(lagna_lord, moon, [seventh_lord, ninth_lord, twelfth_lord], target_lord)
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Travel Ithasala",
                "strong",
                f"{main_yoga['source']} applies to {main_yoga['target']} by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees; the journey/documentation is moving forward.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 4
        blockers += 2
        evidence.append(
            item(
                "Travel Ithasala",
                "blocked",
                f"{main_yoga['source']} is separating from {main_yoga['target']} by {main_yoga['aspect_name']}; the application or travel window may have slipped.",
            )
        )
    else:
        evidence.append(item("Travel Ithasala", "caution", "No close applying yoga appears between the Lagna/Moon and the 7th, 9th, or 12th lord."))

    roadblocks = travel_roadblocks(lagna_lord, target_lord, planets)
    score += roadblocks["score"]
    blockers += roadblocks["blockers"]
    evidence.extend(roadblocks["evidence"])

    karakas = travel_karakas(rahu, moon, saturn, jupiter, lagna_sign)
    score += karakas["score"]
    blockers += karakas["blockers"]
    evidence.extend(karakas["evidence"])

    settlement = d4_d9_travel_stability(chart, unique_planets([lagna_lord_name, target_lord_name, fourth_lord_name, twelfth_lord_name, "Rahu", "Jupiter"]))
    score += settlement["score"]
    blockers += settlement["blockers"]
    evidence.extend(settlement["evidence"])

    return {
        "domain": "foreign",
        "title": "Foreign Travel and Relocation Prashna Interpretation",
        "intent": intent,
        "verdict": foreign_verdict_from_score(score, blockers, intent["focus"]),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": foreign_timing_from_yoga(main_yoga, main_yoga.get("source_planet"), main_yoga.get("target_planet")) if main_yoga["state"] == "applying" else None,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "third_lord": third_lord_name,
            "fourth_lord": fourth_lord_name,
            "seventh_lord": seventh_lord_name,
            "ninth_lord": ninth_lord_name,
            "twelfth_lord": twelfth_lord_name,
            "target_house": ordinal(target_house),
            "target_lord": target_lord_name,
        },
        "evidence": evidence,
    }

def detect_foreign_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["visa", "passport", "stamp", "immigration", "green card", "pr", "permit"]):
        return {"focus": "visa", "summary": "The querent is asking about visa or immigration documents, so the 9th, 12th, Jupiter, and Rahu lead."}
    if any(word in text for word in ["settle", "relocate", "move abroad", "migration", "permanent", "residency"]):
        return {"focus": "relocation", "summary": "The querent is asking about long-term relocation, so the 12th house and 4th-house detachment lead."}
    if any(word in text for word in ["study abroad", "university", "college", "masters", "phd", "education"]):
        return {"focus": "study_abroad", "summary": "The querent is asking about higher education abroad, so the 9th and 12th houses lead."}
    if any(word in text for word in ["business trip", "conference", "client", "work trip", "holiday", "vacation", "journey"]):
        return {"focus": "journey", "summary": "The querent is asking about a trip or journey, so the 7th/9th houses and Moon lead."}
    if any(word in text for word in ["short trip", "domestic", "commute", "nearby"]):
        return {"focus": "short_travel", "summary": "The querent is asking about short-distance travel, so the 3rd house leads."}
    return {"focus": "foreign_travel", "summary": "The querent is asking about foreign travel or relocation, so the 7th, 9th, 12th, and 4th houses lead."}

def foreign_target_house(focus: str) -> int:
    if focus == "short_travel":
        return 3
    if focus in {"relocation", "visa"}:
        return 12
    if focus == "study_abroad":
        return 9
    if focus == "journey":
        return 7
    return 12

def travel_root_anchor(lagna_sign: int, fourth_sign: int, fourth_lord: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    fixed = {1, 4, 7, 10}
    movable = {0, 3, 6, 9}
    if lagna_sign in movable:
        score += 1
        evidence.append(item("Root anchor", "support", f"Lagna is movable {SIGNS[lagna_sign]}, showing readiness for displacement."))
    elif lagna_sign in fixed:
        score -= 1
        evidence.append(item("Root anchor", "caution", f"Lagna is fixed {SIGNS[lagna_sign]}, anchoring the querent to the current place."))
    else:
        evidence.append(item("Root anchor", "neutral", f"Lagna is dual {SIGNS[lagna_sign]}, showing conditional movement."))

    if fourth_sign in fixed and fourth_lord["house"] in SUPPORT_HOUSES:
        score -= 2
        blockers += 1
        evidence.append(item("Homeland grip", "blocked", f"The 4th house is fixed {SIGNS[fourth_sign]} and its lord is supported; roots are strong and travel may delay."))
    elif fourth_lord["house"] == 12 or fourth_lord["house"] in HIDDEN_HOUSES:
        score += 2
        evidence.append(item("Homeland release", "support", f"The 4th lord sits in the {ordinal(fourth_lord['house'])} house, showing detachment from homeland comforts."))
    else:
        evidence.append(item("Homeland release", "neutral", f"The 4th lord is in the {ordinal(fourth_lord['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def travel_destination_bridge(lagna_lord: dict, target_lord: dict, target_label: str, fourth_lord: dict, twelfth_lord: dict, focus: str) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for label, planet, meaning in [
        ("Lagna lord", lagna_lord, "querent readiness and adaptability"),
        (target_label, target_lord, "destination and travel objective"),
    ]:
        if planet["house"] in HIDDEN_HOUSES and planet["house"] != 12:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house, showing friction or hidden documentation pressure."))
        else:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
    if focus in {"relocation", "visa", "foreign_travel"}:
        if twelfth_lord["house"] in SUPPORT_HOUSES or twelfth_lord["house"] == 12:
            score += 1
            evidence.append(item("12th house", "support", f"{twelfth_lord['name']} makes the foreign-land house active from the {ordinal(twelfth_lord['house'])} house."))
        else:
            evidence.append(item("12th house", "neutral", f"{twelfth_lord['name']} rules foreign land and sits in the {ordinal(twelfth_lord['house'])} house."))
    if fourth_lord["house"] == 12 or twelfth_lord["house"] == 4:
        score += 2
        evidence.append(item("4th-12th link", "strong", "The homeland and foreign-land houses connect, supporting relocation or long-distance displacement."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def best_travel_yoga(lagna_lord: dict, moon: dict, travel_lords: list[dict], target_lord: dict) -> dict:
    candidates = []
    seen = set()
    for target in [target_lord, *travel_lords]:
        if target["name"] in seen:
            continue
        seen.add(target["name"])
        for source, label in [(lagna_lord, lagna_lord["name"]), (moon, "Moon")]:
            if source["name"] == target["name"]:
                continue
            yoga = applying_yoga(source, target)
            if yoga["state"] != "none":
                priority = 0 if target["name"] == target_lord["name"] else 1
                candidates.append({**yoga, "source": label, "source_planet": source, "target": target["name"], "target_planet": target, "priority": priority})
    if not candidates:
        return {"state": "none"}
    applying = [candidate for candidate in candidates if candidate["state"] == "applying"]
    pool = applying or candidates
    return sorted(pool, key=lambda item: (item["priority"], item["degree_gap"]))[0]

def travel_roadblocks(lagna_lord: dict, target_lord: dict, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for name, meaning in [
        ("Saturn", "bureaucratic delay, backlogs, appointment cancellation, or long processing"),
        ("Mars", "technical rejection, rushed errors, conflict with officials, or schedule disruption"),
        ("Rahu", "unusual documentation, foreign-system complexity, or unconventional route"),
        ("Ketu", "missing paperwork, detachment, sudden cancellation, or unclear status"),
    ]:
        planet = planets[name]
        touches_path = aspect_between(planet["longitude"], lagna_lord["longitude"]) or aspect_between(planet["longitude"], target_lord["longitude"])
        if touches_path and planet["house"] in HIDDEN_HOUSES:
            score -= 2
            blockers += 1
            evidence.append(item("Travel roadblock", "blocked", f"{name} blocks the travel path from the {ordinal(planet['house'])} house: {meaning}."))
        elif touches_path:
            score -= 1
            evidence.append(item("Travel roadblock", "caution", f"{name} contacts the travel path, indicating {meaning}."))
    if not evidence:
        evidence.append(item("Travel roadblock", "support", "Saturn, Mars, Rahu, and Ketu do not strongly interrupt the travel path."))
        score += 1
    return {"score": score, "blockers": blockers, "evidence": evidence}

def travel_karakas(rahu: dict, moon: dict, saturn: dict, jupiter: dict, lagna_sign: int) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (rahu, "Rahu", "foreign elements, visas, cross-border systems, and cultural breakaway"),
        (moon, "Moon", "movement speed, mental flexibility, and immediate travel flow"),
        (saturn, "Saturn", "long-term settlement, structured displacement, and durable relocation"),
        (jupiter, "Jupiter", "legal documents, sponsorship, visas, and higher learning abroad"),
    ]:
        if planet["house"] in {7, 9, 12, 1}:
            score += 1
            evidence.append(item(label, "support", f"{label} activates travel terrain from the {ordinal(planet['house'])} house: {meaning}."))
        elif planet["house"] in HIDDEN_HOUSES and planet["house"] != 12:
            score -= 1
            blockers += 1 if label in {"Rahu", "Jupiter"} else 0
            evidence.append(item(label, "caution", f"{label} is in the {ordinal(planet['house'])} house, complicating {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{label} is in the {ordinal(planet['house'])} house."))
    if rahu["house"] in {1, 7} and aspect_between(rahu["longitude"], (lagna_sign + 8) % 12 * 30.0):
        score += 2
        evidence.append(item("Rahu alignment", "strong", "Rahu links the self/far horizon with the 9th-house direction, making foreign breakaway highly active."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d4_d9_travel_stability(chart: dict, planet_names: list[str]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    for varga, label in [("D4", "D4 residence"), ("D9", "D9 support")]:
        lagna_sign = varga_sign_index(chart["lagna"]["longitude"], varga)
        for name in planet_names:
            planet = planets[name]
            sign = varga_sign_index(planet["longitude"], varga)
            house = whole_sign_house(sign * 30.0, lagna_sign)
            if house in {9, 12} and DEBILITATION_SIGNS.get(name) != sign:
                score += 1
                evidence.append(item(label, "support", f"{name} falls in the {varga} {ordinal(house)} house, supporting distance, settlement, or horizon expansion."))
            elif DEBILITATION_SIGNS.get(name) == sign:
                score -= 2
                blockers += 1
                evidence.append(item(label, "blocked", f"{name} is debilitated in {varga} {SIGNS[sign]}, weakening travel/settlement quality."))
            elif house in HIDDEN_HOUSES and house != 12:
                score -= 1
                evidence.append(item(label, "caution", f"{name} falls in the {varga} {ordinal(house)} house, bringing friction, expense, or loneliness."))
            else:
                evidence.append(item(label, "neutral", f"{name} falls in {varga} {SIGNS[sign]}, house {house}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def foreign_verdict_from_score(score: int, blockers: int, focus: str) -> dict:
    target = {
        "visa": "visa or documentation",
        "relocation": "foreign relocation",
        "study_abroad": "study-abroad move",
        "journey": "journey",
        "short_travel": "short-distance travel",
    }.get(focus, "foreign travel")
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": f"The {target} is not clearly promised now; anchoring, paperwork, or roadblocks dominate."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": f"The {target} is strongly supported, with movement and foreign-land indicators cooperating."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": f"The {target} can happen, but documentation, timing, or root-detachment needs careful handling."}
    return {"level": "uncertain", "summary": "The chart is mixed; desire to move is visible, but the path is not fully open yet."}

def foreign_timing_from_yoga(yoga: dict, first: dict | None, second: dict | None) -> dict | None:
    if not first or not second:
        return None
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9} or first["house"] in {1, 4, 7, 10} or second["house"] in {1, 4, 7, 10}:
        unit = "days to a few weeks"
    elif sign_index in {2, 5, 8, 11}:
        unit = "weeks to months"
    else:
        unit = "processing-window weeks to months"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the departure/approval timing seed, read as {unit}.",
    }

