import asyncio
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.astrology.constants import PLANET_ORDER
from app.astrology.divisional import build_all_divisional_charts, build_d1
from app.astrology.vimshottari import vimshottari_from_moon
from app.astrology.zodiac import nakshatra_for, normalize_degrees, whole_sign_house, zodiac_point
from app.astrology.kp_system import get_kp_lords, calculate_placidus_cusps, build_kp_significators
from app.services.timezone_service import timezone_at


class CalculationDependencyError(RuntimeError):
    pass


def load_swe():
    try:
        import swisseph as swe
    except ImportError as exc:
        raise CalculationDependencyError(
            "pyswisseph is not installed. Run `python3 -m pip install -r requirements.txt`."
        ) from exc
    return swe


async def calculate_prashna_chart(
    *,
    question: str,
    name: str,
    asked_at_utc: datetime,
    latitude: float,
    longitude: float,
    place_name: str,
    chart_type: str = "prashna",
    gender: str = "",
    question_domain: str = "",
    question_subdomain: str = "",
) -> dict:
    swe = load_swe()
    if asked_at_utc.tzinfo is None:
        asked_at_utc = asked_at_utc.replace(tzinfo=timezone.utc)
    asked_at_utc = asked_at_utc.astimezone(timezone.utc)

    ephe_path = Path("ephemeris")
    ephemeris = ephemeris_status(ephe_path)
    if ephe_path.exists():
        swe.set_ephe_path(str(ephe_path))

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = julian_day(swe, asked_at_utc)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    tz_name = timezone_at(latitude, longitude)
    asked_at_local = asked_at_utc.astimezone(ZoneInfo(tz_name))

    lagna_task = asyncio.to_thread(calculate_lagna, swe, jd, latitude, longitude, ayanamsa)
    kp_cusps_task = asyncio.to_thread(calculate_placidus_cusps, swe, jd, latitude, longitude, ayanamsa)
    lagna, kp_cusps = await asyncio.gather(lagna_task, kp_cusps_task)

    planets = await asyncio.to_thread(calculate_planets, swe, jd, lagna["sign_index"])
    moon = next(planet for planet in planets if planet["name"] == "Moon")
    
    # Calculate KP data, Divisional charts and Dashas concurrently
    kp_data_task = asyncio.to_thread(build_kp_significators, planets, kp_cusps)
    dashas_task = asyncio.to_thread(vimshottari_from_moon, moon["longitude"], asked_at_utc)
    divisional_task = asyncio.to_thread(build_all_divisional_charts, planets, lagna)
    
    transit_task = None
    if chart_type == "lagna":
        transit_task = asyncio.to_thread(
            calculate_transit,
            swe=swe,
            latitude=latitude,
            longitude=longitude,
            timezone_name=tz_name,
            natal_lagna_sign_index=lagna["sign_index"],
        )
        tasks = [kp_data_task, dashas_task, divisional_task, transit_task]
        kp_data, dashas, divisional_charts, transit = await asyncio.gather(*tasks)
    else:
        transit = None
        tasks = [kp_data_task, dashas_task, divisional_task]
        kp_data, dashas, divisional_charts = await asyncio.gather(*tasks)

    chart = {
        "meta": {
            "chart_type": chart_type,
            "engine_version": "0.1.0",
            "swe_version": getattr(swe, "version", "unknown"),
            "ayanamsa": "Lahiri",
            "ayanamsa_degrees": round(ayanamsa, 6),
            "house_system": "whole_sign",
            "julian_day": round(jd, 8),
            "ephemeris": ephemeris,
        },
        "question": {
            "name": name,
            "text": question,
            "domain": question_domain,
            "subdomain": question_subdomain,
            "gender": gender,
            "asked_at_utc": asked_at_utc.isoformat(),
            "asked_at_local": asked_at_local.isoformat(),
            "place_name": place_name,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": tz_name,
        },
        "lagna": lagna,
        "planets": planets,
        "kp_system": kp_data,
        "dashas": dashas,
        "divisional_charts": divisional_charts,
    }
    if transit:
        chart["transit"] = transit
    return chart


def calculate_transit(
    *,
    swe,
    latitude: float,
    longitude: float,
    timezone_name: str,
    natal_lagna_sign_index: int,
) -> dict:
    transit_utc = datetime.now(timezone.utc)
    jd = julian_day(swe, transit_utc)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    transit_lagna = calculate_lagna(swe, jd, latitude, longitude, ayanamsa)
    planets = calculate_planets(swe, jd, natal_lagna_sign_index)
    transit_local = transit_utc.astimezone(ZoneInfo(timezone_name))

    return {
        "system": "Lahiri sidereal gochar",
        "calculated_at_utc": transit_utc.isoformat(),
        "calculated_at_local": transit_local.isoformat(),
        "timezone": timezone_name,
        "ayanamsa_degrees": round(ayanamsa, 6),
        "house_reference": "birth_lagna",
        "lagna": transit_lagna,
        "planets": planets,
        "chart": build_d1(planets, transit_lagna),
    }


def julian_day(swe, dt: datetime) -> float:
    hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3_600_000_000.0
    return swe.julday(dt.year, dt.month, dt.day, hour, swe.GREG_CAL)


def ephemeris_status(ephe_path: Path) -> dict:
    required = ["sepl_18.se1", "semo_18.se1"]
    optional = ["seas_18.se1"]
    files = {}
    for name in required + optional:
        path = ephe_path / name
        files[name] = {
            "present": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
        }
    return {
        "path": str(ephe_path),
        "core_files_present": all(files[name]["present"] for name in required),
        "files": files,
    }


def calculate_lagna(swe, jd: float, latitude: float, longitude: float, ayanamsa: float) -> dict:
    _cusps, ascmc = swe.houses(jd, latitude, longitude, b"P")
    sidereal_asc = normalize_degrees(ascmc[0] - ayanamsa)
    point = zodiac_point(sidereal_asc)
    nak = nakshatra_for(sidereal_asc)
    kp_lords = get_kp_lords(sidereal_asc)
    
    return {
        "longitude": point.longitude,
        "sign_index": point.sign_index,
        "sign": point.sign,
        "degree_in_sign": point.degree_in_sign,
        "formatted_degree": point.formatted,
        "nakshatra": nak["name"],
        "pada": nak["pada"],
        **kp_lords
    }


def calculate_planets(swe, jd: float, lagna_sign_index: int) -> list[dict]:
    planet_ids = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mars": swe.MARS,
        "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS,
        "Saturn": swe.SATURN,
        "Rahu": swe.TRUE_NODE,
    }
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    results = []

    for name in PLANET_ORDER:
        if name == "Ketu":
            rahu = next(item for item in results if item["name"] == "Rahu")
            lon = normalize_degrees(rahu["longitude"] + 180.0)
            speed = rahu["speed"]
        else:
            values, _retflag = swe.calc_ut(jd, planet_ids[name], flags)
            lon = normalize_degrees(values[0])
            speed = values[3]

        point = zodiac_point(lon)
        nak = nakshatra_for(lon)
        kp_lords = get_kp_lords(lon)
        
        results.append(
            {
                "name": name,
                "longitude": point.longitude,
                "sign_index": point.sign_index,
                "sign": point.sign,
                "degree_in_sign": point.degree_in_sign,
                "formatted_degree": point.formatted,
                "house": whole_sign_house(lon, lagna_sign_index),
                "nakshatra": nak["name"],
                "pada": nak["pada"],
                "speed": round(speed, 6),
                "retrograde": speed < 0,
                **kp_lords
            }
        )

    return results
