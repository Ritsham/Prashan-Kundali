from app.astrology.constants import NAKSHATRAS, SIGNS, ZodiacPoint


def normalize_degrees(value: float) -> float:
    return value % 360.0


def zodiac_point(longitude: float) -> ZodiacPoint:
    lon = normalize_degrees(longitude)
    sign_index = int(lon // 30)
    degree_in_sign = lon % 30
    return ZodiacPoint(
        longitude=round(lon, 6),
        sign_index=sign_index,
        sign=SIGNS[sign_index],
        degree_in_sign=round(degree_in_sign, 6),
        formatted=format_dms(degree_in_sign),
    )


def format_dms(value: float) -> str:
    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60)
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        degrees += 1
    return f"{degrees:02d}° {minutes:02d}' {seconds:02d}\""


def nakshatra_for(longitude: float) -> dict:
    lon = normalize_degrees(longitude)
    span = 360.0 / 27.0
    pada_span = span / 4.0
    index = int(lon // span)
    degree_in_nakshatra = lon - (index * span)
    pada = int(degree_in_nakshatra // pada_span) + 1
    return {
        "index": index,
        "name": NAKSHATRAS[index],
        "pada": pada,
        "degree_in_nakshatra": round(degree_in_nakshatra, 6),
    }


def whole_sign_house(longitude: float, lagna_sign_index: int) -> int:
    sign_index = zodiac_point(longitude).sign_index
    return ((sign_index - lagna_sign_index) % 12) + 1

