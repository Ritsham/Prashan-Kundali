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

def interpret_wealth_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    intent = detect_wealth_intent(chart["question"].get("text", ""))

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    second_lord_name = SIGN_LORDS[(lagna_sign + 1) % 12]
    fifth_lord_name = SIGN_LORDS[(lagna_sign + 4) % 12]
    eighth_lord_name = SIGN_LORDS[(lagna_sign + 7) % 12]
    eleventh_lord_name = SIGN_LORDS[(lagna_sign + 10) % 12]
    twelfth_lord_name = SIGN_LORDS[(lagna_sign + 11) % 12]

    lagna_lord = planets[lagna_lord_name]
    second_lord = planets[second_lord_name]
    fifth_lord = planets[fifth_lord_name]
    eighth_lord = planets[eighth_lord_name]
    eleventh_lord = planets[eleventh_lord_name]
    twelfth_lord = planets[twelfth_lord_name]
    moon = planets["Moon"]

    evidence = []
    score = 0
    blockers = 0

    motive = wealth_motive_check(lagna, moon, planets)
    evidence.append(motive)
    if motive["status"] == "blocked":
        score -= 3
        blockers += 2
    elif motive["status"] == "caution":
        score -= 1
        blockers += 1
    else:
        score += 1

    flow = wealth_flow_support(lagna_lord, second_lord, eleventh_lord)
    score += flow["score"]
    blockers += flow["blockers"]
    evidence.extend(flow["evidence"])

    if intent["focus"] == "speculation":
        score += wealth_house_factor(fifth_lord, "5th house", "speculation, trading, and risk appetite", evidence)
    elif intent["focus"] in {"inheritance", "loan_funding", "settlement"}:
        score += wealth_house_factor(eighth_lord, "8th house", "unearned wealth, funding, taxes, or settlements", evidence)

    main_yoga = best_wealth_yoga(lagna_lord, second_lord, eleventh_lord)
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Financial Ithasala",
                "strong",
                f"{lagna_lord_name} applies to {main_yoga['target_lord']} by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees; money is moving toward the querent.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 4
        blockers += 2
        evidence.append(
            item(
                "Financial Ithasala",
                "blocked",
                f"{lagna_lord_name} is separating from {main_yoga['target_lord']} by {main_yoga['aspect_name']}; the financial peak may have passed.",
            )
        )
    else:
        evidence.append(item("Financial Ithasala", "caution", "No close applying yoga appears between the Lagna lord and the 2nd or 11th lord."))

    leakage = wealth_leakage(second_lord, twelfth_lord, lagna_sign)
    score += leakage["score"]
    blockers += leakage["blockers"]
    evidence.extend(leakage["evidence"])

    dignity = wealth_dignity([second_lord, eleventh_lord, fifth_lord, eighth_lord], intent["focus"])
    score += dignity["score"]
    blockers += dignity["blockers"]
    evidence.extend(dignity["evidence"])

    karakas = wealth_karakas(planets["Jupiter"], planets["Venus"], planets["Mercury"], moon)
    score += karakas["score"]
    blockers += karakas["blockers"]
    evidence.extend(karakas["evidence"])

    d4 = d4_wealth_stability(chart, unique_planets(["Jupiter", "Venus", "Mercury", second_lord_name, eleventh_lord_name]))
    score += d4["score"]
    blockers += d4["blockers"]
    evidence.extend(d4["evidence"])

    return {
        "domain": "wealth",
        "title": "Wealth Prashna Interpretation",
        "intent": intent,
        "verdict": wealth_verdict_from_score(score, blockers, intent["focus"]),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": wealth_timing_from_yoga(main_yoga, lagna_lord, main_yoga.get("target_planet")) if main_yoga["state"] == "applying" else None,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "second_lord": second_lord_name,
            "fifth_lord": fifth_lord_name,
            "eighth_lord": eighth_lord_name,
            "eleventh_lord": eleventh_lord_name,
            "twelfth_lord": twelfth_lord_name,
        },
        "evidence": evidence,
    }

def detect_wealth_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["stock", "share", "crypto", "trade", "trading", "investment", "speculation", "market"]):
        return {"focus": "speculation", "summary": "The querent is asking about speculative gains or trading, so the 5th and 11th houses become critical."}
    if any(word in text for word in ["inheritance", "insurance", "tax", "settlement", "claim", "secret money"]):
        return {"focus": "inheritance", "summary": "The querent is asking about unearned or hidden wealth, so the 8th house becomes critical."}
    if any(word in text for word in ["loan", "funding", "investor", "capital", "raise", "startup"]):
        return {"focus": "loan_funding", "summary": "The querent is asking about funding or borrowed capital, so the 8th and 11th houses lead."}
    if any(word in text for word in ["payment", "salary", "income", "profit", "revenue", "client", "commission", "bonus"]):
        return {"focus": "income", "summary": "The querent is asking about income or payment realization, so the 11th house leads."}
    if any(word in text for word in ["saving", "savings", "bank", "cash", "retain", "keep"]):
        return {"focus": "savings", "summary": "The querent is asking about retained wealth, so the 2nd house leads."}
    return {"focus": "wealth_flow", "summary": "The querent is asking about general wealth flow, so the 2nd and 11th houses lead together."}

def wealth_motive_check(lagna: dict, moon: dict, planets: dict[str, dict]) -> dict:
    mars_or_rahu_pressure = any(
        planet["name"] in {"Mars", "Rahu"} and aspect_between(planet["longitude"], moon["longitude"])
        for planet in planets.values()
    )
    benefic_growth = moon["house"] in {3, 11} and any(
        planet["name"] in BENEFICS and planet["name"] != "Moon" and aspect_between(planet["longitude"], moon["longitude"])
        for planet in planets.values()
    )
    if moon["house"] in HIDDEN_HOUSES and mars_or_rahu_pressure:
        return item("Motive check", "blocked", f"Moon is in the {ordinal(moon['house'])} house under Mars/Rahu pressure; panic, debt pressure, or desperation is distorting judgment.")
    if moon["house"] in HIDDEN_HOUSES:
        return item("Motive check", "caution", f"Moon is in the {ordinal(moon['house'])} house, showing anxiety around money.")
    if benefic_growth:
        return item("Motive check", "clear", f"Moon in the {ordinal(moon['house'])} house with benefic support shows calculated financial growth.")
    return item("Motive check", "clear", f"Lagna is {lagna['sign']} and Moon is in the {ordinal(moon['house'])} house; the wealth question is readable.")

def wealth_flow_support(lagna_lord: dict, second_lord: dict, eleventh_lord: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for label, planet, meaning in [
        ("Lagna lord", lagna_lord, "effort and ability to seize opportunity"),
        ("2nd lord", second_lord, "savings and retained wealth"),
        ("11th lord", eleventh_lord, "income, profits, and realization"),
    ]:
        if planet["house"] in SUPPORT_HOUSES or planet["house"] == 2:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
        elif planet["house"] in HIDDEN_HOUSES:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house, weakening {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} is in the {ordinal(planet['house'])} house."))
    if eleventh_lord["house"] == 2 or second_lord["house"] == 11:
        score += 3
        evidence.append(item("Dhana yoga", "strong", "The 2nd and 11th houses exchange savings and gains, showing clean wealth flow and retention."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def wealth_house_factor(planet: dict, label: str, meaning: str, evidence: list[dict]) -> int:
    if planet["house"] in HIDDEN_HOUSES:
        evidence.append(item(label, "caution", f"{planet['name']} rules {meaning} and sits in the {ordinal(planet['house'])} house."))
        return -1
    evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
    return 1

def best_wealth_yoga(lagna_lord: dict, second_lord: dict, eleventh_lord: dict) -> dict:
    candidates = []
    for target_lord, target_label in [(second_lord, "2nd lord"), (eleventh_lord, "11th lord")]:
        if target_lord["name"] == lagna_lord["name"]:
            continue
        yoga = applying_yoga(lagna_lord, target_lord)
        if yoga["state"] != "none":
            candidates.append({**yoga, "target_lord": f"{target_lord['name']} ({target_label})", "target_planet": target_lord})
    if not candidates:
        return {"state": "none"}
    applying = [candidate for candidate in candidates if candidate["state"] == "applying"]
    pool = applying or candidates
    return sorted(pool, key=lambda item: item["degree_gap"])[0]

def wealth_leakage(second_lord: dict, twelfth_lord: dict, lagna_sign: int) -> dict:
    evidence = []
    score = 0
    blockers = 0
    second_house_lon = ((lagna_sign + 1) % 12) * 30.0
    loss_yoga = applying_yoga(second_lord, twelfth_lord)
    twelfth_aspects_second = aspect_between(twelfth_lord["longitude"], second_house_lon)
    if loss_yoga["state"] == "applying":
        score -= 3
        blockers += 2
        evidence.append(item("12th leakage", "blocked", f"The 2nd lord applies to the 12th lord by {loss_yoga['aspect_name']}; income may be wiped out by expenses or old liabilities."))
    elif twelfth_aspects_second:
        score -= 2
        blockers += 1
        evidence.append(item("12th leakage", "blocked", "The 12th lord aspects the 2nd-house sign, showing leakage through expenses, debts, or losses."))
    elif twelfth_lord["house"] == 2:
        score -= 2
        blockers += 1
        evidence.append(item("12th leakage", "caution", f"{twelfth_lord['name']} rules losses and sits in the 2nd house of savings."))
    else:
        score += 1
        evidence.append(item("12th leakage", "support", "The 12th lord does not strongly drain the savings house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def wealth_dignity(planets: list[dict], focus: str) -> dict:
    evidence = []
    score = 0
    blockers = 0
    seen = set()
    for planet in planets:
        if planet["name"] in seen:
            continue
        seen.add(planet["name"])
        if planet["retrograde"]:
            score -= 1
            evidence.append(item("Financial dignity", "caution", f"{planet['name']} is retrograde, so money may need follow-up, revision, or delay."))
        if DEBILITATION_SIGNS.get(planet["name"]) == planet["sign_index"]:
            score -= 2
            blockers += 1
            evidence.append(item("Financial dignity", "blocked", f"{planet['name']} is debilitated in {planet['sign']}, weakening financial stability."))
        elif EXALTATION_SIGNS.get(planet["name"]) == planet["sign_index"] or SIGN_LORDS[planet["sign_index"]] == planet["name"]:
            score += 1
            evidence.append(item("Financial dignity", "support", f"{planet['name']} is dignified in {planet['sign']}, improving wealth reliability."))
    if not evidence:
        evidence.append(item("Financial dignity", "neutral", f"No severe dignity issue appears among the main wealth lords for {focus}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def wealth_karakas(jupiter: dict, venus: dict, mercury: dict, moon: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (jupiter, "Jupiter", "abundance, expansion, and financial luck"),
        (venus, "Venus", "cash flow, assets, luxury, and prosperity"),
        (mercury, "Mercury", "trade, calculation, commerce, and business intelligence"),
    ]:
        if planet["house"] in HIDDEN_HOUSES or planet["retrograde"]:
            score -= 1
            blockers += 1 if planet["house"] in HIDDEN_HOUSES else 0
            reason = "retrograde" if planet["retrograde"] else f"in the {ordinal(planet['house'])} house"
            evidence.append(item(label, "caution", f"{label} is {reason}, weakening {meaning}."))
        else:
            score += 1
            evidence.append(item(label, "support", f"{label} supports {meaning} from the {ordinal(planet['house'])} house."))
    if moon["house"] in {2, 5, 11}:
        score += 1
        evidence.append(item("Moon cash flow", "support", f"Moon in the {ordinal(moon['house'])} house supports active cash movement."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d4_wealth_stability(chart: dict, planet_names: list[str]) -> dict:
    evidence = [item("D11 check", "neutral", "D11 is not calculated by this engine yet, so D4 is used as the available stability check for assets and retained value.")]
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna_sign = varga_sign_index(chart["lagna"]["longitude"], "D4")
    for name in planet_names:
        planet = planets[name]
        sign = varga_sign_index(planet["longitude"], "D4")
        house = whole_sign_house(sign * 30.0, lagna_sign)
        if DEBILITATION_SIGNS.get(name) == sign:
            score -= 2
            blockers += 1
            evidence.append(item("D4 stability", "blocked", f"{name} is debilitated in D4 {SIGNS[sign]}, weakening asset permanence."))
        elif EXALTATION_SIGNS.get(name) == sign or SIGN_LORDS[sign] == name:
            score += 1
            evidence.append(item("D4 stability", "support", f"{name} is strong in D4 {SIGNS[sign]}, supporting retained value."))
        elif house in HIDDEN_HOUSES:
            score -= 1
            evidence.append(item("D4 stability", "caution", f"{name} falls in the D4 {ordinal(house)} house, so gains may not settle easily."))
        else:
            evidence.append(item("D4 stability", "neutral", f"{name} falls in D4 {SIGNS[sign]}, house {house}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def wealth_verdict_from_score(score: int, blockers: int, focus: str) -> dict:
    target = {
        "speculation": "speculative gain",
        "inheritance": "hidden or unearned wealth",
        "loan_funding": "funding or capital inflow",
        "income": "income or payment",
        "savings": "retained savings",
    }.get(focus, "wealth flow")
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": f"The {target} is not cleanly promised now; blockage, delay, or leakage dominates."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": f"The {target} is strongly supported, with enough flow to materialize and some capacity to retain it."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": f"The {target} can materialize, but retention, expenses, or follow-up need careful control."}
    return {"level": "uncertain", "summary": "The chart is mixed; money may move, but the pipeline is not fully open or stable."}

def wealth_timing_from_yoga(yoga: dict, first: dict, second: dict | None) -> dict:
    if not second:
        return None
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9} or first["house"] in {1, 4, 7, 10} or second["house"] in {1, 4, 7, 10}:
        unit = "days to weeks"
    elif sign_index in {1, 4, 7, 10} or first["house"] in {2, 5, 8, 11} or second["house"] in {2, 5, 8, 11}:
        unit = "weeks to months"
    else:
        unit = "weeks, depending on follow-up"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the cash-flow timing seed, read as {unit}.",
    }

