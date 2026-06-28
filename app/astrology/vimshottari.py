from datetime import datetime, timedelta, timezone

from app.astrology.constants import DASHA_SEQUENCE, DASHA_YEARS
from app.astrology.zodiac import normalize_degrees

DASHA_YEAR_DAYS = 365.25
NAKSHATRA_SPAN = 360.0 / 27.0


def add_years_as_days(start: datetime, years: float) -> datetime:
    return start + timedelta(days=years * DASHA_YEAR_DAYS)


def sequence_from(lord: str) -> list[str]:
    idx = DASHA_SEQUENCE.index(lord)
    return DASHA_SEQUENCE[idx:] + DASHA_SEQUENCE[:idx]


def vimshottari_from_moon(moon_longitude: float, event_time: datetime) -> dict:
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)

    lon = normalize_degrees(moon_longitude)
    nakshatra_index = int(lon // NAKSHATRA_SPAN)
    nakshatra_lord = DASHA_SEQUENCE[nakshatra_index % len(DASHA_SEQUENCE)]
    degree_in_nakshatra = lon - (nakshatra_index * NAKSHATRA_SPAN)
    elapsed_fraction = degree_in_nakshatra / NAKSHATRA_SPAN

    md_years = DASHA_YEARS[nakshatra_lord]
    elapsed_md_years = md_years * elapsed_fraction
    balance_md_years = md_years - elapsed_md_years
    md_start = add_years_as_days(event_time, -elapsed_md_years)
    md_end = add_years_as_days(event_time, balance_md_years)

    current_ad = current_subperiod(
        parent_lord=nakshatra_lord,
        parent_start=md_start,
        parent_years=md_years,
        event_time=event_time,
    )
    current_pd = current_subperiod(
        parent_lord=current_ad["lord"],
        parent_start=datetime.fromisoformat(current_ad["start"]),
        parent_years=current_ad["duration_years"],
        event_time=event_time,
    )
    current_sd = current_subperiod(
        parent_lord=current_pd["lord"],
        parent_start=datetime.fromisoformat(current_pd["start"]),
        parent_years=current_pd["duration_years"],
        event_time=event_time,
    )
    current_prana = current_subperiod(
        parent_lord=current_sd["lord"],
        parent_start=datetime.fromisoformat(current_sd["start"]),
        parent_years=current_sd["duration_years"],
        event_time=event_time,
    )

    mahadasha_timeline = major_periods_from(nakshatra_lord, md_start, event_time)
    antardasha_timeline = subperiods(
        parent_lord=nakshatra_lord,
        parent_start=md_start,
        parent_years=md_years,
        prefix=[nakshatra_lord],
    )
    pratyantardasha_timeline = subperiods(
        parent_lord=current_ad["lord"],
        parent_start=datetime.fromisoformat(current_ad["start"]),
        parent_years=current_ad["duration_years"],
        prefix=[nakshatra_lord, current_ad["lord"]],
    )
    sookshma_timeline = subperiods(
        parent_lord=current_pd["lord"],
        parent_start=datetime.fromisoformat(current_pd["start"]),
        parent_years=current_pd["duration_years"],
        prefix=[nakshatra_lord, current_ad["lord"], current_pd["lord"]],
    )
    prana_timeline = subperiods(
        parent_lord=current_sd["lord"],
        parent_start=datetime.fromisoformat(current_sd["start"]),
        parent_years=current_sd["duration_years"],
        prefix=[nakshatra_lord, current_ad["lord"], current_pd["lord"], current_sd["lord"]],
    )

    return {
        "system": "Vimshottari",
        "event_time": event_time.isoformat(),
        "nakshatra_lord": nakshatra_lord,
        "current_mahadasha": {
            "lord": nakshatra_lord,
            "start": md_start.isoformat(),
            "end": md_end.isoformat(),
            "elapsed_years": round(elapsed_md_years, 6),
            "balance_years": round(balance_md_years, 6),
            "duration_years": md_years,
        },
        "current_antardasha": current_ad,
        "current_pratyantardasha": current_pd,
        "current_sookshma": current_sd,
        "current_prana": current_prana,
        "mahadasha_timeline": mahadasha_timeline,
        "antardasha_timeline": antardasha_timeline,
        "pratyantardasha_timeline": pratyantardasha_timeline,
        "sookshma_timeline": sookshma_timeline,
        "prana_timeline": prana_timeline,
    }


def current_subperiod(
    parent_lord: str,
    parent_start: datetime,
    parent_years: float,
    event_time: datetime,
) -> dict:
    if parent_start.tzinfo is None:
        parent_start = parent_start.replace(tzinfo=timezone.utc)
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)

    cursor = parent_start
    for lord in sequence_from(parent_lord):
        duration_years = parent_years * DASHA_YEARS[lord] / 120.0
        end = add_years_as_days(cursor, duration_years)
        if cursor <= event_time <= end:
            return {
                "lord": lord,
                "start": cursor.isoformat(),
                "end": end.isoformat(),
                "duration_years": round(duration_years, 6),
            }
        cursor = end

    lord = sequence_from(parent_lord)[-1]
    return {
        "lord": lord,
        "start": cursor.isoformat(),
        "end": cursor.isoformat(),
        "duration_years": 0,
    }


def major_periods_from(first_lord: str, first_start: datetime, event_time: datetime) -> list[dict]:
    timeline = []
    cursor = first_start
    for lord in sequence_from(first_lord) + sequence_from(first_lord):
        years = DASHA_YEARS[lord]
        start = cursor
        end = add_years_as_days(start, years)
        if end >= event_time:
            timeline.append(
                {
                    "lord": lord,
                    "path": [lord],
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "duration_years": years,
                }
            )
        cursor = end
        if len(timeline) >= 9:
            break
    return timeline


def subperiods(parent_lord: str, parent_start: datetime, parent_years: float, prefix: list[str]) -> list[dict]:
    if parent_start.tzinfo is None:
        parent_start = parent_start.replace(tzinfo=timezone.utc)

    periods = []
    cursor = parent_start
    for lord in sequence_from(parent_lord):
        duration_years = parent_years * DASHA_YEARS[lord] / 120.0
        end = add_years_as_days(cursor, duration_years)
        periods.append(
            {
                "lord": lord,
                "path": prefix + [lord],
                "start": cursor.isoformat(),
                "end": end.isoformat(),
                "duration_years": round(duration_years, 6),
            }
        )
        cursor = end
    return periods
