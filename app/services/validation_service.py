import os
import httpx
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

CASE_FILE = Path("validation/reference_cases/prashna_cases.csv")

EXPECTED_FIELDS = [
    "expected_lagna_sign",
    "expected_lagna_degree",
    "expected_moon_sign",
    "expected_moon_nakshatra",
    "expected_moon_pada",
    "expected_mahadasha",
    "expected_antardasha",
]


def read_cases() -> list[dict]:
    with CASE_FILE.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_cases(rows: list[dict]) -> None:
    if not rows:
        return
    with CASE_FILE.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def generated_output(row: dict) -> dict:
    astrology_url = os.getenv("ASTROLOGY_ENGINE_URL", "http://localhost:8001")
    payload_data = {
        "chart_type": "prashna",
        "name": row["name"],
        "question": row["question"],
        "location": {
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "place_name": row["place_name"]
        },
        "asked_at_utc": datetime.fromisoformat(row["asked_at_utc"]).isoformat()
    }
    
    with httpx.Client() as client:
        resp = client.post(f"{astrology_url}/calculate", json=payload_data, timeout=30.0)
        resp.raise_for_status()
        chart = resp.json()["chart"]
    moon = next(planet for planet in chart["planets"] if planet["name"] == "Moon")
    return {
        "lagna_sign": chart["lagna"]["sign"],
        "lagna_degree": chart["lagna"]["degree_in_sign"],
        "lagna_nakshatra": chart["lagna"]["nakshatra"],
        "lagna_pada": chart["lagna"]["pada"],
        "moon_sign": moon["sign"],
        "moon_degree": moon["degree_in_sign"],
        "moon_nakshatra": moon["nakshatra"],
        "moon_pada": moon["pada"],
        "mahadasha": chart["dashas"]["current_mahadasha"]["lord"],
        "antardasha": chart["dashas"]["current_antardasha"]["lord"],
        "pratyantardasha": chart["dashas"]["current_pratyantardasha"]["lord"],
        "sookshma": chart["dashas"]["current_sookshma"]["lord"],
        "prana": chart["dashas"]["current_prana"]["lord"],
        "ayanamsa_degrees": chart["meta"]["ayanamsa_degrees"],
        "ephemeris_core_files_present": chart["meta"]["ephemeris"]["core_files_present"],
    }


def populated_expected_count(row: dict) -> int:
    return sum(1 for field in EXPECTED_FIELDS if row.get(field))


def mismatch_fields(row: dict, actual: dict) -> list[str]:
    failures = []
    if row.get("expected_lagna_sign") and row["expected_lagna_sign"] != actual["lagna_sign"]:
        failures.append("lagna_sign")
    if row.get("expected_lagna_degree") and abs(float(row["expected_lagna_degree"]) - float(actual["lagna_degree"])) > 0.2:
        failures.append("lagna_degree")
    if row.get("expected_moon_sign") and row["expected_moon_sign"] != actual["moon_sign"]:
        failures.append("moon_sign")
    if row.get("expected_moon_nakshatra") and row["expected_moon_nakshatra"] != actual["moon_nakshatra"]:
        failures.append("moon_nakshatra")
    if row.get("expected_moon_pada") and str(row["expected_moon_pada"]) != str(actual["moon_pada"]):
        failures.append("moon_pada")
    if row.get("expected_mahadasha") and row["expected_mahadasha"] != actual["mahadasha"]:
        failures.append("mahadasha")
    if row.get("expected_antardasha") and row["expected_antardasha"] != actual["antardasha"]:
        failures.append("antardasha")
    return failures


def case_payload(row: dict) -> dict:
    actual = generated_output(row)
    populated = populated_expected_count(row)
    failures = mismatch_fields(row, actual)
    return {
        "case": row,
        "actual": actual,
        "populated_expected_fields": populated,
        "missing_expected_fields": [field for field in EXPECTED_FIELDS if not row.get(field)],
        "mismatches": failures,
        "status": "missing" if populated == 0 else "fail" if failures else "pass",
    }


def all_cases_payload() -> dict:
    cases = [case_payload(row) for row in read_cases()]
    total = len(cases)
    populated_cases = sum(1 for item in cases if item["populated_expected_fields"] > 0)
    passed_cases = sum(1 for item in cases if item["status"] == "pass" and item["populated_expected_fields"] > 0)
    failed_cases = sum(1 for item in cases if item["status"] == "fail")
    return {
        "summary": {
            "total_cases": total,
            "populated_cases": populated_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "coverage_percent": round((populated_cases / total) * 100, 2) if total else 0,
        },
        "cases": cases,
    }


def update_case(case_id: str, updates: dict) -> Optional[dict]:
    rows = read_cases()
    updated = None
    for row in rows:
        if row["case_id"] == case_id:
            for field in EXPECTED_FIELDS + ["source_notes"]:
                if field in updates:
                    row[field] = str(updates[field]).strip()
            updated = row
            break

    if updated is None:
        return None

    write_cases(rows)
    return case_payload(updated)
