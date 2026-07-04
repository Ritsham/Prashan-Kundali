from app.astrology.constants import DASHA_SEQUENCE, DASHA_YEARS
from app.astrology.zodiac import normalize_degrees, NAKSHATRAS

NAKSHATRA_SPAN = 360.0 / 27.0
TOTAL_DASHA_YEARS = 120.0

def _get_sequence_from(lord: str) -> list[str]:
    idx = DASHA_SEQUENCE.index(lord)
    return DASHA_SEQUENCE[idx:] + DASHA_SEQUENCE[:idx]

def get_kp_lords(longitude: float) -> dict:
    """
    Returns the Sign Lord, Star Lord, Sub Lord, and Sub-Sub Lord for a given longitude in KP astrology.
    """
    lon = normalize_degrees(longitude)
    
    # 1. Sign Lord (assuming standard planetary rulership of signs)
    sign_index = int(lon // 30)
    sign_lords = [
        "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", 
        "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"
    ]
    sign_lord = sign_lords[sign_index]

    # 2. Star Lord (Nakshatra Lord)
    nakshatra_index = int(lon // NAKSHATRA_SPAN)
    star_lord = DASHA_SEQUENCE[nakshatra_index % len(DASHA_SEQUENCE)]
    
    degree_in_nakshatra = lon - (nakshatra_index * NAKSHATRA_SPAN)
    
    # 3. Sub Lord
    sub_sequence = _get_sequence_from(star_lord)
    sub_lord = None
    sub_start = 0.0
    sub_span = 0.0
    
    for lord in sub_sequence:
        lord_span = (DASHA_YEARS[lord] / TOTAL_DASHA_YEARS) * NAKSHATRA_SPAN
        if sub_start <= degree_in_nakshatra < sub_start + lord_span:
            sub_lord = lord
            sub_span = lord_span
            break
        sub_start += lord_span
        
    if not sub_lord:
        sub_lord = sub_sequence[-1] # fallback to last due to float precision
        sub_span = (DASHA_YEARS[sub_lord] / TOTAL_DASHA_YEARS) * NAKSHATRA_SPAN
        
    # 4. Sub-Sub Lord
    degree_in_sub = degree_in_nakshatra - sub_start
    sub_sub_sequence = _get_sequence_from(sub_lord)
    sub_sub_lord = None
    
    ss_start = 0.0
    for ss_lord in sub_sub_sequence:
        # Proportion of the sub_span
        ss_lord_span = (DASHA_YEARS[ss_lord] / TOTAL_DASHA_YEARS) * sub_span
        if ss_start <= degree_in_sub <= ss_start + ss_lord_span + 1e-9:
            sub_sub_lord = ss_lord
            break
        ss_start += ss_lord_span
        
    if not sub_sub_lord:
        sub_sub_lord = sub_sub_sequence[-1]

    return {
        "sign_lord": sign_lord,
        "star_lord": star_lord,
        "sub_lord": sub_lord,
        "sub_sub_lord": sub_sub_lord
    }

def calculate_placidus_cusps(swe, jd: float, latitude: float, longitude: float, ayanamsa: float) -> list[dict]:
    """
    Calculates the 12 house cusps using the Placidus system, taking Ayanamsa into account for Sidereal cusps.
    """
    _cusps, ascmc = swe.houses(jd, latitude, longitude, b"P")
    
    cusp_list = []
    # _cusps has 12 elements, index 0 to 11 are the cusps.
    for i in range(12):
        cusp_lon = normalize_degrees(_cusps[i] - ayanamsa)
        lords = get_kp_lords(cusp_lon)
        cusp_list.append({
            "house": i + 1,
            "longitude": round(cusp_lon, 6),
            **lords
        })
        
    return cusp_list

def build_kp_significators(planets: list[dict], cusps: list[dict]) -> dict:
    """
    Builds KP Significators.
    Returns a dict mapping planets to the houses they signify, and houses to the planets that signify them.
    Levels (A, B, C, D) are simplified here.
    """
    # Create maps for easy lookup
    planet_map = {p["name"]: p for p in planets}
    
    # Identify occupants of each house.
    # In KP, a planet occupies a house if its longitude is between the cusp of that house and the next cusp.
    house_occupants = {i: [] for i in range(1, 13)}
    
    for p in planets:
        p_lon = p["longitude"]
        occupied_house = 1
        for i in range(1, 13):
            curr_cusp = cusps[i-1]["longitude"]
            next_cusp = cusps[i]["longitude"] if i < 12 else cusps[0]["longitude"]
            
            if next_cusp < curr_cusp: # Crosses Aries point
                if p_lon >= curr_cusp or p_lon < next_cusp:
                    occupied_house = i
                    break
            else:
                if curr_cusp <= p_lon < next_cusp:
                    occupied_house = i
                    break
        
        p["kp_house"] = occupied_house
        house_occupants[occupied_house].append(p["name"])
        
    # Generate significators (simplified)
    # A planet signifies:
    # 1. House occupied by its Star Lord
    # 2. House occupied by itself
    # 3. Houses owned by its Star Lord
    # 4. Houses owned by itself
    
    planet_significators = {}
    for p in planets:
        name = p["name"]
        star_lord = p["star_lord"]
        
        sl_data = planet_map.get(star_lord)
        sl_occupies = sl_data["kp_house"] if sl_data else None
        
        self_occupies = p["kp_house"]
        
        sl_owns = [c["house"] for c in cusps if c["sign_lord"] == star_lord]
        self_owns = [c["house"] for c in cusps if c["sign_lord"] == name]
        
        # Level 1 (Strongest) to 4 (Weakest)
        sigs = []
        if sl_occupies: sigs.append(sl_occupies)
        sigs.append(self_occupies)
        sigs.extend(sl_owns)
        sigs.extend(self_owns)
        
        # Deduplicate while preserving order
        planet_significators[name] = list(dict.fromkeys(sigs))
        
    return {
        "planet_significators": planet_significators,
        "cusps": cusps,
        "house_occupants": house_occupants
    }
