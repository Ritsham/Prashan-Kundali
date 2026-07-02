from __future__ import annotations


def sign_lord_name(sign_index: int | None) -> str:
    lords = {
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
    return lords.get(sign_index, "Lagna lord")


def planets_by_name(chart: dict) -> dict[str, dict]:
    return {planet.get("name"): planet for planet in chart.get("planets", []) if planet.get("name")}


def angular_gap(first: float, second: float) -> float:
    gap = abs((first - second) % 360)
    return min(gap, 360 - gap)


def aspect_synthesis_hint(first: dict, second: dict, aspect: str) -> str:
    first_name = first.get("name", "first planet")
    second_name = second.get("name", "second planet")
    if aspect in {"conjunction", "trine", "sextile"}:
        tone = "blend or support each other"
    elif aspect == "opposition":
        tone = "create an axis that must be balanced"
    else:
        tone = "create friction that must be handled deliberately"
    return f"{first_name} and {second_name} {tone}; interpret their combined houses before isolating either placement."


def planets_connected(planets: dict[str, dict], first_name: str, second_name: str) -> bool:
    first = planets.get(first_name)
    second = planets.get(second_name)
    if not first or not second or first_name == second_name:
        return False
    if first.get("sign_index") == second.get("sign_index") or first.get("house") == second.get("house"):
        return True
    first_sign = first.get("sign_index")
    second_sign = second.get("sign_index")
    if isinstance(first_sign, int) and isinstance(second_sign, int) and (first_sign - second_sign) % 12 == 6:
        return True
    first_lon = first.get("longitude")
    second_lon = second.get("longitude")
    if isinstance(first_lon, (int, float)) and isinstance(second_lon, (int, float)):
        return any(abs(angular_gap(float(first_lon), float(second_lon)) - exact) <= 6 for exact in [0, 60, 90, 120, 180])
    return False


def add_if_present(items: list[dict], name: str, condition: bool, note: str) -> None:
    if condition:
        items.append({"name": name, "interpretive_note": note})


def planet_strength_matrix(chart: dict) -> list[dict]:
    return [planet_strength_note(planet) for planet in chart.get("planets", [])]


def planet_strength_note(planet: dict) -> dict:
    name = planet.get("name", "")
    sign_index = planet.get("sign_index")
    sign = planet.get("sign", "")
    house = planet.get("house")
    dignity = "ordinary"
    reason = "No special sign dignity is supplied from the basic dignity checks."
    exaltation = {
        "Sun": 0,
        "Moon": 1,
        "Mars": 9,
        "Mercury": 5,
        "Jupiter": 3,
        "Venus": 11,
        "Saturn": 6,
    }
    debilitation = {
        "Sun": 6,
        "Moon": 7,
        "Mars": 3,
        "Mercury": 11,
        "Jupiter": 9,
        "Venus": 5,
        "Saturn": 0,
    }
    own_signs = {
        "Sun": {4},
        "Moon": {3},
        "Mars": {0, 7},
        "Mercury": {2, 5},
        "Jupiter": {8, 11},
        "Venus": {1, 6},
        "Saturn": {9, 10},
    }
    if sign_index == exaltation.get(name):
        dignity = "exalted"
        reason = f"{name} is exalted in {sign}."
    elif sign_index == debilitation.get(name):
        dignity = "debilitated"
        reason = f"{name} is debilitated in {sign}."
    elif sign_index in own_signs.get(name, set()):
        dignity = "own sign"
        reason = f"{name} is in its own sign {sign}."
    house_condition = "supportive" if house in {1, 4, 5, 7, 9, 10, 11} else "pressured" if house in {6, 8, 12} else "neutral"
    motion = "retrograde" if planet.get("retrograde") else "direct"
    if house_condition == "supportive":
        house_note = f"{name} is in a house that can express results more visibly, so its agenda is easier to use constructively."
    elif house_condition == "pressured":
        house_note = f"{name} is in a pressure house, so its agenda may work through delay, correction, conflict, expense, or hidden work before results become stable."
    else:
        house_note = f"{name} is in a neutral house, so its result depends more on dignity, aspects, and role in the question."
    motion_note = (
        f"{name} is retrograde, therefore its promise may require review, repetition, delay, or internal correction before it becomes reliable."
        if planet.get("retrograde")
        else f"{name} is direct, therefore its agenda can move more straightforwardly if other factors support it."
    )
    return {
        "planet": name,
        "sign": sign,
        "house": house,
        "dignity": dignity,
        "house_condition": house_condition,
        "motion": motion,
        "nakshatra": planet.get("nakshatra"),
        "pada": planet.get("pada"),
        "interpretive_note": reason,
        "causal_note": f"{reason} {house_note} {motion_note}",
    }


def relationship_scan(chart: dict) -> dict:
    planets = chart.get("planets", [])
    conjunctions = []
    oppositions = []
    house_clusters: dict[int, list[str]] = {}
    for planet in planets:
        house = planet.get("house")
        if isinstance(house, int):
            house_clusters.setdefault(house, []).append(planet.get("name", ""))
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            if first.get("sign_index") == second.get("sign_index"):
                conjunctions.append(
                    {
                        "planets": [first.get("name"), second.get("name")],
                        "sign": first.get("sign"),
                        "house": first.get("house"),
                    }
                )
            first_sign = first.get("sign_index")
            second_sign = second.get("sign_index")
            if isinstance(first_sign, int) and isinstance(second_sign, int) and (first_sign - second_sign) % 12 == 6:
                oppositions.append(
                    {
                        "planets": [first.get("name"), second.get("name")],
                        "axis": [first.get("sign"), second.get("sign")],
                        "houses": [first.get("house"), second.get("house")],
                    }
                )
    return {
        "same_sign_conjunctions": conjunctions,
        "opposition_axes": oppositions,
        "house_clusters": {str(house): names for house, names in house_clusters.items() if len(names) > 1},
        "note": "This is a basic relationship scan from supplied signs and houses; use rule evidence for exact Tajika applying/separating yogas.",
    }


def aspect_matrix(chart: dict) -> list[dict]:
    planets = chart.get("planets", [])
    aspects = []
    aspect_defs = [
        (0, "conjunction"),
        (60, "sextile"),
        (90, "square"),
        (120, "trine"),
        (180, "opposition"),
    ]
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            first_lon = first.get("longitude")
            second_lon = second.get("longitude")
            if not isinstance(first_lon, (int, float)) or not isinstance(second_lon, (int, float)):
                continue
            gap = angular_gap(float(first_lon), float(second_lon))
            for exact, name in aspect_defs:
                orb = abs(gap - exact)
                if orb <= 6:
                    aspects.append(
                        {
                            "planets": [first.get("name"), second.get("name")],
                            "aspect": name,
                            "orb_degrees": round(orb, 2),
                            "houses": [first.get("house"), second.get("house")],
                            "signs": [first.get("sign"), second.get("sign")],
                            "synthesis_hint": aspect_synthesis_hint(first, second, name),
                        }
                    )
                    break
    return aspects


def exchange_scan(chart: dict) -> list[dict]:
    planets = [planet for planet in chart.get("planets", []) if planet.get("name") not in {"Rahu", "Ketu"}]
    exchanges = []
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            first_sign = first.get("sign_index")
            second_sign = second.get("sign_index")
            if not isinstance(first_sign, int) or not isinstance(second_sign, int):
                continue
            if sign_lord_name(first_sign) == second.get("name") and sign_lord_name(second_sign) == first.get("name"):
                exchanges.append(
                    {
                        "planets": [first.get("name"), second.get("name")],
                        "signs": [first.get("sign"), second.get("sign")],
                        "houses": [first.get("house"), second.get("house")],
                        "interpretive_note": "Parivartana-style exchange candidate; blend both house agendas before judging either planet separately.",
                    }
                )
    return exchanges


def combustion_scan(chart: dict) -> list[dict]:
    planets = planets_by_name(chart)
    sun = planets.get("Sun")
    if not sun or not isinstance(sun.get("longitude"), (int, float)):
        return []
    thresholds = {
        "Moon": 12,
        "Mars": 17,
        "Mercury": 14,
        "Jupiter": 11,
        "Venus": 10,
        "Saturn": 15,
    }
    combust = []
    for name, threshold in thresholds.items():
        planet = planets.get(name)
        if not planet or not isinstance(planet.get("longitude"), (int, float)):
            continue
        gap = angular_gap(float(sun["longitude"]), float(planet["longitude"]))
        if gap <= threshold:
            combust.append(
                {
                    "planet": name,
                    "sun_gap_degrees": round(gap, 2),
                    "threshold_degrees": threshold,
                    "interpretive_note": f"{name} is close enough to the Sun to require combustion-style caution before interpreting its promise.",
                }
            )
    return combust


def yoga_candidate_scan(chart: dict, archetype: str, domain: str | None) -> list[dict]:
    planets = planets_by_name(chart)
    lagna = chart.get("lagna", {})
    lagna_sign = lagna.get("sign_index")
    candidates = []

    if not isinstance(lagna_sign, int):
        return candidates

    house_lords = {
        house: sign_lord_name((lagna_sign + house - 1) % 12)
        for house in range(1, 13)
    }

    def lord(house: int) -> str:
        return house_lords.get(house, "")

    def lord_in_house(house_lord_of: int, target_houses: set[int]) -> bool:
        planet = planets.get(lord(house_lord_of), {})
        return planet.get("house") in target_houses

    def lords_connected(a: int, b: int) -> bool:
        return planets_connected(planets, lord(a), lord(b))

    def planet_in_houses(name: str, houses: set[int]) -> bool:
        return planets.get(name, {}).get("house") in houses

    def any_lord_connected(houses_a: list[int], houses_b: list[int]) -> bool:
        return any(lords_connected(a, b) for a in houses_a for b in houses_b)

    # -------------------------
    # COMMON CORE YOGAS
    # -------------------------

    add_if_present(
        candidates,
        "Dhana Yoga candidate",
        any(
            lord(a) == lord(b) or lords_connected(a, b)
            for a in [2, 5, 9, 11]
            for b in [2, 5, 9, 11]
            if a < b
        ),
        "Money, merit, intelligence, and gain houses show a relationship bridge. Use only after judging strength, dignity, and leakage factors.",
    )

    add_if_present(
        candidates,
        "Raja Yoga candidate",
        any_lord_connected([1, 4, 7, 10], [5, 9]),
        "Kendra and trikona factors connect, suggesting capacity for rise, support, or recognition if dignity and domain relevance agree.",
    )

    add_if_present(
        candidates,
        "Viparita Raja Yoga candidate",
        any(lord_in_house(h, {6, 8, 12}) for h in [6, 8, 12]),
        "A dusthana lord sits in a dusthana, so pressure may convert into advantage after struggle, correction, or hidden work.",
    )

    add_if_present(
        candidates,
        "Neecha Bhanga candidate",
        any(note["dignity"] == "debilitated" for note in planet_strength_matrix(chart)),
        "A debilitated planet exists. Check whether cancellation support exists before treating weakness as final.",
    )

    add_if_present(
        candidates,
        "Parivartana Yoga candidate",
        bool(exchange_scan(chart)),
        "An exchange exists. The exchanged houses must be interpreted as one combined mechanism rather than separately.",
    )

    add_if_present(
        candidates,
        "Lagna-Result Bridge",
        any_lord_connected([1], [10, 11, 4]),
        "The querent connects with action, fulfillment, or final outcome. This improves result potential if the connected lords are strong.",
    )

    add_if_present(
        candidates,
        "Moon-Support Protection",
        planets_connected(planets, "Moon", "Jupiter") or planets_connected(planets, "Moon", "Venus"),
        "Moon receives support from a benefic factor. This may protect judgment, flow, or emotional steadiness.",
    )

    add_if_present(
        candidates,
        "Chandra Mangala candidate",
        planets_connected(planets, "Moon", "Mars"),
        "Moon and Mars connect. This can show drive, commercial instinct, urgency, or emotional impatience depending on the domain.",
    )

    add_if_present(
        candidates,
        "Gaja Kesari candidate",
        planets_connected(planets, "Moon", "Jupiter"),
        "Moon and Jupiter connect. This can protect judgment, guidance, public trust, or recovery depending on the question.",
    )

    add_if_present(
        candidates,
        "Lakshmi-style Prosperity candidate",
        any_lord_connected([1, 9], [2, 11]) or any_lord_connected([5, 9], [2, 11]),
        "Fortune/intelligence houses connect with wealth/gain houses. This can support prosperity if leakage and dusthana pressure do not dominate.",
    )

    add_if_present(
        candidates,
        "Obstacle-to-Outcome Bridge",
        any_lord_connected([6, 8, 12], [10, 11, 4]),
        "Obstacle houses connect with action, gains, or final outcome. The matter may succeed only after handling pressure, delay, debt, illness, opposition, or hidden complications.",
    )

    # -------------------------
    # WEALTH / MONEY
    # -------------------------

    if domain == "wealth" or archetype in {"Wealth / Money", "Startup / Business Launch"}:
        add_if_present(
            candidates,
            "Income-Retention Bridge",
            lords_connected(2, 11),
            "The stored-wealth house and gains house connect. This supports converting inflow into retained money if 12th-house leakage is controlled.",
        )

        add_if_present(
            candidates,
            "Speculation-Gain Bridge",
            lords_connected(5, 11),
            "The intelligence/speculation house connects with gains. Useful for investment or risk-based wealth only if the question truly involves speculation.",
        )

        add_if_present(
            candidates,
            "Wealth Leakage Warning",
            any_lord_connected([12, 8], [2, 11]) or planet_in_houses("Moon", {12}) or planet_in_houses("Venus", {8, 12}),
            "Loss, expense, debt, or hidden-risk houses touch money/gain factors. Revenue may not automatically become retained wealth.",
        )

        add_if_present(
            candidates,
            "Funding / Other People's Money Signal",
            any_lord_connected([8], [2, 10, 11]) or planet_in_houses("Jupiter", {8}) or planet_in_houses("Venus", {8}),
            "The 8th house connects with wealth or action. This may show funding, investors, debt, taxation, hidden capital, or delayed realization.",
        )

    # -------------------------
    # STARTUP / BUSINESS / APP
    # -------------------------

    if archetype == "Startup / Business Launch":
        add_if_present(
            candidates,
            "Founder-Execution Bridge",
            lords_connected(1, 10),
            "Founder and execution houses connect. This supports building capacity, but strength decides whether execution is clean or pressured.",
        )

        add_if_present(
            candidates,
            "Execution-Gain Bridge",
            lords_connected(10, 11),
            "Business action connects with gains. This supports monetization or traction if market acceptance also appears.",
        )

        add_if_present(
            candidates,
            "Market-Acceptance Bridge",
            lords_connected(1, 7) or lords_connected(7, 11),
            "Founder, market, and gains connect. This is important for user adoption, customer response, and public acceptance.",
        )

        add_if_present(
            candidates,
            "Product-Communication Bridge",
            lords_connected(3, 10) or lords_connected(3, 11) or planet_in_houses("Mercury", {3, 10, 11}),
            "Communication/software/iteration factors connect with execution or gains. This supports product iteration, marketing, or platform growth.",
        )

        add_if_present(
            candidates,
            "Scale / Network Signal",
            lords_connected(11, 3) or lords_connected(11, 7) or planet_in_houses("Rahu", {3, 7, 10, 11}),
            "Network, market, or technology factors are activated. This can support scale, but Rahu/Saturn pressure may make growth unstable or delayed.",
        )

        add_if_present(
            candidates,
            "Burn-Rate Warning",
            any_lord_connected([12], [10, 11, 2]) or planet_in_houses("Moon", {12}),
            "Expense or invisible-effort factors touch business/gain houses. The venture may require controlled burn and slower scaling.",
        )

    # -------------------------
    # HEALTH / ILLNESS
    # -------------------------

    if domain == "illness" or archetype == "Health / Illness":
        add_if_present(
            candidates,
            "Vitality-Recovery Bridge",
            any_lord_connected([1], [4, 10, 11]) or planets_connected(planets, lord(1), "Sun"),
            "Vitality connects with medicine, doctor, recovery, or fulfillment factors. This supports improvement if disease pressure is not stronger.",
        )

        add_if_present(
            candidates,
            "Disease Pressure Signal",
            any_lord_connected([6, 8, 12], [1]) or lord_in_house(1, {6, 8, 12}),
            "Disease, chronic pressure, or hospitalization houses affect the body/vitality. Medical care and monitoring become essential.",
        )

        add_if_present(
            candidates,
            "Treatment Support Signal",
            lords_connected(4, 10) or any_lord_connected([4, 10], [1, 11]),
            "Medicine and doctor/treatment houses support recovery. This favors proper diagnosis, treatment, and follow-up.",
        )

        add_if_present(
            candidates,
            "Chronic / Hidden Condition Warning",
            any_lord_connected([8], [1, 6, 12]) or planet_in_houses("Moon", {8, 12}),
            "Deep, hidden, chronic, or recurring pressure is indicated. Do not rely on symbolic timing alone; medical testing matters.",
        )

    # -------------------------
    # MARRIAGE / RELATIONSHIP
    # -------------------------

    if domain == "marriage" or archetype == "Marriage / Relationship":
        add_if_present(
            candidates,
            "Union Bridge",
            lords_connected(1, 7),
            "Querent and partner houses connect. This is the primary relationship/union bridge; dignity decides whether it is smooth or conflicted.",
        )

        add_if_present(
            candidates,
            "Marriage Fulfillment Bridge",
            any_lord_connected([7], [2, 11]) or any_lord_connected([1, 7], [2, 11]),
            "Partner/union factors connect with family and fulfillment houses. This supports formalization, family acceptance, or completion.",
        )

        add_if_present(
            candidates,
            "Romance-to-Commitment Bridge",
            any_lord_connected([5], [7, 11]),
            "Romance or affection connects with partnership or fulfillment. This supports relationship movement beyond attraction if stable factors agree.",
        )

        add_if_present(
            candidates,
            "Relationship Stress / Break Signal",
            any_lord_connected([6, 8, 12], [1, 7]) or planet_in_houses("Venus", {6, 8, 12}),
            "Conflict, fear, distance, secrecy, or withdrawal houses touch relationship factors. The matter needs careful handling.",
        )

        add_if_present(
            candidates,
            "Harmony Support",
            planets_connected(planets, "Moon", "Venus") or planets_connected(planets, "Jupiter", "Venus"),
            "Emotional flow or wisdom connects with relationship harmony. This can soften conflict if other factors do not block union.",
        )

    # -------------------------
    # CHILD / PROGENY
    # -------------------------

    if domain == "child" or archetype == "Child / Conception":
        add_if_present(
            candidates,
            "Progeny Promise Bridge",
            any_lord_connected([1, 5], [5, 9, 11]) or planets_connected(planets, lord(5), "Jupiter"),
            "Body, child, fortune, and fulfillment factors connect. This supports progeny promise if afflictions do not dominate.",
        )

        add_if_present(
            candidates,
            "Jupiter-5th Support",
            planet_in_houses("Jupiter", {1, 5, 9, 11}) or planets_connected(planets, "Jupiter", lord(5)),
            "Jupiter supports the child/progeny matter. Judge strength and affliction before giving a positive result.",
        )

        add_if_present(
            candidates,
            "Delay / Medical Caution for Progeny",
            any_lord_connected([6, 8, 12], [5]) or lord_in_house(5, {6, 8, 12}),
            "The child house connects with disease, delay, hidden factors, or loss houses. Medical guidance and patience may be needed.",
        )

        add_if_present(
            candidates,
            "Family Continuity Support",
            any_lord_connected([2, 5, 9], [11]),
            "Family, child, fortune, and fulfillment houses connect. This supports eventual continuity if the main promise is not blocked.",
        )

    # -------------------------
    # GOVERNMENT CAREER
    # -------------------------

    if archetype == "Government Career" or (domain == "job_career" and str(archetype).lower().startswith("government")):
        add_if_present(
            candidates,
            "Government Authority Bridge",
            any_lord_connected([10], [5, 6, 11]) or planet_in_houses("Sun", {1, 6, 10, 11}),
            "Career/authority connects with competition, exam, or appointment houses. This supports government selection if strength agrees.",
        )

        add_if_present(
            candidates,
            "Competition-to-Appointment Bridge",
            lords_connected(6, 11) or any_lord_connected([5, 6], [10, 11]),
            "Competition/exam factors connect with appointment/gain. This is useful for selection after effort.",
        )

        add_if_present(
            candidates,
            "Bureaucratic Delay Signal",
            any_lord_connected([8, 12], [10, 11]) or planet_in_houses("Saturn", {6, 8, 10, 12}),
            "Delay, paperwork, authority gatekeeping, or procedural pressure may affect the career result.",
        )

        add_if_present(
            candidates,
            "Service Stability Signal",
            planet_in_houses("Saturn", {6, 10, 11}) or lords_connected(6, 10),
            "Service, discipline, routine, and career houses connect. This favors stable employment if selection is achieved.",
        )

    # -------------------------
    # PRIVATE CAREER
    # -------------------------

    if archetype in {"Career / Job", "Private Career"} or (domain == "job_career" and archetype != "Government Career"):
        add_if_present(
            candidates,
            "Interview-Offer Bridge",
            any_lord_connected([6, 7], [10, 11]),
            "Interview/employer/contract factors connect with role or offer fulfillment. This supports job movement if dignity agrees.",
        )

        add_if_present(
            candidates,
            "Salary-Growth Bridge",
            any_lord_connected([2, 10], [11]) or lords_connected(2, 10),
            "Income, role, and gains connect. This supports salary/package or career growth.",
        )

        add_if_present(
            candidates,
            "Corporate Communication Support",
            planet_in_houses("Mercury", {1, 6, 7, 10, 11}) or any_lord_connected([3], [6, 7, 10, 11]),
            "Communication, interview, documentation, or corporate process factors support the job path.",
        )

        add_if_present(
            candidates,
            "Workplace Pressure Warning",
            any_lord_connected([6, 8, 12], [10]) or planet_in_houses("Saturn", {8, 12}),
            "Workload, delay, hidden pressure, or dissatisfaction may affect career quality even if a role appears.",
        )

    # -------------------------
    # FOREIGN / TRAVEL
    # -------------------------

    if domain == "foreign" or archetype == "Travel / Foreign":
        add_if_present(
            candidates,
            "Foreign Movement Bridge",
            any_lord_connected([1, 4], [7, 9, 12]) or any_lord_connected([3, 9], [12]),
            "Self/home/document/travel houses connect with foreign or distance houses. This supports movement if permissions align.",
        )

        add_if_present(
            candidates,
            "Visa / Permission Bridge",
            any_lord_connected([9, 10, 11], [12]) or any_lord_connected([3], [9, 11]),
            "Permission, authority, documents, and foreign houses connect. This supports visa or approval if not blocked by Saturn/8th/12th pressure.",
        )

        add_if_present(
            candidates,
            "Settlement Away From Home Signal",
            any_lord_connected([4], [12]) or planet_in_houses("Rahu", {7, 9, 12}),
            "Home/base connects with foreign residence or separation. This supports relocation or distance from birthplace if other factors agree.",
        )

        add_if_present(
            candidates,
            "Travel Delay / Document Warning",
            any_lord_connected([6, 8, 12], [3, 9]) or planet_in_houses("Saturn", {3, 9, 12}),
            "Documents, permissions, delay, or procedural obstacles may slow travel or foreign settlement.",
        )

    # -------------------------
    # EDUCATION
    # -------------------------

    if domain == "education" or archetype == "Education / Exam":
        add_if_present(
            candidates,
            "Study-Result Bridge",
            any_lord_connected([4, 5, 9], [10, 11]),
            "Education, exam, higher study, result, and fulfillment houses connect. This supports academic outcome if discipline is present.",
        )

        add_if_present(
            candidates,
            "Exam Intelligence Support",
            planet_in_houses("Mercury", {1, 4, 5, 9, 10, 11}) or planets_connected(planets, "Mercury", lord(5)),
            "Mercury supports learning, analysis, exam thinking, or communication. Judge stress and consistency before final result.",
        )

        add_if_present(
            candidates,
            "Teacher / Higher Knowledge Support",
            planet_in_houses("Jupiter", {1, 5, 9, 10, 11}) or planets_connected(planets, "Jupiter", lord(9)),
            "Jupiter supports guidance, higher education, wisdom, or mentor help.",
        )

        add_if_present(
            candidates,
            "Study Delay / Concentration Warning",
            any_lord_connected([6, 8, 12], [4, 5, 9]) or planet_in_houses("Moon", {6, 8, 12}),
            "Stress, delay, distraction, health, or hidden pressure may affect preparation and concentration.",
        )

    # -------------------------
    # PROPERTY / HOME
    # -------------------------

    if domain == "property" or archetype == "Property / Home":
        add_if_present(
            candidates,
            "Property Acquisition Bridge",
            any_lord_connected([1, 4], [2, 10, 11]) or lords_connected(4, 11),
            "Home/property factors connect with money, action, or fulfillment. This supports acquisition or settlement if documents are clean.",
        )

        add_if_present(
            candidates,
            "Document / Payment Warning",
            any_lord_connected([6, 8, 12], [2, 4]) or planet_in_houses("Saturn", {4, 8, 12}),
            "Property, money, debt, dispute, or document houses are pressured. Verification and staged payment are important.",
        )

        add_if_present(
            candidates,
            "Stable Asset Signal",
            planet_in_houses("Saturn", {4, 10, 11}) or lords_connected(2, 4),
            "Stability and asset houses connect. This supports long-term property value if legal/payment risks are controlled.",
        )

    # -------------------------
    # LITIGATION / CONFLICT
    # -------------------------

    if archetype == "Litigation / Conflict":
        add_if_present(
            candidates,
            "Dispute Victory Bridge",
            any_lord_connected([1, 6], [10, 11]) or lord_in_house(6, {6, 10, 11}),
            "Querent/dispute factors connect with authority or fulfillment. This may support victory after effort if the opponent is weaker.",
        )

        add_if_present(
            candidates,
            "Opponent Pressure Signal",
            any_lord_connected([7], [6, 8, 12]) or lord_in_house(7, {6, 8, 12}),
            "The opponent/other party is under pressure. This can weaken their position if the querent's factors are stronger.",
        )

        add_if_present(
            candidates,
            "Settlement Possibility",
            any_lord_connected([1, 7], [4, 11]) or planets_connected(planets, "Venus", lord(7)),
            "Querent and opponent factors connect with peace/final settlement/fulfillment. Settlement may be possible if conflict indicators soften.",
        )

        add_if_present(
            candidates,
            "Legal Delay Warning",
            any_lord_connected([8, 12], [6, 7, 10]) or planet_in_houses("Saturn", {6, 8, 10, 12}),
            "Court, dispute, authority, or delay houses are pressured. The matter may stretch through procedure or hidden complications.",
        )

    return candidates
