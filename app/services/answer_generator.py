from __future__ import annotations

import json
import os
import textwrap
import urllib.error
import urllib.request
from datetime import datetime


DEFAULT_OPENAI_MODEL = "gpt-5.2"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
ENV_LOADED = False
ENV_PATH = ".env"


def generate_interpretation_answer(chart: dict, interpretation: dict) -> dict:
    load_local_env()
    try:
        provider = selected_provider()
        if provider == "openai":
            return llm_answer(chart, interpretation, provider, call_openai)
        if provider == "gemini":
            return llm_answer(chart, interpretation, provider, call_gemini)
        if provider == "groq":
            return llm_answer(chart, interpretation, provider, call_groq)
        raise RuntimeError("PRASHNA_LLM_PROVIDER must be openai, gemini, or groq")
    except Exception as exc:
        return llm_unavailable_payload(str(exc))


def selected_provider() -> str:
    configured = os.getenv("PRASHNA_LLM_PROVIDER", "").strip().lower()
    if configured in {"local", "off"}:
        raise RuntimeError("Local/off interpretation mode is disabled. Configure openai, gemini, or groq.")
    if configured in {"openai", "gemini", "groq"}:
        return configured
    if configured:
        raise RuntimeError("PRASHNA_LLM_PROVIDER must be openai, gemini, or groq")
    if api_keys_for("GROQ"):
        return "groq"
    if api_keys_for("OPENAI"):
        return "openai"
    if api_keys_for("GEMINI") or api_keys_for("GOOGLE"):
        return "gemini"
    raise RuntimeError("No LLM provider/key configured. Add .env with PRASHNA_LLM_PROVIDER=groq, openai, or gemini and the matching API key.")


def llm_answer(chart: dict, interpretation: dict, provider: str, caller) -> dict:
    return caller(chart, interpretation)


def call_openai(chart: dict, interpretation: dict) -> dict:
    api_keys = api_keys_for("OPENAI")
    if not api_keys:
        raise RuntimeError("OPENAI_API_KEY or OPENAI_API_KEYS is not set")
    model = os.getenv("OPENAI_INTERPRETATION_MODEL", DEFAULT_OPENAI_MODEL)
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt()}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt(chart, interpretation)}]},
        ],
    }
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                "https://api.openai.com/v1/responses",
                payload,
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors))
    text = extract_openai_text(data)
    if not text:
        raise RuntimeError("OpenAI response did not contain output text")
    return answer_payload(text, "llm", "openai", model, "")


def call_gemini(chart: dict, interpretation: dict) -> dict:
    api_keys = api_keys_for("GEMINI") or api_keys_for("GOOGLE")
    if not api_keys:
        raise RuntimeError("GEMINI_API_KEY, GEMINI_API_KEYS, GOOGLE_API_KEY, or GOOGLE_API_KEYS is not set")
    model = os.getenv("GEMINI_INTERPRETATION_MODEL", DEFAULT_GEMINI_MODEL)
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt()}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt(chart, interpretation)}]}],
    }
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                payload,
                {"Content-Type": "application/json"},
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors))
    text = extract_gemini_text(data)
    if not text:
        raise RuntimeError("Gemini response did not contain output text")
    return answer_payload(text, "llm", "gemini", model, "")


def call_groq(chart: dict, interpretation: dict) -> dict:
    api_keys = api_keys_for("GROQ")
    if not api_keys:
        raise RuntimeError("GROQ_API_KEY or GROQ_API_KEYS is not set")
    model = os.getenv("GROQ_INTERPRETATION_MODEL", DEFAULT_GROQ_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(chart, interpretation)},
        ],
        "temperature": 0.7,
    }
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                "https://api.groq.com/openai/v1/chat/completions",
                payload,
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors))
    text = extract_chat_completion_text(data)
    if not text:
        raise RuntimeError("Groq response did not contain output text")
    return answer_payload(text, "llm", "groq", model, "")


def post_json(url: str, payload: dict, headers: dict) -> dict:
    timeout = float(os.getenv("PRASHNA_LLM_TIMEOUT_SECONDS", "20"))
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "KundaliStudio/1.0 (+https://localhost)",
        **headers,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403 and "error code: 1010" in body.lower():
            raise RuntimeError(
                "HTTP 403 from Groq edge: Cloudflare error 1010 blocked this request before it reached the model. "
                "The key may be valid, but Groq is rejecting this machine/network/request fingerprint."
            ) from exc
        raise RuntimeError(f"HTTP {exc.code}: {body[:500]}") from exc


def load_local_env() -> None:
    global ENV_LOADED
    if ENV_LOADED:
        return
    ENV_LOADED = True
    for path in [".env", ".env.local", ".env.example"]:
        if os.path.exists(path):
            load_env_file(path)


def load_env_file(path: str) -> None:
    with open(path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ and not is_placeholder_secret(key, value):
                os.environ[key] = value


def is_placeholder_secret(key: str, value: str) -> bool:
    if "KEY" not in key and "TOKEN" not in key and "SECRET" not in key:
        return False
    lowered = value.lower()
    return not value or "your-" in lowered or "first-key" in lowered or "second-key" in lowered


def api_keys_for(prefix: str) -> list[str]:
    keys = []
    for name in [f"{prefix}_API_KEYS", f"{prefix}_API_KEY"]:
        keys.extend(split_keys(os.getenv(name, "")))
    index = 1
    while True:
        value = os.getenv(f"{prefix}_API_KEY_{index}", "")
        if not value:
            break
        keys.extend(split_keys(value))
        index += 1
    deduped = []
    for key in keys:
        if key and key not in deduped:
            deduped.append(key)
    return deduped


def split_keys(value: str) -> list[str]:
    normalized = value.replace("\n", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def extract_openai_text(data: dict) -> str:
    if data.get("output_text"):
        return data["output_text"].strip()
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def extract_gemini_text(data: dict) -> str:
    parts = []
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text = part.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def extract_chat_completion_text(data: dict) -> str:
    parts = []
    for choice in data.get("choices", []):
        text = choice.get("message", {}).get("content")
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def system_prompt() -> str:
    return (
        "You are a senior Prashna astrologer. Use the supplied JSON only as reasoning context, "
        "then write a natural human reading. Do not output JSON, checklists, placement catalogs, "
        "or copied context instructions. Mention only factors that change the judgment. Give a "
        "clear answer, strongest support, strongest obstacle, likely outcome, supported timing, "
        "practical next step, mistake to avoid, and confidence reason. For health, money, legal, "
        "career, travel, relationship, and child matters, avoid guarantees and include grounded caution."
    )


def user_prompt(chart: dict, interpretation: dict) -> str:
    return (
        "Write the final Prashna reading from this compact context. "
        "Use it only as reasoning material; do not copy instructions or JSON. "
        "The question text overrides broad domain labels. If timing is weak, do not invent dates.\n\n"
        + json.dumps(llm_context_payload(chart, interpretation), separators=(",", ":"))
    )


def natural_output_rules() -> list[str]:
    return [
        "Use context only for reasoning; do not copy it.",
        "Write naturally, with no placement catalog or repeated template phrases.",
        "Mention only factors that change the answer.",
    ]


def opening_context(chart: dict, interpretation: dict, verdict: dict, confidence: str, health_note: str) -> dict:
    question = chart.get("question", {})
    question_text = question.get("text", "your question")
    domain = interpretation.get("domain", "general")
    subdomain = interpretation.get("subdomain", "")
    archetype = question_archetype(question_text, domain, subdomain)

    return {
        "section": "opening",
        "name": first_name(question.get("name", "Querent")),
        "question_text": question_text,
        "question_archetype": archetype,
        "domain": domain,
        "subdomain": subdomain,
        "asked_at": readable_datetime(question.get("asked_at_local") or question.get("asked_at_utc")),
        "place": question.get("place_name", "the asked place"),
        "intent_summary": interpretation.get("intent", {}).get("summary", ""),
        "rule_engine_summary": verdict.get("summary", "The chart gives a mixed answer that needs careful judgment."),
        "confidence": confidence,
        "health_note": health_note,
        "instruction": "Open with the user's real concern and direct answer; mention time/place only naturally.",
    }


def foundation_context(chart: dict, interpretation: dict) -> dict:
    lagna = chart.get("lagna", {})
    planets = planets_by_name(chart)
    moon = planets.get("Moon", {})

    lagna_lord_name = (
        interpretation.get("key_lords", {}).get("lagna_lord")
        or sign_lord_name(lagna.get("sign_index"))
    )
    lagna_lord = planets.get(lagna_lord_name, {})

    return {
        "section": "foundation",
        "lagna": {
            "sign": lagna.get("sign"),
            "degree": lagna.get("formatted_degree"),
            "nakshatra": lagna.get("nakshatra"),
            "pada": lagna.get("pada"),
            "nakshatra_lord": nakshatra_lord(lagna.get("nakshatra")),
        },
        "lagna_lord": {
            "name": lagna_lord_name,
            "sign": lagna_lord.get("sign"),
            "house": lagna_lord.get("house"),
            "degree": lagna_lord.get("formatted_degree"),
            "nakshatra": lagna_lord.get("nakshatra"),
            "retrograde": lagna_lord.get("retrograde"),
        },
        "moon": {
            "sign": moon.get("sign"),
            "house": moon.get("house"),
            "degree": moon.get("formatted_degree"),
            "nakshatra": moon.get("nakshatra"),
            "pada": moon.get("pada"),
            "nakshatra_lord": nakshatra_lord(moon.get("nakshatra")),
            "retrograde": moon.get("retrograde"),
        },
        "instruction": "Synthesize Lagna, Lagna lord, and Moon into one judgment about control, clarity, pressure, delay, or momentum.",
    }


def karya_context(chart: dict, interpretation: dict) -> dict:
    domain = interpretation.get("domain", "general")
    subdomain = interpretation.get("subdomain", "")
    question = chart.get("question", {}).get("text", "")
    archetype = question_archetype(question, domain, subdomain)
    key_lords = interpretation.get("key_lords", {})
    planets = planets_by_name(chart)

    relevant_lords = []
    for key in domain_lord_sequence(domain):
        lord_name = key_lords.get(key)
        planet = planets.get(lord_name, {})
        if lord_name and planet:
            relevant_lords.append({
                "role": key,
                "planet": lord_name,
                "sign": planet.get("sign"),
                "house": planet.get("house"),
                "degree": planet.get("formatted_degree"),
                "nakshatra": planet.get("nakshatra"),
                "retrograde": planet.get("retrograde"),
            })

    return {
        "section": "domain_result",
        "domain": domain,
        "subdomain": subdomain,
        "question_archetype": archetype,
        "domain_method": domain_method(interpretation),
        "relevant_lords": relevant_lords,
        "success_definition": archetype_focus(archetype),
        "instruction": "Define success for this exact question; separate promise, obstacle, and practical path in real-life language.",
    }


def chart_logic_context(verdict: dict, supportive: list[dict], caution: list[dict], neutral: list[dict]) -> dict:
    support_items = [plain_item_text(item) for item in supportive if plain_item_text(item)]
    caution_items = [plain_item_text(item) for item in caution if plain_item_text(item)]
    neutral_items = [plain_item_text(item) for item in neutral if plain_item_text(item)]

    return {
        "section": "chart_logic",
        "rule_engine_summary": verdict.get("summary", "The final judgment is mixed."),
        "supportive_factors": support_items[:4],
        "caution_factors": caution_items[:4],
        "neutral_factors": neutral_items[:2],
        "instruction": "Rank evidence; identify dominant theme, strongest support, strongest obstacle, net judgment, and whether the obstacle is correctable.",
    }


def practical_context(domain: str, supportive: list[dict], caution: list[dict], verdict: dict, archetype: str = "") -> dict:
    strongest_support = plain_item_text(supportive[0]) if supportive else ""
    strongest_obstacle = plain_item_text(caution[0]) if caution else ""

    return {
        "section": "practical_direction",
        "domain": domain,
        "archetype": archetype,
        "strongest_support_hint": strongest_support,
        "strongest_obstacle_hint": strongest_obstacle,
        "advice_dimensions": advice_dimensions(archetype, domain)[:10],
        "instruction": "Give only the 2-4 most relevant practical directions, next step, and mistake to avoid.",
    }


def timing_context(timing: dict | None, dashas: dict | None = None) -> dict:
    return {
        "section": "timing",
        "timing": timing,
        "dashas": dashas or {},
        "instruction": "Use timing only if supplied evidence supports it; do not invent dates; separate promise from timing.",
    }


def final_boundary_context(domain: str, verdict: dict, confidence: str = "") -> dict:
    return {
        "section": "final_verdict",
        "domain": domain,
        "rule_engine_summary": verdict.get("summary", "the matter is mixed and needs careful handling"),
        "confidence": confidence or verdict.get("confidence", ""),
        "instruction": "Close with clear verdict, likely outcome, reason, confidence, next step, and mistake to avoid.",
        "safety_instruction": {
            "health": "Medical care, testing, and treatment must come first.",
            "money_business_legal_travel": "Avoid guarantees. Frame astrology as guidance and preparation.",
            "relationship_child": "Avoid absolute promises. Encourage grounded decisions and proper support.",
        },
    }


def natural_reading_context(chart: dict, interpretation: dict) -> dict:
    evidence = interpretation.get("evidence", [])

    supportive = [
        item for item in evidence
        if item.get("status") in {"strong", "support", "clear"}
    ]
    caution = [
        item for item in evidence
        if item.get("status") in {"caution", "blocked"}
    ]
    neutral = [
        item for item in evidence
        if item.get("status") == "neutral"
    ]

    verdict = interpretation.get("verdict", {})
    confidence = interpretation.get("confidence", "")
    domain = interpretation.get("domain", "general")
    subdomain = interpretation.get("subdomain", "")
    question = chart.get("question", {}).get("text", "")
    archetype = question_archetype(question, domain, subdomain)
    dashas = chart.get("dashas", {})

    health_note = ""
    if domain == "illness":
        health_note = (
            "Health matters must always be handled with proper medical diagnosis, "
            "testing, and treatment; astrology is only supplementary guidance."
        )

    return {
        "natural_output_rules": natural_output_rules(),
        "opening": opening_context(chart, interpretation, verdict, confidence, health_note),
        "foundation": foundation_context(chart, interpretation),
        "domain_result": karya_context(chart, interpretation),
        "chart_logic": chart_logic_context(verdict, supportive, caution, neutral),
        "practical_direction": practical_context(domain, supportive, caution, verdict, archetype),
        "timing": timing_context(interpretation.get("timing"), dashas),
        "final_verdict": final_boundary_context(domain, verdict, confidence),
    }


def llm_context_payload(chart: dict, interpretation: dict) -> dict:
    planets = planets_by_name(chart)
    moon = planets.get("Moon", {})
    lagna = chart.get("lagna", {})
    dashas = chart.get("dashas", {})
    question = chart.get("question", {}).get("text", "")
    domain = interpretation.get("domain")
    subdomain = interpretation.get("subdomain", "")
    archetype = question_archetype(question, domain, subdomain)
    return {
        "user_metadata": {
            "name": chart.get("question", {}).get("name", "Querent"),
            "question": question,
            "domain": domain,
            "subdomain": subdomain,
            "question_archetype": archetype,
            "archetype_focus_questions": archetype_focus(archetype),
            "intent": interpretation.get("intent", {}),
            "asked_at_local": chart.get("question", {}).get("asked_at_local"),
            "asked_at_utc": chart.get("question", {}).get("asked_at_utc"),
            "place_name": chart.get("question", {}).get("place_name"),
            "timezone": chart.get("question", {}).get("timezone"),
        },
        "natural_reading_context": natural_reading_context(chart, interpretation),
        "lagna_and_moon": {
            "lagna_sign": lagna.get("sign"),
            "lagna_degree": lagna.get("formatted_degree"),
            "lagna_nakshatra": lagna.get("nakshatra"),
            "lagna_pada": lagna.get("pada"),
            "lagna_nakshatra_lord": nakshatra_lord(lagna.get("nakshatra")),
            "moon_sign": moon.get("sign"),
            "moon_house": moon.get("house"),
            "moon_degree": moon.get("formatted_degree"),
            "moon_nakshatra": moon.get("nakshatra"),
            "moon_pada": moon.get("pada"),
            "moon_nakshatra_lord": nakshatra_lord(moon.get("nakshatra")),
        },
        "planetary_facts": compact_planets(chart.get("planets", [])),
        "derived_interpretive_context": {
            "planet_strength_matrix": compact_items(planet_strength_matrix(chart), 9),
            "relationship_scan": relationship_scan(chart),
            "aspect_matrix": compact_items(aspect_matrix(chart), 12),
            "exchange_scan": compact_items(exchange_scan(chart), 6),
            "combustion_scan": compact_items(combustion_scan(chart), 6),
            "yoga_candidate_scan": compact_items(yoga_candidate_scan(chart, archetype, domain), 8),
            "relevant_yoga_checklist": relevant_yoga_checklist(archetype, domain)[:8],
            "contradiction_resolution_frame": contradiction_resolution_frame(interpretation),
            "question_specific_advice_dimensions": advice_dimensions(archetype, domain)[:10],
            "synthesis_sequence": [
                "question -> success definition -> strongest support/obstacle -> promise -> timing -> action -> verdict",
            ],
            "available_calculation_limits": [
                "Do not invent missing advanced factors or yogas.",
                "Use only supplied dignity, house, sign, motion, nakshatra, divisional, dasha, timing, relationship, aspect, and rule evidence.",
            ],
            "answer_quality_rules": [
                *natural_output_rules(),
                "Resolve contradictions into one net judgment.",
                "Separate promise from timing.",
                "Translate astrology into the user's domain language.",
            ],
        },
        "rule_engine_verdict": {
            "score": interpretation.get("score"),
            "confidence": interpretation.get("confidence"),
            "verdict": interpretation.get("verdict"),
            "key_lords": interpretation.get("key_lords"),
            "structured_evidence_points": compact_evidence(interpretation.get("evidence", []), 12),
            "domain_method": domain_method(interpretation),
        },
        "timing_and_dashas": compact_timing_and_dashas(interpretation.get("timing"), dashas),
        "divisional_charts": compact_divisional_charts(chart.get("divisional_charts", {}), domain, archetype),
    }


def compact_planets(planets: list[dict]) -> list[dict]:
    return [
        {
            "name": planet.get("name"),
            "sign": planet.get("sign"),
            "house": planet.get("house"),
            "degree": planet.get("formatted_degree"),
            "nakshatra": planet.get("nakshatra"),
            "pada": planet.get("pada"),
            "retrograde": planet.get("retrograde"),
        }
        for planet in planets
    ]


def compact_items(items, limit: int):
    if isinstance(items, list):
        return items[:limit]
    return items


def compact_evidence(evidence: list[dict], limit: int) -> list[dict]:
    return [
        {
            "label": item.get("label"),
            "status": item.get("status"),
            "text": item.get("text"),
        }
        for item in evidence[:limit]
    ]


def compact_timing_and_dashas(timing: dict | None, dashas: dict) -> dict:
    return {
        "calculated_timing_window": timing,
        "nakshatra_lord": dashas.get("nakshatra_lord"),
        "current_mahadasha": compact_period(dashas.get("current_mahadasha")),
        "current_antardasha": compact_period(dashas.get("current_antardasha")),
        "current_pratyantardasha": compact_period(dashas.get("current_pratyantardasha")),
        "current_sookshma": compact_period(dashas.get("current_sookshma")),
        "current_prana": compact_period(dashas.get("current_prana")),
    }


def compact_period(period: dict | None) -> dict:
    if not period:
        return {}
    return {
        "lord": period.get("lord"),
        "start": period.get("start"),
        "end": period.get("end"),
    }


def compact_divisional_charts(charts: dict, domain: str | None, archetype: str) -> dict:
    selected = ["D1", "D9"]
    if domain == "job_career":
        selected.append("D10")
    if domain == "education":
        selected.append("D24")
    if domain == "illness":
        selected.append("D6")
    if domain == "child":
        selected.append("D7")
    if domain == "foreign":
        selected.extend(["D4", "D12"])
    if domain == "wealth" or archetype == "Startup / Business Launch":
        selected.append("D2")

    compact = {}
    for varga in selected:
        chart = charts.get(varga)
        if not chart:
            continue
        occupied = {
            sign: bodies
            for sign, bodies in chart.items()
            if bodies
        }
        if occupied:
            compact[varga] = occupied
    return compact

def question_archetype(question: str, domain: str | None, subdomain: str = "") -> str:
    text = (question or "").lower().strip()
    
    # --- PHASE 1: DIRECT CONFIGURATION ENFORCEMENT ---
    # Explicit domain/subdomain inputs from frontend take programmatic precedence
    if domain == "job_career" and subdomain == "government":
        return "Government Career"
    if domain == "job_career" and subdomain == "private":
        return "Career / Job"
    if domain == "illness":
        return "Health / Illness"
    if domain == "child":
        return "Child / Conception"
    
    # --- PHASE 2: HIERARCHICAL PRIORITY KEYWORD MATRIX ---
    # Ordered strategically to catch high-leverage business, legal, and government vectors first
    patterns = [
        ("Government Career", [
            "upsc", "ssc", "bpsc", "mpsc", "ias", "ips", "ifs", "irs", "psu", "government exam", 
            "govt job", "government job", "sarkari", "civil services", "bureaucracy", "gazetted", 
            "notification", "seat allocation", "state authority", "official appointment"
        ]),
        
        ("Startup / Business Launch", [
            "startup", "app", "application", "saas", "mvp", "platform", "launch", "founder", 
            "co-founder", "pitch deck", "venture", "angel investor", "seed round", "series a", 
            "valuation", "scaling", "b2b", "b2c", "solopreneur", "micro-saas", "product-market fit", 
            "churn rate", "user retention", "bootstrapping", "equity split"
        ]),
        
        ("Career / Job", [
            "job", "career", "interview", "promotion", "salary hike", "ctc", "offer letter", 
            "appraisal", "corporate", "manager", "hiring", "hr review", "notice period", "resignation", 
            "wfh", "tech lead", "faang", "multinational", "increment", "layoff", "severance"
        ]),
        
        ("Litigation / Conflict", [
            "case", "court", "legal", "litigation", "lawsuit", "police", "dispute", "conflict", 
            "fir", "arbitration", "lawyer", "advocate", "judgment", "hearing", "summon", "bail", 
            "compromise", "legal notice", "accused", "petition", "hc", "sc", "tribunal"
        ]),
        
        ("Travel / Foreign", [
            "foreign", "abroad", "visa", "passport", "immigration", "relocate", "relocation", 
            "pr", "citizenship", "green card", "h1b", "schengen", "embassy", "consulate", "gre", 
            "ielts", "toefl", "flight booking", "overseas", "expatriate", "border clearance"
        ]),
        
        ("Wealth / Money", [
            "money", "wealth", "profit", "loss", "income", "funding", "investment", "payment", 
            "loan", "debt", "scalping", "nifty", "bank nifty", "index options", "trading options", 
            "crypto", "portfolio", "dividend", "bankruptcy", "liquidity", "capital", "roi", 
            "equity trading", "futures", "hft", "creditor", "defaulter"
        ]),
        
        ("Property / Home", [
            "property", "house", "home", "land", "flat", "real estate", "rent", "lease", 
            "plot", "builder", "rera", "possession", "deed", "registration", "mortgage", 
            "commercial space", "token money", "tenant", "landlord", "encumbrance"
        ]),
        
        ("Education / Exam", [
            "exam", "study", "education", "college", "school", "admission", "degree", "marks", 
            "research", "phd", "university", "gate", "jee", "neet", "cat exam", "gmat", "scholarship", 
            "thesis", "viva", "semester", "cgpa", "coaching", "quota"
        ]),
        
        ("Marriage / Relationship", [
            "marriage", "marry", "wedding", "relationship", "love", "partner", "spouse", "husband", 
            "wife", "fiance", "proposal", "kundli matching", "compatibility", "breakup", "divorce", 
            "separation", "in-laws", "commitment", "extramarital"
        ]),
        
        ("Child / Conception", [
            "child", "conception", "baby", "pregnancy", "pregnant", "conceive", "fertility", 
            "ivf", "delivery", "birth", "progeny", "offspring", "miscarriage", "paternity"
        ]),
        
        ("Health / Illness", [
            "health", "illness", "disease", "recover", "recovery", "medicine", "doctor", "surgery", 
            "hospital", "diagnosis", "chronic", "acute", "medical report", "treatment", "pain", 
            "infection", "clinic", "physician", "therapy"
        ])
    ]
    
    for archetype, keywords in patterns:
        if any(keyword in text for keyword in keywords):
            return archetype
            
    # --- PHASE 3: METADATA FALLBACK INTERSECTION ---
    # If text is too short or casual, leverage fallback maps from systemic labels
    domain_map = {
        "wealth": "Wealth / Money",
        "marriage": "Marriage / Relationship",
        "education": "Education / Exam",
        "child": "Child / Conception",
        "illness": "Health / Illness",
        "foreign": "Travel / Foreign",
        "job_career": "Career / Job"
    }
    
    return domain_map.get(domain or "", "General Prashna")

def archetype_focus(archetype: str) -> list[str]:
    focus = {
        "Startup / Business Launch": [
            "Market & Product Adoption: Will targeted users naturally adopt, use, and trust this specific product or platform architecture?",
            "Unit Economics & Monetization: Can the business model reliably generate organic revenue, preserve user retention, or secure investor funding support?",
            "Competitive Moat & Execution Obstacles: What is the single biggest operational bottleneck, regulatory barrier, or competitive threat trying to break momentum?",
            "Founder Stamina & Decision Clarity: Does the founder possess the mental stamina, clarity of execution, and cognitive stability to manage high-stress cycles?",
            "Scalability Matrix: Can the core infrastructure, tech stack, or operational model scale efficiently after hitting initial traction?",
            "Strategic Directive: Is the chart commanding the user to aggressively launch, execute an immediate pivot, delay deployment, or correct an underlying system flaw first?"
        ],
        "Career / Job": [
            "Corporate Role Alignment: Does the specific corporate ecosystem, day-to-day role structure, and company culture align with the user's core operational capabilities?",
            "Executive & Gatekeeper Approval: Will management, the hiring committee, or cross-functional HR gatekeepers actively support and approve the user's advancement?",
            "Interview Pipeline Mechanics: Is the interview, screening, or internal promotion pipeline structurally open, or is it blocked by hidden internal candidates?",
            "CTC & Financial Optimization: Will the position yield an aggressive salary upgrade, equity optimization, and clear upward professional mobility?",
            "Immediate Tactical Action: What exact step should the user take right now regarding follow-ups, contract negotiations, or upskilling to secure the position?"
        ],
        "Government Career": [
            "Competitive Merit Moat: Does the candidate have the examination discipline, score optimization potential, and competitive edge to surpass massive candidate pools?",
            "Institutional & Sovereign Support: Is the backing of state authority, bureaucratic favor, or institutional verification strong enough to grant the position?",
            "Vetting & Absolute Appointment: Will the official appointment letter, background verification, or structural medical clearances finalize without legal hiccups?",
            "Bureaucratic Gatekeeping Delays: Are there systemic structural delays, administrative holds, court stays on the exam, or red tape trying to trap the process?",
            "Sustained Preparation Stamina: Can the user maintain maximum preparation focus and psychological resilience if the recruitment pipeline faces deep timeline stretches?"
        ],
        "Wealth / Money": [
            "Capital Inflow Integrity: Is the promised source of incoming cash, investment distribution, trading profit, or outstanding client payment authentic and active?",
            "Structural Capital Retention: Will the generated capital be successfully retained, or will it be instantly absorbed by sudden operational overhead or liabilities?",
            "Systemic Leakage & Debt Traps: Are there hidden financial drains, uncalculated tax exposures, pending interest burdens, or operational burn rates threatening solvency?",
            "Speculative Risk Exposure: Does the chart warn against high-risk options trading, unhedged financial speculation, or unverified capital allocations right now?",
            "Wealth Compounding Safeguards: What structural, legal, or documentation protections must be deployed immediately to secure existing assets from depreciation?"
        ],
        "Marriage / Relationship": [
            "Mutual Psychological Readiness: Are both individuals genuinely prepared for structural, long-term commitment, or is the relationship driven by superficial transition panic?",
            "Contractual & Values Alignment: Is there a deep alignment regarding financial accountability, long-term lifestyle goals, communication frameworks, and core life principles?",
            "Social & Familial Consent: Will both family networks, cultural structures, or primary social circles actively endorse, support, and bless the union?",
            "Ego Blocks & Conflict Triggers: What is the primary hidden source of friction, silent manipulation, unvoiced expectations, or compatibility stress trying to break communication?",
            "Union Timeline & Conduct: When is the optimal cosmic and practical window to formalize the marriage, and what specific interpersonal conduct must be practiced?"
        ],
        "Litigation / Conflict": [
            "Adversary Capability & Strategy: What is the true financial, legal, and operational strength of the opponent? Are they preparing a hidden counter-offensive?",
            "Arbitrator & Judicial Disposition: Is the presiding judge, legal panel, or institutional authority naturally aligned with the user's presentation of evidence?",
            "Evidentiary Integrity: Is the existing legal documentation, contractual backup, or eyewitness strategy airtight enough to survive rigorous cross-examination?",
            "Settlement vs. Total War: Does the chart command an immediate out-of-court mediation/settlement path, or is a full-scale confrontational litigation route favored?",
            "Systemic Exposure & Downside Risk: What is the maximum downside risk to the user's reputation, financial standing, or freedom if the case stretches out?"
        ],
        "Health / Illness": [
            "Vitality Anchor Strength: Does the user's core physical constitution, cellular energy, and immune system possess the baseline stamina to naturally fight the disease?",
            "Diagnostic Precision: Are the current laboratory tests, medical opinions, and clinical scans capturing the accurate root cause, or is there a hidden anomaly?",
            "Treatment & Pharmaceutical Resonance: Will the body adapt favorably to the prescribed medical treatments, surgical procedures, or pharmaceutical regimens without adverse reaction?",
            "Recovery Trajectory & Velocity: Is the physiological timeline pointing to a rapid, clean recovery path, or will the healing process require extended, patient care?",
            "Recurrence & Preventive Safeguards: What lifestyle modifications, secondary screenings, or physiological vulnerabilities must be addressed to block future flare-ups?"
        ],
        "Property / Home": [
            "Asset Promise & Structural Value: Is the specific piece of land, commercial property, or residential asset structurally sound and cosmically supportive for the user?",
            "Deed & Legal Clearness: Are the land titles, building permits, zoning laws, encumbrance certificates, and institutional clearances 100% legitimate and free of dispute?",
            "Liquidity & Payment Cash Flow: Is the capital structure behind the purchase or sale stable, or will a sudden banking, loan disbursement, or cash flow block halt the transaction?",
            "Counterparty & Broker Reliability: Is the seller, real estate developer, or broker acting with complete transparency, or are they hiding structural defects or financial distress?",
            "Closing & Handover Timelines: When will the absolute legal transfer of deed, physical possession, and registration execute without administrative friction?"
        ],
        "Education / Exam": [
            "Cognitive Retention & Focus: Is the student's brain actively absorbing, processing, and retaining complex data structures, logical frameworks, or academic material?",
            "Real-Time Test Execution: Will the user be able to perform under acute high-pressure exam hall testing conditions without experiencing cognitive block or anxiety freezes?",
            "Score & Merit Rank Optimization: Will the final scorecard or cut-off ranking clear the aggressive baseline required to beat institutional selection parameters?",
            "Institutional Admission Fulfillment: Will the targeted top-tier university, technical college, or research program accept the credentials and grant enrollment?",
            "Strategic Curricular Correction: Which specific subject domain, learning methodology, or conceptual gap must be aggressively audited and corrected immediately?"
        ],
        "Travel / Foreign": [
            "Consular & Visa Clearance: Will immigration authorities, embassy gatekeepers, or passport offices clear documentation, or will paperwork face red-tape rejections?",
            "Distance Relocation Logistics: Is the physical movement across geographic borders promised smoothly, or will sudden logistical, travel, or flight bottlenecks disrupt migration?",
            "Socio-Cultural System Integration: How seamlessly will the user adapt to the host country’s economic environment, legal frameworks, language barriers, and social customs?",
            "Long-Term Permanent Settlement: Does the chart support permanent residency, citizenship acquisition, and asset creation abroad, or does it demand an eventual return to the home base?",
            "Strategic Backup Planning: What exact regulatory safeguard or financial cushion must be kept ready in case immediate cross-border operational shifts occur?"
        ],
        "Child / Conception": [
            "Biological Continuity Promise: Is the baseline physiological fertility, reproductive vitality, and genetic promise strong and unblocked in the cosmic map?",
            "Gestation & Pregnancy Stability: Will the multi-month pregnancy cycle remain structurally stable, protected from physiological trauma, stress, or premature disruptions?",
            "Safe Delivery & Birth Vitality: Is the labor and delivery channel promised to clear cleanly, ensuring maximum medical support and high postnatal vitality?",
            "Cooperative Care Matrix: Are both partners, immediate family structures, and medical counselors fully synchronized to create a stress-free environment?",
            "Conception Optimization Windows: What specific immediate timeline windows are most fertile, and what health parameters must be optimized before attempting conception?"
        ]
    }
    return focus.get(archetype, ["core promise", "main obstacle", "likely outcome", "timing if supported", "best practical action"])



def planet_strength_matrix(chart: dict) -> list[dict]:
    return [planet_strength_note(planet) for planet in chart.get("planets", [])]


def planet_strength_note(planet: dict) -> dict:
    name = planet.get("name", "")
    sign_index = planet.get("sign_index")
    sign = planet.get("sign", "")
    house = planet.get("house")
    dignity = "ordinary"
    reason = "No special sign dignity is supplied from the basic dignity checks."
    exaltaion = {
        "Sun": 0,
        "Moon": 1,
        "Mars": 9,
        "Mercury": 5,
        "Jupiter": 3,
        "Venus": 11,
        "Saturn": 6,
    }
    debilitation = {
        "Sun": 6,
        "Moon": 7,
        "Mars": 3,
        "Mercury": 11,
        "Jupiter": 9,
        "Venus": 5,
        "Saturn": 0,
    }
    own_signs = {
        "Sun": {4},
        "Moon": {3},
        "Mars": {0, 7},
        "Mercury": {2, 5},
        "Jupiter": {8, 11},
        "Venus": {1, 6},
        "Saturn": {9, 10},
    }
    if sign_index == exaltaion.get(name):
        dignity = "exalted"
        reason = f"{name} is exalted in {sign}."
    elif sign_index == debilitation.get(name):
        dignity = "debilitated"
        reason = f"{name} is debilitated in {sign}."
    elif sign_index in own_signs.get(name, set()):
        dignity = "own sign"
        reason = f"{name} is in its own sign {sign}."
    house_condition = "supportive" if house in {1, 4, 5, 7, 9, 10, 11} else "pressured" if house in {6, 8, 12} else "neutral"
    motion = "retrograde" if planet.get("retrograde") else "direct"
    return {
        "planet": name,
        "sign": sign,
        "house": house,
        "dignity": dignity,
        "house_condition": house_condition,
        "motion": motion,
        "nakshatra": planet.get("nakshatra"),
        "pada": planet.get("pada"),
        "interpretive_note": reason,
    }


def relationship_scan(chart: dict) -> dict:
    planets = chart.get("planets", [])
    conjunctions = []
    oppositions = []
    house_clusters: dict[int, list[str]] = {}
    for planet in planets:
        house = planet.get("house")
        if isinstance(house, int):
            house_clusters.setdefault(house, []).append(planet.get("name", ""))
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            if first.get("sign_index") == second.get("sign_index"):
                conjunctions.append(
                    {
                        "planets": [first.get("name"), second.get("name")],
                        "sign": first.get("sign"),
                        "house": first.get("house"),
                    }
                )
            first_sign = first.get("sign_index")
            second_sign = second.get("sign_index")
            if isinstance(first_sign, int) and isinstance(second_sign, int) and (first_sign - second_sign) % 12 == 6:
                oppositions.append(
                    {
                        "planets": [first.get("name"), second.get("name")],
                        "axis": [first.get("sign"), second.get("sign")],
                        "houses": [first.get("house"), second.get("house")],
                    }
                )
    return {
        "same_sign_conjunctions": conjunctions,
        "opposition_axes": oppositions,
        "house_clusters": {str(house): names for house, names in house_clusters.items() if len(names) > 1},
        "note": "This is a basic relationship scan from supplied signs and houses; use rule evidence for exact Tajika applying/separating yogas.",
    }


def aspect_matrix(chart: dict) -> list[dict]:
    planets = chart.get("planets", [])
    aspects = []
    aspect_defs = [
        (0, "conjunction"),
        (60, "sextile"),
        (90, "square"),
        (120, "trine"),
        (180, "opposition"),
    ]
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            first_lon = first.get("longitude")
            second_lon = second.get("longitude")
            if not isinstance(first_lon, (int, float)) or not isinstance(second_lon, (int, float)):
                continue
            gap = angular_gap(float(first_lon), float(second_lon))
            for exact, name in aspect_defs:
                orb = abs(gap - exact)
                if orb <= 6:
                    aspects.append(
                        {
                            "planets": [first.get("name"), second.get("name")],
                            "aspect": name,
                            "orb_degrees": round(orb, 2),
                            "houses": [first.get("house"), second.get("house")],
                            "signs": [first.get("sign"), second.get("sign")],
                            "synthesis_hint": aspect_synthesis_hint(first, second, name),
                        }
                    )
                    break
    return aspects


def exchange_scan(chart: dict) -> list[dict]:
    planets = [planet for planet in chart.get("planets", []) if planet.get("name") not in {"Rahu", "Ketu"}]
    exchanges = []
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            first_sign = first.get("sign_index")
            second_sign = second.get("sign_index")
            if not isinstance(first_sign, int) or not isinstance(second_sign, int):
                continue
            if sign_lord_name(first_sign) == second.get("name") and sign_lord_name(second_sign) == first.get("name"):
                exchanges.append(
                    {
                        "planets": [first.get("name"), second.get("name")],
                        "signs": [first.get("sign"), second.get("sign")],
                        "houses": [first.get("house"), second.get("house")],
                        "interpretive_note": "Parivartana-style exchange candidate; blend both house agendas before judging either planet separately.",
                    }
                )
    return exchanges


def combustion_scan(chart: dict) -> list[dict]:
    planets = planets_by_name(chart)
    sun = planets.get("Sun")
    if not sun or not isinstance(sun.get("longitude"), (int, float)):
        return []
    thresholds = {
        "Moon": 12,
        "Mars": 17,
        "Mercury": 14,
        "Jupiter": 11,
        "Venus": 10,
        "Saturn": 15,
    }
    combust = []
    for name, threshold in thresholds.items():
        planet = planets.get(name)
        if not planet or not isinstance(planet.get("longitude"), (int, float)):
            continue
        gap = angular_gap(float(sun["longitude"]), float(planet["longitude"]))
        if gap <= threshold:
            combust.append(
                {
                    "planet": name,
                    "sun_gap_degrees": round(gap, 2),
                    "threshold_degrees": threshold,
                    "interpretive_note": f"{name} is close enough to the Sun to require combustion-style caution before interpreting its promise.",
                }
            )
    return combust

def yoga_candidate_scan(chart: dict, archetype: str, domain: str | None) -> list[dict]:
    planets = planets_by_name(chart)
    lagna = chart.get("lagna", {})
    lagna_sign = lagna.get("sign_index")
    candidates = []

    if not isinstance(lagna_sign, int):
        return candidates

    house_lords = {
        house: sign_lord_name((lagna_sign + house - 1) % 12)
        for house in range(1, 13)
    }

    def lord(house: int) -> str:
        return house_lords.get(house, "")

    def lord_in_house(house_lord_of: int, target_houses: set[int]) -> bool:
        planet = planets.get(lord(house_lord_of), {})
        return planet.get("house") in target_houses

    def lords_connected(a: int, b: int) -> bool:
        return planets_connected(planets, lord(a), lord(b))

    def planet_in_houses(name: str, houses: set[int]) -> bool:
        return planets.get(name, {}).get("house") in houses

    def any_lord_connected(houses_a: list[int], houses_b: list[int]) -> bool:
        return any(lords_connected(a, b) for a in houses_a for b in houses_b)

    # -------------------------
    # COMMON CORE YOGAS
    # -------------------------

    add_if_present(
        candidates,
        "Dhana Yoga candidate",
        any(
            lord(a) == lord(b) or lords_connected(a, b)
            for a in [2, 5, 9, 11]
            for b in [2, 5, 9, 11]
            if a < b
        ),
        "Money, merit, intelligence, and gain houses show a relationship bridge. Use only after judging strength, dignity, and leakage factors.",
    )

    add_if_present(
        candidates,
        "Raja Yoga candidate",
        any_lord_connected([1, 4, 7, 10], [5, 9]),
        "Kendra and trikona factors connect, suggesting capacity for rise, support, or recognition if dignity and domain relevance agree.",
    )

    add_if_present(
        candidates,
        "Viparita Raja Yoga candidate",
        any(lord_in_house(h, {6, 8, 12}) for h in [6, 8, 12]),
        "A dusthana lord sits in a dusthana, so pressure may convert into advantage after struggle, correction, or hidden work.",
    )

    add_if_present(
        candidates,
        "Neecha Bhanga candidate",
        any(note["dignity"] == "debilitated" for note in planet_strength_matrix(chart)),
        "A debilitated planet exists. Check whether cancellation support exists before treating weakness as final.",
    )

    add_if_present(
        candidates,
        "Parivartana Yoga candidate",
        bool(exchange_scan(chart)),
        "An exchange exists. The exchanged houses must be interpreted as one combined mechanism rather than separately.",
    )

    add_if_present(
        candidates,
        "Lagna-Result Bridge",
        any_lord_connected([1], [10, 11, 4]),
        "The querent connects with action, fulfillment, or final outcome. This improves result potential if the connected lords are strong.",
    )

    add_if_present(
        candidates,
        "Moon-Support Protection",
        planets_connected(planets, "Moon", "Jupiter") or planets_connected(planets, "Moon", "Venus"),
        "Moon receives support from a benefic factor. This may protect judgment, flow, or emotional steadiness.",
    )

    add_if_present(
        candidates,
        "Chandra Mangala candidate",
        planets_connected(planets, "Moon", "Mars"),
        "Moon and Mars connect. This can show drive, commercial instinct, urgency, or emotional impatience depending on the domain.",
    )

    add_if_present(
        candidates,
        "Gaja Kesari candidate",
        planets_connected(planets, "Moon", "Jupiter"),
        "Moon and Jupiter connect. This can protect judgment, guidance, public trust, or recovery depending on the question.",
    )

    add_if_present(
        candidates,
        "Lakshmi-style Prosperity candidate",
        any_lord_connected([1, 9], [2, 11]) or any_lord_connected([5, 9], [2, 11]),
        "Fortune/intelligence houses connect with wealth/gain houses. This can support prosperity if leakage and dusthana pressure do not dominate.",
    )

    add_if_present(
        candidates,
        "Obstacle-to-Outcome Bridge",
        any_lord_connected([6, 8, 12], [10, 11, 4]),
        "Obstacle houses connect with action, gains, or final outcome. The matter may succeed only after handling pressure, delay, debt, illness, opposition, or hidden complications.",
    )

    # -------------------------
    # WEALTH / MONEY
    # -------------------------

    if domain == "wealth" or archetype in {"Wealth / Money", "Startup / Business Launch"}:
        add_if_present(
            candidates,
            "Income-Retention Bridge",
            lords_connected(2, 11),
            "The stored-wealth house and gains house connect. This supports converting inflow into retained money if 12th-house leakage is controlled.",
        )

        add_if_present(
            candidates,
            "Speculation-Gain Bridge",
            lords_connected(5, 11),
            "The intelligence/speculation house connects with gains. Useful for investment or risk-based wealth only if the question truly involves speculation.",
        )

        add_if_present(
            candidates,
            "Wealth Leakage Warning",
            any_lord_connected([12, 8], [2, 11]) or planet_in_houses("Moon", {12}) or planet_in_houses("Venus", {8, 12}),
            "Loss, expense, debt, or hidden-risk houses touch money/gain factors. Revenue may not automatically become retained wealth.",
        )

        add_if_present(
            candidates,
            "Funding / Other People's Money Signal",
            any_lord_connected([8], [2, 10, 11]) or planet_in_houses("Jupiter", {8}) or planet_in_houses("Venus", {8}),
            "The 8th house connects with wealth or action. This may show funding, investors, debt, taxation, hidden capital, or delayed realization.",
        )

    # -------------------------
    # STARTUP / BUSINESS / APP
    # -------------------------

    if archetype == "Startup / Business Launch":
        add_if_present(
            candidates,
            "Founder-Execution Bridge",
            lords_connected(1, 10),
            "Founder and execution houses connect. This supports building capacity, but strength decides whether execution is clean or pressured.",
        )

        add_if_present(
            candidates,
            "Execution-Gain Bridge",
            lords_connected(10, 11),
            "Business action connects with gains. This supports monetization or traction if market acceptance also appears.",
        )

        add_if_present(
            candidates,
            "Market-Acceptance Bridge",
            lords_connected(1, 7) or lords_connected(7, 11),
            "Founder, market, and gains connect. This is important for user adoption, customer response, and public acceptance.",
        )

        add_if_present(
            candidates,
            "Product-Communication Bridge",
            lords_connected(3, 10) or lords_connected(3, 11) or planet_in_houses("Mercury", {3, 10, 11}),
            "Communication/software/iteration factors connect with execution or gains. This supports product iteration, marketing, or platform growth.",
        )

        add_if_present(
            candidates,
            "Scale / Network Signal",
            lords_connected(11, 3) or lords_connected(11, 7) or planet_in_houses("Rahu", {3, 7, 10, 11}),
            "Network, market, or technology factors are activated. This can support scale, but Rahu/Saturn pressure may make growth unstable or delayed.",
        )

        add_if_present(
            candidates,
            "Burn-Rate Warning",
            any_lord_connected([12], [10, 11, 2]) or planet_in_houses("Moon", {12}),
            "Expense or invisible-effort factors touch business/gain houses. The venture may require controlled burn and slower scaling.",
        )

    # -------------------------
    # HEALTH / ILLNESS
    # -------------------------

    if domain == "illness" or archetype == "Health / Illness":
        add_if_present(
            candidates,
            "Vitality-Recovery Bridge",
            any_lord_connected([1], [4, 10, 11]) or planets_connected(planets, lord(1), "Sun"),
            "Vitality connects with medicine, doctor, recovery, or fulfillment factors. This supports improvement if disease pressure is not stronger.",
        )

        add_if_present(
            candidates,
            "Disease Pressure Signal",
            any_lord_connected([6, 8, 12], [1]) or lord_in_house(1, {6, 8, 12}),
            "Disease, chronic pressure, or hospitalization houses affect the body/vitality. Medical care and monitoring become essential.",
        )

        add_if_present(
            candidates,
            "Treatment Support Signal",
            lords_connected(4, 10) or any_lord_connected([4, 10], [1, 11]),
            "Medicine and doctor/treatment houses support recovery. This favors proper diagnosis, treatment, and follow-up.",
        )

        add_if_present(
            candidates,
            "Chronic / Hidden Condition Warning",
            any_lord_connected([8], [1, 6, 12]) or planet_in_houses("Moon", {8, 12}),
            "Deep, hidden, chronic, or recurring pressure is indicated. Do not rely on symbolic timing alone; medical testing matters.",
        )

    # -------------------------
    # MARRIAGE / RELATIONSHIP
    # -------------------------

    if domain == "marriage" or archetype == "Marriage / Relationship":
        add_if_present(
            candidates,
            "Union Bridge",
            lords_connected(1, 7),
            "Querent and partner houses connect. This is the primary relationship/union bridge; dignity decides whether it is smooth or conflicted.",
        )

        add_if_present(
            candidates,
            "Marriage Fulfillment Bridge",
            any_lord_connected([7], [2, 11]) or any_lord_connected([1, 7], [2, 11]),
            "Partner/union factors connect with family and fulfillment houses. This supports formalization, family acceptance, or completion.",
        )

        add_if_present(
            candidates,
            "Romance-to-Commitment Bridge",
            any_lord_connected([5], [7, 11]),
            "Romance or affection connects with partnership or fulfillment. This supports relationship movement beyond attraction if stable factors agree.",
        )

        add_if_present(
            candidates,
            "Relationship Stress / Break Signal",
            any_lord_connected([6, 8, 12], [1, 7]) or planet_in_houses("Venus", {6, 8, 12}),
            "Conflict, fear, distance, secrecy, or withdrawal houses touch relationship factors. The matter needs careful handling.",
        )

        add_if_present(
            candidates,
            "Harmony Support",
            planets_connected(planets, "Moon", "Venus") or planets_connected(planets, "Jupiter", "Venus"),
            "Emotional flow or wisdom connects with relationship harmony. This can soften conflict if other factors do not block union.",
        )

    # -------------------------
    # CHILD / PROGENY
    # -------------------------

    if domain == "child" or archetype == "Child / Conception":
        add_if_present(
            candidates,
            "Progeny Promise Bridge",
            any_lord_connected([1, 5], [5, 9, 11]) or planets_connected(planets, lord(5), "Jupiter"),
            "Body, child, fortune, and fulfillment factors connect. This supports progeny promise if afflictions do not dominate.",
        )

        add_if_present(
            candidates,
            "Jupiter-5th Support",
            planet_in_houses("Jupiter", {1, 5, 9, 11}) or planets_connected(planets, "Jupiter", lord(5)),
            "Jupiter supports the child/progeny matter. Judge strength and affliction before giving a positive result.",
        )

        add_if_present(
            candidates,
            "Delay / Medical Caution for Progeny",
            any_lord_connected([6, 8, 12], [5]) or lord_in_house(5, {6, 8, 12}),
            "The child house connects with disease, delay, hidden factors, or loss houses. Medical guidance and patience may be needed.",
        )

        add_if_present(
            candidates,
            "Family Continuity Support",
            any_lord_connected([2, 5, 9], [11]),
            "Family, child, fortune, and fulfillment houses connect. This supports eventual continuity if the main promise is not blocked.",
        )

    # -------------------------
    # GOVERNMENT CAREER
    # -------------------------

    if archetype == "Government Career" or (domain == "job_career" and str(archetype).lower().startswith("government")):
        add_if_present(
            candidates,
            "Government Authority Bridge",
            any_lord_connected([10], [5, 6, 11]) or planet_in_houses("Sun", {1, 6, 10, 11}),
            "Career/authority connects with competition, exam, or appointment houses. This supports government selection if strength agrees.",
        )

        add_if_present(
            candidates,
            "Competition-to-Appointment Bridge",
            lords_connected(6, 11) or any_lord_connected([5, 6], [10, 11]),
            "Competition/exam factors connect with appointment/gain. This is useful for selection after effort.",
        )

        add_if_present(
            candidates,
            "Bureaucratic Delay Signal",
            any_lord_connected([8, 12], [10, 11]) or planet_in_houses("Saturn", {6, 8, 10, 12}),
            "Delay, paperwork, authority gatekeeping, or procedural pressure may affect the career result.",
        )

        add_if_present(
            candidates,
            "Service Stability Signal",
            planet_in_houses("Saturn", {6, 10, 11}) or lords_connected(6, 10),
            "Service, discipline, routine, and career houses connect. This favors stable employment if selection is achieved.",
        )

    # -------------------------
    # PRIVATE CAREER
    # -------------------------

    if archetype in {"Career / Job", "Private Career"} or (domain == "job_career" and archetype != "Government Career"):
        add_if_present(
            candidates,
            "Interview-Offer Bridge",
            any_lord_connected([6, 7], [10, 11]),
            "Interview/employer/contract factors connect with role or offer fulfillment. This supports job movement if dignity agrees.",
        )

        add_if_present(
            candidates,
            "Salary-Growth Bridge",
            any_lord_connected([2, 10], [11]) or lords_connected(2, 10),
            "Income, role, and gains connect. This supports salary/package or career growth.",
        )

        add_if_present(
            candidates,
            "Corporate Communication Support",
            planet_in_houses("Mercury", {1, 6, 7, 10, 11}) or any_lord_connected([3], [6, 7, 10, 11]),
            "Communication, interview, documentation, or corporate process factors support the job path.",
        )

        add_if_present(
            candidates,
            "Workplace Pressure Warning",
            any_lord_connected([6, 8, 12], [10]) or planet_in_houses("Saturn", {8, 12}),
            "Workload, delay, hidden pressure, or dissatisfaction may affect career quality even if a role appears.",
        )

    # -------------------------
    # FOREIGN / TRAVEL
    # -------------------------

    if domain == "foreign" or archetype == "Travel / Foreign":
        add_if_present(
            candidates,
            "Foreign Movement Bridge",
            any_lord_connected([1, 4], [7, 9, 12]) or any_lord_connected([3, 9], [12]),
            "Self/home/document/travel houses connect with foreign or distance houses. This supports movement if permissions align.",
        )

        add_if_present(
            candidates,
            "Visa / Permission Bridge",
            any_lord_connected([9, 10, 11], [12]) or any_lord_connected([3], [9, 11]),
            "Permission, authority, documents, and foreign houses connect. This supports visa or approval if not blocked by Saturn/8th/12th pressure.",
        )

        add_if_present(
            candidates,
            "Settlement Away From Home Signal",
            any_lord_connected([4], [12]) or planet_in_houses("Rahu", {7, 9, 12}),
            "Home/base connects with foreign residence or separation. This supports relocation or distance from birthplace if other factors agree.",
        )

        add_if_present(
            candidates,
            "Travel Delay / Document Warning",
            any_lord_connected([6, 8, 12], [3, 9]) or planet_in_houses("Saturn", {3, 9, 12}),
            "Documents, permissions, delay, or procedural obstacles may slow travel or foreign settlement.",
        )

    # -------------------------
    # EDUCATION
    # -------------------------

    if domain == "education" or archetype == "Education / Exam":
        add_if_present(
            candidates,
            "Study-Result Bridge",
            any_lord_connected([4, 5, 9], [10, 11]),
            "Education, exam, higher study, result, and fulfillment houses connect. This supports academic outcome if discipline is present.",
        )

        add_if_present(
            candidates,
            "Exam Intelligence Support",
            planet_in_houses("Mercury", {1, 4, 5, 9, 10, 11}) or planets_connected(planets, "Mercury", lord(5)),
            "Mercury supports learning, analysis, exam thinking, or communication. Judge stress and consistency before final result.",
        )

        add_if_present(
            candidates,
            "Teacher / Higher Knowledge Support",
            planet_in_houses("Jupiter", {1, 5, 9, 10, 11}) or planets_connected(planets, "Jupiter", lord(9)),
            "Jupiter supports guidance, higher education, wisdom, or mentor help.",
        )

        add_if_present(
            candidates,
            "Study Delay / Concentration Warning",
            any_lord_connected([6, 8, 12], [4, 5, 9]) or planet_in_houses("Moon", {6, 8, 12}),
            "Stress, delay, distraction, health, or hidden pressure may affect preparation and concentration.",
        )

    # -------------------------
    # PROPERTY / HOME
    # -------------------------

    if domain == "property" or archetype == "Property / Home":
        add_if_present(
            candidates,
            "Property Acquisition Bridge",
            any_lord_connected([1, 4], [2, 10, 11]) or lords_connected(4, 11),
            "Home/property factors connect with money, action, or fulfillment. This supports acquisition or settlement if documents are clean.",
        )

        add_if_present(
            candidates,
            "Document / Payment Warning",
            any_lord_connected([6, 8, 12], [2, 4]) or planet_in_houses("Saturn", {4, 8, 12}),
            "Property, money, debt, dispute, or document houses are pressured. Verification and staged payment are important.",
        )

        add_if_present(
            candidates,
            "Stable Asset Signal",
            planet_in_houses("Saturn", {4, 10, 11}) or lords_connected(2, 4),
            "Stability and asset houses connect. This supports long-term property value if legal/payment risks are controlled.",
        )

    # -------------------------
    # LITIGATION / CONFLICT
    # -------------------------

    if archetype == "Litigation / Conflict":
        add_if_present(
            candidates,
            "Dispute Victory Bridge",
            any_lord_connected([1, 6], [10, 11]) or lord_in_house(6, {6, 10, 11}),
            "Querent/dispute factors connect with authority or fulfillment. This may support victory after effort if the opponent is weaker.",
        )

        add_if_present(
            candidates,
            "Opponent Pressure Signal",
            any_lord_connected([7], [6, 8, 12]) or lord_in_house(7, {6, 8, 12}),
            "The opponent/other party is under pressure. This can weaken their position if the querent's factors are stronger.",
        )

        add_if_present(
            candidates,
            "Settlement Possibility",
            any_lord_connected([1, 7], [4, 11]) or planets_connected(planets, "Venus", lord(7)),
            "Querent and opponent factors connect with peace/final settlement/fulfillment. Settlement may be possible if conflict indicators soften.",
        )

        add_if_present(
            candidates,
            "Legal Delay Warning",
            any_lord_connected([8, 12], [6, 7, 10]) or planet_in_houses("Saturn", {6, 8, 10, 12}),
            "Court, dispute, authority, or delay houses are pressured. The matter may stretch through procedure or hidden complications.",
        )

    return candidates

def contradiction_resolution_frame(interpretation: dict) -> dict:
    evidence = interpretation.get("evidence", [])
    positives = [plain_item_text(item) for item in evidence if item.get("status") in {"strong", "support", "clear"} and plain_item_text(item)]
    negatives = [plain_item_text(item) for item in evidence if item.get("status") in {"caution", "blocked"} and plain_item_text(item)]
    neutrals = [plain_item_text(item) for item in evidence if item.get("status") == "neutral" and plain_item_text(item)]
    score = interpretation.get("score", 0)
    if score >= 4:
        net = "support wins, but only after accounting for the named resistance"
    elif score <= -2:
        net = "resistance wins unless the practical remedy area is corrected"
    else:
        net = "mixed chart; outcome depends on handling the strongest contradiction"
    return {
        "positive_factors_to_synthesize": positives[:6],
        "negative_factors_to_synthesize": negatives[:6],
        "neutral_texture": neutrals[:4],
        "net_weight_instruction": net,
        "confidence": interpretation.get("confidence"),
        "confidence_reason_instruction": "Explain confidence from agreement or disagreement among Lagna, Moon, key lords, yogas, dasha, and rule evidence.",
    }


def advice_dimensions(archetype: str, domain: str | None) -> list[str]:
    """
    Returns decision/advice dimensions, not fixed advice.

    Purpose:
    - Give the LLM the areas where practical guidance should be generated.
    - Do not force the same advice every time.
    - The final advice should be selected based on chart support, resistance,
      timing, contradiction, and domain context.
    """

    normalized_domain = (domain or "").strip().lower()
    normalized_archetype = (archetype or "").strip()

    frameworks = {
        "Startup / Business Launch": [
            "core product validation",
            "market acceptance",
            "user trust and credibility",
            "customer acquisition",
            "retention and repeat usage",
            "monetization model",
            "cash-flow discipline",
            "burn-rate control",
            "competition and differentiation",
            "founder focus and decision clarity",
            "execution consistency",
            "timing of launch versus timing of scaling",
            "partnership or funding strategy",
            "revenue before aggressive expansion",
            "what mistake to avoid: scaling before product-market fit",
        ],

        "Wealth / Money": [
            "income generation",
            "retained wealth",
            "cash-flow stability",
            "capital protection",
            "expense leakage",
            "debt or liability management",
            "investment discipline",
            "speculation risk",
            "profit versus actual savings",
            "timing of inflow",
            "risk appetite",
            "documentation of financial commitments",
            "whether to act, wait, conserve, or restructure",
            "what mistake to avoid: confusing possible inflow with secured wealth",
        ],

        "Health / Illness": [
            "medical diagnosis and professional treatment",
            "vitality and recovery capacity",
            "acute versus chronic pressure",
            "treatment response",
            "medicine and doctor support",
            "hospitalization or isolation risk",
            "mental stress and emotional stability",
            "lifestyle correction",
            "recurrence prevention",
            "follow-up testing",
            "rest and recovery discipline",
            "family/support system",
            "what mistake to avoid: relying on astrology instead of medical care",
        ],

        "Marriage / Relationship": [
            "commitment potential",
            "emotional compatibility",
            "communication quality",
            "trust and consistency of actions",
            "family acceptance",
            "formalization or marriage promise",
            "conflict resolution",
            "ego, secrecy, or distance issues",
            "timing of proposal or decision",
            "partner's readiness",
            "relationship stability",
            "whether to proceed, wait, reconcile, or create distance",
            "what mistake to avoid: judging promises without observing actions",
        ],

        "Child / Conception": [
            "conception or child promise",
            "physical and medical readiness",
            "partner cooperation",
            "family continuity",
            "delay or obstruction factors",
            "emotional pressure",
            "treatment or medical guidance",
            "timing of attempt or result",
            "pregnancy stability",
            "patience and follow-up",
            "what mistake to avoid: ignoring medical evaluation when delay is shown",
        ],

        "Government Career": [
            "exam discipline",
            "competition strength",
            "authority approval",
            "selection possibility",
            "appointment or joining",
            "document and eligibility compliance",
            "bureaucratic delay",
            "preparation strategy",
            "patience under slow process",
            "role stability",
            "seniority or institutional rules",
            "whether to continue preparation, change strategy, or wait",
            "what mistake to avoid: stopping effort because of delay",
        ],

        "Private Career": [
            "interview performance",
            "employer or HR response",
            "offer possibility",
            "salary or package quality",
            "role fit",
            "workplace stability",
            "career growth",
            "negotiation timing",
            "communication and documentation",
            "manager or team alignment",
            "switching versus staying",
            "workload and pressure",
            "what mistake to avoid: negotiating before the offer path is concrete",
        ],

        "Career / Job": [
            "selection or opportunity path",
            "authority or employer response",
            "skill and execution evidence",
            "income and role quality",
            "competition or workplace pressure",
            "timing of offer or progress",
            "stability after selection",
            "whether to prepare, apply, negotiate, switch, or wait",
            "what mistake to avoid: assuming opportunity is final before confirmation",
        ],

        "Travel / Foreign": [
            "permission or visa approval",
            "document readiness",
            "movement possibility",
            "short travel versus relocation",
            "foreign settlement quality",
            "financial cost of movement",
            "delay or rejection risk",
            "authority and paperwork",
            "distance from home/family",
            "adaptation in foreign place",
            "backup timeline",
            "whether to apply, wait, retry, or correct documents",
            "what mistake to avoid: making irreversible plans before permission is secured",
        ],

        "Education / Exam": [
            "study discipline",
            "concentration",
            "conceptual clarity",
            "exam performance",
            "admission possibility",
            "mentor or teacher support",
            "revision strategy",
            "stress management",
            "delay or distraction",
            "higher education versus basic exam result",
            "consistency over last-minute panic",
            "whether to continue, change strategy, or seek guidance",
            "what mistake to avoid: changing direction because of temporary anxiety",
        ],

        "Property / Home": [
            "legal verification",
            "document clarity",
            "payment schedule",
            "loan or debt pressure",
            "seller/buyer reliability",
            "registration or possession timing",
            "property stability",
            "family agreement",
            "hidden defect or dispute risk",
            "negotiation discipline",
            "whether to buy, sell, wait, verify, or renegotiate",
            "what mistake to avoid: rushing signing before documents are verified",
        ],

        "Litigation / Conflict": [
            "strength of querent's position",
            "opponent's strength",
            "evidence quality",
            "authority or judge factor",
            "settlement possibility",
            "delay through procedure",
            "legal cost and stress",
            "documentation",
            "strategy versus emotional reaction",
            "whether to fight, settle, wait, or gather proof",
            "what mistake to avoid: acting from anger instead of evidence",
        ],

        "General Prashna": [
            "core promise of the matter",
            "main obstacle",
            "correctable versus blocking factor",
            "timing only if supported",
            "practical next step",
            "what to avoid",
            "confidence level and reason",
        ],
    }

    # Domain override when the selected domain is more reliable than keyword archetype.
    domain_to_archetype = {
        "wealth": "Wealth / Money",
        "money": "Wealth / Money",
        "illness": "Health / Illness",
        "health": "Health / Illness",
        "marriage": "Marriage / Relationship",
        "relationship": "Marriage / Relationship",
        "child": "Child / Conception",
        "progeny": "Child / Conception",
        "education": "Education / Exam",
        "foreign": "Travel / Foreign",
        "travel": "Travel / Foreign",
        "property": "Property / Home",
        "litigation": "Litigation / Conflict",
        "legal": "Litigation / Conflict",
    }

    # Special handling for career subtypes already detected by archetype.
    if normalized_archetype in frameworks:
        selected = normalized_archetype
    elif normalized_domain == "job_career":
        selected = "Career / Job"
    else:
        selected = domain_to_archetype.get(normalized_domain, "General Prashna")

    base = frameworks.get(selected, frameworks["General Prashna"])

    # Universal guidance dimensions that make the LLM less robotic.
    universal = [
        "identify the single strongest support",
        "identify the single strongest obstacle",
        "explain whether the obstacle is correctable",
        "give only chart-specific advice, not a generic checklist",
        "connect advice directly to the asked question",
    ]

    # Avoid duplicate items while preserving order.
    result = []
    for item in base + universal:
        if item not in result:
            result.append(item)

    return result
def add_if_present(items: list[dict], name: str, condition: bool, note: str) -> None:
    if condition:
        items.append({"name": name, "interpretive_note": note})


def planets_connected(planets: dict[str, dict], first_name: str, second_name: str) -> bool:
    first = planets.get(first_name)
    second = planets.get(second_name)
    if not first or not second or first_name == second_name:
        return False
    if first.get("sign_index") == second.get("sign_index") or first.get("house") == second.get("house"):
        return True
    first_sign = first.get("sign_index")
    second_sign = second.get("sign_index")
    if isinstance(first_sign, int) and isinstance(second_sign, int) and (first_sign - second_sign) % 12 == 6:
        return True
    first_lon = first.get("longitude")
    second_lon = second.get("longitude")
    if isinstance(first_lon, (int, float)) and isinstance(second_lon, (int, float)):
        return any(abs(angular_gap(float(first_lon), float(second_lon)) - exact) <= 6 for exact in [0, 60, 90, 120, 180])
    return False


def aspect_synthesis_hint(first: dict, second: dict, aspect: str) -> str:
    first_name = first.get("name", "first planet")
    second_name = second.get("name", "second planet")
    if aspect in {"conjunction", "trine", "sextile"}:
        tone = "blend or support each other"
    elif aspect == "opposition":
        tone = "create an axis that must be balanced"
    else:
        tone = "create friction that must be handled deliberately"
    return f"{first_name} and {second_name} {tone}; interpret their combined houses before isolating either placement."


def angular_gap(first: float, second: float) -> float:
    gap = abs((first - second) % 360)
    return min(gap, 360 - gap)

def relevant_yoga_checklist(archetype: str, domain: str | None) -> list[str]:

    common = [
        "Check Raja Yoga only if kendra-trikona relationships are supported by supplied evidence. Judge whether it improves authority, achievement, or success in this question rather than assuming overall prosperity.",
        "Check Dhana Yoga only if wealth-producing lords are connected and strong. Verify whether gains become retained wealth after leakage and contradiction are considered.",
        "Check Viparita Raja Yoga only if dusthana lords occupy or connect with dusthana houses. Judge whether struggle converts into eventual advantage rather than immediate success.",
        "Check Neecha Bhanga only if debility exists. Verify cancellation before treating weakness as final.",
        "Check Parivartana Yoga and interpret the exchanged houses as one combined mechanism rather than separately.",
        "Check Gaja Kesari Yoga to determine whether it protects judgment, reputation, public support, wisdom, or recovery depending on the domain.",
        "Check Chandra Mangala Yoga to determine whether it produces commercial drive, initiative, emotional urgency, or financial volatility depending on the question.",
    ]

    if archetype == "Startup / Business Launch":
        return common + [
            "Evaluate founder (1st), execution (10th), market (7th), and gains (11th) as one integrated business mechanism.",
            "Check Mercury for product quality, software, communication, and iteration.",
            "Check Jupiter for wisdom, trust, credibility, and long-term value creation.",
            "Check Venus for user appeal, perceived value, and monetization.",
            "Check Rahu for technology, innovation, viral reach, and unconventional scaling, while judging instability.",
            "Check Saturn for execution discipline, operational delay, and sustainable scaling.",
            "Determine whether the chart favors product-market fit, gradual growth, or premature scaling.",
        ]

    if domain == "wealth":
        return common + [
            "Check whether gains (11th) convert into retained wealth (2nd).",
            "Judge leakage from 8th/12th before promising financial success.",
            "Distinguish recurring income, speculation, debt, inheritance, funding, and capital appreciation.",
            "Determine whether wealth is created through effort, opportunity, partnership, or accumulated stability.",
        ]

    if domain == "marriage":
        return common + [
            "Judge 1st and 7th together before concluding on union.",
            "Evaluate Venus for harmony and Jupiter for marriage support where applicable.",
            "Check whether family acceptance (2nd) supports or obstructs marriage.",
            "Use D9 only as reinforcement, never as the primary promise.",
            "Determine whether delay, incompatibility, distance, or commitment issues dominate.",
        ]

    if domain == "child":
        return common + [
            "Judge the 5th house and Jupiter together before concluding on progeny.",
            "Differentiate promise, delay, medical issues, and timing.",
            "Use D7 only as reinforcement.",
            "Determine whether obstacles are temporary or structural.",
        ]

    if domain == "education":
        return common + [
            "Judge 4th, 5th, and 9th together for learning, exams, and higher education.",
            "Evaluate Mercury for learning ability and Jupiter for guidance.",
            "Use D24 only to reinforce the main chart.",
            "Separate intelligence, preparation, admission, and final result.",
        ]

    if domain == "foreign":
        return common + [
            "Judge 4th, 7th, 9th, and 12th together before concluding on travel or settlement.",
            "Evaluate Rahu for foreign influence and Saturn for procedural delay.",
            "Distinguish travel, relocation, visa approval, and long-term settlement.",
            "Use D4 and D9 only as supporting evidence.",
        ]

    if domain == "illness":
        return [
            "Judge Lagna and Lagna lord first for vitality.",
            "Judge 6th for disease, 8th for chronicity, and 12th for hospitalization or isolation.",
            "Evaluate Moon for current condition and Sun for vitality.",
            "Judge 4th for medicine/support and 10th for physician/treatment.",
            "Use D6 only to reinforce the main chart.",
            "Determine whether the chart supports recovery, management, recurrence, or urgent medical attention.",
        ]

    if domain == "job_career":
        return common + [
            "Separate government and private career logic.",
            "Judge 10th for profession, 6th for competition/service, and 11th for fulfillment.",
            "For government jobs, evaluate Sun, Saturn, authority, examination, and appointment.",
            "For private careers, evaluate Mercury, contracts (7th), salary (2nd), growth (11th), and role fit.",
            "Determine whether the chart supports selection, appointment, promotion, change, or stability.",
        ]

    return common


def nakshatra_lord(name: str | None) -> str:
    if not name:
        return ""
    sequence = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    nakshatras = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
        "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
        "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
        "Uttara Bhadrapada", "Revati",
    ]
    try:
        return sequence[nakshatras.index(name) % len(sequence)]
    except ValueError:
        return ""


def domain_method(interpretation: dict) -> list[str]:
    domain = interpretation.get("domain", "")
    subdomain = interpretation.get("subdomain", "")

    universal = [
        "Understand the exact real-life question before judging the chart",
        "Define what success means for this domain",
        "Judge Lagna, Moon, and relevant house lords only in relation to the asked question",
        "Judge planetary strength before house meaning",
        "Blend aspects, conjunctions, yogas, divisional charts, dasha, and contradiction evidence",
        "Identify the single strongest support and single strongest obstacle",
        "Resolve whether support or resistance dominates",
        "Judge promise before timing",
        "Give timing only if applying yoga, dasha, or supplied timing evidence supports it",
        "End with practical action and confidence level",
    ]

    if domain == "marriage":
        return universal + [
            "Define success as commitment, union, reconciliation, family acceptance, or relationship stability depending on the question",
            "Judge 1st house/querent and 7th house/other party together",
            "Use 2nd for family integration and 11th for fulfillment",
            "Use 5th for romance only when the question is about love or affection",
            "Use 8th/12th for secrecy, fear, distance, withdrawal, or breakage",
            "Use Venus for harmony and Jupiter for mature marriage support",
            "Verify D9 only as reinforcement, not as the primary promise",
            "Clearly say whether the relationship is supported, delayed, conflicted, or weak",
        ]

    if domain == "education":
        return universal + [
            "Define success as exam result, admission, concentration, research progress, or degree completion depending on the question",
            "Judge 4th for educational foundation, 5th for intelligence/exam performance, and 9th for higher education/admission",
            "Use Mercury for learning, memory, analytics, and communication",
            "Use Jupiter for guidance, teacher support, wisdom, and higher knowledge",
            "Use Moon for concentration and emotional steadiness",
            "Inspect Saturn/Mars/Rahu pressure for delay, competition, distraction, or wrong strategy",
            "Verify D24 only as reinforcement",
            "Give practical study direction: consistency, revision, mentor, weak-topic correction, or exam strategy",
        ]

    if domain == "wealth":
        return universal + [
            "Define success as income, retained wealth, profit, funding, debt relief, or investment gain depending on the question",
            "Do not treat every wealth question as speculation",
            "Judge 2nd for retained money, 11th for gains, 5th for speculation only if relevant, 8th for debt/funding/risk, and 12th for leakage",
            "Check whether inflow actually becomes retained wealth",
            "Use Jupiter/Venus/Mercury/Moon according to the specific money question",
            "Use D4 stability only as support where supplied",
            "Clearly separate revenue, profit, savings, funding, debt, and loss",
            "Give practical financial direction: protect capital, control leakage, document commitments, avoid blind risk, or restructure",
        ]

    if domain == "child":
        return universal + [
            "Define success as conception, pregnancy stability, childbirth, progeny promise, or delay resolution depending on the question",
            "Judge 5th house and 5th lord as the main child factor",
            "Use Jupiter as child/progeny karaka",
            "Use Lagna and Moon for body readiness and emotional state",
            "Use 7th for partner cooperation and 11th for fulfillment",
            "Inspect 6th/8th/12th for medical delay, obstruction, loss anxiety, or hidden complications",
            "Verify D7 only as reinforcement",
            "Avoid certainty; advise medical guidance where physical fertility or pregnancy is involved",
        ]

    if domain == "illness":
        return universal + [
            "State clearly that astrology is supplementary and medical diagnosis/treatment comes first",
            "Define success as recovery, stabilization, correct diagnosis, treatment response, or chronic management depending on the question",
            "Judge Lagna and Lagna lord for vitality",
            "Use Sun for vitality and Moon for current condition/emotional flow",
            "Classify 6th as acute/treatable disease pressure and 8th as chronic/hidden/deeper pressure",
            "Use 12th for hospitalization, isolation, expense, or sleep/loss factors",
            "Use 4th for medicine/support and 10th for doctor/treatment direction",
            "Verify D6 only as reinforcement",
            "Clearly say whether the chart supports recovery, delay, recurrence, or urgent attention",
        ]

    if domain == "foreign":
        return universal + [
            "Define success as visa approval, short travel, relocation, foreign study, foreign job, or settlement depending on the question",
            "Judge 4th for current base/home and whether it releases the person",
            "Use 3rd for documents and short movement",
            "Use 7th for foreign/distant place, 9th for long-distance travel/fortune, and 12th for residence abroad or separation",
            "Use Rahu/Ketu for foreignness, unusual movement, or dislocation",
            "Use Saturn for paperwork, delay, procedure, and institutional blocks",
            "Verify D4/D9 only as settlement support where supplied",
            "Clearly separate permission, movement, settlement, cost, and long-term benefit",
        ]

    if domain == "job_career" and subdomain == "government":
        return universal + [
            "Define success as exam success, selection, appointment, joining, promotion, or government stability depending on the question",
            "Judge Sun/authority first but do not ignore Lagna and Moon",
            "Use 6th for competition/service/exam struggle",
            "Use 5th for exam intelligence and preparation",
            "Use 10th for state authority/career status",
            "Use 11th for appointment, selection, or fulfillment",
            "Use Saturn for discipline, delay, service structure, and bureaucracy",
            "Use Mars for competition and Jupiter for merit/guidance",
            "Verify D10 only as reinforcement",
            "Clearly say whether the path favors selection, delay, continued preparation, documentation correction, or strategy change",
        ]

    if domain == "job_career" and subdomain == "private":
        return universal + [
            "Define success as interview call, offer, salary, role fit, promotion, switch, or career growth depending on the question",
            "Judge Mercury and Lagna for capability, communication, and interview performance",
            "Use 6th for interviews, competition, and employment service",
            "Use 7th for employer, HR, contract, and negotiation",
            "Use 10th for role/status and 11th for offer/package/fulfillment",
            "Use 2nd for salary and income stability",
            "Use Venus for package/comfort and Saturn for workload/stability",
            "Use Rahu for corporate, technology, foreign company, or unconventional growth where relevant",
            "Verify D10 only as reinforcement",
            "Clearly say whether the chart supports offer, negotiation, role quality, delay, or workplace pressure",
        ]

    return universal + [
        "Judge Lagna lord, Moon, 10th action, 11th fulfillment, 4th conclusion, and 7th outside party",
        "Use hidden houses and malefic pressure for delay, blockage, loss, or correction areas",
        "Do not force timing if no supplied timing evidence supports it",
        "Give the user one clear likely outcome and one practical next step",
    ]

def first_name(name: str) -> str:
    cleaned = str(name or "Querent").strip()
    return cleaned.split()[0] if cleaned else "Querent"


def readable_datetime(value: str | None) -> str:
    if not value:
        return "the asked time"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    date = dt.strftime("%B %-d, %Y") if os.name != "nt" else dt.strftime("%B %#d, %Y")
    return f"{dt.strftime('%I:%M %p').lstrip('0')} on {date}"


def planets_by_name(chart: dict) -> dict[str, dict]:
    return {planet.get("name"): planet for planet in chart.get("planets", []) if planet.get("name")}


def sign_lord_name(sign_index: int | None) -> str:
    lords = {
        0: "Mars",
        1: "Venus",
        2: "Mercury",
        3: "Moon",
        4: "Sun",
        5: "Mercury",
        6: "Venus",
        7: "Mars",
        8: "Jupiter",
        9: "Saturn",
        10: "Saturn",
        11: "Jupiter",
    }
    return lords.get(sign_index, "Lagna lord")


def domain_lord_sequence(domain: str) -> list[str]:
    sequences = {
        "wealth": ["lagna_lord", "second_lord", "eleventh_lord", "eighth_lord", "twelfth_lord"],
        "marriage": ["lagna_lord", "seventh_lord", "second_lord", "eleventh_lord"],
        "education": ["lagna_lord", "target_lord", "fourth_lord", "ninth_lord"],
        "child": ["lagna_lord", "fifth_lord", "ninth_lord", "seventh_lord"],
        "illness": ["lagna_lord", "sixth_lord", "eighth_lord", "fourth_lord", "tenth_lord"],
        "foreign": ["lagna_lord", "fourth_lord", "seventh_lord", "ninth_lord", "twelfth_lord", "target_lord"],
        "job_career": ["lagna_lord", "sixth_lord", "tenth_lord", "eleventh_lord"],
    }
    return sequences.get(domain, ["lagna_lord", "tenth_lord", "eleventh_lord", "fourth_lord", "seventh_lord"])


def plain_item_text(item: dict | None) -> str:
    if not item:
        return ""
    label = item.get("label", "")
    text = item.get("text", "")
    if label == "D11 check":
        return ""
    if label and text:
        return f"the {label.lower()} shows that {decapitalize(text).rstrip('.')}"
    return text or label


def decapitalize(text: str) -> str:
    if not text:
        return ""
    return text[:1].lower() + text[1:]


def answer_payload(text: str, mode: str, provider: str, model: str, note: str) -> dict:
    return {
        "text": clean_text(text),
        "mode": mode,
        "provider": provider,
        "model": model,
        "note": note,
    }


def llm_unavailable_payload(message: str) -> dict:
    return {
        "text": "",
        "mode": "llm_required",
        "provider": selected_provider_label(),
        "model": "",
        "note": message,
        "error": message,
    }


def selected_provider_label() -> str:
    configured = os.getenv("PRASHNA_LLM_PROVIDER", "").strip().lower()
    if configured:
        return configured
    if api_keys_for("OPENAI"):
        return "openai"
    if api_keys_for("GEMINI") or api_keys_for("GOOGLE"):
        return "gemini"
    return "not_configured"


def clean_text(text: str) -> str:
    return textwrap.dedent(text).strip()
