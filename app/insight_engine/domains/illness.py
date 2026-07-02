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

def interpret_illness_prashna(chart: dict) -> dict:
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna = chart["lagna"]
    lagna_sign = lagna["sign_index"]
    sixth_sign = (lagna_sign + 5) % 12
    eighth_sign = (lagna_sign + 7) % 12
    fourth_sign = (lagna_sign + 3) % 12
    seventh_sign = (lagna_sign + 6) % 12
    tenth_sign = (lagna_sign + 9) % 12
    twelfth_sign = (lagna_sign + 11) % 12

    lagna_lord_name = SIGN_LORDS[lagna_sign]
    sixth_lord_name = SIGN_LORDS[sixth_sign]
    eighth_lord_name = SIGN_LORDS[eighth_sign]
    fourth_lord_name = SIGN_LORDS[fourth_sign]
    seventh_lord_name = SIGN_LORDS[seventh_sign]
    tenth_lord_name = SIGN_LORDS[tenth_sign]
    twelfth_lord_name = SIGN_LORDS[twelfth_sign]

    lagna_lord = planets[lagna_lord_name]
    sixth_lord = planets[sixth_lord_name]
    eighth_lord = planets[eighth_lord_name]
    fourth_lord = planets[fourth_lord_name]
    seventh_lord = planets[seventh_lord_name]
    tenth_lord = planets[tenth_lord_name]
    twelfth_lord = planets[twelfth_lord_name]
    sun = planets["Sun"]
    moon = planets["Moon"]

    evidence = [item("Medical note", "caution", "This is a traditional Prashna interpretation only; it must not replace professional medical diagnosis, testing, or treatment.")]
    score = 0
    blockers = 0
    intent = detect_illness_intent(chart["question"].get("text", ""))

    vitality = illness_vitality_baseline(lagna_lord, sun, planets)
    score += vitality["score"]
    blockers += vitality["blockers"]
    evidence.extend(vitality["evidence"])

    category = illness_category(lagna_lord, sixth_lord, eighth_lord)
    score += category["score"]
    blockers += category["blockers"]
    evidence.extend(category["evidence"])

    progression = illness_progression(lagna_lord, sixth_lord, eighth_lord)
    score += progression["score"]
    blockers += progression["blockers"]
    evidence.extend(progression["evidence"])

    treatment = treatment_pillars(lagna_lord, fourth_lord, tenth_lord)
    score += treatment["score"]
    blockers += treatment["blockers"]
    evidence.extend(treatment["evidence"])

    disease = disease_pillars(seventh_lord, twelfth_lord, moon)
    score += disease["score"]
    blockers += disease["blockers"]
    evidence.extend(disease["evidence"])

    karakas = illness_karakas(sun, moon, planets["Mars"], planets["Saturn"], planets["Rahu"], planets["Ketu"])
    score += karakas["score"]
    blockers += karakas["blockers"]
    evidence.extend(karakas["evidence"])

    d6 = d6_hidden_source(chart, unique_planets([lagna_lord_name, sixth_lord_name, eighth_lord_name, "Sun", "Moon", "Mars", "Saturn"]))
    score += d6["score"]
    blockers += d6["blockers"]
    evidence.extend(d6["evidence"])

    return {
        "domain": "illness",
        "title": "Illness and Recovery Prashna Interpretation",
        "intent": intent,
        "verdict": illness_verdict_from_score(score, blockers, progression["state"]),
        "score": score,
        "confidence": confidence_label(score, blockers),
        "timing": illness_timing_from_yoga(progression.get("yoga"), lagna_lord, progression.get("target_planet")),
        "key_lords": {
            "lagna_lord": lagna_lord_name,
            "sixth_lord": sixth_lord_name,
            "eighth_lord": eighth_lord_name,
            "seventh_lord": seventh_lord_name,
            "fourth_lord": fourth_lord_name,
            "tenth_lord": tenth_lord_name,
            "twelfth_lord": twelfth_lord_name,
        },
        "evidence": evidence,
    }

def detect_illness_intent(question: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["recover", "recovery", "cure", "heal", "better", "relief"]):
        return {"focus": "recovery", "summary": "The querent is asking about recovery or relief, so vitality, treatment, and separating disease yogas lead."}
    if any(word in text for word in ["surgery", "operation", "accident", "injury", "blood", "fever", "infection"]):
        return {"focus": "acute", "summary": "The querent is asking about acute illness, injury, infection, or surgery, so the 6th house and Mars are critical."}
    if any(word in text for word in ["chronic", "long", "recurring", "genetic", "serious", "critical"]):
        return {"focus": "chronic", "summary": "The querent is asking about a chronic or deep-rooted issue, so the 8th house and Saturn are critical."}
    if any(word in text for word in ["diagnosis", "test", "doctor", "medicine", "treatment"]):
        return {"focus": "diagnosis_treatment", "summary": "The querent is asking about diagnosis or treatment, so the 10th doctor and 4th medicine pillars lead."}
    return {"focus": "illness", "summary": "The querent is asking about illness and recovery, so the patient, disease, doctor, and medicine pillars lead."}

def illness_vitality_baseline(lagna_lord: dict, sun: dict, planets: dict[str, dict]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    mars_saturn_pressure = any(
        planet["name"] in {"Mars", "Saturn"} and aspect_between(planet["longitude"], lagna_lord["longitude"])
        for planet in planets.values()
    )
    if lagna_lord["house"] in {1, 4, 7, 10} and not mars_saturn_pressure:
        score += 3
        evidence.append(item("Vitality baseline", "strong", f"{lagna_lord['name']} is angular and free from close Mars/Saturn pressure; the body has fighting strength."))
    elif lagna_lord["house"] in {6, 8} or DEBILITATION_SIGNS.get(lagna_lord["name"]) == lagna_lord["sign_index"]:
        score -= 3
        blockers += 2
        evidence.append(item("Vitality baseline", "blocked", f"{lagna_lord['name']} is compromised in the {ordinal(lagna_lord['house'])} house or weak by dignity; recovery needs strong external support."))
    elif mars_saturn_pressure:
        score -= 1
        blockers += 1
        evidence.append(item("Vitality baseline", "caution", "Mars/Saturn pressure on the Lagna lord shows strain on the immune response."))
    else:
        score += 1
        evidence.append(item("Vitality baseline", "support", f"{lagna_lord['name']} in the {ordinal(lagna_lord['house'])} house gives moderate vitality."))

    if sun["house"] in HIDDEN_HOUSES or DEBILITATION_SIGNS.get("Sun") == sun["sign_index"]:
        score -= 1
        blockers += 1 if sun["house"] in {6, 8} else 0
        evidence.append(item("Sun immunity", "caution", f"Sun is in the {ordinal(sun['house'])} house or weak by dignity, reducing core resilience."))
    else:
        score += 1
        evidence.append(item("Sun immunity", "support", f"Sun supports life force from the {ordinal(sun['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def illness_category(lagna_lord: dict, sixth_lord: dict, eighth_lord: dict) -> dict:
    sixth_yoga = applying_yoga(lagna_lord, sixth_lord)
    eighth_yoga = applying_yoga(lagna_lord, eighth_lord)
    evidence = []
    score = 0
    blockers = 0
    sixth_gap = sixth_yoga.get("degree_gap", 99)
    eighth_gap = eighth_yoga.get("degree_gap", 99)
    if sixth_yoga["state"] != "none" and sixth_gap <= eighth_gap:
        evidence.append(item("Ailment category", "caution", "The strongest disease connection is to the 6th lord, suggesting an acute, treatable, or inflammatory condition."))
        blockers += 1 if sixth_yoga["state"] == "applying" else 0
        score += 1 if sixth_yoga["state"] == "separating" else -1
    elif eighth_yoga["state"] != "none":
        evidence.append(item("Ailment category", "blocked", "The strongest disease connection is to the 8th lord, suggesting chronicity, depth, crisis, or surgical/structural involvement."))
        blockers += 2 if eighth_yoga["state"] == "applying" else 1
        score -= 2 if eighth_yoga["state"] == "applying" else 0
    else:
        evidence.append(item("Ailment category", "neutral", "No close Lagna-lord contact with the 6th or 8th lord; symptoms may be situational or still unclear."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def illness_progression(lagna_lord: dict, sixth_lord: dict, eighth_lord: dict) -> dict:
    candidates = []
    for target, label in [(sixth_lord, "6th lord"), (eighth_lord, "8th lord")]:
        yoga = applying_yoga(lagna_lord, target)
        if yoga["state"] != "none":
            weight = 1 if label == "6th lord" else 2
            candidates.append({**yoga, "target_label": label, "target_planet": target, "weight": weight})
    if not candidates:
        return {
            "score": 0,
            "blockers": 0,
            "state": "none",
            "yoga": None,
            "target_planet": None,
            "evidence": [item("Disease progression", "neutral", "No close Tajika disease yoga is active between the body and 6th/8th lords.")],
        }
    applying = [candidate for candidate in candidates if candidate["state"] == "applying"]
    pool = applying or candidates
    chosen = sorted(pool, key=lambda item: (item["degree_gap"], -item["weight"]))[0]
    if chosen["state"] == "applying":
        score = -3 if chosen["target_label"] == "6th lord" else -4
        blockers = 1 if chosen["target_label"] == "6th lord" else 2
        status = "blocked"
        text = f"The Lagna lord applies to the {chosen['target_label']} by {chosen['aspect_name']} within {chosen['degree_gap']} degrees; the illness may still be intensifying."
    else:
        score = 3
        blockers = 0
        status = "support"
        text = f"The Lagna lord separates from the {chosen['target_label']} by {chosen['aspect_name']}; the peak has likely passed and recovery can begin."
    return {
        "score": score,
        "blockers": blockers,
        "state": chosen["state"],
        "yoga": chosen,
        "target_planet": chosen["target_planet"],
        "evidence": [item("Disease progression", status, text)],
    }

def treatment_pillars(lagna_lord: dict, fourth_lord: dict, tenth_lord: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    if tenth_lord["house"] in SUPPORT_HOUSES and aspect_between(tenth_lord["longitude"], lagna_lord["longitude"]):
        score += 2
        evidence.append(item("Doctor", "strong", f"{tenth_lord['name']} is strong and contacts the Lagna lord; the doctor understands the case."))
    elif tenth_lord["house"] in HIDDEN_HOUSES or tenth_lord["retrograde"]:
        score -= 1
        blockers += 1
        evidence.append(item("Doctor", "caution", f"{tenth_lord['name']} is weak/retrograde or hidden, so medical guidance may need review or second opinion."))
    else:
        evidence.append(item("Doctor", "neutral", f"{tenth_lord['name']} is in the {ordinal(tenth_lord['house'])} house."))

    if fourth_lord["house"] in HIDDEN_HOUSES or fourth_lord["retrograde"]:
        score -= 2
        blockers += 1
        evidence.append(item("Medicine", "blocked", f"{fourth_lord['name']} rules treatment and is weak/retrograde or hidden; medication may need re-evaluation."))
    else:
        score += 1
        evidence.append(item("Medicine", "support", f"{fourth_lord['name']} supports treatment from the {ordinal(fourth_lord['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def disease_pillars(seventh_lord: dict, twelfth_lord: dict, moon: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    if seventh_lord["house"] in SUPPORT_HOUSES:
        score -= 1
        evidence.append(item("Disease strength", "caution", f"{seventh_lord['name']} as disease lord is visible in the {ordinal(seventh_lord['house'])} house."))
    elif seventh_lord["house"] in HIDDEN_HOUSES:
        evidence.append(item("Disease strength", "neutral", f"{seventh_lord['name']} as disease lord is hidden in the {ordinal(seventh_lord['house'])} house."))

    if twelfth_lord["house"] in {1, 6, 8, 12}:
        score -= 2
        blockers += 1
        evidence.append(item("Hospitalization", "caution", f"{twelfth_lord['name']} links hospitalization/bed rest with the {ordinal(twelfth_lord['house'])} house."))
    else:
        score += 1
        evidence.append(item("Hospitalization", "support", "The 12th lord does not strongly force confinement or bed-rest indicators."))

    if moon["house"] in HIDDEN_HOUSES:
        score -= 1
        evidence.append(item("Moon mind-body", "caution", f"Moon in the {ordinal(moon['house'])} house shows stress, fluids, sleep, or psychosomatic load affecting recovery."))
    else:
        evidence.append(item("Moon mind-body", "neutral", f"Moon is in the {ordinal(moon['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def illness_karakas(sun: dict, moon: dict, mars: dict, saturn: dict, rahu: dict, ketu: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for planet, label, meaning in [
        (mars, "Mars", "fever, inflammation, blood pressure, surgery, or accident signatures"),
        (saturn, "Saturn", "chronic, structural, joint, nerve, or degenerative signatures"),
        (rahu, "Rahu", "toxicity, allergy, viral, mysterious, or hard-to-diagnose signatures"),
        (ketu, "Ketu", "hidden, sudden, surgical, or atypical symptom signatures"),
    ]:
        if planet["house"] in {1, 6, 8, 12}:
            score -= 1
            blockers += 1 if planet["house"] in {6, 8} else 0
            evidence.append(item(label, "caution", f"{label} activates illness terrain from the {ordinal(planet['house'])} house: {meaning}."))
        else:
            evidence.append(item(label, "neutral", f"{label} is in the {ordinal(planet['house'])} house."))
    if sun["house"] in {1, 4, 5, 9, 10, 11} and moon["house"] in {1, 4, 5, 9, 10, 11}:
        score += 1
        evidence.append(item("Luminaries", "support", "Sun and Moon both have reasonably supportive house placement for recovery resilience."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d6_hidden_source(chart: dict, planet_names: list[str]) -> dict:
    evidence = []
    score = 0
    blockers = 0
    planets = {planet["name"]: planet for planet in chart["planets"]}
    lagna_sign = varga_sign_index(chart["lagna"]["longitude"], "D6")
    for name in planet_names:
        planet = planets[name]
        sign = varga_sign_index(planet["longitude"], "D6")
        house = whole_sign_house(sign * 30.0, lagna_sign)
        ruler = SIGN_LORDS[sign]
        root = d6_root_meaning(ruler)
        if DEBILITATION_SIGNS.get(name) == sign:
            score -= 2
            blockers += 1
            evidence.append(item("D6 hidden source", "blocked", f"{name} is debilitated in D6 {SIGNS[sign]}, pointing to vulnerable {root}."))
        elif EXALTATION_SIGNS.get(name) == sign or SIGN_LORDS[sign] == name:
            score += 1
            evidence.append(item("D6 hidden source", "support", f"{name} is strong in D6 {SIGNS[sign]}, giving internal defense around {root}."))
        elif house in HIDDEN_HOUSES:
            score -= 1
            evidence.append(item("D6 hidden source", "caution", f"{name} falls in the D6 {ordinal(house)} house, pointing to hidden {root}."))
        else:
            evidence.append(item("D6 hidden source", "neutral", f"{name} falls in D6 {SIGNS[sign]}, house {house}, pointing toward {root}."))
    return {"score": score, "blockers": blockers, "evidence": evidence}

def d6_root_meaning(ruler: str) -> str:
    return {
        "Mars": "inflammatory, blood, fever, injury, or surgical themes",
        "Saturn": "structural, nerve, chronic, degenerative, or blockage themes",
        "Rahu": "toxic, allergic, viral, or unclear themes",
        "Ketu": "hidden, atypical, sudden, or surgical themes",
        "Moon": "fluid, sleep, mind-body, circulation, or hormonal themes",
        "Sun": "immunity, heart, bones, vitality, or constitutional themes",
        "Mercury": "nervous, skin, respiratory, digestive, or diagnostic-complexity themes",
        "Jupiter": "growth, liver, fat/metabolic, or protective-system themes",
        "Venus": "sugar, reproductive, urinary, tissue, or comfort-related themes",
    }.get(ruler, "mixed bodily themes")

def illness_verdict_from_score(score: int, blockers: int, progression_state: str) -> dict:
    if progression_state == "applying" and (blockers >= 3 or score <= -2):
        return {"level": "worsening_or_needs_care", "summary": "The chart shows illness still intensifying; timely professional medical care and treatment review are important."}
    if blockers >= 4 or score <= -3:
        return {"level": "no_or_delayed", "summary": "Recovery is not cleanly shown yet; chronicity, weak vitality, or treatment complications dominate."}
    if progression_state == "separating" and score >= 3:
        return {"level": "recovery", "summary": "The crisis appears to be passing and recovery is supported, especially with proper treatment."}
    if score >= 5 and blockers <= 1:
        return {"level": "yes", "summary": "Recovery is strongly supported, with vitality and treatment pillars helping the patient."}
    if score >= 2:
        return {"level": "possible_with_effort", "summary": "Recovery is possible, but treatment consistency, diagnosis, or follow-up needs attention."}
    return {"level": "uncertain", "summary": "The chart is mixed; vitality and disease indicators are not clearly resolved yet."}

def illness_timing_from_yoga(yoga: dict | None, first: dict, second: dict | None) -> dict | None:
    if not yoga or not second:
        return None
    sign_index = first["sign_index"] if abs(first["speed"]) >= abs(second["speed"]) else second["sign_index"]
    if sign_index in {0, 3, 6, 9, 2, 5, 8, 11}:
        unit = "days to weeks"
    else:
        unit = "weeks to months"
    direction = "relief/recovery" if yoga["state"] == "separating" else "peak/intensification"
    return {
        "degree_gap": yoga["degree_gap"],
        "unit": unit,
        "summary": f"Use about {yoga['degree_gap']} degrees as the health timing seed for {direction}, read as {unit}.",
    }

