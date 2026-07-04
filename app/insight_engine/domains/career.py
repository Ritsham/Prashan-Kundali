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

def interpret_government_job_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    sixth_sign = (lagna_sign + 5) % 12
    tenth_sign = (lagna_sign + 9) % 12
    eleventh_sign = (lagna_sign + 10) % 12
    fifth_sign = (lagna_sign + 4) % 12

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    sixth_lord_name = SIGN_LORDS[sixth_sign]
    tenth_lord_name = SIGN_LORDS[tenth_sign]
    eleventh_lord_name = SIGN_LORDS[eleventh_sign]
    fifth_lord_name = SIGN_LORDS[fifth_sign]

    lagna_lord = planets[lagna_lord_name]
    sixth_lord = planets[sixth_lord_name]
    tenth_lord = planets[tenth_lord_name]
    eleventh_lord = planets[eleventh_lord_name]
    fifth_lord = planets[fifth_lord_name]
    sun = planets["Sun"]
    mars = planets["Mars"]
    jupiter = planets["Jupiter"]
    saturn = planets["Saturn"]
    rahu = planets["Rahu"]

    evidence = []
    score = 0
    blockers = 0
    intent = detect_government_job_intent(chart["question"].get("text", ""))

    solar = government_solar_authority(sun, planets)
    score += solar["score"]
    blockers += solar["blockers"]
    evidence.extend(solar["evidence"])

    competition = government_competition_selection(lagna_lord, sixth_lord, tenth_lord, eleventh_lord, fifth_lord)
    score += competition["score"]
    blockers += competition["blockers"]
    evidence.extend(competition["evidence"])

    main_yoga = best_government_yoga(lagna_lord, tenth_lord, sun)
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Administrative Ithasala",
                "strong",
                f"{main_yoga['source']} applies to {main_yoga['target']} by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees; state authority is approaching the candidate.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 4
        blockers += 2
        evidence.append(
            item(
                "Administrative Ithasala",
                "blocked",
                f"{main_yoga['source']} separates from {main_yoga['target']} by {main_yoga['aspect_name']}; the vacancy, exam window, or selection opportunity may have slipped.",
            )
        )
    else:
        evidence.append(item("Administrative Ithasala", "caution", "No close applying yoga appears between Lagna lord and 10th lord, or Sun and Lagna lord."))

    roadblocks = government_roadblocks(lagna_lord, tenth_lord, sun, saturn, rahu)
    score += roadblocks["score"]
    blockers += roadblocks["blockers"]
    evidence.extend(roadblocks["evidence"])

    karakas = government_karakas(sun, mars, jupiter, saturn)
    score += karakas["score"]
    blockers += karakas["blockers"]
    evidence.extend(karakas["evidence"])

    d10 = d10_government_career(chart, unique_planets([tenth_lord_name, lagna_lord_name, "Sun", "Mars", "Jupiter", "Saturn"]))
    score += d10["score"]
    blockers += d10["blockers"]
    evidence.extend(d10["evidence"])

    return {
        "domain": "job_career",
        "subdomain": "government",
        "title": "Government Job Prashna Interpretation",
        "intent": intent,
        "verdict": government_job_verdict_from_score(score, blockers, intent["focus"]),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": government_timing_from_yoga(main_yoga, main_yoga.get("source_planet"), main_yoga.get("target_planet")) if main_yoga["state"] == "applying" else None,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "sixth_lord": sixth_lord_name,
            "tenth_lord": tenth_lord_name,
            "eleventh_lord": eleventh_lord_name,
            "fifth_lord": fifth_lord_name,
        },
        "evidence": evidence,
    }

def detect_government_job_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["upsc", "ssc", "psc", "exam", "tier", "prelims", "mains", "written"]):
        return {"focus": "competitive_exam", "summary": "The querent is asking about a government competitive exam, so the 6th, 5th, 10th, and Sun lead."}
    if any(word in text for word in ["interview", "document", "verification", "joining", "appointment", "letter", "posting"]):
        return {"focus": "appointment", "summary": "The querent is asking about appointment/joining, so the 10th and 11th houses lead."}
    if any(word in text for word in ["ias", "ips", "police", "army", "military", "defence", "defense"]):
        return {"focus": "executive_service", "summary": "The querent is asking about executive, police, military, or administrative service, so Sun and Mars become critical."}
    if any(word in text for word in ["judiciary", "judge", "gazetted", "officer", "treasury", "finance"]):
        return {"focus": "gazetted_service", "summary": "The querent is asking about gazetted, judicial, policy, or finance authority, so Sun and Jupiter become critical."}
    return {"focus": "government_job", "summary": "The querent is asking about government service, so Sun, 10th, 6th, 11th, and D10 lead."}

def government_solar_authority(sun: dict, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    nodal_pressure = any(
        planet["name"] in {"Rahu", "Ketu"} and aspect_gap(planet["longitude"], sun["longitude"], 0) <= ASPECT_ORB
        for planet in planets.values()
    )
    if DEBILITATION_SIGNS["Sun"] == sun["sign_index"] or nodal_pressure:
        score -= 4
        blockers += 2
        reason = "debilitated" if DEBILITATION_SIGNS["Sun"] == sun["sign_index"] else "under Rahu/Ketu Grahan pressure"
        evidence.append(item("Solar authority", "blocked", f"Sun is {reason}; state authority is blocked at the first gate."))
    elif sun["house"] in {1, 4, 5, 7, 9, 10} or EXALTATION_SIGNS["Sun"] == sun["sign_index"] or sun["sign_index"] == 4:
        score += 3
        evidence.append(item("Solar authority", "strong", f"Sun is strong from the {ordinal(sun['house'])} house/sign, validating Sarkari authority."))
    elif sun["house"] in HIDDEN_HOUSES:
        score -= 1
        blockers += 1
        evidence.append(item("Solar authority", "caution", f"Sun sits in the {ordinal(sun['house'])} house, weakening direct state support."))
    else:
        evidence.append(item("Solar authority", "neutral", f"Sun is in the {ordinal(sun['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def government_competition_selection(lagna_lord: dict, sixth_lord: dict, tenth_lord: dict, eleventh_lord: dict, fifth_lord: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    if planet_strength_score(lagna_lord) >= planet_strength_score(sixth_lord):
        score += 2
        evidence.append(item("Competition", "support", "The Lagna lord is at least as strong as the 6th lord, showing capacity to defeat rivals."))
    else:
        score -= 1
        blockers += 1
        evidence.append(item("Competition", "caution", "The 6th lord appears stronger than the Lagna lord, so competition is heavy."))

    for label, planet, meaning in [
        ("6th lord", sixth_lord, "competition, exams, and service"),
        ("10th lord", tenth_lord, "state authority and career status"),
        ("11th lord", eleventh_lord, "selection list and appointment letter"),
        ("5th lord", fifth_lord, "written tests, intelligence, and scoring"),
    ]:
        if planet["house"] in SUPPORT_HOUSES or planet["house"] == 6:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
        elif planet["house"] in {8, 12}:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house, weakening {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} is in the {ordinal(planet['house'])} house."))
    if tenth_lord["house"] == 6 or sixth_lord["house"] == 10:
        score += 2
        evidence.append(item("Service route", "strong", "The 10th and 6th houses connect, showing entry into authority through competition/service."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def best_government_yoga(lagna_lord: dict, tenth_lord: dict, sun: dict) -> dict:
    candidates = []
    for source, target, label in [
        (lagna_lord, tenth_lord, f"{lagna_lord['name']} to {tenth_lord['name']}"),
        (sun, lagna_lord, f"Sun to {lagna_lord['name']}"),
    ]:
        if source["name"] == target["name"]:
            continue
        yoga = applying_yoga(source, target)
        if yoga["state"] != "none":
            candidates.append({**yoga, "source": label.split(" to ")[0], "target": label.split(" to ")[1], "source_planet": source, "target_planet": target})
    if not candidates:
        return {"state": "none"}
    applying = [candidate for candidate in candidates if candidate["state"] == "applying"]
    pool = applying or candidates
    return sorted(pool, key=lambda item: item["degree_gap"])[0]

def government_roadblocks(lagna_lord: dict, tenth_lord: dict, sun: dict, saturn: dict, rahu: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (saturn, "Saturn", "legal delay, court stay, quota/reservation issue, or slow result processing"),
        (rahu, "Rahu", "corruption, pattern change, hidden bureaucracy, or sudden irregularity"),
    ]:
        touches = any(aspect_between(planet["longitude"], target["longitude"]) for target in [lagna_lord, tenth_lord, sun] if target["name"] != planet["name"])
        if touches and planet["house"] in HIDDEN_HOUSES:
            score -= 2
            blockers += 1
            evidence.append(item("Gatekeeper", "blocked", f"{label} interrupts authority from the {ordinal(planet['house'])} house: {meaning}."))
        elif touches:
            score -= 1
            evidence.append(item("Gatekeeper", "caution", f"{label} contacts the government-job path, indicating {meaning}."))
    if not evidence:
        score += 1
        evidence.append(item("Gatekeeper", "support", "Saturn and Rahu do not strongly interrupt the government-job path."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def government_karakas(sun: dict, mars: dict, jupiter: dict, saturn: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (sun, "Sun", "government, administration, command, and state authority"),
        (mars, "Mars", "police, military, executive power, and competitive grit"),
        (jupiter, "Jupiter", "gazetted posts, judiciary, policy, treasury, and guidance"),
        (saturn, "Saturn", "public sector service, discipline, and long-term preparation"),
    ]:
        if planet["house"] in {1, 5, 6, 9, 10, 11}:
            score += 1
            evidence.append(item(label, "support", f"{label} supports {meaning} from the {ordinal(planet['house'])} house."))
        elif planet["house"] in {8, 12} or planet["retrograde"]:
            score -= 1
            blockers += 1 if planet["house"] in {8, 12} else 0
            reason = "retrograde" if planet["retrograde"] else f"in the {ordinal(planet['house'])} house"
            evidence.append(item(label, "caution", f"{label} is {reason}, weakening {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{label} is in the {ordinal(planet['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d10_government_career(chart: dict, planet_names: list[str]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna_sign = varga_sign_index(chart["lagna"]["longitude"], "D10")
    for name in planet_names:
        planet = planets[name]
        sign = varga_sign_index(planet["longitude"], "D10")
        house = whole_sign_house(sign * 30.0, lagna_sign)
        if house in {1, 5, 9, 10} and DEBILITATION_SIGNS.get(name) != sign:
            score += 1
            evidence.append(item("D10 career", "support", f"{name} falls in the D10 {ordinal(house)} house, supporting long-term authority and respect."))
        elif DEBILITATION_SIGNS.get(name) == sign:
            score -= 2
            blockers += 1
            evidence.append(item("D10 career", "blocked", f"{name} is debilitated in D10 {SIGNS[sign]}, weakening career authority."))
        elif house in HIDDEN_HOUSES:
            score -= 1
            evidence.append(item("D10 career", "caution", f"{name} falls in the D10 {ordinal(house)} house, showing transfer, delay, or joining friction."))
        else:
            evidence.append(item("D10 career", "neutral", f"{name} falls in D10 {SIGNS[sign]}, house {house}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def government_job_verdict_from_score(score: int, blockers: int, focus: str) -> dict:
    target = {
        "competitive_exam": "government exam selection",
        "appointment": "appointment or joining",
        "executive_service": "executive/public-service selection",
        "gazetted_service": "gazetted or policy-role selection",
    }.get(focus, "government job")
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": f"The {target} is not clearly promised now; Sun/10th authority, competition, or administrative blocks dominate."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": f"The {target} is strongly supported, with state authority and competition indicators cooperating."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": f"The {target} is possible, but exam grind, paperwork, or delays need careful handling."}
    return {"level": "uncertain", "summary": "The chart is mixed; ability is visible, but state authority and appointment fulfillment are not fully aligned."}

def government_timing_from_yoga(yoga: dict, first: dict | None, second: dict | None) -> dict | None:
    if not first or not second:
        return None
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9} or first["house"] in {1, 4, 7, 10} or second["house"] in {1, 4, 7, 10}:
        unit = "days to weeks"
    elif sign_index in {1, 4, 7, 10}:
        unit = "months or longer through government processing"
    else:
        unit = "weeks to months"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the selection/joining timing seed, read as {unit}.",
    }

def interpret_private_job_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    sixth_sign = (lagna_sign + 5) % 12
    seventh_sign = (lagna_sign + 6) % 12
    tenth_sign = (lagna_sign + 9) % 12
    eleventh_sign = (lagna_sign + 10) % 12

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    sixth_lord_name = SIGN_LORDS[sixth_sign]
    seventh_lord_name = SIGN_LORDS[seventh_sign]
    tenth_lord_name = SIGN_LORDS[tenth_sign]
    eleventh_lord_name = SIGN_LORDS[eleventh_sign]

    lagna_lord = planets[lagna_lord_name]
    sixth_lord = planets[sixth_lord_name]
    seventh_lord = planets[seventh_lord_name]
    tenth_lord = planets[tenth_lord_name]
    eleventh_lord = planets[eleventh_lord_name]
    mercury = planets["Mercury"]
    venus = planets["Venus"]
    rahu = planets["Rahu"]
    saturn = planets["Saturn"]

    evidence = []
    score = 0
    blockers = 0
    intent = detect_private_job_intent(chart["question"].get("text", ""))

    capability = private_capability_filter(lagna_lord, mercury)
    score += capability["score"]
    blockers += capability["blockers"]
    evidence.extend(capability["evidence"])

    bridge = private_contract_bridge(lagna_lord, sixth_lord, seventh_lord, tenth_lord)
    score += bridge["score"]
    blockers += bridge["blockers"]
    evidence.extend(bridge["evidence"])

    main_yoga = best_private_job_yoga(lagna_lord, sixth_lord, seventh_lord, tenth_lord)
    if main_yoga["state"] == "applying":
        score += 4
        evidence.append(
            item(
                "Corporate Ithasala",
                "strong",
                f"{lagna_lord_name} applies to {main_yoga['target']} by {main_yoga['aspect_name']} within {main_yoga['degree_gap']} degrees; the hiring process is moving toward offer/placement.",
            )
        )
    elif main_yoga["state"] == "separating":
        score -= 4
        blockers += 2
        evidence.append(
            item(
                "Corporate Ithasala",
                "blocked",
                f"{lagna_lord_name} separates from {main_yoga['target']} by {main_yoga['aspect_name']}; the role may be filled, frozen, or drifting away.",
            )
        )
    else:
        evidence.append(item("Corporate Ithasala", "caution", "No close applying yoga appears between the Lagna lord and the 6th, 7th, or 10th lord."))

    compensation = private_compensation_check(eleventh_lord, planets)
    score += compensation["score"]
    blockers += compensation["blockers"]
    evidence.extend(compensation["evidence"])

    karakas = private_job_karakas(mercury, venus, rahu, saturn)
    score += karakas["score"]
    blockers += karakas["blockers"]
    evidence.extend(karakas["evidence"])

    d10 = d10_private_career(chart, unique_planets(["Mercury", "Rahu", lagna_lord_name, seventh_lord_name, tenth_lord_name, eleventh_lord_name]))
    score += d10["score"]
    blockers += d10["blockers"]
    evidence.extend(d10["evidence"])

    return {
        "domain": "job_career",
        "subdomain": "private",
        "title": "Private Sector Job Prashna Interpretation",
        "intent": intent,
        "verdict": private_job_verdict_from_score(score, blockers, intent["focus"]),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": private_job_timing_from_yoga(main_yoga, lagna_lord, main_yoga.get("target_planet")) if main_yoga["state"] == "applying" else None,
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "sixth_lord": sixth_lord_name,
            "seventh_lord": seventh_lord_name,
            "tenth_lord": tenth_lord_name,
            "eleventh_lord": eleventh_lord_name,
        },
        "evidence": evidence,
    }

def detect_private_job_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["offer", "offer letter", "joining", "onboarding", "background check"]):
        return {"focus": "offer", "summary": "The querent is asking about offer or joining, so the 7th contract, 10th role, and 11th package lead."}
    if any(word in text for word in ["interview", "hr", "technical", "round", "screening"]):
        return {"focus": "interview", "summary": "The querent is asking about interview performance, so Mercury, 6th house, and 7th HR/employer lead."}
    if any(word in text for word in ["salary", "ctc", "package", "bonus", "hike", "appraisal"]):
        return {"focus": "compensation", "summary": "The querent is asking about package or compensation, so the 11th house and Venus/Mercury lead."}
    if any(word in text for word in ["mnc", "startup", "remote", "foreign client", "tech", "ai", "fintech"]):
        return {"focus": "mnc_startup", "summary": "The querent is asking about MNC/startup/tech opportunity, so Rahu and Mercury become critical."}
    return {"focus": "private_job", "summary": "The querent is asking about private-sector placement, so Mercury, 7th contract, 10th role, 6th interviews, and 11th CTC lead."}

def private_capability_filter(lagna_lord: dict, mercury: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    if (mercury["retrograde"] or mercury["house"] in {8, 12}) and mercury["house"] in {8, 12}:
        score -= 3
        blockers += 2
        state = "retrograde and hidden" if mercury["retrograde"] else f"in the {ordinal(mercury['house'])} house"
        evidence.append(item("Capability filter", "blocked", f"Mercury is {state}; interview communication, resume clarity, or self-marketing is compromised."))
    elif mercury["retrograde"] or mercury["house"] in HIDDEN_HOUSES:
        score -= 1
        blockers += 1 if mercury["house"] in {8, 12} else 0
        state = "retrograde" if mercury["retrograde"] else f"in the {ordinal(mercury['house'])} house"
        evidence.append(item("Capability filter", "caution", f"Mercury is {state}, so communication and interview execution need attention."))
    else:
        score += 2
        evidence.append(item("Capability filter", "support", f"Mercury supports private-sector skill exchange from the {ordinal(mercury['house'])} house."))

    if lagna_lord["house"] in SUPPORT_HOUSES:
        score += 1
        evidence.append(item("Candidate", "support", f"{lagna_lord['name']} gives confidence and job-hunting effort from the {ordinal(lagna_lord['house'])} house."))
    elif lagna_lord["house"] in {8, 12}:
        score -= 1
        blockers += 1
        evidence.append(item("Candidate", "caution", f"{lagna_lord['name']} is in the {ordinal(lagna_lord['house'])} house, reducing confidence or visibility."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def private_contract_bridge(lagna_lord: dict, sixth_lord: dict, seventh_lord: dict, tenth_lord: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for label, planet, meaning in [
        ("6th lord", sixth_lord, "interviews, employment grind, and daily operations"),
        ("7th lord", seventh_lord, "employer, HR, contract, and negotiation"),
        ("10th lord", tenth_lord, "role, designation, and professional responsibility"),
    ]:
        if planet["house"] in SUPPORT_HOUSES or planet["house"] == 6:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
        elif planet["house"] in {8, 12}:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house, weakening {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} is in the {ordinal(planet['house'])} house."))
    if planet_strength_score(seventh_lord) > planet_strength_score(lagna_lord):
        score -= 1
        evidence.append(item("Negotiation leverage", "caution", "The 7th lord is stronger than the Lagna lord, so the employer may hold salary leverage."))
    else:
        score += 1
        evidence.append(item("Negotiation leverage", "support", "The candidate has enough leverage to negotiate the contract."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def best_private_job_yoga(lagna_lord: dict, sixth_lord: dict, seventh_lord: dict, tenth_lord: dict) -> dict:
    candidates = []
    for target, label, priority in [
        (seventh_lord, "7th lord/Employer", 0),
        (tenth_lord, "10th lord/Role", 1),
        (sixth_lord, "6th lord/Interview", 2),
    ]:
        if target["name"] == lagna_lord["name"]:
            continue
        yoga = applying_yoga(lagna_lord, target)
        if yoga["state"] != "none":
            candidates.append({**yoga, "target": f"{target['name']} ({label})", "target_planet": target, "priority": priority})
    if not candidates:
        return {"state": "none"}
    applying = [candidate for candidate in candidates if candidate["state"] == "applying"]
    pool = applying or candidates
    return sorted(pool, key=lambda item: (item["priority"], item["degree_gap"]))[0]

def private_compensation_check(eleventh_lord: dict, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    mars_saturn_affliction = any(
        planet["name"] in {"Mars", "Saturn"} and aspect_between(planet["longitude"], eleventh_lord["longitude"])
        for planet in planets.values()
    )
    if eleventh_lord["house"] in SUPPORT_HOUSES and not mars_saturn_affliction:
        score += 2
        evidence.append(item("11th CTC", "support", f"{eleventh_lord['name']} supports compensation, bonuses, and perks from the {ordinal(eleventh_lord['house'])} house."))
    elif mars_saturn_affliction or eleventh_lord["house"] in {8, 12}:
        score -= 2
        blockers += 1
        evidence.append(item("11th CTC", "caution", f"{eleventh_lord['name']} is pressured or hidden; package/perks may be underwhelming or revised downward."))
    else:
        evidence.append(item("11th CTC", "neutral", f"{eleventh_lord['name']} is in the {ordinal(eleventh_lord['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def private_job_karakas(mercury: dict, venus: dict, rahu: dict, saturn: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (mercury, "Mercury", "communication, coding/data, strategy, and interview performance"),
        (venus, "Venus", "corporate diplomacy, networking, work environment, and compensation"),
        (rahu, "Rahu", "MNCs, startups, tech disruption, foreign clients, and remote work"),
        (saturn, "Saturn", "KPIs, hierarchy, labor, and structured corporate growth"),
    ]:
        if planet["house"] in {1, 6, 7, 10, 11}:
            score += 1
            evidence.append(item(label, "support", f"{label} supports {meaning} from the {ordinal(planet['house'])} house."))
        elif planet["house"] in {8, 12} or planet["retrograde"]:
            score -= 1
            blockers += 1 if planet["house"] in {8, 12} else 0
            state = "retrograde" if planet["retrograde"] else f"in the {ordinal(planet['house'])} house"
            evidence.append(item(label, "caution", f"{label} is {state}, weakening {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{label} is in the {ordinal(planet['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d10_private_career(chart: dict, planet_names: list[str]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna_sign = varga_sign_index(chart["lagna"]["longitude"], "D10")
    for name in planet_names:
        planet = planets[name]
        sign = varga_sign_index(planet["longitude"], "D10")
        house = whole_sign_house(sign * 30.0, lagna_sign)
        if name in {"Mercury", "Rahu"} and house in {1, 5, 7, 9, 10, 11} and DEBILITATION_SIGNS.get(name) != sign:
            score += 2
            evidence.append(item("D10 corporate", "strong", f"{name} is prominent in the D10 {ordinal(house)} house, supporting private-sector agility and growth."))
        elif house in {1, 5, 9, 10, 11} and DEBILITATION_SIGNS.get(name) != sign:
            score += 1
            evidence.append(item("D10 corporate", "support", f"{name} falls in the D10 {ordinal(house)} house, supporting corporate longevity."))
        elif DEBILITATION_SIGNS.get(name) == sign:
            score -= 2
            blockers += 1
            evidence.append(item("D10 corporate", "blocked", f"{name} is debilitated in D10 {SIGNS[sign]}, weakening corporate growth/culture fit."))
        elif house in HIDDEN_HOUSES:
            score -= 1
            evidence.append(item("D10 corporate", "caution", f"{name} falls in the D10 {ordinal(house)} house, warning of toxic culture, layoffs, or early exit risk."))
        else:
            evidence.append(item("D10 corporate", "neutral", f"{name} falls in D10 {SIGNS[sign]}, house {house}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def private_job_verdict_from_score(score: int, blockers: int, focus: str) -> dict:
    target = {
        "offer": "offer or joining",
        "interview": "interview outcome",
        "compensation": "package/CTC outcome",
        "mnc_startup": "MNC/startup opportunity",
    }.get(focus, "private-sector job")
    if blockers >= 4 or score <= -2:
        return {"level": "no_or_delayed", "summary": f"The {target} is not clearly promised now; communication, contract, role, or package blocks dominate."}
    if score >= 6 and blockers <= 1:
        return {"level": "yes", "summary": f"The {target} is strongly supported, with skill, contract, and corporate-growth indicators cooperating."}
    if score >= 3:
        return {"level": "possible_with_effort", "summary": f"The {target} can materialize, but interview execution, negotiation, or compensation details need careful handling."}
    return {"level": "uncertain", "summary": "The chart is mixed; employability is visible, but contract execution and monetization are not fully aligned."}

def private_job_timing_from_yoga(yoga: dict, first: dict, second: dict | None) -> dict | None:
    if not second:
        return None
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9} or first["house"] in {1, 4, 7, 10} or second["house"] in {1, 4, 7, 10}:
        unit = "days to a few weeks"
    elif sign_index in {1, 4, 7, 10}:
        unit = "weeks to months through HR/background checks"
    else:
        unit = "weeks to months"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the offer/onboarding timing seed, read as {unit}.",
    }

