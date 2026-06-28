import csv
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chart_calculator import calculate_prashna_chart


CASE_FILE = Path("validation/reference_cases/prashna_cases.csv")


def close_enough(actual: float, expected: str, tolerance: float) -> bool:
    if not expected:
        return True
    return abs(actual - float(expected)) <= tolerance


def equals_if_present(actual: object, expected: str) -> bool:
    return True if not expected else str(actual) == expected


def validate_case(row: dict) -> list[str]:
    chart = calculate_prashna_chart(
        question=row["question"],
        name=row["name"],
        asked_at_utc=datetime.fromisoformat(row["asked_at_utc"]),
        latitude=float(row["latitude"]),
        longitude=float(row["longitude"]),
        place_name=row["place_name"],
    )
    moon = next(planet for planet in chart["planets"] if planet["name"] == "Moon")
    checks = {
        "lagna_sign": equals_if_present(chart["lagna"]["sign"], row["expected_lagna_sign"]),
        "lagna_degree": close_enough(chart["lagna"]["degree_in_sign"], row["expected_lagna_degree"], 0.2),
        "moon_sign": equals_if_present(moon["sign"], row["expected_moon_sign"]),
        "moon_nakshatra": equals_if_present(moon["nakshatra"], row["expected_moon_nakshatra"]),
        "moon_pada": equals_if_present(moon["pada"], row["expected_moon_pada"]),
        "mahadasha": equals_if_present(chart["dashas"]["current_mahadasha"]["lord"], row["expected_mahadasha"]),
        "antardasha": equals_if_present(chart["dashas"]["current_antardasha"]["lord"], row["expected_antardasha"]),
    }
    return [name for name, passed in checks.items() if not passed]


def expected_field_count(row: dict) -> int:
    return sum(
        1
        for key in [
            "expected_lagna_sign",
            "expected_lagna_degree",
            "expected_moon_sign",
            "expected_moon_nakshatra",
            "expected_moon_pada",
            "expected_mahadasha",
            "expected_antardasha",
        ]
        if row.get(key)
    )


def main() -> int:
    if not CASE_FILE.exists():
        print(f"Missing {CASE_FILE}")
        return 1

    failures = []
    total_cases = 0
    populated_cases = 0
    populated_fields = 0
    with CASE_FILE.open(newline="") as handle:
        for row in csv.DictReader(handle):
            total_cases += 1
            field_count = expected_field_count(row)
            populated_fields += field_count
            if field_count:
                populated_cases += 1
            failed = validate_case(row)
            if failed:
                failures.append((row["case_id"], failed))

    if failures:
        for case_id, failed in failures:
            print(f"FAIL {case_id}: {', '.join(failed)}")
        return 1

    print("Reference validation passed for all populated expected fields.")
    print(f"Coverage: {populated_cases}/{total_cases} cases have expected values; {populated_fields} expected fields populated.")
    if populated_cases < total_cases:
        print("Next: fill blank expected fields from AstroSage/DrikPanchang/Jagannatha Hora and rerun.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
