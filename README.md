# Prashna Kundli MVP

A calculation-first Prashna Kundli prototype.

The first milestone is deliberately narrow:

- capture the exact server-side question time
- accept latitude/longitude and place name
- calculate Lahiri sidereal varga charts, nakshatra/pada, and Vimshottari dasha
- persist every chart as structured JSON in SQLite
- render a clean browser UI for testing and validation

## Run

```bash
python3 -m pip install -r requirements.txt
python3 scripts/download_ephemeris.py
python3 main.py
```

Open `http://127.0.0.1:8000`.

Open `http://127.0.0.1:8000/validation.html` for the calculation validation console.

## Interpretation Answer Layer

`POST /api/prashna` returns both the calculated chart and a complete interpretation. The backend first runs deterministic Prashna rules: domain-specific rules when the question is marriage, education, wealth, child, illness, foreign travel, or job/career, and a general Prashna rule set for any other question. It then adds `chart.interpretation.answer` as the human-readable astrologer-style response.

By default it uses a local template answer, so no API key is required. To use an LLM for deeper narrative answers, copy `.env.example` to `.env` and add fresh keys there.

```bash
# OpenAI
export PRASHNA_LLM_PROVIDER=openai
export OPENAI_API_KEYS=sk-proj-key-1,sk-proj-key-2
export OPENAI_INTERPRETATION_MODEL=gpt-5.2

# Gemini
export PRASHNA_LLM_PROVIDER=gemini
export GEMINI_API_KEYS=AIza-key-1,AIza-key-2
export GEMINI_INTERPRETATION_MODEL=gemini-2.0-flash
```

`OPENAI_API_KEY` and `GEMINI_API_KEY` also work for a single key. If multiple keys are supplied, the answer layer tries them in order. If the selected provider fails or a key is missing, the API falls back to a local answer and includes the reason in `interpretation.answer.note`.

## Validation Target

Before adding interpretation, compare at least 20 charts against trusted tools using the same:

- UTC/local time
- latitude/longitude
- Lahiri ayanamsa
- whole-sign Vedic house placement

The engine should match planet signs, Moon nakshatra, dasha lords, D1, D9, and other enabled vargas before interpretation work begins.

## Ephemeris Files

Run `python3 scripts/download_ephemeris.py` to populate `ephemeris/` with the current-era Swiss Ephemeris files used by the MVP:

- `sepl_18.se1`
- `semo_18.se1`
- `seas_18.se1`

The folder is ignored by git because these are third-party data files.
