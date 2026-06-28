# Calculation Validation Protocol

Do not add interpretation until the calculation engine passes this checklist.

## Required Inputs

For each validation chart, record:

- exact date and time
- timezone
- UTC time
- latitude and longitude
- place name
- ayanamsa: Lahiri
- house placement: whole sign from Lagna sign

## Compare Against

Use at least two trusted references per chart, such as:

- AstroSage
- DrikPanchang
- Jagannatha Hora
- Astro.com where applicable

## Acceptance Criteria

- Planet sign: exact
- Moon nakshatra: exact
- Moon pada: exact
- Lagna sign: exact
- Lagna degree: within 0.2 degree
- Planet longitude: within 0.1 degree
- D9 sign: exact
- Current Mahadasha: exact
- Current Antardasha: exact

## Minimum Test Set

Validate at least 20 charts:

- 5 India metro cities
- 5 non-India locations
- 5 charts near sunrise/sunset
- 3 charts near sign boundaries
- 2 charts near nakshatra boundaries

The seed file `validation/reference_cases/prashna_cases.csv` already contains 20 input cases across these categories.

## Working Loop

1. Run `python3 scripts/download_ephemeris.py`.
2. Run `python3 scripts/export_reference_outputs.py`.
3. Open `validation/generated_outputs.csv`.
4. For each case, enter the same UTC/local time, latitude, longitude, Lahiri ayanamsa, and whole-sign style settings in reference tools.
5. Copy trusted expected values back into `validation/reference_cases/prashna_cases.csv`.
6. Run `python3 scripts/validate_reference_cases.py`.

The validator permits blank expected fields while comparison is incomplete, but reports coverage so we know how much trust work remains.

You can also use the browser console at `http://127.0.0.1:8000/validation.html` to enter expected values and save them directly into `validation/reference_cases/prashna_cases.csv`.

Run `python3 scripts/audit_engine_consistency.py` for a local consistency audit across all seeded cases. This checks local ephemeris presence, planet count, D1/D9 ascendant placement, house range, nakshatra/pada range, and dasha timeline shape.

## Known Engine Notes

- The MVP uses Swiss Ephemeris through `pyswisseph`.
- If an `ephemeris/` folder is present, the engine points Swiss Ephemeris there.
- Use `python3 scripts/download_ephemeris.py` before serious validation.
- The current MVP downloads `sepl_18.se1`, `semo_18.se1`, and `seas_18.se1`, which cover the current era needed for ordinary Prashna testing.
- Without local ephemeris files, Swiss Ephemeris may use its fallback calculation mode. For production-grade accuracy, keep local ephemeris files present and re-run validation.
- Fill `validation/reference_cases/prashna_cases.csv` with manually checked expected values, then run `python3 scripts/validate_reference_cases.py`.
