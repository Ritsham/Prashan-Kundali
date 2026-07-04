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


def planet_strength_score(planet: dict) -> int:
    score = 0
    if planet["house"] in {1, 4, 7, 10}:
        score += 3
    elif planet["house"] in {5, 9, 11}:
        score += 2
    elif planet["house"] in {6, 8, 12}:
        score -= 1
    if EXALTATION_SIGNS.get(planet["name"]) == planet["sign_index"] or SIGN_LORDS[planet["sign_index"]] == planet["name"]:
        score += 2
    if DEBILITATION_SIGNS.get(planet["name"]) == planet["sign_index"]:
        score -= 2
    if planet["retrograde"]:
        score -= 1
    return score

def unique_planets(names: list[str]) -> list[str]:
    result = []
    for name in names:
        if name not in result:
            result.append(name)
    return result

def authenticity_check(lagna: dict, moon: dict, planets: dict[str, dict]) -> dict:
    lagna_afflictions = [
        planet["name"]
        for planet in planets.values()
        if planet["name"] in MALEFICS and planet["house"] == 1
    ]
    moon_afflicted = moon["house"] in HIDDEN_HOUSES and not any(
        aspect_between(planet["longitude"], moon["longitude"]) for planet in planets.values() if planet["name"] in BENEFICS and planet["name"] != "Moon"
    )
    if lagna_afflictions and moon_afflicted:
        return item("Authenticity", "blocked", f"Lagna is afflicted by {', '.join(lagna_afflictions)} and Moon is in the {ordinal(moon['house'])} house.")
    if lagna_afflictions:
        return item("Authenticity", "caution", f"Lagna has pressure from {', '.join(lagna_afflictions)}; read the chart with caution.")
    if moon_afflicted:
        return item("Authenticity", "caution", f"Moon is in the {ordinal(moon['house'])} house without a close benefic aspect.")
    return item("Authenticity", "clear", f"Lagna is {lagna['sign']} and Moon is in the {ordinal(moon['house'])} house; the chart is readable.")

def analyze_primary_lords(lagna_lord: dict, seventh_lord: dict) -> tuple[list[dict], int, int]:
    evidence = []
    score = 0
    blockers = 0
    for label, planet in [("Lagna lord", lagna_lord), ("7th lord", seventh_lord)]:
        if planet["house"] in SUPPORT_HOUSES:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} is in the {ordinal(planet['house'])} house, giving visible support."))
        elif planet["house"] in HIDDEN_HOUSES:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house, showing delay, conflict, or hidden pressure."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} is in the {ordinal(planet['house'])} house."))
    if lagna_lord["house"] == 7 or seventh_lord["house"] == 1:
        score += 2
        evidence.append(item("Mutual desire", "strong", "One of the main lords occupies the other's house, showing direct attraction or focus."))
    return evidence, score, blockers

def house_support(second_lord: dict, eleventh_lord: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    if second_lord["house"] in HIDDEN_HOUSES:
        score -= 1
        blockers += 1
        evidence.append(item("2nd house", "caution", f"{second_lord['name']} rules family expansion and sits in the {ordinal(second_lord['house'])} house."))
    else:
        score += 1
        evidence.append(item("2nd house", "support", f"{second_lord['name']} gives family-integration support from the {ordinal(second_lord['house'])} house."))
    if eleventh_lord["house"] in HIDDEN_HOUSES:
        score -= 2
        blockers += 1
        evidence.append(item("11th house", "blocked", f"{eleventh_lord['name']} rules fulfilment and sits in the {ordinal(eleventh_lord['house'])} house."))
    else:
        score += 1
        evidence.append(item("11th house", "support", f"{eleventh_lord['name']} supports desire fulfilment from the {ordinal(eleventh_lord['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def karaka_support(venus: dict, jupiter: dict, seventh_sign: int) -> dict:
    evidence = []
    score = 0
    for planet, label in [(venus, "Venus"), (jupiter, "Jupiter")]:
        aspects_7th = aspect_between(planet["longitude"], seventh_sign * 30.0)
        if planet["house"] in HIDDEN_HOUSES:
            evidence.append(item(label, "caution", f"{label} is in the {ordinal(planet['house'])} house, reducing ease and harmony."))
            score -= 1
        elif aspects_7th:
            evidence.append(item(label, "support", f"{label} aspects the 7th-house sign, adding grace to the marriage matter."))
            score += 1
        else:
            evidence.append(item(label, "neutral", f"{label} is in the {ordinal(planet['house'])} house."))
    return {"score": score, "evidence": evidence}

def d9_dignity(chart: dict, planet_names: list[str]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna_sign = varga_sign_index(chart["lagna"]["longitude"], "D9")
    for name in planet_names:
        planet = planets[name]
        sign = varga_sign_index(planet["longitude"], "D9")
        house = whole_sign_house(sign * 30.0, lagna_sign)
        if DEBILITATION_SIGNS.get(name) == sign:
            score -= 2
            blockers += 1
            evidence.append(item("D9 dignity", "blocked", f"{name} is debilitated in D9 {SIGNS[sign]}, weakening post-marriage stability."))
        elif EXALTATION_SIGNS.get(name) == sign or SIGN_LORDS[sign] == name:
            score += 1
            evidence.append(item("D9 dignity", "support", f"{name} is strong in D9 {SIGNS[sign]}."))
        elif house in HIDDEN_HOUSES:
            score -= 1
            evidence.append(item("D9 dignity", "caution", f"{name} falls in the D9 {ordinal(house)} house, so the promise needs care."))
        else:
            evidence.append(item("D9 dignity", "neutral", f"{name} falls in D9 {SIGNS[sign]}, house {house}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def best_bridge(source: dict, targets: list[dict], target_names: set[str]) -> dict | None:
    bridges = []
    for target in targets:
        yoga = applying_yoga(source, target)
        if yoga["state"] == "applying":
            bridges.append({**yoga, "target": target["name"] if target["name"] in target_names else "target lord"})
    if not bridges:
        return None
    return sorted(bridges, key=lambda item: item["degree_gap"])[0]

def applying_yoga(first: dict, second: dict) -> dict:
    matches = []
    for aspect in FAVORABLE_ASPECTS:
        exact_forward = normalize_degrees(second["longitude"] - first["longitude"] - aspect)
        exact_backward = normalize_degrees(first["longitude"] - second["longitude"] - aspect)
        gap = min(exact_forward, exact_backward, 360 - exact_forward, 360 - exact_backward)
        if gap <= ASPECT_ORB:
            separating = gap_is_widening(first, second, aspect)
            matches.append(
                {
                    "state": "separating" if separating else "applying",
                    "aspect_degrees": aspect,
                    "aspect_name": aspect_name(aspect),
                    "degree_gap": round(gap, 2),
                }
            )
    if not matches:
        return {"state": "none"}
    return sorted(matches, key=lambda item: item["degree_gap"])[0]

def gap_is_widening(first: dict, second: dict, aspect: int) -> bool:
    now = aspect_gap(first["longitude"], second["longitude"], aspect)
    next_gap = aspect_gap(first["longitude"] + first["speed"], second["longitude"] + second["speed"], aspect)
    return next_gap > now

def aspect_between(first_lon: float, second_lon: float) -> bool:
    return any(aspect_gap(first_lon, second_lon, aspect) <= ASPECT_ORB for aspect in FAVORABLE_ASPECTS)

def aspect_gap(first_lon: float, second_lon: float, aspect: int) -> float:
    separation = abs(normalize_degrees(first_lon - second_lon))
    separation = min(separation, 360 - separation)
    return abs(separation - aspect)

def timing_from_yoga(yoga: dict, first: dict, second: dict) -> dict:
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9}:
        unit = "days to weeks"
    elif sign_index in {2, 5, 8, 11}:
        unit = "weeks to months"
    else:
        unit = "months to years"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the timing seed, read as {unit} by sign modality.",
    }

def verdict_from_score(score: int, blockers: int) -> dict:
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": "Marriage is not clearly promised now; obstacles or delay dominate this Prashna."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": "Marriage is strongly promised if the querent acts while the applying factors remain active."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": "Marriage is possible, but the chart asks for effort, mediation, or patience."}
    return {"level": "uncertain", "summary": "The chart is mixed; desire is visible but execution is not fully secured."}

def confidence_label(score: int, blockers: int) -> str:
    if abs(score) >= 6 and blockers <= 1:
        return "high"
    if abs(score) >= 3:
        return "medium"
    return "low"

def aspect_name(degrees: int) -> str:
    return {0: "conjunction", 60: "sextile", 120: "trine"}.get(degrees, f"{degrees}-degree aspect")

def ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"

def item(label: str, status: str, text: str) -> dict:
    return {"label": label, "status": status, "text": text}

