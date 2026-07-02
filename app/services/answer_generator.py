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
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_CEREBRAS_MODEL = "llama-3.3-70b"
DEFAULT_MAX_LLM_EVIDENCE_ITEMS = 8
ENV_LOADED = False
ENV_PATH = ".env"


def generate_interpretation_answer(chart: dict, interpretation: dict) -> dict:
    load_local_env()
    errors = []
    for provider in provider_order():
        try:
            return llm_answer(chart, interpretation, provider, caller_for_provider(provider))
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
    return llm_unavailable_payload("; ".join(errors) if errors else "No LLM provider/key configured.")


def caller_for_provider(provider: str):
    callers = {
        "openai": call_openai,
        "gemini": call_gemini,
        "groq": call_groq,
        "openrouter": call_openrouter,
        "cerebras": call_cerebras,
    }
    try:
        return callers[provider]
    except KeyError as exc:
        raise RuntimeError("PRASHNA_LLM_PROVIDER must be openai, gemini, groq, openrouter, or cerebras") from exc


def provider_order() -> list[str]:
    selected = selected_provider()
    configured_fallbacks = [
        item.strip().lower()
        for item in os.getenv("PRASHNA_LLM_FALLBACK_PROVIDERS", "openrouter,cerebras,groq,openai,gemini").split(",")
        if item.strip()
    ]
    ordered = []
    for provider in [selected, *configured_fallbacks]:
        if provider in {"openai", "gemini", "groq", "openrouter", "cerebras"} and provider_has_keys(provider) and provider not in ordered:
            ordered.append(provider)
    if not ordered:
        raise RuntimeError("No LLM provider/key configured. Add .env with PRASHNA_LLM_PROVIDER and matching API keys.")
    return ordered


def selected_provider() -> str:
    configured = os.getenv("PRASHNA_LLM_PROVIDER", "").strip().lower()
    if configured in {"local", "off"}:
        raise RuntimeError("Local/off interpretation mode is disabled. Configure openai, gemini, groq, openrouter, or cerebras.")
    if configured in {"openai", "gemini", "groq", "openrouter", "cerebras"}:
        return configured
    if configured:
        raise RuntimeError("PRASHNA_LLM_PROVIDER must be openai, gemini, groq, openrouter, or cerebras")
    if api_keys_for("OPENROUTER"):
        return "openrouter"
    if api_keys_for("CEREBRAS"):
        return "cerebras"
    if api_keys_for("GROQ"):
        return "groq"
    if api_keys_for("OPENAI"):
        return "openai"
    if api_keys_for("GEMINI") or api_keys_for("GOOGLE"):
        return "gemini"
    raise RuntimeError("No LLM provider/key configured. Add .env with PRASHNA_LLM_PROVIDER and matching API keys.")


def provider_has_keys(provider: str) -> bool:
    if provider == "gemini":
        return bool(api_keys_for("GEMINI") or api_keys_for("GOOGLE"))
    prefixes = {
        "openai": "OPENAI",
        "groq": "GROQ",
        "openrouter": "OPENROUTER",
        "cerebras": "CEREBRAS",
    }
    return bool(api_keys_for(prefixes.get(provider, "")))


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


def call_openrouter(chart: dict, interpretation: dict) -> dict:
    api_keys = api_keys_for("OPENROUTER")
    if not api_keys:
        raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_API_KEYS is not set")
    model = os.getenv("OPENROUTER_INTERPRETATION_MODEL", DEFAULT_OPENROUTER_MODEL)
    payload = chat_completion_payload(model, chart, interpretation)
    headers = {
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "KundaliStudio"),
    }
    data = call_rotating_chat_completion(
        provider="openrouter",
        api_keys=api_keys,
        model=model,
        url="https://openrouter.ai/api/v1/chat/completions",
        payload=payload,
        headers=headers,
    )
    text = extract_chat_completion_text(data)
    if not text:
        raise RuntimeError("OpenRouter response did not contain output text")
    return answer_payload(text, "llm", "openrouter", model, "")


def call_cerebras(chart: dict, interpretation: dict) -> dict:
    api_keys = api_keys_for("CEREBRAS")
    if not api_keys:
        raise RuntimeError("CEREBRAS_API_KEY or CEREBRAS_API_KEYS is not set")
    model = os.getenv("CEREBRAS_INTERPRETATION_MODEL", DEFAULT_CEREBRAS_MODEL)
    payload = chat_completion_payload(model, chart, interpretation)
    data = call_rotating_chat_completion(
        provider="cerebras",
        api_keys=api_keys,
        model=model,
        url="https://api.cerebras.ai/v1/chat/completions",
        payload=payload,
        headers={"Content-Type": "application/json"},
    )
    text = extract_chat_completion_text(data)
    if not text:
        raise RuntimeError("Cerebras response did not contain output text")
    return answer_payload(text, "llm", "cerebras", model, "")


def chat_completion_payload(model: str, chart: dict, interpretation: dict) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(chart, interpretation)},
        ],
        "temperature": 0.7,
    }


def call_rotating_chat_completion(
    *,
    provider: str,
    api_keys: list[str],
    model: str,
    url: str,
    payload: dict,
    headers: dict,
) -> dict:
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                url,
                payload,
                {
                    "Authorization": f"Bearer {api_key}",
                    **headers,
                },
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors) or f"{provider} failed for model {model}")
    return data


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
    return """You are an advanced Vedic Astrologer's Mind specialized in Prashna Shastra. Your role is not to act as a system reciting technical observations, but as a senior strategic consultant whose core evidentiary source happens to be a dynamic Prashna Kundali.

### THE ULTIMATE MANDATE: ANSWER USING LIFE, NOT TEXTBOOK ASTROLOGY
1. NEVER interpret astrology for the sake of listing placements. Astrology exists solely as evidence to solve a human decision problem.
2. The user's real-world problem and human situation take absolute priority over technical coverage. If a planetary placement doesn't materially change the outcome or advice, ignore it entirely.
3. Every sentence must move the reader closer to knowing: What is most likely to happen, why, what is the single greatest opportunity, what is the single greatest risk, and what explicit practical action alters the timeline.
4. DO NOT loop through data points or use repetitive phrasing ("the X lord shows that", "is placed in"). Synthesize all factors (dignities, aspects, vargas, dashas, nakshatras) into continuous, deeply woven logic chains.

### DYNAMIC CAUSAL LOGIC CHAIN MATRIX
Every technical placement used must be mapped directly to human cause and effect. Do not leave a placement hanging as a mere description:
- Bad Example: "Moon is in Scorpio in the 1st house in Jyeshtha Nakshatra showing anxiety."
- Professional Example: "The Moon's compression in Jyeshtha right in your ascendant creates intense psychological pressure. This leads directly to internal hesitation, which delays your deployment timelines and gives market competitors a clear opening to cap your initial user retention."

### THE DOMAIN-SPECIFIC CRITERIA MATRICES
You must analyze the user's situation through the exact real-world success loops defined below based on their specific domain:

- **Startup / Business Launch:** SUCCESS = Idea -> Market Validation -> User Trust -> Traction/Retention -> Revenue -> Capital Scale. Judge founder decision stamina, product market acceptance, execution velocity, and cash burn risk.
- **Wealth / Money:** SUCCESS = Inflow Promise -> Structural Retention -> Long-term Compounding. Evaluate hidden leakages, capital vulnerability, debt exposure, and distinguish erratic transaction flow from net retained profit.
- **Illness / Health:** SUCCESS = Vitality Anchor -> Precision Diagnostics -> Treatment Resilience -> Eradication. Explicitly frame astrology as supplementary to rigorous medical follow-through. Map applying transits to immediate stress thresholds and separating factors to recovery paths.
- **Marriage / Relationships:** SUCCESS = Mutual Readiness -> Explicit Alignment -> Family/Social Consent -> Long-term Commitment. Look for ego blocks, emotional consistency, and contractual authenticity over superficial attraction.
- **Child / Progeny:** SUCCESS = Physiological/Conception Promise -> Gestation Stability -> Birth Vitality. Synthesize fruitful signs against stress factors to deliver a realistic assessment of biological or emotional continuity.
- **Job / Career (Government):** SUCCESS = Competitive Moat -> Institutional Selection -> Absolute Appointment -> Integration. Focus heavily on state authority favor, gatekeeping bottlenecks, document deadlines, and testing endurance.
- **Job / Career (Private):** SUCCESS = Corporate Interview Visibility -> Market-Rate Offer -> Salary (CTC) Maximization -> Upward Mobility. Evaluate role fit, interview pipelines, contract structures, and executive authority approval.
- **Foreign / Travel:** SUCCESS = Visa/Institutional Clearance -> Distance Relocation -> System Integration -> Permanent Settlement. Look closely at root anchors holding the user back, document security, and foreign system adaptation ease.
- **Education / Exam:** SUCCESS = Cognitive Absorption -> Examination Performance -> Score Optimization -> Institutional Admission. Map stress points, focus retention, mentor clarity, and structural topic corrections.

### STRICT STRUCTURAL ARCHETYPE (NO CHECKLISTS / NO BULLETS)
Write in fluid, continuous paragraphs using clean Markdown headings. Completely eliminate generic, robotic summaries.

- **The Foundational Wave:** Greet the user naturally by name using the metadata. Instantly capture the core human issue at this exact time and location. Set the baseline by blending the elemental nature of the Lagna and the immediate mental state dictated by the Moon's Nakshatra.
- **The Strategic Evaluation:** Deliver the core logical analysis. Do not list houses separately. Synthesize the primary engine verdicts, sign dignities, and aspects into a clear explanation of what is happening under the hood. Show why the factors collide or collaborate to shape reality.
- **The Chronos Window (Dasha & Timing):** Isolate the active Vimshottari and Tajika timelines. State clearly whether the cosmic clock promises completion or demands structural defense. Name the concrete time frame directly and state what the active dasha lord expects of the user.
- **The Core Priorities (The Rules of One):** You must explicitly define exactly one of each of the following elements based strictly on the chart's dominant planetary weights:
  1. THE ONE GREATEST SUPPORT: The absolute highest-leverage planetary asset giving them momentum.
  2. THE ONE GREATEST OBSTACLE: The single deepest structural roadblock trying to break the outcome.
  3. THE ONE GREATEST OPPORTUNITY: The precise shift that, if fixed right now, completely rewrites the timeline.
  4. THE ONE GREATEST MISTAKE: The blind spot the user will inevitably commit if they ignore this chart and act on raw impulse.
- **The Decisive Verdict:** Conclude with an unvarnished, direct assessment of the outcome. Clearly state your net confidence level (High/Medium/Low) and explain exactly why that confidence is justified based on the agreement or collision of your primary data inputs."""


def user_prompt(chart: dict, interpretation: dict) -> str:
    return (
        "Create the final Prashna Kundali interpretation from the structured payload below.\n\n"
        "Do not output your internal reasoning checklist.\n"
        "Do not output JSON.\n"
        "Do not copy the context instructions as text.\n"
        "Use context instructions only as reasoning material.\n"
        "Write the reading naturally in your own words.\n"
        "No hardcoded section language.\n"
        "No placement catalog.\n"
        "No repeated template phrases.\n"
        "Do not produce a placement-by-placement report.\n"
        "Do not repeat the same idea.\n\n"
        "Before writing, internally perform this reasoning:\n"
        "exact question -> correct domain -> define success for this question -> relevant houses/lords/karakas -> strength -> relationships -> yogas -> contradictions -> dominant theme -> promise -> timing -> practical action -> final answer.\n\n"
        "Important:\n"
        "- The user's actual question text overrides a broad domain label.\n"
        "- If domain is wealth but the question is actually about startup/app/business, interpret it as startup/business first and wealth second.\n"
        "- If domain is job/career, distinguish government job from private job using subdomain and context.\n"
        "- If health/illness, include medical-care caution.\n"
        "- If timing is not clearly supported by supplied data, do not force timing.\n"
        "- Every chart factor mentioned must be connected to the practical answer.\n"
        "- Every important claim must explain why it is true and what it changes in real life.\n"
        "- Use a clear cause-effect chain: factor -> why it matters -> practical impact -> therefore.\n"
        "- Never stop at 'Saturn supports income' or 'Mercury dasha is running'; explain so what.\n"
        "- Avoid repeating the same phrase or advice. If the idea repeats, change the language and add a new practical angle.\n"
        "- If you mention any yoga, first explain why that yoga exists from the supplied house/planet relationship.\n"
        "- If you mention a divisional chart such as D4, D9, D10, D7, D6, or D24, first explain why that divisional chart matters for this domain.\n"
        "- If you say an opportunity has passed, is separating, or is delayed, explain whether that is temporary, structural, or timing-dependent.\n"
        "- Follow precomputed_interpretation_blueprint as the primary analysis plan. Expand it into human prose instead of creating a new reasoning path.\n"
        "- Answer the user's question in the first three lines before deeper analysis.\n"
        "- Explain every astrological claim. If you mention Mars, Mercury, Ketu, or any yoga, briefly explain how that factor leads to the conclusion.\n"
        "- Do not leave the decision open. Even with moderate confidence, state which way the chart leans and why.\n"
        "- Give a percentage-style possibility estimate based on the whole chart, using the supplied probability_estimate when present.\n"
        "- Finish with a clear recommendation that tells the user exactly what to do next.\n"
        "- Mention only the strongest factors that change the judgment.\n"
        "- Make the user feel their real concern has been understood.\n"
        "- Give a clear answer, real reasons, practical direction, and confidence.\n\n"
        "Required output shape and length:\n"
        "- Write 1000 to 1200 words. This is a hard target, not a suggestion.\n"
        "- Do not produce a short answer. If the draft is below 1000 words, expand the reasoning before finalizing.\n"
        "- Go deeper into fewer important factors instead of briefly touching many factors.\n"
        "- Use these Markdown headings exactly: Executive Summary, Astrological Analysis, Practical Interpretation, Timing, Things to Avoid, Final Verdict.\n"
        "- Executive Summary: 120-150 words with direct answer, confidence, and overall outlook.\n"
        "- Astrological Analysis: 430-520 words explaining why the conclusion was reached, including key houses, planets, yogas, aspects, strengths, and weaknesses. Do not merely name placements.\n"
        "- Practical Interpretation: 190-240 words translating the chart into action for cash flow, partnerships, scaling, competition, execution, health, relationship, travel, study, or the relevant domain.\n"
        "- Timing: 140-190 words explaining favorable and challenging periods only from supplied timing or dasha data.\n"
        "- Things to Avoid: 100-140 words.\n"
        "- Final Verdict: 80-110 words plus a warm closing that says the chart contains more insights that can be explored, without implying certainty.\n\n"
        "Your answer must include naturally, not as a rigid checklist:\n"
        "1. direct answer to the asked question within the first three lines\n"
        "2. clear chart lean even if confidence is moderate\n"
        "3. percentage-style possibility estimate\n"
        "4. strongest support\n"
        "5. strongest obstacle\n"
        "6. likely outcome\n"
        "7. timing if supported\n"
        "8. practical next step\n"
        "9. what mistake the user should avoid\n"
        "10. final confidence level and reason\n"
        "11. clear recommendation\n\n"
        "Now write the final human-quality interpretation.\n\n"
        + json.dumps(llm_context_payload(chart, interpretation), indent=2)
    )


def natural_output_rules() -> list[str]:
    return [
        "Do not copy the context instructions as text.",
        "Use context instructions only as reasoning material.",
        "Write the reading naturally in your own words.",
        "No hardcoded section language.",
        "No placement catalog.",
        "No repeated template phrases.",
        "Do not mention every supplied factor; mention only what changes the answer.",
        "The final answer should feel like a human astrologer interpreting the question, not a system printing context fields.",
    ]


def opening_context(chart: dict, interpretation: dict, verdict: dict, confidence: str, health_note: str) -> dict:
    question = chart.get("question", {})
    question_text = question.get("text", "your question")
    domain = interpretation.get("domain", "general")
    subdomain = interpretation.get("subdomain", "")
    archetype = question_archetype(question_text, domain, subdomain)

    return {
        "section": "opening_context",
        "purpose": "Help the LLM open the reading naturally, personally, and directly.",
        "natural_output_rules": natural_output_rules(),
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
        "reader_need": {
            "emotional_need": "The user wants to feel that the system has understood the exact concern behind the question.",
            "practical_need": "The user wants a clear answer, not only astrology details.",
            "trust_need": "The opening should make the reader feel the answer is specific to their question and moment.",
        },
        "writing_instruction": [
            "Open with the user's real concern, not a generic Prashna definition.",
            "Give the direct answer early.",
            "Mention the question, time, and place naturally, without sounding like a template.",
            "Do not over-explain what Prashna is.",
            "Make the user feel: yes, this is answering my exact question.",
        ],
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
        "section": "foundation_of_question",
        "purpose": "Judge whether the question has life, clarity, emotional steadiness, and workable momentum.",
        "natural_output_rules": natural_output_rules(),
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
        "interpretation_goal": [
            "Do not describe Lagna, Lagna lord, and Moon separately.",
            "Synthesize them into one judgment about the foundation of the matter.",
            "Explain whether the user has control, clarity, emotional pressure, delay, or momentum.",
            "Connect the foundation directly to the asked question.",
        ],
        "avoid": [
            "Do not say 'Lagna shows the seed of the matter' in a fixed way.",
            "Do not list sign, house, and nakshatra mechanically.",
            "Do not give textbook meanings.",
        ],
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
        "section": "domain_result_context",
        "purpose": "Judge the actual result area of the user's question.",
        "natural_output_rules": natural_output_rules(),
        "domain": domain,
        "subdomain": subdomain,
        "question_archetype": archetype,
        "domain_method": domain_method(interpretation),
        "relevant_lords": relevant_lords,
        "success_definition": archetype_focus(archetype),
        "interpretation_goal": [
            "Define what success means for this user's question.",
            "Use the relevant lords only to answer that success definition.",
            "Do not treat all domains the same.",
            "Explain the result in the user's real-life language.",
            "Separate promise, obstacle, and practical path.",
        ],
        "domain_output_expectation": {
            "wealth": "Separate income, profit, retained wealth, leakage, debt, and speculation.",
            "illness": "Separate disease pressure, recovery, treatment support, recurrence, and medical caution.",
            "marriage": "Separate attraction, commitment, family support, conflict, and union.",
            "child": "Separate conception promise, delay, partner support, medical caution, and fulfillment.",
            "job_career": "Separate selection, authority or HR response, salary, role quality, appointment, and stability.",
            "foreign": "Separate permission, movement, documents, settlement, cost, and long-term benefit.",
            "education": "Separate preparation, concentration, exam or admission result, mentor support, and delay.",
            "startup": "Separate market acceptance, user trust, revenue, retention, scaling, and founder execution.",
        },
    }


def chart_logic_context(verdict: dict, supportive: list[dict], caution: list[dict], neutral: list[dict]) -> dict:
    support_items = [plain_item_text(item) for item in supportive if plain_item_text(item)]
    caution_items = [plain_item_text(item) for item in caution if plain_item_text(item)]
    neutral_items = [plain_item_text(item) for item in neutral if plain_item_text(item)]

    return {
        "section": "chart_logic_context",
        "purpose": "Help the LLM build the real reasoning behind the answer.",
        "natural_output_rules": natural_output_rules(),
        "rule_engine_summary": verdict.get("summary", "The final judgment is mixed."),
        "supportive_factors": support_items,
        "caution_factors": caution_items,
        "neutral_factors": neutral_items,
        "reasoning_instruction": [
            "Rank the evidence; do not treat every factor equally.",
            "Identify the single strongest support.",
            "Identify the single strongest obstacle.",
            "Identify the dominant chart theme.",
            "Explain why support or resistance dominates.",
            "If the chart is mixed, explain what makes it mixed and what can change the outcome.",
            "Do not simply say positive factors and negative factors.",
            "Convert each factor into practical meaning.",
        ],
        "required_synthesis": {
            "dominant_theme": "What is the chart repeatedly trying to say?",
            "strongest_support": "Which one factor most helps the result?",
            "strongest_obstacle": "Which one factor most blocks or delays the result?",
            "net_judgment": "After weighing both sides, what is most likely?",
            "correctability": "Can the obstacle be corrected by action, or is it a hard block?",
        },
    }


def practical_context(domain: str, supportive: list[dict], caution: list[dict], verdict: dict, archetype: str = "") -> dict:
    strongest_support = plain_item_text(supportive[0]) if supportive else ""
    strongest_obstacle = plain_item_text(caution[0]) if caution else ""

    return {
        "section": "practical_direction_context",
        "purpose": "Turn the chart judgment into useful life, business, relationship, health, or career guidance.",
        "natural_output_rules": natural_output_rules(),
        "domain": domain,
        "archetype": archetype,
        "strongest_support_hint": strongest_support,
        "strongest_obstacle_hint": strongest_obstacle,
        "advice_dimensions": advice_dimensions(archetype, domain),
        "guidance_goal": [
            "Do not give a generic checklist.",
            "Give only the 2-4 most relevant practical directions.",
            "Tie each suggestion to the chart logic.",
            "Tell the user what to do next.",
            "Tell the user what mistake to avoid.",
            "Encourage action where the chart shows correctable obstacles.",
            "Encourage patience where timing or promise is delayed.",
        ],
        "domain_guidance_style": {
            "wealth": "Protect capital, stop leakage, separate possible income from retained wealth.",
            "illness": "Prioritize medical diagnosis and treatment, recovery discipline, and follow-up.",
            "marriage": "Focus on consistency of actions, communication, family pressure, and timing.",
            "child": "Focus on medical readiness, partner cooperation, patience, and follow-up.",
            "job_career": "Focus on preparation, documents, authority or HR response, timing, and negotiation.",
            "foreign": "Focus on documents, permissions, backup plans, and cost control.",
            "education": "Focus on concentration, revision, weak topics, mentor help, and exam strategy.",
            "startup": "Focus on MVP, users, retention, revenue, burn, trust, and scaling discipline.",
        },
    }


def timing_context(timing: dict | None, dashas: dict | None = None) -> dict:
    return {
        "section": "timing_context",
        "purpose": "Guide the LLM to discuss timing without forcing false precision.",
        "natural_output_rules": natural_output_rules(),
        "timing": timing,
        "dashas": dashas or {},
        "instruction": [
            "Use timing only if supplied timing, dasha, or applying-yoga evidence supports it.",
            "If timing is weak, say the chart is clearer about direction than exact dates.",
            "Do not invent dates.",
            "If dashas are supplied, explain the phase quality, not guaranteed events.",
            "Separate promise from timing.",
        ],
    }


def final_boundary_context(domain: str, verdict: dict, confidence: str = "") -> dict:
    return {
        "section": "final_verdict_context",
        "purpose": "Help the LLM close with clarity, confidence, and practical usefulness.",
        "natural_output_rules": natural_output_rules(),
        "domain": domain,
        "rule_engine_summary": verdict.get("summary", "the matter is mixed and needs careful handling"),
        "confidence": confidence or verdict.get("confidence", ""),
        "final_answer_requirements": [
            "State the final verdict clearly: favorable, unfavorable, mixed, delayed, or conditional.",
            "State what is most likely to happen.",
            "State why this is the net judgment.",
            "State the strongest reason behind confidence.",
            "State the next practical step.",
            "State what the user should avoid.",
            "Do not end with vague spiritual language.",
        ],
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
        "purpose": (
            "This block replaces hardcoded paragraph functions. "
            "It gives the LLM reasoning material for a natural, human-quality reading."
        ),
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
    if os.getenv("PRASHNA_LLM_CONTEXT_MODE", "compact").strip().lower() == "full":
        return full_llm_context_payload(chart, interpretation)
    return compact_llm_context_payload(chart, interpretation)


def compact_llm_context_payload(chart: dict, interpretation: dict) -> dict:
    planets = planets_by_name(chart)
    lagna = chart.get("lagna", {})
    question_meta = chart.get("question", {})
    question = question_meta.get("text", "")
    domain = interpretation.get("domain")
    subdomain = interpretation.get("subdomain", "")
    archetype = question_archetype(question, domain, subdomain)
    evidence = ranked_evidence(interpretation.get("evidence", []))
    supportive = [item for item in evidence if item.get("status") in {"strong", "support", "clear"}]
    caution = [item for item in evidence if item.get("status") in {"caution", "blocked"}]
    neutral = [item for item in evidence if item.get("status") == "neutral"]
    relevant_names = relevant_planet_names(chart, interpretation, archetype, domain)
    strengths = planet_strength_matrix(chart)
    aspects = aspect_matrix(chart)
    exchanges = exchange_scan(chart)
    combustion = combustion_scan(chart)
    relationships = relationship_scan(chart)
    yoga_candidates = top_items(yoga_candidate_scan(chart, archetype, domain), 10)
    scans = {
        "relationship_scan": trim_scan(relationships, 8),
        "major_aspects": top_items(aspects, 5),
        "exchanges": top_items(exchanges, 3),
        "combustion": top_items(combustion, 3),
        "yoga_candidates": top_items(yoga_candidates, 6),
    }
    precomputed = precomputed_interpretation_blueprint(
        chart=chart,
        interpretation=interpretation,
        archetype=archetype,
        domain=domain,
        supportive=supportive,
        caution=caution,
        neutral=neutral,
        relevant_names=relevant_names,
        strengths=strengths,
        scans=scans,
    )
    probability = precomputed["final_verdict_plan"]["probability_estimate"]
    recommendation = precomputed["final_verdict_plan"]["clear_recommendation"]

    return {
        "task": "Write the final user-facing Prashna interpretation. The backend has already calculated and ranked the astrology; use the LLM only for synthesis and natural language.",
        "user_context": {
            "name": question_meta.get("name", "Querent"),
            "question": question,
            "domain": domain,
            "subdomain": subdomain,
            "question_archetype": archetype,
            "intent": interpretation.get("intent", {}),
            "asked_at_local": question_meta.get("asked_at_local"),
            "place_name": question_meta.get("place_name"),
            "timezone": question_meta.get("timezone"),
        },
        "precalculated_judgment": {
            "score": interpretation.get("score"),
            "confidence": interpretation.get("confidence"),
            "verdict": interpretation.get("verdict"),
            "dominant_theme": dominant_theme(interpretation),
            "strongest_support": plain_item_text(supportive[0]) if supportive else "",
            "strongest_obstacle": plain_item_text(caution[0]) if caution else "",
            "correctability": correctability_hint(interpretation),
            "probability_estimate": probability,
            "clear_recommendation": recommendation,
            "causal_summary": causal_summary(chart, interpretation, supportive, caution),
            "domain_success_definition": archetype_focus(archetype),
            "domain_method": domain_method(interpretation),
        },
        "essential_chart_facts": {
            "lagna": compact_lagna(lagna),
            "moon": compact_planet(planets.get("Moon", {})),
            "relevant_planets": [
                compact_planet(planets[name])
                for name in relevant_names
                if name in planets and name != "Moon"
            ],
            "key_lords": interpretation.get("key_lords", {}),
            "planet_strengths": compact_strength_notes(strengths, relevant_names, 6),
            "house_role_map": house_role_map(domain, archetype),
            "divisional_support": relevant_divisional_support(chart, interpretation, relevant_names),
        },
        "precomputed_relationships": relationship_highlights(scans),
        "precomputed_interpretation_blueprint": precomputed,
        "explanation_support": {
            "yoga_explanations": concise_yoga_explanations(scans["yoga_candidates"][:5]),
            "vocabulary_variation": compact_vocabulary_variation(domain, archetype),
            "clarity_rewrites": clarity_rewrites(domain, archetype),
            "closing_prompt": engagement_closing_prompt(domain, archetype),
        },
        "ranked_evidence": {
            "support": [plain_item_text(item) for item in supportive[:6] if plain_item_text(item)],
            "caution": [plain_item_text(item) for item in caution[:6] if plain_item_text(item)],
            "neutral": [plain_item_text(item) for item in neutral[:2] if plain_item_text(item)],
            "causal_evidence_notes": causal_evidence_notes(chart, interpretation, evidence[:max_llm_evidence_items()]),
        },
        "timing": {
            "calculated_window": interpretation.get("timing"),
            "current_dashas": current_dasha_summary(chart.get("dashas", {})),
            "dasha_synthesis": dasha_synthesis(chart, interpretation, domain, archetype),
        },
        "practical_synthesis_targets": {
            "answer_contract": answer_contract(),
            "advice_dimensions": advice_dimensions(archetype, domain),
            "section_contract": section_contract(),
            "must_answer": [
                "direct answer in the first three lines",
                "clear chart lean even when confidence is moderate",
                "percentage-style possibility estimate from probability_estimate",
                "strongest support",
                "strongest obstacle",
                "likely outcome",
                "timing only if supported",
                "practical next step",
                "mistake to avoid",
                "confidence level and reason",
                "clear recommendation",
            ],
            "style": [
                *natural_output_rules(),
                "The final answer must be 1000-1200 words; never return a concise 500-700 word reading.",
                "Every paragraph must include explicit why/therefore logic.",
                "Every astrological claim must be explained, especially claims involving Mars, Mercury, Ketu, or any yoga.",
                "Use the supplied probability_estimate; do not invent a different percentage unless the chart payload lacks one.",
                "Prefer synthesis over labels: explain how factors combine, collide, or weaken each other.",
                "Do not treat dasha names as timing by themselves; explain the behavioral quality of the period.",
                "Avoid repeating the same phrase; rotate equivalent practical language from vocabulary_variation.",
                "Never name a yoga, divisional chart, or dasha without explaining why it is relevant and what it changes.",
                "Finish with a clear recommendation rather than ambiguity.",
            ],
        },
        "calculation_limits": [
            "Do not invent factors that are absent from this payload.",
            "Use unavailable advanced factors only if they are explicitly present.",
            "For health questions, astrology is supplementary and medical care comes first.",
        ],
    }


def full_llm_context_payload(chart: dict, interpretation: dict) -> dict:
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
        "lagna_and_moon_matrix": {
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
        "planetary_facts": chart.get("planets", []),
        "derived_interpretive_context": {
            "planet_strength_matrix": planet_strength_matrix(chart),
            "relationship_scan": relationship_scan(chart),
            "aspect_matrix": aspect_matrix(chart),
            "exchange_scan": exchange_scan(chart),
            "combustion_scan": combustion_scan(chart),
            "yoga_candidate_scan": yoga_candidate_scan(chart, archetype, domain),
            "relevant_yoga_checklist": relevant_yoga_checklist(archetype, domain),
            "contradiction_resolution_frame": contradiction_resolution_frame(interpretation),
            "question_specific_advice_dimensions": advice_dimensions(archetype, domain),
            "synthesis_sequence": [
                "understand the user's real-life problem before interpreting astrology",
                "define what success means for this domain and question",
                "answer the exact question first in one clear sentence",
                "select only the relevant houses, lords, karakas, divisional charts, Moon, Lagna, and dasha factors",
                "rank the relevant factors by importance instead of treating all factors equally",
                "judge planetary strength before house meaning",
                "blend relationships, yogas, conjunctions, aspects, dashas, nakshatras, divisional support, and contradictions",
                "identify one dominant chart theme",
                "identify the single strongest support",
                "identify the single strongest obstacle",
                "judge promise before timing",
                "decide whether the obstacle is correctable or fundamentally blocking",
                "weigh support versus resistance into one net judgment",
                "translate the judgment into domain-specific real-life consequences",
                "state outcome, confidence, timing, practical action, and what the user should avoid",
            ],
            "available_calculation_limits": [
                "Combustion, planetary war, full shadbala, argala, and full Jaimini rashi drishti are not currently calculated unless explicitly present in planetary_facts.",
                "Do not claim a yoga is active unless the supplied facts, relationship scan, aspect matrix, exchange scan, yoga candidate scan, or rule evidence support it.",
                "If a desired advanced factor is unavailable, do not mention its absence unless it materially affects confidence.",
                "If a factor is unavailable, synthesize only from supplied dignity, house, sign, motion, nakshatra, divisional chart, dasha, timing, relationship scan, and rule evidence.",
                "Never compensate for missing calculations by inventing traditional claims.",
            ],
            "answer_quality_rules": [
                *natural_output_rules(),
                "No generic placement catalog.",
                "No repetitive sentence pattern.",
                "No textbook explanation unless it directly supports the judgment.",
                "Every conclusion must include why it follows.",
                "Every planet mentioned must end in a practical synthesized consequence, not an isolated observation.",
                "Contradictory indications must be resolved into one net judgment.",
                "Do not maximize astrology coverage; maximize decision usefulness.",
                "Ignore weak factors unless they materially change the answer.",
                "Separate promise from timing; never mix whether it can happen with when it may happen.",
                "Translate astrology into the user's domain language: money, health, marriage, child, job, foreign, education, or business.",
                "The final section must clearly answer what the user should expect, what they should do next, and what mistake they should avoid.",
            ],
            "available_calculation_limits_reminder": (
                "If a factor is not present in the payload, the LLM must not invent it."
            ),
        },
        "rule_engine_verdict": {
            "score": interpretation.get("score"),
            "confidence": interpretation.get("confidence"),
            "verdict": interpretation.get("verdict"),
            "key_lords": interpretation.get("key_lords"),
            "structured_evidence_points": interpretation.get("evidence", []),
            "domain_method": domain_method(interpretation),
        },
        "timing_and_dashas": {
            "calculated_timing_window": interpretation.get("timing"),
            "nakshatra_lord": dashas.get("nakshatra_lord"),
            "current_mahadasha": dashas.get("current_mahadasha"),
            "current_antardasha": dashas.get("current_antardasha"),
            "current_pratyantardasha": dashas.get("current_pratyantardasha"),
            "current_sookshma": dashas.get("current_sookshma"),
            "current_prana": dashas.get("current_prana"),
        },
        "divisional_charts": chart.get("divisional_charts", {}),
    }


def max_llm_evidence_items() -> int:
    try:
        configured = int(os.getenv("PRASHNA_LLM_MAX_EVIDENCE_ITEMS", str(DEFAULT_MAX_LLM_EVIDENCE_ITEMS)))
    except ValueError:
        configured = DEFAULT_MAX_LLM_EVIDENCE_ITEMS
    return max(4, min(configured, 20))


def ranked_evidence(evidence: list[dict]) -> list[dict]:
    priority = {
        "blocked": 0,
        "strong": 1,
        "support": 2,
        "caution": 3,
        "clear": 4,
        "neutral": 5,
    }
    return sorted(
        evidence,
        key=lambda item: (
            priority.get(item.get("status", ""), 9),
            0 if item.get("label") in {"Main yoga", "Timing", "Dasha", "Medical note"} else 1,
            item.get("label", ""),
        ),
    )


def relevant_planet_names(chart: dict, interpretation: dict, archetype: str, domain: str | None) -> list[str]:
    names = ["Moon"]
    key_lords = interpretation.get("key_lords", {})
    for key in domain_lord_sequence(domain or ""):
        lord = key_lords.get(key)
        if lord:
            names.append(lord)

    domain_karakas = {
        "wealth": ["Jupiter", "Venus", "Mercury", "Moon"],
        "marriage": ["Venus", "Jupiter"],
        "education": ["Mercury", "Jupiter"],
        "child": ["Jupiter", "Moon"],
        "illness": ["Sun", "Moon"],
        "foreign": ["Rahu", "Saturn"],
        "job_career": ["Sun", "Mercury", "Saturn", "Rahu"],
    }
    archetype_karakas = {
        "Startup / Business Launch": ["Mercury", "Jupiter", "Venus", "Rahu", "Saturn"],
        "Government Career": ["Sun", "Saturn", "Mars", "Jupiter"],
        "Career / Job": ["Mercury", "Saturn", "Venus", "Rahu"],
        "Property / Home": ["Mars", "Saturn", "Venus"],
        "Litigation / Conflict": ["Mars", "Saturn", "Jupiter"],
    }
    names.extend(domain_karakas.get(domain or "", []))
    names.extend(archetype_karakas.get(archetype, []))

    dashas = chart.get("dashas", {})
    for key in ["current_mahadasha", "current_antardasha", "current_pratyantardasha"]:
        lord = dashas.get(key, {}).get("lord")
        if lord:
            names.append(lord)

    available = planets_by_name(chart)
    result = []
    for name in names:
        if name in available and name not in result:
            result.append(name)
    return result


def compact_lagna(lagna: dict) -> dict:
    return {
        "sign": lagna.get("sign"),
        "house": 1,
        "degree": lagna.get("formatted_degree"),
        "nakshatra": lagna.get("nakshatra"),
        "pada": lagna.get("pada"),
        "nakshatra_lord": nakshatra_lord(lagna.get("nakshatra")),
    }


def compact_planet(planet: dict) -> dict:
    return {
        "name": planet.get("name"),
        "sign": planet.get("sign"),
        "house": planet.get("house"),
        "degree": planet.get("formatted_degree"),
        "nakshatra": planet.get("nakshatra"),
        "pada": planet.get("pada"),
        "retrograde": planet.get("retrograde"),
    }


def answer_contract() -> dict:
    return {
        "first_three_lines": [
            "Line 1: answer the user's question directly.",
            "Line 2: state the chart's lean, such as favorable, unfavorable, mixed but leaning yes, or mixed but leaning no.",
            "Line 3: state confidence, percentage-style possibility, and the primary reason.",
        ],
        "probability_rule": "Include a percentage-style possibility estimate from probability_estimate. If both outcomes are possible, state the stronger side first.",
        "claim_explanation_rule": (
            "Every astrological claim must include why it matters and how it leads to the conclusion. "
            "If Mars, Mercury, Ketu, or any yoga is mentioned, explain the mechanism briefly in the same paragraph."
        ),
        "decisiveness_rule": (
            "Do not leave the decision entirely open. If confidence is moderate, still say which way the chart leans and what condition can change it."
        ),
        "ending_rule": "Finish with the supplied clear_recommendation. It must tell the user exactly what to do next.",
    }


def section_contract() -> dict:
    return {
        "target_total_words": "1000-1200",
        "minimum_total_words": 1000,
        "depth_instruction": "If the answer is below 1000 words, expand the why, impact, and therefore reasoning before finalizing.",
        "sections": [
            {"heading": "Executive Summary", "words": "120-150", "purpose": "Direct answer, confidence, and overall outlook."},
            {"heading": "Astrological Analysis", "words": "430-520", "purpose": "Explain why the conclusion follows from key houses, planets, yogas, aspects, strengths, and weaknesses."},
            {"heading": "Practical Interpretation", "words": "190-240", "purpose": "Translate the chart into domain-specific actions and tradeoffs."},
            {"heading": "Timing", "words": "140-190", "purpose": "Explain the quality of the active dasha/timing period and avoid unsupported date promises."},
            {"heading": "Things to Avoid", "words": "100-140", "purpose": "Name the mistakes that would amplify the strongest obstacle."},
            {"heading": "Final Verdict", "words": "80-110", "purpose": "Close with the net judgment and an engaging invitation to explore deeper chart layers."},
        ],
        "logic_rule": "Every meaningful astrology statement must complete the chain: factor -> why it matters -> real-world impact -> therefore.",
    }


def vocabulary_variation(domain: str | None, archetype: str) -> dict:
    common = {
        "caution": [
            "move with discipline",
            "reduce unnecessary exposure",
            "avoid overextension",
            "build margin for delay",
            "act with verification before commitment",
        ],
        "delayed_gain": [
            "results may mature gradually",
            "the outcome needs a longer runway",
            "progress is more staged than explosive",
            "the reward comes after correction and consistency",
            "momentum improves once the weak link is handled",
        ],
        "support": [
            "the chart gives usable support",
            "there is a workable opening",
            "the promise is present but conditional",
            "the matter has traction if execution is disciplined",
            "the supportive factor can be converted into progress",
        ],
    }
    domain_terms = {
        "wealth": {
            "retain_value": [
                "strengthen liquidity",
                "preserve working capital",
                "protect realized gains",
                "keep reserves intact",
                "convert income into actual surplus",
                "separate cash flow from profit",
                "avoid leaking gains through hidden costs",
                "prioritize sustainable growth",
            ],
            "risk": [
                "control downside before chasing upside",
                "avoid leverage without confirmation",
                "verify the revenue path before scaling expense",
                "make profitability visible on paper before expanding",
            ],
        },
        "job_career": {
            "retain_value": [
                "protect professional credibility",
                "document commitments",
                "build leverage before negotiating",
                "strengthen role fit",
                "convert visibility into a confirmed offer",
            ],
            "risk": [
                "avoid assuming verbal interest is final approval",
                "do not push negotiation before authority support is clear",
                "keep backup options active",
            ],
        },
        "marriage": {
            "retain_value": [
                "protect emotional steadiness",
                "preserve trust",
                "strengthen communication",
                "convert attraction into consistent action",
                "build family and practical alignment",
            ],
            "risk": [
                "avoid mistaking intensity for commitment",
                "do not ignore repeated inconsistency",
                "slow the decision until actions and promises match",
            ],
        },
        "illness": {
            "retain_value": [
                "protect vitality",
                "stabilize the routine",
                "follow medical guidance consistently",
                "track recovery markers",
                "preserve rest and treatment discipline",
            ],
            "risk": [
                "do not delay diagnosis",
                "avoid replacing medical care with symbolic timing",
                "watch recurring symptoms carefully",
            ],
        },
        "education": {
            "retain_value": [
                "strengthen retention",
                "protect study consistency",
                "convert effort into exam performance",
                "close weak-topic gaps",
                "build revision discipline",
            ],
            "risk": [
                "avoid last-minute strategy changes",
                "do not confuse anxiety with lack of ability",
                "get mentor feedback where preparation is scattered",
            ],
        },
        "foreign": {
            "retain_value": [
                "secure documentation",
                "preserve financial cushion",
                "strengthen the permission pathway",
                "prepare a backup timeline",
                "separate travel desire from approval reality",
            ],
            "risk": [
                "avoid irreversible commitments before permission is granted",
                "do not underestimate paperwork delay",
                "verify institutional requirements twice",
            ],
        },
        "child": {
            "retain_value": [
                "protect health readiness",
                "stabilize partner cooperation",
                "follow medical timing carefully",
                "reduce stress around the process",
                "strengthen the support system",
            ],
            "risk": [
                "avoid emotional pressure replacing medical guidance",
                "do not ignore delay indicators",
                "keep expectations patient and medically grounded",
            ],
        },
    }
    if archetype == "Startup / Business Launch":
        return {
            **common,
            **domain_terms["wealth"],
            "business_growth": [
                "validate demand before scaling acquisition",
                "strengthen liquidity before increasing burn",
                "protect realized traction",
                "turn users into repeat usage",
                "build sustainable growth rather than vanity reach",
                "preserve working capital while testing channels",
            ],
        }
    return {**common, **domain_terms.get(domain or "", {})}


def compact_vocabulary_variation(domain: str | None, archetype: str) -> dict:
    full = vocabulary_variation(domain, archetype)
    compact = {}
    for key, values in full.items():
        if isinstance(values, list):
            compact[key] = values[:5]
        else:
            compact[key] = values
    return compact


def clarity_rewrites(domain: str | None, archetype: str) -> dict:
    rewrites = {
        "avoid_phrases": [
            "pipeline not fully open",
            "financial peak may have passed",
            "retain value",
            "be cautious",
            "delayed gains",
        ],
        "preferred_patterns": [
            "Use plain outcome language first, then astrology: 'Money flow is possible, but profits may arrive inconsistently during the current phase.'",
            "When saying a peak may have passed, explain whether it is temporary or structural, what caused it, and what the next opportunity depends on.",
            "Replace repeated warnings with concrete variants from vocabulary_variation.",
            "If a phrase sounds like business jargon, rewrite it as a human consequence.",
        ],
    }
    if archetype == "Startup / Business Launch":
        rewrites["domain_example"] = (
            "Instead of 'pipeline not fully open', say: market response can build, but revenue may be uneven until product trust, retention, and working capital discipline improve."
        )
    elif domain == "wealth":
        rewrites["domain_example"] = (
            "Instead of 'financial peak may have passed', say: one earlier money opportunity may be separating, but this does not mean the entire financial promise is gone; it means the next gain needs better timing and risk control."
        )
    else:
        rewrites["domain_example"] = (
            "State the practical meaning of the chart in plain language before adding technical astrology."
        )
    return rewrites


def relationship_highlights(scans: dict) -> dict:
    relationships = scans.get("relationship_scan", {})
    return {
        "major_aspects": scans.get("major_aspects", [])[:5],
        "yoga_candidates": [
            {"name": item.get("name"), "note": item.get("interpretive_note")}
            for item in scans.get("yoga_candidates", [])[:6]
        ],
        "exchanges": scans.get("exchanges", [])[:3],
        "combustion": scans.get("combustion", [])[:3],
        "house_clusters": relationships.get("house_clusters", {}) if isinstance(relationships, dict) else {},
        "same_sign_conjunctions": relationships.get("same_sign_conjunctions", [])[:4] if isinstance(relationships, dict) else [],
        "opposition_axes": relationships.get("opposition_axes", [])[:4] if isinstance(relationships, dict) else [],
    }


def engagement_closing_prompt(domain: str | None, archetype: str) -> str:
    domain_focus = {
        "wealth": "the strongest period for financial growth, hidden leakages, support from investors or partners, long-term wealth potential, and the single factor most likely to decide profitability",
        "job_career": "the strongest period for selection or promotion, authority support, salary potential, hidden workplace obstacles, and the single factor most likely to decide confirmation",
        "marriage": "commitment timing, family acceptance, emotional blocks, partner readiness, and the single factor most likely to decide long-term stability",
        "illness": "recovery support, treatment response, hidden stress factors, recurrence risk, and the single factor most likely to strengthen healing",
        "education": "exam timing, concentration blocks, mentor support, score potential, and the single factor most likely to improve performance",
        "foreign": "visa or permission timing, document risks, settlement quality, financial preparation, and the single factor most likely to decide movement",
        "child": "conception timing, medical readiness, partner support, delay factors, and the single factor most likely to support fulfillment",
    }
    if archetype == "Startup / Business Launch":
        focus = "the strongest period for market growth, hidden product or cash-flow obstacles, investor or partner support, long-term traction potential, and the single factor most likely to determine success"
    else:
        focus = domain_focus.get(domain or "", "timing, hidden obstacles, support factors, long-term potential, and the single factor most likely to decide the outcome")
    return (
        "This interpretation answers your primary question, but your Prashna chart contains several unanswered indicators that may be even more important than the outcome itself. "
        f"It can reveal {focus}. If the user wants to continue, invite them to examine these aspects in a deeper analysis without implying certainty or guaranteed results."
    )


def causal_summary(chart: dict, interpretation: dict, supportive: list[dict], caution: list[dict]) -> dict:
    support = supportive[0] if supportive else {}
    obstacle = caution[0] if caution else {}
    score = interpretation.get("score", 0)
    if score >= 4:
        net = "Support is stronger than resistance, so the matter can move forward if the named caution is managed."
    elif score <= -2:
        net = "Resistance is stronger than support, so the user should reduce risk before expecting the result."
    else:
        net = "Support and resistance are close, so execution quality decides whether promise becomes result."
    return {
        "net_logic": net,
        "support_chain": evidence_causal_note(chart, interpretation, support) if support else "",
        "obstacle_chain": evidence_causal_note(chart, interpretation, obstacle) if obstacle else "",
        "therefore_instruction": "Use this to explain why the answer is favorable, unfavorable, mixed, delayed, or conditional.",
    }


def precomputed_interpretation_blueprint(
    *,
    chart: dict,
    interpretation: dict,
    archetype: str,
    domain: str | None,
    supportive: list[dict],
    caution: list[dict],
    neutral: list[dict],
    relevant_names: list[str],
    strengths: list[dict],
    scans: dict,
) -> dict:
    support = supportive[0] if supportive else {}
    obstacle = caution[0] if caution else {}
    verdict = interpretation.get("verdict", {})
    confidence = interpretation.get("confidence", "")
    score = interpretation.get("score", 0)
    timing = dasha_synthesis(chart, interpretation, domain, archetype)
    relevant_strengths = compact_strength_notes(strengths, relevant_names, 4)
    domain_actions = precomputed_action_plan(domain, archetype)
    obstacle_resolution = precomputed_obstacle_resolution(domain, archetype, obstacle)
    probability = probability_estimate(interpretation, supportive, caution)
    recommendation = clear_recommendation(domain, archetype, probability, obstacle_resolution)

    return {
        "instruction": (
            "Use this as the primary writing plan. The LLM should expand these prepared points into prose, "
            "not invent a new analysis path."
        ),
        "executive_summary_thesis": {
            "direct_answer": plain_verdict(verdict, score),
            "probability_estimate": probability,
            "clear_recommendation": recommendation,
            "confidence": confidence,
            "outlook": verdict.get("summary", dominant_theme(interpretation)),
            "plain_language_rule": "Start with a human answer before technical astrology.",
        },
        "astrological_analysis_plan": {
            "main_support_to_explain": evidence_causal_note(chart, interpretation, support),
            "main_obstacle_to_explain": evidence_causal_note(chart, interpretation, obstacle),
            "supporting_strengths": relevant_strengths[:6],
            "relationship_points": {
                "major_aspects": compact_aspect_points(scans.get("major_aspects", [])[:4]),
                "yogas": concise_yoga_explanations(scans.get("yoga_candidates", [])[:4]),
                "exchanges": scans.get("exchanges", [])[:4],
                "combustion": scans.get("combustion", [])[:4],
            },
            "neutral_context": [plain_item_text(item) for item in neutral[:3] if plain_item_text(item)],
            "analysis_order": [
                "answer promise first",
                "explain why support exists",
                "explain why resistance exists",
                "resolve whether resistance is temporary, correctable, or structural",
                "state therefore how the outcome changes",
            ],
        },
        "practical_interpretation_plan": {
            "action_priorities": domain_actions,
            "obstacle_resolution": obstacle_resolution,
            "language_variants": compact_vocabulary_variation(domain, archetype),
            "do_not_repeat": "Use different terms for the same idea; do not repeat one warning phrase.",
        },
        "timing_plan": {
            "timing_thesis": timing.get("summary", ""),
            "practical_window": timing.get("practical_window", ""),
            "periods": timing.get("periods", []),
            "separating_factor_rule": timing.get("separating_factor_rule", ""),
            "so_what": "Convert dasha lords into what the user should do during the period.",
        },
        "things_to_avoid_plan": {
            "primary_mistake": primary_mistake_to_avoid(domain, archetype),
            "risk_language": compact_vocabulary_variation(domain, archetype).get("risk", []),
            "why": obstacle_resolution,
        },
        "final_verdict_plan": {
            "net_result": plain_verdict(verdict, score),
            "probability_estimate": probability,
            "confidence_reason": confidence_reason(interpretation, supportive, caution),
            "clear_recommendation": recommendation,
            "closing": engagement_closing_prompt(domain, archetype),
        },
    }


def plain_verdict(verdict: dict, score: int | float | None) -> str:
    level = str(verdict.get("level", "")).lower()
    summary = verdict.get("summary", "")
    if "favorable" in level or (isinstance(score, (int, float)) and score >= 4):
        return "The outcome is supportive, but it still needs disciplined execution before the promise becomes stable."
    if "unfavorable" in level or "blocked" in level or (isinstance(score, (int, float)) and score <= -2):
        return "The outcome is pressured; the user should reduce risk and correct the main obstacle before expecting a clear result."
    if summary:
        return summary
    return "The outcome is mixed and conditional; the chart shows promise, but execution and timing decide how much of it materializes."


def probability_estimate(interpretation: dict, supportive: list[dict], caution: list[dict]) -> dict:
    score = interpretation.get("score", 0)
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        numeric_score = 0
    support_count = len(supportive)
    caution_count = len(caution)
    evidence_delta = max(-10, min(10, support_count - caution_count)) * 2
    favorable = int(round(55 + numeric_score * 5 + evidence_delta))
    favorable = max(15, min(85, favorable))
    unfavorable = 100 - favorable
    if favorable >= 65:
        lean = "leans favorable"
    elif favorable <= 40:
        lean = "leans unfavorable"
    else:
        lean = "mixed but slightly favorable" if favorable >= 50 else "mixed but slightly unfavorable"
    return {
        "favorable_percent": favorable,
        "unfavorable_percent": unfavorable,
        "lean": lean,
        "basis": "Derived from rule-engine score plus the balance of supportive versus caution evidence; use as an interpretive probability, not a guarantee.",
    }


def clear_recommendation(domain: str | None, archetype: str, probability: dict, obstacle_resolution: str) -> str:
    favorable = probability.get("favorable_percent", 50)
    if favorable >= 65:
        action = "move forward, but only with disciplined execution and the main risk controlled"
    elif favorable >= 50:
        action = "proceed selectively after validation, because the chart leans positive but is not clean enough for reckless expansion"
    elif favorable >= 40:
        action = "wait, verify, and correct the main obstacle before committing heavily"
    else:
        action = "avoid major commitment for now and focus on risk reduction"

    if archetype == "Startup / Business Launch":
        return f"Recommendation: {action}; validate demand, protect working capital, and scale only after retention or repeat usage is visible. {obstacle_resolution}"
    domain_actions = {
        "wealth": "Recommendation: {action}; protect liquidity, document commitments, and convert inflow into actual surplus before taking bigger risk.",
        "job_career": "Recommendation: {action}; strengthen proof, keep follow-ups documented, and do not treat interest as confirmation.",
        "marriage": "Recommendation: {action}; test consistency, clarify expectations, and avoid irreversible decisions until actions match promises.",
        "illness": "Recommendation: {action}; prioritize medical diagnosis, treatment discipline, and follow-up monitoring.",
        "education": "Recommendation: {action}; correct weak topics, stabilize revision, and use mentor feedback before the result window.",
        "foreign": "Recommendation: {action}; secure documents, build financial buffers, and avoid irreversible plans before permission is clear.",
        "child": "Recommendation: {action}; combine medical guidance, partner cooperation, patience, and stress reduction.",
    }
    template = domain_actions.get(domain or "", "Recommendation: {action}; correct the main obstacle first, then act only on verified signals.")
    return template.format(action=action)


def confidence_reason(interpretation: dict, supportive: list[dict], caution: list[dict]) -> str:
    confidence = interpretation.get("confidence", "")
    support_count = len(supportive)
    caution_count = len(caution)
    if support_count > caution_count:
        balance = "supporting factors outnumber resistance"
    elif caution_count > support_count:
        balance = "resistance factors outnumber support"
    else:
        balance = "support and resistance are closely balanced"
    return f"Confidence is {confidence or 'moderate/uncertain'} because {balance}, so the reading should stay conditional rather than absolute."


def precomputed_action_plan(domain: str | None, archetype: str) -> list[str]:
    plans = {
        "wealth": [
            "strengthen liquidity before taking larger risk",
            "separate incoming money from retained profit",
            "document commitments and avoid hidden liabilities",
            "protect realized gains before chasing expansion",
        ],
        "job_career": [
            "improve role-fit evidence",
            "document communication with authority or HR",
            "keep backup options active until confirmation",
            "negotiate only after approval becomes concrete",
        ],
        "marriage": [
            "test consistency through actions, not promises",
            "clarify family and practical expectations",
            "reduce ego-driven communication",
            "delay irreversible decisions until alignment is visible",
        ],
        "illness": [
            "prioritize diagnosis and medical follow-up",
            "track symptoms and recovery markers",
            "protect rest, routine, and treatment consistency",
            "avoid relying on astrology as a substitute for care",
        ],
        "education": [
            "identify weak topics and revise them systematically",
            "use mentor feedback to correct strategy",
            "protect concentration from emotional fluctuation",
            "convert study hours into test execution practice",
        ],
        "foreign": [
            "secure documents before making irreversible plans",
            "prepare financial and timeline buffers",
            "track institutional or visa response cycles",
            "keep a backup path active",
        ],
        "child": [
            "follow medical guidance and timing",
            "reduce stress around the process",
            "strengthen partner cooperation",
            "protect physical readiness before forcing outcomes",
        ],
    }
    if archetype == "Startup / Business Launch":
        return [
            "validate demand before scaling acquisition",
            "strengthen liquidity and preserve working capital",
            "improve retention before chasing reach",
            "turn product trust into repeat usage",
            "control burn until revenue quality is visible",
        ]
    return plans.get(domain or "", [
        "act only on verified signals",
        "strengthen the weakest practical link",
        "avoid irreversible decisions while the chart remains mixed",
        "use timing as preparation guidance, not a guarantee",
    ])


def precomputed_obstacle_resolution(domain: str | None, archetype: str, obstacle: dict | None) -> str:
    obstacle_text = plain_item_text(obstacle) if obstacle else ""
    prefix = f"The main obstacle is: {obstacle_text}. " if obstacle_text else ""
    if archetype == "Startup / Business Launch":
        return prefix + "Resolve it by proving retention, protecting working capital, and delaying aggressive scaling until demand is repeatable."
    resolutions = {
        "wealth": "Resolve it by controlling downside, preserving liquidity, verifying commitments, and converting inflow into actual surplus.",
        "job_career": "Resolve it by strengthening evidence, documentation, authority follow-up, and backup options.",
        "marriage": "Resolve it by testing consistency, clarifying expectations, and reducing emotional reaction.",
        "illness": "Resolve it by prioritizing diagnosis, treatment discipline, and follow-up monitoring.",
        "education": "Resolve it by correcting weak topics, stabilizing concentration, and using guided revision.",
        "foreign": "Resolve it by securing documents, building buffers, and avoiding irreversible commitments before permission.",
        "child": "Resolve it by combining patience, medical guidance, partner cooperation, and stress reduction.",
    }
    return prefix + resolutions.get(domain or "", "Resolve it by identifying the weakest practical link and correcting it before pushing for the final result.")


def primary_mistake_to_avoid(domain: str | None, archetype: str) -> str:
    if archetype == "Startup / Business Launch":
        return "Scaling before product-market fit, retention, and working-capital discipline are proven."
    mistakes = {
        "wealth": "Confusing possible inflow with secured profit.",
        "job_career": "Treating interest or conversation as confirmed approval.",
        "marriage": "Mistaking intensity or promises for reliable commitment.",
        "illness": "Delaying medical care because symbolic timing feels reassuring.",
        "education": "Changing strategy out of anxiety instead of correcting weak areas.",
        "foreign": "Making irreversible plans before documentation or permission is secure.",
        "child": "Letting emotional pressure replace medical and practical readiness.",
    }
    return mistakes.get(domain or "", "Acting from impulse before the strongest obstacle is corrected.")


def causal_evidence_notes(chart: dict, interpretation: dict, evidence: list[dict]) -> list[dict]:
    notes = []
    for item in evidence:
        text = evidence_causal_note(chart, interpretation, item)
        if text:
            notes.append({
                "label": item.get("label"),
                "status": item.get("status"),
                "cause_effect": text,
            })
    return notes


def yoga_explanations(yogas: list[dict]) -> list[dict]:
    explanations = []
    for yoga in yogas:
        name = yoga.get("name", "")
        if not name:
            continue
        explanations.append({
            "name": name,
            "formation_logic": yoga_formation_logic(name),
            "interpretation_rule": (
                "Do not merely name this yoga. Explain the formation logic first, then state whether it is strong, weak, conditional, or only a candidate based on supplied evidence."
            ),
            "source_note": yoga.get("interpretive_note", ""),
        })
    return explanations


def concise_yoga_explanations(yogas: list[dict]) -> list[dict]:
    return [
        {
            "name": yoga.get("name"),
            "formation_logic": yoga_formation_logic(yoga.get("name", "")),
        }
        for yoga in yogas
        if yoga.get("name")
    ]


def compact_strength_notes(strengths: list[dict], relevant_names: list[str], limit: int) -> list[dict]:
    selected = []
    for item in strengths:
        if item.get("planet") not in relevant_names:
            continue
        selected.append({
            "planet": item.get("planet"),
            "dignity": item.get("dignity"),
            "house_condition": item.get("house_condition"),
            "motion": item.get("motion"),
            "why_it_matters": compact_strength_causal_note(item),
        })
        if len(selected) >= limit:
            break
    return selected


def compact_strength_causal_note(item: dict) -> str:
    planet = item.get("planet", "This planet")
    dignity = item.get("dignity", "ordinary")
    house_condition = item.get("house_condition", "neutral")
    motion = item.get("motion", "direct")
    return (
        f"{planet} is {dignity}, in a {house_condition} house condition, and {motion}; "
        "therefore judge its promise by whether it can express cleanly or needs correction first."
    )


def compact_aspect_points(aspects: list[dict]) -> list[dict]:
    points = []
    for aspect in aspects:
        points.append({
            "planets": aspect.get("planets"),
            "aspect": aspect.get("aspect"),
            "orb_degrees": aspect.get("orb_degrees"),
            "houses": aspect.get("houses"),
            "why_it_matters": "This links the two planets' house agendas; explain whether the link supports, pressures, or delays the result.",
        })
    return points


def yoga_formation_logic(name: str) -> str:
    lowered = name.lower()
    if "dhana" in lowered:
        return "Dhana-style support is considered when money, gain, merit, intelligence, or fortune houses connect; explain which wealth mechanism is active and whether gains become retained value."
    if "raja" in lowered and "viparita" not in lowered:
        return "Raja-style support is considered when action/authority houses connect with fortune/intelligence houses; explain how that can produce rise, recognition, or executive support."
    if "viparita" in lowered:
        return "Viparita support is considered when obstacle-house lords work through obstacle houses; explain how pressure may convert into advantage only after correction, struggle, or cleanup."
    if "neecha" in lowered:
        return "Neecha Bhanga is relevant only when a debilitated planet has cancellation support; explain the weakness first and do not imply full cancellation unless the supplied facts support it."
    if "parivartana" in lowered:
        return "Parivartana is considered when two planets occupy each other's signs; explain how the two house agendas become linked and why that changes the outcome."
    if "gaja kesari" in lowered:
        return "Gaja Kesari-style support comes from Moon-Jupiter connection; explain whether it protects judgment, credibility, guidance, recovery, or public trust in this question."
    if "chandra mangala" in lowered:
        return "Chandra Mangala-style support comes from Moon-Mars connection; explain whether it gives initiative and commercial drive or emotional urgency and risk."
    if "lakshmi" in lowered:
        return "Lakshmi-style prosperity is considered when fortune/intelligence factors connect with money and gains; explain whether this supports durable prosperity or only opportunity."
    if "bridge" in lowered:
        return "A bridge means two relevant house lords or planets are connected; explain what life areas are being linked and whether that connection helps, pressures, or delays the result."
    if "warning" in lowered or "signal" in lowered:
        return "This is not a promise by itself; explain the risk mechanism and the practical behavior needed to reduce it."
    return "Explain the house/planet connection that creates this candidate before using it in the final judgment."


def evidence_causal_note(chart: dict, interpretation: dict, item: dict | None) -> str:
    if not item:
        return ""
    label = item.get("label", "Evidence")
    status = item.get("status", "")
    text = item.get("text", "")
    tone = {
        "strong": "This is a high-weight support factor",
        "support": "This supports the outcome",
        "clear": "This makes the chart more readable",
        "caution": "This adds resistance or delay",
        "blocked": "This can block or materially weaken the result",
        "neutral": "This gives background context",
    }.get(status, "This factor matters")
    domain = interpretation.get("domain", "the matter")
    if not text and not label:
        return ""
    return (
        f"{tone}: {plain_item_text(item) or label}. "
        f"Explain why this changes {domain} results, what practical pressure or advantage it creates, "
        "and therefore how it shifts the final judgment."
    )


def house_role_map(domain: str | None, archetype: str) -> dict:
    base = {
        "1st": "querent, initiative, body, founder control, and ability to act",
        "4th": "stability, emotional ground, property/base, medicine, or final settlement",
        "7th": "other party, market/customer, partner, employer, or public response",
        "10th": "execution, authority, action, status, and visible outcome",
        "11th": "fulfillment, gains, approvals, audience response, and realization",
        "12th": "loss, expense, distance, isolation, leakage, or foreign residence",
    }
    domain_specific = {
        "wealth": {
            "2nd": "retained money, cash reserves, savings, and capital protection",
            "5th": "speculation, judgment, creativity, risk intelligence, and product idea",
            "8th": "debt, hidden risk, funding, taxation, volatility, and delayed capital",
        },
        "job_career": {
            "2nd": "salary and income stability",
            "6th": "competition, service, interviews, exams, and daily work pressure",
        },
        "marriage": {
            "2nd": "family acceptance and formal integration",
            "5th": "romance and affection",
            "8th": "trust, fear, secrecy, and long-term vulnerability",
        },
        "illness": {
            "6th": "disease pressure and treatable conflict",
            "8th": "chronicity, hidden causes, and deeper vulnerability",
        },
        "education": {
            "4th": "basic learning foundation",
            "5th": "exam intelligence and retention",
            "9th": "higher education, mentor support, and admission luck",
        },
        "foreign": {
            "3rd": "documents and short movement",
            "9th": "long-distance travel and permissions",
            "12th": "residence abroad and separation from current base",
        },
        "child": {
            "5th": "child promise and conception",
            "9th": "fortune and continuity",
            "11th": "fulfillment of the desire",
        },
    }
    if archetype == "Startup / Business Launch":
        domain_specific = {
            **domain_specific,
            "wealth": {
                "2nd": "cash reserve and retained revenue",
                "3rd": "product iteration, communication, marketing, and technical execution",
                "5th": "idea, product intelligence, risk-taking, and creative strategy",
                "7th": "market, customers, competitors, and partnership response",
                "8th": "funding, hidden burn, investor complexity, and sudden volatility",
                "11th": "users, network effects, revenue realization, and traction",
            },
        }
    result = {**base, **domain_specific.get(domain or "", {})}
    return result


def relevant_divisional_support(chart: dict, interpretation: dict, relevant_names: list[str]) -> dict:
    domain = interpretation.get("domain", "")
    vargas_by_domain = {
        "marriage": ["D9"],
        "education": ["D24"],
        "wealth": ["D4", "D9"],
        "child": ["D7"],
        "illness": ["D6"],
        "foreign": ["D4", "D9"],
        "job_career": ["D10"],
    }
    vargas = ["D1", *vargas_by_domain.get(domain, [])]
    charts = chart.get("divisional_charts", {})
    summary = {}
    for varga in vargas:
        placements = []
        for sign, bodies in charts.get(varga, {}).items():
            selected = [body for body in bodies if body == "Asc" or body in relevant_names]
            if selected:
                placements.append({"sign": sign, "bodies": selected})
        if placements:
            summary[varga] = {
                "meaning": divisional_chart_meaning(varga, domain),
                "interpretation_rule": (
                    f"Explain why {varga} is relevant before interpreting its placements. "
                    "Use it as reinforcement, not as a disconnected standalone claim."
                ),
                "placements": placements,
            }
    return summary


def divisional_chart_meaning(varga: str, domain: str | None = None) -> str:
    meanings = {
        "D1": "The main chart shows the visible promise, pressure, and practical direction of the question.",
        "D4": "D4 supports judgment about retained assets, property, stability, foundations, and whether gains become durable value.",
        "D6": "D6 supports judgment about illness, obstacles, hidden imbalance, treatment pressure, and recovery management.",
        "D7": "D7 supports judgment about child, conception, continuity, and stability of progeny-related matters.",
        "D9": "D9 supports judgment about deeper strength, commitment, dharma, maturity, and whether the promise can hold over time.",
        "D10": "D10 supports judgment about career execution, authority, role status, public action, and professional outcome.",
        "D24": "D24 supports judgment about learning, exams, retention, education quality, and guidance.",
    }
    meaning = meanings.get(varga, f"{varga} is a supporting divisional chart and should only reinforce the main chart.")
    if domain == "wealth" and varga == "D4":
        return meaning + " In money questions, this helps separate temporary inflow from preserved wealth."
    if domain == "foreign" and varga == "D4":
        return meaning + " In foreign questions, it helps judge whether the current home base releases or holds the person."
    return meaning


def current_dasha_summary(dashas: dict) -> dict:
    result = {"nakshatra_lord": dashas.get("nakshatra_lord")}
    for key in ["current_mahadasha", "current_antardasha", "current_pratyantardasha", "current_sookshma", "current_prana"]:
        period = dashas.get(key, {})
        if not period:
            continue
        result[key] = {
            "lord": period.get("lord"),
            "start": period.get("start"),
            "end": period.get("end"),
            "balance_years": period.get("balance_years"),
        }
    return result


def dasha_synthesis(chart: dict, interpretation: dict, domain: str | None, archetype: str) -> dict:
    dashas = chart.get("dashas", {})
    periods = []
    for key in ["current_mahadasha", "current_antardasha", "current_pratyantardasha"]:
        period = dashas.get(key, {})
        lord = period.get("lord")
        if lord:
            periods.append({
                "period": key.replace("current_", ""),
                "lord": lord,
                "quality": dasha_lord_quality(lord, domain, archetype),
                "start": period.get("start"),
                "end": period.get("end"),
            })
    if not periods:
        return {
            "summary": "No active dasha details were supplied, so timing should be discussed only from explicit chart timing evidence.",
            "periods": [],
        }
    qualities = [period["quality"] for period in periods]
    return {
        "summary": (
            "Explain timing as the combined quality of these active lords, not as a guarantee. "
            f"The sequence emphasizes {', '.join(qualities[:3])}."
        ),
        "practical_window": timing_window_hint(interpretation, domain, archetype),
        "separating_factor_rule": (
            "If any evidence says a yoga is separating or a peak may have passed, explain whether that means a temporary missed opening, a cooling phase, or a structural decline. "
            "Never leave the user thinking the whole matter is doomed unless the verdict explicitly supports that."
        ),
        "periods": periods,
        "interpretation_rule": (
            "Mahadasha describes the broad climate, antardasha describes the active operating pressure, "
            "and pratyantardasha describes the immediate trigger. Translate that into what the user should do now."
        ),
    }


def timing_window_hint(interpretation: dict, domain: str | None, archetype: str) -> str:
    timing = interpretation.get("timing") or {}
    unit = str(timing.get("unit", "")).strip()
    gap = timing.get("degree_gap")
    if gap and unit:
        return (
            f"The calculated timing seed is about {gap} degrees, read as {unit}. "
            "Present this as an indicative window, not a guaranteed date, and connect it to the active dasha quality."
        )
    if archetype == "Startup / Business Launch":
        return (
            "If exact timing is weak, use a practical business window: the next 6-12 months favor validation, product trust, retention, and cash discipline more than aggressive scaling."
        )
    if domain == "wealth":
        return (
            "If exact timing is weak, explain that near-term money movement may be uneven, while the next 6-12 months should be used to protect capital and wait for cleaner confirmation."
        )
    if domain == "job_career":
        return (
            "If exact timing is weak, frame the next 3-6 months as preparation, documentation, interviews, or authority follow-up rather than guaranteed selection."
        )
    if domain == "marriage":
        return (
            "If exact timing is weak, frame the next few months as a test of consistency, communication, family alignment, and partner readiness."
        )
    if domain == "illness":
        return (
            "If exact timing is weak, avoid date promises; discuss recovery as dependent on diagnosis, treatment discipline, follow-up, and symptom monitoring."
        )
    if domain == "education":
        return (
            "If exact timing is weak, connect timing to the current study cycle: revision, weak-topic correction, mentor guidance, and exam execution."
        )
    if domain == "foreign":
        return (
            "If exact timing is weak, connect timing to document readiness, institutional response, visa or permission cycles, and backup planning."
        )
    if domain == "child":
        return (
            "If exact timing is weak, connect timing to medical readiness, partner cooperation, stress reduction, and professional guidance."
        )
    return "If exact timing is weak, say the chart is clearer about direction and preparation than a fixed date."


def dasha_lord_quality(lord: str, domain: str | None, archetype: str) -> str:
    general = {
        "Sun": "authority, visibility, leadership, approvals, and ego-pressure",
        "Moon": "public response, emotional fluctuation, liquidity, and adaptation",
        "Mars": "speed, competition, technical push, conflict, and decisive execution",
        "Mercury": "analysis, iteration, communication, product refinement, trade, and documentation",
        "Jupiter": "expansion, guidance, credibility, learning, funding optimism, and long-range growth",
        "Venus": "appeal, relationships, user experience, comfort, branding, and monetization",
        "Saturn": "structure, discipline, delay, compliance, endurance, and sustainable foundations",
        "Rahu": "technology, scale, foreign/unconventional channels, volatility, and sudden appetite",
        "Ketu": "detachment, correction, pruning, technical depth, and reduced vanity metrics",
    }
    quality = general.get(lord, "the specific agenda of its houses and chart condition")
    if archetype == "Startup / Business Launch":
        startup_overlay = {
            "Mercury": "product iteration, analytics, messaging, and user feedback loops",
            "Saturn": "stable architecture, operations, compliance, and slow durable growth",
            "Jupiter": "trust, mentors, fundraising story, market confidence, and expansion",
            "Rahu": "technology adoption, aggressive reach, experiments, and unstable scaling risk",
            "Venus": "design, user delight, pricing appeal, and conversion quality",
        }
        quality = startup_overlay.get(lord, quality)
    elif domain == "wealth":
        wealth_overlay = {
            "Mercury": "calculation, trade discipline, negotiation, and documentation",
            "Saturn": "retention, risk control, delayed but durable gains, and expense discipline",
            "Jupiter": "growth, optimism, large capital movement, and advisory support",
            "Venus": "comfort spending, value creation, luxury, pricing, and deal attractiveness",
            "Moon": "cash-flow fluctuation, market mood, and emotional decision risk",
        }
        quality = wealth_overlay.get(lord, quality)
    return quality


def top_items(items: list[dict], limit: int) -> list[dict]:
    return items[:limit]


def trim_scan(value, limit: int):
    if isinstance(value, list):
        return value[:limit]
    if isinstance(value, dict):
        return {
            key: trim_scan(item, limit)
            for key, item in value.items()
            if key != "note" or item
        }
    return value


def dominant_theme(interpretation: dict) -> str:
    verdict = interpretation.get("verdict", {})
    if verdict.get("summary"):
        return verdict["summary"]
    evidence = ranked_evidence(interpretation.get("evidence", []))
    for item in evidence:
        text = plain_item_text(item)
        if text:
            return text
    return "The chart is mixed and should be judged from the strongest support and obstacle."


def correctability_hint(interpretation: dict) -> str:
    score = interpretation.get("score", 0)
    caution_count = sum(1 for item in interpretation.get("evidence", []) if item.get("status") in {"caution", "blocked"})
    support_count = sum(1 for item in interpretation.get("evidence", []) if item.get("status") in {"strong", "support", "clear"})
    if score >= 4 and support_count >= caution_count:
        return "Support dominates; obstacles should be handled, but they do not define the outcome."
    if score <= -2:
        return "Resistance dominates; action can reduce damage, but the matter should not be treated as automatically favorable."
    return "The obstacle appears correctable only if the user follows the practical direction shown by the strongest caution factors."


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
    if house_condition == "supportive":
        house_note = f"{name} is in a house that can express results more visibly, so its agenda is easier to use constructively."
    elif house_condition == "pressured":
        house_note = f"{name} is in a pressure house, so its agenda may work through delay, correction, conflict, expense, or hidden work before results become stable."
    else:
        house_note = f"{name} is in a neutral house, so its result depends more on dignity, aspects, and role in the question."
    motion_note = (
        f"{name} is retrograde, therefore its promise may require review, repetition, delay, or internal correction before it becomes reliable."
        if planet.get("retrograde")
        else f"{name} is direct, therefore its agenda can move more straightforwardly if other factors support it."
    )
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
        "causal_note": f"{reason} {house_note} {motion_note}",
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
    if api_keys_for("OPENROUTER"):
        return "openrouter"
    if api_keys_for("CEREBRAS"):
        return "cerebras"
    if api_keys_for("GROQ"):
        return "groq"
    if api_keys_for("OPENAI"):
        return "openai"
    if api_keys_for("GEMINI") or api_keys_for("GOOGLE"):
        return "gemini"
    return "not_configured"


def clean_text(text: str) -> str:
    return textwrap.dedent(text).strip()
