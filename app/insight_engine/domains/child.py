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

def interpret_child_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    fifth_sign = (lagna_sign + 4) % 12
    ninth_sign = (lagna_sign + 8) % 12
    seventh_sign = (lagna_sign + 6) % 12
    second_sign = (lagna_sign + 1) % 12

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    fifth_lord_name = SIGN_LORDS[fifth_sign]
    ninth_lord_name = SIGN_LORDS[ninth_sign]
    seventh_lord_name = SIGN_LORDS[seventh_sign]
    second_lord_name = SIGN_LORDS[second_sign]

    lagna_lord = planets[lagna_lord_name]
    fifth_lord = planets[fifth_lord_name]
    ninth_lord = planets[ninth_lord_name]
    seventh_lord = planets[seventh_lord_name]
    second_lord = planets[second_lord_name]
    jupiter = planets["Jupiter"]
    moon = planets["Moon"]
    mars = planets["Mars"]
    venus = planets["Venus"]

    evidence = []
    score = 0
    blockers = 0
    intent = detect_child_intent(chart["question"].get("text", ""))

    fertility = fertility_sign_check(lagna_sign, fifth_sign, fifth_lord, planets)
    score += fertility["score"]
    blockers += fertility["blockers"]
    evidence.extend(fertility["evidence"])

    bridge = child_creation_bridge(lagna_lord, fifth_lord, jupiter)
    score += bridge["score"]
    blockers += bridge["blockers"]
    evidence.extend(bridge["evidence"])

    main_yoga = best_child_yoga(lagna_lord, moon, fifth_lord)
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Conception Ithasala",
                "strong",
                f"{main_yoga['source']} applies to {fifth_lord_name} by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees; conception or child-related progress is approaching.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 4
        blockers += 2
        evidence.append(
            item(
                "Conception Ithasala",
                "blocked",
                f"{main_yoga['source']} is separating from {fifth_lord_name} by {main_yoga['aspect_name']}; the fertile window or immediate opportunity may have passed.",
            )
        )
    else:
        evidence.append(item("Conception Ithasala", "caution", "No close applying yoga appears between the Lagna/Moon and the 5th lord."))

    afflictions = child_afflictions(fifth_lord, jupiter, fifth_sign, planets)
    score += afflictions["score"]
    blockers += afflictions["blockers"]
    evidence.extend(afflictions["evidence"])

    support = child_family_support(seventh_lord, second_lord, ninth_lord, jupiter)
    score += support["score"]
    blockers += support["blockers"]
    evidence.extend(support["evidence"])

    karakas = child_karakas(jupiter, moon, mars, venus, fifth_sign)
    score += karakas["score"]
    blockers += karakas["blockers"]
    evidence.extend(karakas["evidence"])

    d7 = d7_lineage_stability(chart, unique_planets([fifth_lord_name, "Jupiter", "Moon", lagna_lord_name]))
    score += d7["score"]
    blockers += d7["blockers"]
    evidence.extend(d7["evidence"])

    return {
        "domain": "child",
        "title": "Childbirth and Progeny Prashna Interpretation",
        "intent": intent,
        "verdict": child_verdict_from_score(score, blockers, intent["focus"]),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": child_timing_from_yoga(main_yoga, main_yoga.get("source_planet"), fifth_lord) if main_yoga["state"] == "applying" else None,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "fifth_lord": fifth_lord_name,
            "ninth_lord": ninth_lord_name,
            "seventh_lord": seventh_lord_name,
            "second_lord": second_lord_name,
        },
        "evidence": evidence,
    }

def detect_child_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["pregnant", "pregnancy", "safe", "miscarriage", "health", "delivery"]):
        return {"focus": "pregnancy_safety", "summary": "The querent is asking about pregnancy safety or child wellbeing, so the 5th lord, Moon, Jupiter, and D7 are critical."}
    if any(word in text for word in ["conceive", "conception", "fertile", "fertility", "ivf", "treatment"]):
        return {"focus": "conception", "summary": "The querent is asking about conception, so the 1st, 5th, Moon, Jupiter, Venus, and Mars lead."}
    if any(word in text for word in ["delay", "problem", "blocked", "issue", "when"]):
        return {"focus": "delay", "summary": "The querent is asking about delay or timing for children, so afflictions and applying yogas lead."}
    if any(word in text for word in ["son", "daughter", "child", "baby", "children", "progeny"]):
        return {"focus": "progeny", "summary": "The querent is asking about childbirth or progeny promise, so the 5th and 9th houses lead."}
    return {"focus": "progeny", "summary": "The querent is asking about children, so the 5th house, Jupiter, Moon, and D7 lead."}

def fertility_sign_check(lagna_sign: int, fifth_sign: int, fifth_lord: dict, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    if lagna_sign in FRUITFUL_SIGNS:
        score += 1
        evidence.append(item("Fertility signs", "support", f"Lagna falls in fruitful {SIGNS[lagna_sign]}, supporting biological readiness."))
    elif lagna_sign in BARREN_SIGNS:
        score -= 1
        evidence.append(item("Fertility signs", "caution", f"Lagna falls in barren {SIGNS[lagna_sign]}, showing reduced ease or delay."))
    else:
        evidence.append(item("Fertility signs", "neutral", f"Lagna falls in neutral {SIGNS[lagna_sign]}."))

    fifth_afflicted = any(
        planet["name"] in MALEFICS and aspect_between(planet["longitude"], fifth_sign * 30.0)
        for planet in planets.values()
    )
    fifth_lord_barren = fifth_lord["sign_index"] in BARREN_SIGNS
    if fifth_sign in FRUITFUL_SIGNS and not fifth_afflicted:
        score += 2
        evidence.append(item("5th house", "support", f"The 5th house falls in fruitful {SIGNS[fifth_sign]} without close malefic pressure."))
    elif fifth_sign in BARREN_SIGNS and fifth_lord_barren and fifth_afflicted:
        score -= 3
        blockers += 2
        evidence.append(item("5th house", "blocked", "The 5th house and 5th lord are in barren signs under malefic pressure, showing biological delay or blockage."))
    elif fifth_sign in BARREN_SIGNS or fifth_lord_barren or fifth_afflicted:
        score -= 1
        blockers += 1
        evidence.append(item("5th house", "caution", "The 5th-house fertility signal is mixed by barren sign placement or malefic pressure."))
    else:
        evidence.append(item("5th house", "neutral", f"The 5th house falls in {SIGNS[fifth_sign]} with moderate fertility support."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def child_creation_bridge(lagna_lord: dict, fifth_lord: dict, jupiter: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for label, planet, meaning in [
        ("Lagna lord", lagna_lord, "querent readiness and vitality"),
        ("5th lord", fifth_lord, "conception, embryo, and progeny promise"),
        ("Jupiter", jupiter, "children, expansion, and divine grace"),
    ]:
        if planet["house"] in SUPPORT_HOUSES:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
        elif planet["house"] in HIDDEN_HOUSES:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house, weakening {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} is in the {ordinal(planet['house'])} house."))
    if aspect_between(jupiter["longitude"], fifth_lord["longitude"]) or aspect_between(jupiter["longitude"], (fifth_lord["sign_index"] * 30.0)):
        score += 2
        evidence.append(item("Jupiter grace", "strong", "Jupiter closely supports the 5th lord/sign, giving protective grace for progeny."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def best_child_yoga(lagna_lord: dict, moon: dict, fifth_lord: dict) -> dict:
    candidates = []
    for source, label in [(lagna_lord, lagna_lord["name"]), (moon, "Moon")]:
        yoga = applying_yoga(source, fifth_lord)
        if yoga["state"] != "none":
            candidates.append({**yoga, "source": label, "source_planet": source})
    if not candidates:
        return {"state": "none"}
    applying = [candidate for candidate in candidates if candidate["state"] == "applying"]
    pool = applying or candidates
    return sorted(pool, key=lambda item: item["degree_gap"])[0]

def child_afflictions(fifth_lord: dict, jupiter: dict, fifth_sign: int, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label in [(fifth_lord, "5th lord"), (jupiter, "Jupiter")]:
        if planet["retrograde"]:
            score -= 1
            evidence.append(item("Retrogression", "caution", f"{label} {planet['name']} is retrograde, showing delays or repeated treatment/revision."))
        if DEBILITATION_SIGNS.get(planet["name"]) == planet["sign_index"]:
            score -= 2
            blockers += 1
            evidence.append(item("Affliction", "blocked", f"{label} {planet['name']} is debilitated in {planet['sign']}."))

    rahu = planets["Rahu"]
    ketu = planets["Ketu"]
    fifth_house_lon = fifth_sign * 30.0
    if aspect_between(rahu["longitude"], fifth_house_lon) or aspect_between(ketu["longitude"], fifth_house_lon):
        score -= 2
        blockers += 1
        evidence.append(item("Nodal pressure", "blocked", "Rahu/Ketu pressure on the 5th house shows hidden fears, stress, or karmic/genetic complications."))

    malefic_pressure = [
        planet["name"]
        for planet in planets.values()
        if planet["name"] in MALEFICS and aspect_between(planet["longitude"], fifth_lord["longitude"])
    ]
    if malefic_pressure:
        score -= 1
        evidence.append(item("5th lord pressure", "caution", f"The 5th lord receives pressure from {', '.join(malefic_pressure)}."))
    if not evidence:
        evidence.append(item("Affliction", "support", "The 5th lord and Jupiter avoid the major retrograde/debilitation/nodal warnings."))
        score += 1
    return {"score": score, "blockers": blockers, "evidence": evidence}

def child_family_support(seventh_lord: dict, second_lord: dict, ninth_lord: dict, jupiter: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for label, planet, meaning in [
        ("7th house", seventh_lord, "partner cooperation"),
        ("2nd house", second_lord, "family expansion"),
        ("9th house", ninth_lord, "lineage, grace, and purva punya"),
    ]:
        if planet["house"] in HIDDEN_HOUSES:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} rules {meaning} and sits in the {ordinal(planet['house'])} house."))
        else:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
    if aspect_between(jupiter["longitude"], ninth_lord["longitude"]):
        score += 1
        evidence.append(item("9th grace", "support", "Jupiter supports the 9th lord, strengthening lineage grace."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def child_karakas(jupiter: dict, moon: dict, mars: dict, venus: dict, fifth_sign: int) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (jupiter, "Jupiter", "children, expansion, and lineage"),
        (moon, "Moon", "fertility cycles, fluids, and emotional readiness"),
        (mars, "Mars", "blood, vitality, and male seed"),
        (venus, "Venus", "reproductive tissue, egg quality, and fertility ease"),
    ]:
        if planet["house"] in HIDDEN_HOUSES or planet["retrograde"]:
            score -= 1
            blockers += 1 if planet["house"] in HIDDEN_HOUSES else 0
            reason = "retrograde" if planet["retrograde"] else f"in the {ordinal(planet['house'])} house"
            evidence.append(item(label, "caution", f"{label} is {reason}, weakening {meaning}."))
        elif aspect_between(planet["longitude"], fifth_sign * 30.0):
            score += 1
            evidence.append(item(label, "support", f"{label} supports the 5th-house sign, helping {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{label} is in the {ordinal(planet['house'])} house."))
    if moon["house"] in {1, 5, 9}:
        score += 1
        evidence.append(item("Moon protection", "support", f"Moon in the {ordinal(moon['house'])} house gives extra protection to the progeny matter."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d7_lineage_stability(chart: dict, planet_names: list[str]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna_sign = varga_sign_index(chart["lagna"]["longitude"], "D7")
    for name in planet_names:
        planet = planets[name]
        sign = varga_sign_index(planet["longitude"], "D7")
        house = whole_sign_house(sign * 30.0, lagna_sign)
        if DEBILITATION_SIGNS.get(name) == sign:
            score -= 2
            blockers += 1
            evidence.append(item("D7 stability", "blocked", f"{name} is debilitated in D7 {SIGNS[sign]}, weakening child wellbeing or lineage stability."))
        elif EXALTATION_SIGNS.get(name) == sign or SIGN_LORDS[sign] == name:
            score += 1
            evidence.append(item("D7 stability", "support", f"{name} is strong in D7 {SIGNS[sign]}, supporting a stable progeny outcome."))
        elif house in HIDDEN_HOUSES:
            score -= 1
            evidence.append(item("D7 stability", "caution", f"{name} falls in the D7 {ordinal(house)} house, so pregnancy/child wellbeing needs care."))
        else:
            evidence.append(item("D7 stability", "neutral", f"{name} falls in D7 {SIGNS[sign]}, house {house}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def child_verdict_from_score(score: int, blockers: int, focus: str) -> dict:
    target = {
        "pregnancy_safety": "pregnancy or child wellbeing",
        "conception": "conception",
        "delay": "childbirth timing",
        "progeny": "progeny promise",
    }.get(focus, "childbirth matter")
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": f"The {target} is not clearly promised now; delay, affliction, or biological/karmic blockage dominates."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": f"The {target} is strongly supported, with fertility and lineage factors cooperating."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": f"The {target} is possible, but timing, care, or medical/partner cooperation needs attention."}
    return {"level": "uncertain", "summary": "The chart is mixed; the seed is visible, but biological viability and timing are not fully aligned."}

def child_timing_from_yoga(yoga: dict, first: dict | None, second: dict) -> dict | None:
    if not first:
        return None
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9}:
        unit = "weeks"
    elif sign_index in {2, 5, 8, 11}:
        unit = "weeks to months"
    else:
        unit = "months or longer with patient tracking"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the conception/progress timing seed, read as {unit}.",
    }

