import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.storage.database import get_geocode_cache, save_geocode_cache

USER_AGENT = "PrashnaKundliMVP/0.1 local-validation"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

LOCAL_PLACES = [
    ("new delhi", "New Delhi, Delhi, India", 28.6139, 77.2090, "city"),
    ("delhi", "Delhi, India", 28.6139, 77.2090, "city"),
    ("mumbai", "Mumbai, Maharashtra, India", 19.0760, 72.8777, "city"),
    ("bombay", "Mumbai, Maharashtra, India", 19.0760, 72.8777, "city"),
    ("kolkata", "Kolkata, West Bengal, India", 22.5726, 88.3639, "city"),
    ("calcutta", "Kolkata, West Bengal, India", 22.5726, 88.3639, "city"),
    ("chennai", "Chennai, Tamil Nadu, India", 13.0827, 80.2707, "city"),
    ("madras", "Chennai, Tamil Nadu, India", 13.0827, 80.2707, "city"),
    ("bengaluru", "Bengaluru, Karnataka, India", 12.9716, 77.5946, "city"),
    ("bangalore", "Bengaluru, Karnataka, India", 12.9716, 77.5946, "city"),
    ("hyderabad", "Hyderabad, Telangana, India", 17.3850, 78.4867, "city"),
    ("pune", "Pune, Maharashtra, India", 18.5204, 73.8567, "city"),
    ("ahmedabad", "Ahmedabad, Gujarat, India", 23.0225, 72.5714, "city"),
    ("jaipur", "Jaipur, Rajasthan, India", 26.9124, 75.7873, "city"),
    ("lucknow", "Lucknow, Uttar Pradesh, India", 26.8467, 80.9462, "city"),
    ("varanasi", "Varanasi, Uttar Pradesh, India", 25.3176, 82.9739, "city"),
    ("goa", "Goa, India", 15.2993, 74.1240, "state"),
    ("london", "London, England, United Kingdom", 51.5074, -0.1278, "city"),
    ("new york", "New York, NY, USA", 40.7128, -74.0060, "city"),
    ("dubai", "Dubai, United Arab Emirates", 25.2048, 55.2708, "city"),
    ("sydney", "Sydney, New South Wales, Australia", -33.8688, 151.2093, "city"),
    ("singapore", "Singapore", 1.3521, 103.8198, "city-state"),
    ("tokyo", "Tokyo, Japan", 35.6762, 139.6503, "city"),
    ("los angeles", "Los Angeles, CA, USA", 34.0522, -118.2437, "city"),
]


def geocode_place(query: str, limit: int = 6) -> list[dict]:
    normalized = normalize_query(query)
    if len(normalized) < 2:
        return []

    cached = get_geocode_cache(normalized)
    if cached is not None:
        return cached[:limit]

    local = local_matches(normalized)
    remote = []
    try:
        remote = nominatim_search(normalized, limit=limit)
    except Exception:
        remote = []

    results = merge_results(local, remote)[:limit]
    save_geocode_cache(normalized, results)
    return results


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def local_matches(query: str) -> list[dict]:
    matches = []
    for key, display, lat, lon, place_type in LOCAL_PLACES:
        if query in key or key in query:
            matches.append(
                {
                    "place_name": display,
                    "latitude": lat,
                    "longitude": lon,
                    "source": "local",
                    "type": place_type,
                    "importance": 1.0,
                }
            )
    return matches


def nominatim_search(query: str, limit: int) -> list[dict]:
    params = urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": limit,
        }
    )
    request = Request(f"{NOMINATIM_URL}?{params}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))

    results = []
    for item in payload:
        results.append(
            {
                "place_name": item.get("display_name", query),
                "latitude": round(float(item["lat"]), 6),
                "longitude": round(float(item["lon"]), 6),
                "source": "nominatim",
                "type": item.get("type") or item.get("class") or "place",
                "importance": item.get("importance", 0),
            }
        )
    return results


def merge_results(local: list[dict], remote: list[dict]) -> list[dict]:
    merged = []
    seen = set()
    for item in local + remote:
        key = (round(float(item["latitude"]), 4), round(float(item["longitude"]), 4), item["place_name"].lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def reverse_geocode_place(lat: float, lon: float) -> dict:
    NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
    params = urlencode(
        {
            "lat": str(lat),
            "lon": str(lon),
            "format": "jsonv2",
            "addressdetails": "1",
        }
    )
    request = Request(f"{NOMINATIM_REVERSE_URL}?{params}", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=8) as response:
            item = json.loads(response.read().decode("utf-8"))
            return {
                "place_name": item.get("display_name", f"{lat}, {lon}"),
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "source": "nominatim-reverse",
            }
    except Exception as e:
        return {
            "place_name": f"GPS: {lat}, {lon}",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "source": "fallback",
        }

