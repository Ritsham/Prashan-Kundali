import csv
import asyncio
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chart_calculator import calculate_prashna_chart


CASE_FILE = Path("validation/reference_cases/prashna_cases.csv")
OUTPUT_FILE = Path("validation/generated_outputs.csv")

OUTPUT_FIELDS = [
    "case_id",
    "category",
    "asked_at_utc",
    "place_name",
    "latitude",
    "longitude",
    "lagna_sign",
    "lagna_degree",
    "lagna_nakshatra",
    "lagna_pada",
    "moon_sign",
    "moon_degree",
    "moon_nakshatra",
    "moon_pada",
    "mahadasha",
    "antardasha",
    "pratyantardasha",
    "sookshma",
    "prana",
    "ayanamsa_degrees",
    "ephemeris_core_files_present",
]


async def output_row(row: dict) -> dict:
    chart = await calculate_prashna_chart(
        question=row["question"],
        name=row["name"],
        asked_at_utc=datetime.fromisoformat(row["asked_at_utc"]),
        latitude=float(row["latitude"]),
        longitude=float(row["longitude"]),
        place_name=row["place_name"],
    )
    moon = next(planet for planet in chart["planets"] if planet["name"] == "Moon")
    return {
        "case_id": row["case_id"],
        "category": row["category"],
        "asked_at_utc": row["asked_at_utc"],
        "place_name": row["place_name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
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


async def main() -> int:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CASE_FILE.open(newline="") as input_handle:
        rows = list(csv.DictReader(input_handle))

    with OUTPUT_FILE.open("w", newline="") as output_handle:
        writer = csv.DictWriter(output_handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(await output_row(row))

    print(f"Wrote {len(rows)} generated chart summaries to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
