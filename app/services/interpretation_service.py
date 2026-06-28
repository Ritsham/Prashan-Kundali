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


def detect_general_intent(question: str, domain: str) -> dict:
    text = question.lower()
    if any(word in text for word in ["when", "date", "time", "soon", "how long"]):
        return {"focus": "timing", "summary": "The querent is mainly asking about timing, so applying yogas and the Moon's movement lead the judgment."}
    if any(word in text for word in ["will", "can i", "possible", "happen", "success", "get"]):
        return {"focus": "promise", "summary": "The querent is asking whether the matter will materialize, so Lagna, Moon, 10th action, 11th fulfilment, and 4th conclusion are judged."}
    if any(word in text for word in ["why", "problem", "delay", "stuck", "block", "obstacle"]):
        return {"focus": "obstacle", "summary": "The querent is asking about obstacles, so hidden houses and malefic pressure receive extra weight."}
    return {"focus": domain or "general", "summary": "The question is read as a general Prashna, using the querent, mind, action, fulfilment, conclusion, and outside-party houses."}


def general_readiness(lagna_lord: dict, moon: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for label, planet in [("Querent strength", lagna_lord), ("Moon and intention", moon)]:
        if planet["house"] in {1, 4, 5, 9, 10, 11} and not planet["retrograde"]:
            score += 2
            evidence.append(item(label, "support", f"{planet['name']} is placed in the {ordinal(planet['house'])} house, giving usable strength and clarity."))
        elif planet["house"] in HIDDEN_HOUSES or planet["retrograde"]:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is in the {ordinal(planet['house'])} house or retrograde, showing hesitation, pressure, or hidden conditions."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} is in the {ordinal(planet['house'])} house, giving a moderate baseline."))
    return {"score": score, "blockers": blockers, "evidence": evidence}


def general_outcome_support(fourth_lord: dict, tenth_lord: dict, eleventh_lord: dict) -> dict:
    evidence = []
    score = 0
    blockers = 0
    for label, planet, meaning in [
        ("Action path", tenth_lord, "effort, authority, and execution"),
        ("Fulfilment", eleventh_lord, "gain, approval, and desire fulfilment"),
        ("Final outcome", fourth_lord, "closure, peace, and settled result"),
    ]:
        if planet["house"] in {1, 4, 7, 9, 10, 11}:
            score += 1
            evidence.append(item(label, "support", f"{planet['name']} supports {meaning} from the {ordinal(planet['house'])} house."))
        elif planet["house"] in HIDDEN_HOUSES:
            score -= 1
            blockers += 1
            evidence.append(item(label, "caution", f"{planet['name']} is hidden in the {ordinal(planet['house'])} house, so {meaning} needs patience or correction."))
        else:
            evidence.append(item(label, "neutral", f"{planet['name']} shows {meaning} from the {ordinal(planet['house'])} house."))
    return {"score": score, "blockers": blockers, "evidence": evidence}


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


def unique_planets(names: list[str]) -> list[str]:
    result = []
    for name in names:
        if name not in result:
            result.append(name)
    return result


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
