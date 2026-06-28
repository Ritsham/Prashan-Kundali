from functools import lru_cache


@lru_cache(maxsize=1)
def get_timezone_finder():
    try:
        from timezonefinder import TimezoneFinder
    except ImportError as exc:
        raise RuntimeError(
            "timezonefinder is not installed. Run `python3 -m pip install -r requirements.txt`."
        ) from exc
    return TimezoneFinder()


def timezone_at(latitude: float, longitude: float) -> str:
    finder = get_timezone_finder()
    tz = finder.timezone_at(lat=latitude, lng=longitude)
    if not tz:
        raise ValueError("Could not resolve timezone for the provided coordinates.")
    return tz

