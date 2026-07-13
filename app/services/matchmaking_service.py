from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from app.config import get_settings

from app.astrology.constants import NAKSHATRAS, SIGNS
from app.astrology.divisional import build_d1, build_divisional_chart_from_moon
from app.services.chart_calculator import calculate_prashna_chart
from app.services.geocoding_service import geocode_place
from app.services.timezone_service import timezone_at


GANA_BY_NAKSHATRA = {
    "Ashwini": "Deva",
    "Mrigashira": "Deva",
    "Punarvasu": "Deva",
    "Pushya": "Deva",
    "Hasta": "Deva",
    "Swati": "Deva",
    "Anuradha": "Deva",
    "Shravana": "Deva",
    "Revati": "Deva",
    "Bharani": "Manushya",
    "Rohini": "Manushya",
    "Ardra": "Manushya",
    "Purva Phalguni": "Manushya",
    "Uttara Phalguni": "Manushya",
    "Purva Ashadha": "Manushya",
    "Uttara Ashadha": "Manushya",
    "Purva Bhadrapada": "Manushya",
    "Uttara Bhadrapada": "Manushya",
    "Krittika": "Rakshasa",
    "Ashlesha": "Rakshasa",
    "Magha": "Rakshasa",
    "Chitra": "Rakshasa",
    "Vishakha": "Rakshasa",
    "Jyeshtha": "Rakshasa",
    "Mula": "Rakshasa",
    "Dhanishta": "Rakshasa",
    "Shatabhisha": "Rakshasa",
}

YONI_BY_NAKSHATRA = {
    "Ashwini": "Horse",
    "Bharani": "Elephant",
    "Krittika": "Sheep",
    "Rohini": "Serpent",
    "Mrigashira": "Serpent",
    "Ardra": "Dog",
    "Punarvasu": "Cat",
    "Pushya": "Sheep",
    "Ashlesha": "Cat",
    "Magha": "Rat",
    "Purva Phalguni": "Rat",
    "Uttara Phalguni": "Cow",
    "Hasta": "Buffalo",
    "Chitra": "Tiger",
    "Swati": "Buffalo",
    "Vishakha": "Tiger",
    "Anuradha": "Deer",
    "Jyeshtha": "Deer",
    "Mula": "Dog",
    "Purva Ashadha": "Monkey",
    "Uttara Ashadha": "Mongoose",
    "Shravana": "Monkey",
    "Dhanishta": "Lion",
    "Shatabhisha": "Horse",
    "Purva Bhadrapada": "Lion",
    "Uttara Bhadrapada": "Cow",
    "Revati": "Elephant",
}

SIGN_LORDS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

NATURAL_FRIENDS = {
    "Sun": {"Moon", "Mars", "Jupiter"},
    "Moon": {"Sun", "Mercury"},
    "Mars": {"Sun", "Moon", "Jupiter"},
    "Mercury": {"Sun", "Venus"},
    "Jupiter": {"Sun", "Moon", "Mars"},
    "Venus": {"Mercury", "Saturn"},
    "Saturn": {"Mercury", "Venus"},
}


def normalize_birth_payload(data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name") or "").strip()
    date = str(data.get("date_of_birth") or "").strip()
    time = str(data.get("time_of_birth") or "").strip()
    place = str(data.get("birth_place") or "").strip()
    selected_place = str(data.get("selected_place_name") or "").strip()
    accuracy = str(data.get("birth_time_accuracy") or "exact").strip().lower()
    gender = str(data.get("gender") or "").strip().lower()
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not name or not date or not place or gender not in {"male", "female", "other"}:
        raise ValueError("Name, date of birth, birth place, and gender are required.")
    if accuracy not in {"exact", "approximate", "unknown"}:
        raise ValueError("Birth time accuracy must be exact, approximate, or unknown.")
    if accuracy != "unknown" and not time:
        raise ValueError("Birth time is required unless birth time accuracy is unknown.")
    if accuracy == "unknown":
        time = "12:00"

    try:
        date_obj = datetime.fromisoformat(date)
    except ValueError as exc:
        raise ValueError("Date of birth must be a valid ISO date.") from exc
    if date_obj.date() > datetime.now().date():
        raise ValueError("Future birth dates are not allowed.")

    return {
        "name": name,
        "date_of_birth": date,
        "time_of_birth": time,
        "birth_place": selected_place or place,
        "selected_place_name": selected_place,
        "latitude": float(latitude) if latitude is not None else None,
        "longitude": float(longitude) if longitude is not None else None,
        "gender": gender,
        "birth_time_accuracy": accuracy,
    }


async def build_match_report(boy_input: dict[str, Any], girl_input: dict[str, Any]) -> dict[str, Any]:
    boy = normalize_birth_payload(boy_input)
    girl = normalize_birth_payload(girl_input)
    boy_chart = await generate_birth_chart(boy)
    girl_chart = await generate_birth_chart(girl)
    ashtakoota = calculate_ashtakoota(boy_chart, girl_chart)
    doshas = calculate_doshas(boy_chart, girl_chart)
    recommendation = build_recommendation(ashtakoota, doshas, boy, girl)
    dossier = build_matchmaking_dossier(boy, girl, boy_chart, girl_chart, ashtakoota, doshas, recommendation)

    return {
        "version": "matchmaking-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "participants": {"boy": boy, "girl": girl},
        "charts": {"boy": compact_chart(boy_chart), "girl": compact_chart(girl_chart)},
        "ashtakoota": ashtakoota,
        "doshas": doshas,
        "dossier": dossier,
        "summary": recommendation,
        "disclaimer": (
            "This matchmaking report is based on astrological calculations and traditional interpretation methods. "
            "It is intended for guidance only and should not be treated as a guaranteed prediction or final marriage decision."
        ),
    }


async def generate_birth_chart(person: dict[str, Any]) -> dict[str, Any]:
    if person.get("latitude") is not None and person.get("longitude") is not None:
        place = {
            "place_name": person.get("selected_place_name") or person["birth_place"],
            "latitude": person["latitude"],
            "longitude": person["longitude"],
            "source": "selected",
        }
    else:
        places = geocode_place(person["birth_place"], limit=1)
        if not places:
            raise ValueError(f"Could not resolve birth place: {person['birth_place']}")
        place = places[0]
    tz_name = timezone_at(float(place["latitude"]), float(place["longitude"]))
    local_dt = datetime.fromisoformat(f"{person['date_of_birth']}T{person['time_of_birth']}")
    local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_name))
    birth_utc = local_dt.astimezone(timezone.utc)

    payload = {
        "chart_type": "lagna",
        "name": person["name"],
        "gender": person["gender"],
        "birth_datetime_local": f"{person['date_of_birth']}T{person['time_of_birth']}",
        "location": {
            "latitude": float(place["latitude"]),
            "longitude": float(place["longitude"]),
            "place_name": place["place_name"],
        },
    }
    astrology_url = get_settings().astrology_engine_url
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{astrology_url}/calculate", json=payload, timeout=30.0)
        if resp.status_code == 200:
            chart = resp.json()["chart"]
            if "dashas" not in chart or not chart["dashas"]:
                from app.astrology.vimshottari import vimshottari_from_moon
                moon = next((p for p in chart.get("planets", []) if p.get("name") == "Moon"), None)
                if moon and "longitude" in moon:
                    chart["dashas"] = vimshottari_from_moon(moon["longitude"], birth_utc)
            return chart
    except httpx.RequestError:
        pass

    return await calculate_prashna_chart(
        question="Marriage match making birth chart",
        name=person["name"],
        asked_at_utc=birth_utc,
        latitude=float(place["latitude"]),
        longitude=float(place["longitude"]),
        place_name=place["place_name"],
        chart_type="lagna",
        gender=person["gender"],
        question_domain="marriage",
    )


def compact_chart(chart: dict[str, Any]) -> dict[str, Any]:
    moon = planet(chart, "Moon")
    return {
        "meta": chart.get("meta", {}),
        "birth": chart.get("question", {}),
        "lagna": chart.get("lagna", {}),
        "moon": moon,
        "planets": chart.get("planets", []),
        "dashas": chart.get("dashas", {}),
        "divisional_charts": {
            code: value
            for code, value in (chart.get("divisional_charts") or {}).items()
        },
    }


def build_matchmaking_dossier(
    boy: dict[str, Any],
    girl: dict[str, Any],
    boy_chart: dict[str, Any],
    girl_chart: dict[str, Any],
    ashtakoota: dict[str, Any],
    doshas: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    additional_divisional_charts = paired_divisional_case_summaries(boy_chart, girl_chart)
    return {
        "title": "Marriage Compatibility Case File",
        "couple_information": {
            "boy": couple_person_info(boy),
            "girl": couple_person_info(girl),
        },
        "charts_to_send": {
            "mandatory": [
                chart_case_summary("Boy D1 Lagna Chart", boy_chart, "Marriage promise, 7th house, planetary placements, and overall horoscope."),
                chart_case_summary("Girl D1 Lagna Chart", girl_chart, "Marriage promise, 7th house, planetary placements, and overall horoscope."),
                divisional_case_summary("Boy D9 Navamsa Chart", boy_chart, "Marriage strength, married life, spouse indications, and long-term compatibility."),
                divisional_case_summary("Girl D9 Navamsa Chart", girl_chart, "Marriage strength, married life, spouse indications, and long-term compatibility."),
                moon_chart_summary("Boy Moon Chart", boy_chart),
                moon_chart_summary("Girl Moon Chart", girl_chart),
                {
                    "name": "Boy Bhava Chalit Chart",
                    "purpose": "House cusps and planet occupation by house.",
                    "chart": build_d1(boy_chart.get("planets", []), boy_chart.get("lagna", {})) if boy_chart else {},
                },
                {
                    "name": "Girl Bhava Chalit Chart",
                    "purpose": "House cusps and planet occupation by house.",
                    "chart": build_d1(girl_chart.get("planets", []), girl_chart.get("lagna", {})) if girl_chart else {},
                },
                *additional_divisional_charts,
            ],
            "optional": [],
        },
        "planetary_positions": {
            "boy": planetary_position_table(boy_chart),
            "girl": planetary_position_table(girl_chart),
        },
        "marriage_matching_summary": {
            "overall_compatibility": summary["overall_result"],
            "guna_score": ashtakoota["total_score"],
            "max_score": ashtakoota["max_score"],
            "status": ashtakoota["category"],
            "recommendation": summary["final_recommendation"],
        },
        "complete_guna_milan": [
            {
                "name": item["name"],
                "maximum": item["max_score"],
                "obtained": item["score"],
                "explanation": item["interpretation"],
                "remarks": item["status"],
            }
            for item in ashtakoota["kootas"]
        ],
        "dosha_analysis": detailed_dosha_analysis(boy_chart, girl_chart, doshas),
        "marriage_house_analysis": {
            "boy": seventh_house_analysis(boy_chart),
            "girl": seventh_house_analysis(girl_chart),
        },
        "marriage_karakas": {
            "boy": karaka_analysis(boy_chart, "male"),
            "girl": karaka_analysis(girl_chart, "female"),
        },
        "navamsa_analysis": {
            "boy": navamsa_analysis(boy_chart),
            "girl": navamsa_analysis(girl_chart),
        },
        "compatibility_indicators": compatibility_indicators(ashtakoota, doshas),
        "astrologer_note": "This dossier is auto-generated for faster review. Final judgement should be made by the astrologer with context, consent, health, values, and practical compatibility.",
    }


def couple_person_info(person: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": person["name"],
        "date_of_birth": person["date_of_birth"],
        "time_of_birth": person["time_of_birth"],
        "birth_place": person["birth_place"],
        "age": calculate_age(person["date_of_birth"]),
        "birth_time_accuracy": person["birth_time_accuracy"],
    }


def calculate_age(date_of_birth: str) -> int | None:
    try:
        born = datetime.fromisoformat(date_of_birth).date()
    except ValueError:
        return None
    today = datetime.now().date()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def chart_case_summary(name: str, chart: dict[str, Any], purpose: str) -> dict[str, Any]:
    return {
        "name": name,
        "purpose": purpose,
        "lagna": chart.get("lagna", {}),
        "moon": planet(chart, "Moon"),
        "seventh_house": seventh_house_analysis(chart),
        "chart": build_d1(chart.get("planets", []), chart.get("lagna", {})),
    }


def divisional_case_summary(name: str, chart: dict[str, Any], purpose: str) -> dict[str, Any]:
    d9_raw = (chart.get("divisional_charts") or {}).get("D9", {})
    # d9_raw may be {"chart": {...}, "title": "..."}  or a plain sign->planets dict
    d9 = d9_raw.get("chart", d9_raw) if isinstance(d9_raw, dict) and "chart" in d9_raw else d9_raw
    return {
        "name": name,
        "purpose": purpose,
        "chart": d9,
        "lagna": sign_holding(d9, "Asc"),
        "venus": sign_holding(d9, "Venus"),
        "jupiter": sign_holding(d9, "Jupiter"),
    }


def paired_divisional_case_summaries(boy_chart: dict[str, Any], girl_chart: dict[str, Any]) -> list[dict[str, Any]]:
    boy_divisions = boy_chart.get("divisional_charts") or {}
    girl_divisions = girl_chart.get("divisional_charts") or {}
    codes = sorted(
        (set(boy_divisions.keys()) | set(girl_divisions.keys())) - {"D1", "D9"},
        key=divisional_sort_value,
    )
    summaries: list[dict[str, Any]] = []
    for code in codes:
        summaries.append(generic_divisional_case_summary(f"Boy {code} Chart", boy_chart, code))
        summaries.append(generic_divisional_case_summary(f"Girl {code} Chart", girl_chart, code))
    return summaries


def divisional_sort_value(code: str) -> tuple[int, str]:
    try:
        return (int(str(code).lstrip("D")), str(code))
    except ValueError:
        return (999, str(code))


def generic_divisional_case_summary(name: str, chart: dict[str, Any], code: str) -> dict[str, Any]:
    raw = (chart.get("divisional_charts") or {}).get(code, {})
    divisional_chart = raw.get("chart", raw) if isinstance(raw, dict) and "chart" in raw else raw
    title = raw.get("title") if isinstance(raw, dict) else ""
    return {
        "name": name,
        "purpose": title or "Additional divisional chart for astrologer review.",
        "chart": divisional_chart or {},
        "lagna": sign_holding(divisional_chart, "Asc") if isinstance(divisional_chart, dict) else "",
        "venus": sign_holding(divisional_chart, "Venus") if isinstance(divisional_chart, dict) else "",
        "jupiter": sign_holding(divisional_chart, "Jupiter") if isinstance(divisional_chart, dict) else "",
    }


def moon_chart_summary(name: str, chart: dict[str, Any]) -> dict[str, Any]:
    moon = planet(chart, "Moon")
    moon_longitude = moon.get("longitude")
    # Build a Chandra Lagna chart: place all planets in houses counted from Moon sign
    moon_chart: dict[str, Any] = {}
    if moon_longitude is not None:
        moon_chart = build_divisional_chart_from_moon(chart.get("planets", []), float(moon_longitude))
    return {
        "name": name,
        "purpose": "Emotional compatibility, mental nature, Guna Milan, and marriage happiness.",
        "moon_sign": moon.get("sign"),
        "nakshatra": moon.get("nakshatra"),
        "pada": moon.get("pada"),
        "chart": moon_chart,
    }


def planetary_position_table(chart: dict[str, Any]) -> list[dict[str, Any]]:
    order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    rows = []
    for name in order:
        item = planet(chart, name)
        rows.append({
            "planet": name,
            "longitude": item.get("longitude"),
            "sign": item.get("sign"),
            "house": item.get("house"),
            "nakshatra": item.get("nakshatra"),
            "pada": item.get("pada"),
            "retrograde": bool(item.get("retrograde")),
            "combust": "For astrologer review",
            "degree": item.get("formatted_degree") or item.get("degree_in_sign"),
        })
    return rows


def detailed_dosha_analysis(boy_chart: dict[str, Any], girl_chart: dict[str, Any], doshas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dosha_by_name = {item["name"]: item for item in doshas}
    mars_checks = {
        "boy": mangal_detail_for_chart(boy_chart),
        "girl": mangal_detail_for_chart(girl_chart),
    }
    return [
        {
            "name": "Mangal Dosha",
            "present": any(item["present"] for item in mars_checks.values()),
            "calculated_from": ["Lagna", "Moon", "Venus"],
            "severity": dosha_by_name.get("Mangal Dosha", {}).get("severity", "none"),
            "cancellation": "For astrologer review",
            "reason": "Mars placement checked in sensitive marriage houses.",
            "effective_result": dosha_by_name.get("Mangal Dosha", {}).get("explanation", ""),
            "details": mars_checks,
        },
        *[
            {
                "name": name,
                "present": dosha_by_name.get(name, {}).get("severity") in {"medium", "high"},
                "severity": dosha_by_name.get(name, {}).get("severity", "none"),
                "reason": dosha_by_name.get(name, {}).get("explanation", ""),
                "effective_result": "Review recommended" if dosha_by_name.get(name, {}).get("review_recommended") else "No major issue detected in this basic check",
            }
            for name in ["Nadi Dosha", "Bhakoot Dosha", "Gana Conflict", "Graha Maitri Conflict"]
        ],
    ]


def mangal_detail_for_chart(chart: dict[str, Any]) -> dict[str, Any]:
    mars = planet(chart, "Mars")
    return {
        "present": mars.get("house") in {1, 2, 4, 7, 8, 12},
        "mars_house": mars.get("house"),
        "mars_sign": mars.get("sign"),
        "severity": "review" if mars.get("house") in {1, 2, 4, 7, 8, 12} else "none",
    }


def seventh_house_analysis(chart: dict[str, Any]) -> dict[str, Any]:
    lagna_sign_index = int(chart.get("lagna", {}).get("sign_index", 0))
    seventh_sign_index = (lagna_sign_index + 6) % 12
    seventh_sign = SIGNS[seventh_sign_index]
    occupants = [item["name"] for item in chart.get("planets", []) if item.get("house") == 7]
    malefics = {"Mars", "Saturn", "Rahu", "Ketu", "Sun"}
    afflictions = [name for name in occupants if name in malefics]
    lord = SIGN_LORDS.get(seventh_sign, "")
    lord_planet = planet(chart, lord) if lord else {}
    return {
        "seventh_house": seventh_sign,
        "seventh_lord": lord,
        "seventh_lord_sign": lord_planet.get("sign"),
        "seventh_lord_house": lord_planet.get("house"),
        "planets_in_seventh": occupants,
        "aspect_on_seventh": "For astrologer review",
        "strength": "Needs review" if lord_planet.get("house") in {6, 8, 12} else "Supportive/neutral",
        "affliction": ", ".join(afflictions) if afflictions else "No major malefic occupation detected",
    }


def karaka_analysis(chart: dict[str, Any], gender: str) -> dict[str, Any]:
    primary = "Venus" if gender == "male" else "Jupiter"
    primary_planet = planet(chart, primary)
    seventh = seventh_house_analysis(chart)
    return {
        "primary_karaka": primary,
        "primary_karaka_sign": primary_planet.get("sign"),
        "primary_karaka_house": primary_planet.get("house"),
        "seventh_lord": seventh["seventh_lord"],
        "venus_strength": karaka_strength(planet(chart, "Venus")),
        "jupiter_strength": karaka_strength(planet(chart, "Jupiter")),
        "combustion": "For astrologer review",
        "retrograde": bool(primary_planet.get("retrograde")),
        "afflictions": "Review needed" if primary_planet.get("house") in {6, 8, 12} else "No basic affliction detected",
        "benefic_aspects": "For astrologer review",
    }


def karaka_strength(item: dict[str, Any]) -> str:
    if item.get("house") in {1, 4, 5, 7, 9, 10, 11}:
        return "Supportive"
    if item.get("house") in {6, 8, 12}:
        return "Needs review"
    return "Neutral"


def navamsa_analysis(chart: dict[str, Any]) -> dict[str, Any]:
    d9 = (chart.get("divisional_charts") or {}).get("D9", {})
    lagna = sign_holding(d9, "Asc")
    venus = sign_holding(d9, "Venus")
    jupiter = sign_holding(d9, "Jupiter")
    seventh = seventh_from_sign(lagna) if lagna else ""
    return {
        "d9_lagna": lagna or "Not available",
        "d9_seventh_house": seventh or "Not available",
        "d9_seventh_lord": SIGN_LORDS.get(seventh, "Not available") if seventh else "Not available",
        "venus_in_d9": venus or "Not available",
        "jupiter_in_d9": jupiter or "Not available",
        "marriage_strength": "Supportive/neutral" if lagna and venus and jupiter else "Needs astrologer review",
        "affliction": "For astrologer review",
        "supportive_factors": [item for item in [f"Venus in {venus}" if venus else "", f"Jupiter in {jupiter}" if jupiter else ""] if item],
    }


def compatibility_indicators(ashtakoota: dict[str, Any], doshas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    score = ashtakoota["total_score"]
    kootas = {item["name"]: item for item in ashtakoota["kootas"]}
    dosha_names = {item["name"] for item in doshas if item.get("review_recommended")}
    return [
        indicator("Communication Compatibility", kootas.get("Graha Maitri", {}).get("score", 0), 5),
        indicator("Emotional Compatibility", kootas.get("Bhakoot", {}).get("score", 0), 7),
        indicator("Temperament", kootas.get("Gana", {}).get("score", 0), 6),
        indicator("Financial Outlook", score, 36),
        indicator("Family Values", kootas.get("Vashya", {}).get("score", 0) + kootas.get("Varna", {}).get("score", 0), 3),
        {"name": "Career Alignment", "status": "Needs astrologer review", "remarks": "Requires deeper house and D10 context."},
        {"name": "Children Indicators", "status": "Needs astrologer review" if "Nadi Dosha" in dosha_names else "Basic check clear", "remarks": "Nadi and progeny indicators should be reviewed with full charts."},
        {"name": "Long Distance Possibility", "status": "Needs astrologer review", "remarks": "Requires 7th/12th house and D9 context."},
        {"name": "Foreign Settlement", "status": "Needs astrologer review", "remarks": "Requires 4th/7th/9th/12th house review."},
        {"name": "Conflict Indicators", "status": "Review recommended" if dosha_names else "Low basic conflict", "remarks": ", ".join(sorted(dosha_names)) or "No major conflict flagged by basic checks."},
    ]


def indicator(name: str, score: float, max_score: float) -> dict[str, Any]:
    ratio = score / max_score if max_score else 0
    return {
        "name": name,
        "status": "Strong" if ratio >= 0.7 else "Moderate" if ratio >= 0.35 else "Needs review",
        "remarks": f"Derived from score {round(score, 2)}/{max_score}.",
    }


def sign_holding(chart: dict[str, Any], body: str) -> str:
    for sign, bodies in (chart or {}).items():
        if body in bodies:
            return sign
    return ""


def seventh_from_sign(sign: str) -> str:
    if sign not in SIGNS:
        return ""
    return SIGNS[(SIGNS.index(sign) + 6) % 12]


def calculate_ashtakoota(boy_chart: dict[str, Any], girl_chart: dict[str, Any]) -> dict[str, Any]:
    boy_moon = planet(boy_chart, "Moon")
    girl_moon = planet(girl_chart, "Moon")
    boy_nak = nakshatra_index(boy_moon)
    girl_nak = nakshatra_index(girl_moon)
    boy_sign = int(boy_moon["sign_index"])
    girl_sign = int(girl_moon["sign_index"])

    rows = [
        koota("Varna", 1, varna_score(boy_sign, girl_sign), "Spiritual temperament compatibility."),
        koota("Vashya", 2, vashya_score(boy_sign, girl_sign), "Mutual influence and adaptability."),
        koota("Tara", 3, tara_score(boy_nak, girl_nak), "Birth star harmony and wellbeing."),
        koota("Yoni", 4, yoni_score(boy_moon["nakshatra"], girl_moon["nakshatra"]), "Instinctive and intimate compatibility."),
        koota("Graha Maitri", 5, graha_maitri_score(boy_moon["sign"], girl_moon["sign"]), "Friendship between Moon sign lords."),
        koota("Gana", 6, gana_score(boy_moon["nakshatra"], girl_moon["nakshatra"]), "Temperament and emotional nature."),
        koota("Bhakoot", 7, bhakoot_score(boy_sign, girl_sign), "Long-term emotional and family harmony."),
        koota("Nadi", 8, nadi_score(boy_nak, girl_nak), "Health, progeny, and subtle constitution match."),
    ]
    total = round(sum(item["score"] for item in rows), 2)
    return {
        "system": "Ashtakoota Guna Milan",
        "total_score": total,
        "max_score": 36,
        "percentage": round(total / 36 * 100, 1),
        "category": score_category(total),
        "kootas": rows,
    }


def calculate_doshas(boy_chart: dict[str, Any], girl_chart: dict[str, Any]) -> list[dict[str, Any]]:
    boy_moon = planet(boy_chart, "Moon")
    girl_moon = planet(girl_chart, "Moon")
    boy_nak = nakshatra_index(boy_moon)
    girl_nak = nakshatra_index(girl_moon)
    boy_sign = int(boy_moon["sign_index"])
    girl_sign = int(girl_moon["sign_index"])
    items = [
        dosha_card(
            "Mangal Dosha",
            mangal_severity(boy_chart, girl_chart),
            "Checks Mars placement in traditional sensitive houses for both charts.",
        ),
        dosha_card(
            "Nadi Dosha",
            "high" if boy_nak % 3 == girl_nak % 3 else "none",
            "Same Nadi is traditionally reviewed carefully for health and progeny compatibility.",
        ),
        dosha_card(
            "Bhakoot Dosha",
            "high" if sign_distance_pair(boy_sign, girl_sign) in {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)} else "none",
            "Sensitive Moon-sign distance can indicate family or emotional friction.",
        ),
        dosha_card(
            "Gana Conflict",
            gana_conflict(boy_moon["nakshatra"], girl_moon["nakshatra"]),
            "Temperament mismatch may need deeper review when Deva, Manushya, and Rakshasa patterns conflict.",
        ),
        dosha_card(
            "Graha Maitri Conflict",
            "medium" if graha_maitri_score(boy_moon["sign"], girl_moon["sign"]) < 2 else "none",
            "Moon sign lord relationship is checked for mental compatibility.",
        ),
        dosha_card(
            "7th House Affliction",
            seventh_house_affliction(boy_chart, girl_chart),
            "Reviews malefic influence on the marriage house in both charts.",
        ),
        dosha_card(
            "Venus/Jupiter Marriage Indicators",
            marriage_indicator_severity(boy_chart, girl_chart),
            "Reviews Venus and Jupiter support as basic marriage significators.",
        ),
        dosha_card(
            "Basic Marriage Stability",
            stability_severity(boy_chart, girl_chart),
            "Combines severe Dosha count and score strength into a practical stability signal.",
        ),
    ]
    return items


def build_recommendation(ashtakoota: dict[str, Any], doshas: list[dict[str, Any]], boy: dict[str, Any], girl: dict[str, Any]) -> dict[str, Any]:
    score = ashtakoota["total_score"]
    major = [item for item in doshas if item["severity"] == "high"]
    moderate = [item for item in doshas if item["severity"] == "medium"]
    needs_review = bool(major) or score < 18 or boy["birth_time_accuracy"] != "exact" or girl["birth_time_accuracy"] != "exact"
    strengths = [item["name"] for item in ashtakoota["kootas"] if item["score"] >= item["max_score"] * 0.75]
    concerns = [item["name"] for item in ashtakoota["kootas"] if item["score"] <= item["max_score"] * 0.35]
    concerns.extend(item["name"] for item in major + moderate)
    return {
        "overall_result": "Needs Astrologer Review" if needs_review else ashtakoota["category"],
        "final_recommendation": (
            "This match has sensitive factors that should be reviewed by an astrologer before drawing conclusions."
            if needs_review
            else "This match shows workable compatibility in the traditional checks used here."
        ),
        "strengths": strengths[:5] or ["Some compatibility factors are neutral and can be improved through understanding."],
        "areas_of_concern": list(dict.fromkeys(concerns))[:7],
        "ai_summary": (
            f"Guna Milan score is {score}/36 ({ashtakoota['category']}). "
            f"{len(major)} high-severity and {len(moderate)} medium-severity review points were detected. "
            "Use this as advisory guidance and consider practical compatibility, family context, consent, and communication."
        ),
        "astrologer_review_recommended": needs_review,
    }


def koota(name: str, max_score: int, score: float, meaning: str) -> dict[str, Any]:
    return {
        "name": name,
        "score": round(score, 2),
        "max_score": max_score,
        "status": "good" if score >= max_score * 0.7 else "review" if score >= max_score * 0.35 else "concern",
        "interpretation": meaning,
    }


def varna_score(boy_sign: int, girl_sign: int) -> int:
    groups = {0: 3, 1: 2, 2: 1, 3: 0, 4: 3, 5: 1, 6: 2, 7: 0, 8: 3, 9: 1, 10: 2, 11: 0}
    return 1 if groups[boy_sign] >= groups[girl_sign] else 0


def vashya_score(boy_sign: int, girl_sign: int) -> float:
    groups = {
        "chatushpada": {0, 1, 8, 9},
        "manava": {2, 5, 6, 10},
        "jalachara": {3, 11},
        "vanachara": {4},
        "keeta": {7},
    }
    boy_group = next(name for name, signs in groups.items() if boy_sign in signs)
    girl_group = next(name for name, signs in groups.items() if girl_sign in signs)
    return 2 if boy_group == girl_group else 1 if abs(boy_sign - girl_sign) in {1, 11} else 0


def tara_score(boy_nak: int, girl_nak: int) -> int:
    boy_to_girl = ((girl_nak - boy_nak) % 27) + 1
    girl_to_boy = ((boy_nak - girl_nak) % 27) + 1
    good = {1, 3, 5, 7}
    return int((boy_to_girl % 9 in good) + (girl_to_boy % 9 in good)) * 1.5


def yoni_score(boy_nak: str, girl_nak: str) -> int:
    return 4 if YONI_BY_NAKSHATRA.get(boy_nak) == YONI_BY_NAKSHATRA.get(girl_nak) else 2


def graha_maitri_score(boy_sign: str, girl_sign: str) -> int:
    boy_lord = SIGN_LORDS[boy_sign]
    girl_lord = SIGN_LORDS[girl_sign]
    if boy_lord == girl_lord:
        return 5
    if girl_lord in NATURAL_FRIENDS.get(boy_lord, set()) and boy_lord in NATURAL_FRIENDS.get(girl_lord, set()):
        return 5
    if girl_lord in NATURAL_FRIENDS.get(boy_lord, set()) or boy_lord in NATURAL_FRIENDS.get(girl_lord, set()):
        return 3
    return 1


def gana_score(boy_nak: str, girl_nak: str) -> int:
    boy_gana = GANA_BY_NAKSHATRA.get(boy_nak)
    girl_gana = GANA_BY_NAKSHATRA.get(girl_nak)
    if boy_gana == girl_gana:
        return 6
    if {boy_gana, girl_gana} == {"Deva", "Manushya"}:
        return 5
    if {boy_gana, girl_gana} == {"Manushya", "Rakshasa"}:
        return 1
    return 0


def bhakoot_score(boy_sign: int, girl_sign: int) -> int:
    return 0 if sign_distance_pair(boy_sign, girl_sign) in {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)} else 7


def nadi_score(boy_nak: int, girl_nak: int) -> int:
    return 0 if boy_nak % 3 == girl_nak % 3 else 8


def sign_distance_pair(boy_sign: int, girl_sign: int) -> tuple[int, int]:
    return ((girl_sign - boy_sign) % 12 + 1, (boy_sign - girl_sign) % 12 + 1)


def score_category(score: float) -> str:
    if score >= 28:
        return "Excellent"
    if score >= 22:
        return "Good"
    if score >= 18:
        return "Average"
    return "Sensitive Match"


def dosha_card(name: str, severity: str, explanation: str) -> dict[str, Any]:
    return {
        "name": name,
        "severity": severity,
        "review_recommended": severity in {"medium", "high"},
        "explanation": explanation,
    }


def mangal_severity(boy_chart: dict[str, Any], girl_chart: dict[str, Any]) -> str:
    boy = planet(boy_chart, "Mars").get("house") in {1, 2, 4, 7, 8, 12}
    girl = planet(girl_chart, "Mars").get("house") in {1, 2, 4, 7, 8, 12}
    if boy and girl:
        return "medium"
    if boy or girl:
        return "high"
    return "none"


def gana_conflict(boy_nak: str, girl_nak: str) -> str:
    pair = {GANA_BY_NAKSHATRA.get(boy_nak), GANA_BY_NAKSHATRA.get(girl_nak)}
    if pair == {"Deva", "Rakshasa"}:
        return "high"
    if pair == {"Manushya", "Rakshasa"}:
        return "medium"
    return "none"


def seventh_house_affliction(boy_chart: dict[str, Any], girl_chart: dict[str, Any]) -> str:
    malefics = {"Mars", "Saturn", "Rahu", "Ketu", "Sun"}
    count = sum(1 for chart in [boy_chart, girl_chart] for item in chart.get("planets", []) if item["name"] in malefics and item.get("house") == 7)
    return "high" if count >= 2 else "medium" if count == 1 else "none"


def marriage_indicator_severity(boy_chart: dict[str, Any], girl_chart: dict[str, Any]) -> str:
    weak = 0
    for chart, key in [(boy_chart, "Venus"), (girl_chart, "Jupiter")]:
        item = planet(chart, key)
        if item.get("house") in {6, 8, 12} or item.get("retrograde"):
            weak += 1
    return "medium" if weak else "none"


def stability_severity(boy_chart: dict[str, Any], girl_chart: dict[str, Any]) -> str:
    seventh = seventh_house_affliction(boy_chart, girl_chart)
    mangal = mangal_severity(boy_chart, girl_chart)
    return "high" if "high" in {seventh, mangal} else "medium" if "medium" in {seventh, mangal} else "none"


def planet(chart: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in chart.get("planets", []) if item.get("name") == name)


def nakshatra_index(moon: dict[str, Any]) -> int:
    if "nakshatra_index" in moon:
        return int(moon["nakshatra_index"])
    return NAKSHATRAS.index(moon["nakshatra"])
