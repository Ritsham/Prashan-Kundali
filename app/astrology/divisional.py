from app.astrology.constants import SIGNS
from app.astrology.zodiac import normalize_degrees


VARGA_ORDER = ["D1", "D2", "D3", "D4", "D6", "D7", "D9", "D10", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"]

VARGA_TITLES = {
    "D1": "Rashi / Lagna",
    "D2": "Hora",
    "D3": "Drekkana",
    "D4": "Chaturthamsha",
    "D6": "Shashtamsha",
    "D7": "Saptamsa",
    "D9": "Navamsa",
    "D10": "Dashamsa",
    "D12": "Dwadashamsha",
    "D16": "Shodashamsha",
    "D20": "Vimshamsha",
    "D24": "Chaturvimshamsha",
    "D27": "Bhamsha",
    "D30": "Trimsamsha",
    "D40": "Khavedamsha",
    "D45": "Akshavedamsha",
    "D60": "Shashtiamsha",
}

MOVABLE_SIGNS = {0, 3, 6, 9}
FIXED_SIGNS = {1, 4, 7, 10}


def part_index(degree_in_sign: float, divisions: int) -> int:
    return min(int(degree_in_sign / (30.0 / divisions)), divisions - 1)


def sign_part(longitude: float) -> tuple[int, float]:
    lon = normalize_degrees(longitude)
    sign_index = int(lon // 30)
    return sign_index, lon % 30


def cyclic_sign(sign_index: int, offset: int) -> int:
    return (sign_index + offset) % 12


def modality_start(sign_index: int, movable_start: int, fixed_start: int, dual_start: int) -> int:
    if sign_index in MOVABLE_SIGNS:
        return movable_start
    if sign_index in FIXED_SIGNS:
        return fixed_start
    return dual_start


def parity_start(sign_index: int, odd_start: int, even_start: int) -> int:
    return odd_start if sign_index % 2 == 0 else even_start


def navamsa_sign_index(longitude: float) -> int:
    return varga_sign_index(longitude, "D9")


def varga_sign_index(longitude: float, varga: str) -> int:
    sign_index, degree = sign_part(longitude)
    odd_sign = sign_index % 2 == 0

    if varga == "D1":
        return sign_index

    if varga == "D2":
        first_half = degree < 15
        if odd_sign:
            return 4 if first_half else 3
        return 3 if first_half else 4

    if varga == "D3":
        return cyclic_sign(sign_index, part_index(degree, 3) * 4)

    if varga == "D4":
        return cyclic_sign(sign_index, part_index(degree, 4) * 3)

    if varga == "D6":
        start = sign_index if odd_sign else cyclic_sign(sign_index, 6)
        return cyclic_sign(start, part_index(degree, 6))

    if varga == "D7":
        start = sign_index if odd_sign else cyclic_sign(sign_index, 6)
        return cyclic_sign(start, part_index(degree, 7))

    if varga == "D9":
        start = modality_start(sign_index, sign_index, cyclic_sign(sign_index, 8), cyclic_sign(sign_index, 4))
        return cyclic_sign(start, part_index(degree, 9))

    if varga == "D10":
        start = sign_index if odd_sign else cyclic_sign(sign_index, 8)
        return cyclic_sign(start, part_index(degree, 10))

    if varga == "D12":
        return cyclic_sign(sign_index, part_index(degree, 12))

    if varga == "D16":
        start = modality_start(sign_index, 0, 4, 8)
        return cyclic_sign(start, part_index(degree, 16))

    if varga == "D20":
        start = modality_start(sign_index, 0, 8, 4)
        return cyclic_sign(start, part_index(degree, 20))

    if varga == "D24":
        start = parity_start(sign_index, 4, 3)
        return cyclic_sign(start, part_index(degree, 24))

    if varga == "D27":
        start = modality_start(sign_index, 0, 3, 6)
        return cyclic_sign(start, part_index(degree, 27))

    if varga == "D30":
        return trimsamsha_sign_index(sign_index, degree)

    if varga == "D40":
        start = parity_start(sign_index, 0, 6)
        return cyclic_sign(start, part_index(degree, 40))

    if varga == "D45":
        start = modality_start(sign_index, 0, 4, 8)
        return cyclic_sign(start, part_index(degree, 45))

    if varga == "D60":
        return cyclic_sign(sign_index, part_index(degree, 60))

    raise ValueError(f"Unsupported divisional chart: {varga}")


def trimsamsha_sign_index(sign_index: int, degree: float) -> int:
    odd_sign = sign_index % 2 == 0
    if odd_sign:
        spans = [
            (5, 0),
            (10, 10),
            (18, 8),
            (25, 2),
            (30, 6),
        ]
    else:
        spans = [
            (5, 1),
            (12, 5),
            (20, 11),
            (25, 9),
            (30, 7),
        ]
    for limit, result in spans:
        if degree < limit:
            return result
    return spans[-1][1]


def empty_chart() -> dict:
    return {name: [] for name in SIGNS}


def build_divisional_chart(planets: list[dict], lagna_longitude: float, varga: str) -> dict:
    signs = empty_chart()
    signs[SIGNS[varga_sign_index(lagna_longitude, varga)]].append("Asc")

    for planet in planets:
        signs[SIGNS[varga_sign_index(planet["longitude"], varga)]].append(planet["name"])

    return signs


def build_all_divisional_charts(planets: list[dict], lagna: dict) -> dict:
    return {
        varga: build_divisional_chart(planets, lagna["longitude"], varga)
        for varga in VARGA_ORDER
    }


def build_d1(planets: list[dict], lagna: dict) -> dict:
    return build_divisional_chart(planets, lagna["longitude"], "D1")


def build_d9(planets: list[dict], lagna_longitude: float) -> dict:
    return build_divisional_chart(planets, lagna_longitude, "D9")
