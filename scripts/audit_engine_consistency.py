import csv
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chart_calculator import calculate_prashna_chart


CASE_FILE = Path("validation/reference_cases/prashna_cases.csv")


async def main() -> int:
    rows = list(csv.DictReader(CASE_FILE.open()))
    issues = []
    summary = {
        "cases": len(rows),
        "ephemeris_true": 0,
        "planet_count_9": 0,
        "d1_has_asc": 0,
        "d9_has_asc": 0,
        "valid_houses": 0,
        "valid_nakshatra_pada": 0,
        "valid_dasha_timelines": 0,
    }

    for row in rows:
        case_id = row["case_id"]
        chart = await calculate_prashna_chart(
            question=row["question"],
            name=row["name"],
            asked_at_utc=datetime.fromisoformat(row["asked_at_utc"]),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            place_name=row["place_name"],
        )
        planets = chart["planets"]
        dasha = chart["dashas"]
        timelines = [
            dasha["mahadasha_timeline"],
            dasha["antardasha_timeline"],
            dasha["pratyantardasha_timeline"],
            dasha["sookshma_timeline"],
            dasha["prana_timeline"],
        ]

        check(case_id, "ephemeris core files missing", chart["meta"]["ephemeris"]["core_files_present"], issues, summary, "ephemeris_true")
        check(case_id, f"planet count is {len(planets)}", len(planets) == 9, issues, summary, "planet_count_9")
        check(case_id, "D1 missing Asc", has_asc(chart["divisional_charts"]["D1"]), issues, summary, "d1_has_asc")
        check(case_id, "D9 missing Asc", has_asc(chart["divisional_charts"]["D9"]), issues, summary, "d9_has_asc")
        check(case_id, "invalid house number", all(1 <= planet["house"] <= 12 for planet in planets), issues, summary, "valid_houses")
        check(
            case_id,
            "invalid nakshatra/pada",
            all(1 <= planet["pada"] <= 4 and planet["nakshatra"] for planet in planets) and 1 <= chart["lagna"]["pada"] <= 4,
            issues,
            summary,
            "valid_nakshatra_pada",
        )
        check(
            case_id,
            "invalid dasha timeline",
            all(len(timeline) == 9 for timeline in timelines)
            and all(timeline[i]["end"] <= timeline[i + 1]["end"] for timeline in timelines for i in range(len(timeline) - 1)),
            issues,
            summary,
            "valid_dasha_timelines",
        )

    print(json.dumps({"summary": summary, "issues": issues}, indent=2))
    return 1 if issues else 0


def has_asc(chart: dict) -> bool:
    return any("Asc" in bodies for bodies in chart.values())


def check(case_id: str, message: str, passed: bool, issues: list, summary: dict, key: str) -> None:
    if passed:
        summary[key] += 1
    else:
        issues.append({"case_id": case_id, "issue": message})


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
