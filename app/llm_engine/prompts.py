"""Prompt construction for the LLM Engine.

This module builds the system and user prompts sent to the LLM.
It assembles structured insight data from the Insight Engine into a
tight, directive prompt that enforces the RAG pattern — the AI only
narrates; it does not invent astrological rules.
"""
from __future__ import annotations

import json
import os

from app.llm_engine.context_builders import (
    advice_dimensions,
    domain_lord_sequence,
    domain_method,
    first_name,
    nakshatra_lord,
    plain_item_text,
    planets_by_name,
    question_archetype,
    ranked_evidence,
    readable_datetime,
    sign_lord_name,
)
from app.llm_engine.archetype import archetype_focus
from app.llm_engine.chart_scanners import (
    aspect_matrix,
    combustion_scan,
    exchange_scan,
    planet_strength_matrix,
    relationship_scan,
    yoga_candidate_scan,
)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# User prompt
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Context section builders
# ---------------------------------------------------------------------------

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

    supportive = [item for item in evidence if item.get("status") in {"strong", "support", "clear"}]
    caution = [item for item in evidence if item.get("status") in {"caution", "blocked"}]
    neutral = [item for item in evidence if item.get("status") == "neutral"]

    verdict = interpretation.get("verdict", {})
    confidence = interpretation.get("confidence", "")
    domain = interpretation.get("domain", "general")
    question = chart.get("question", {}).get("text", "")
    subdomain = interpretation.get("subdomain", "")
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


# ---------------------------------------------------------------------------
# Payload routing
# ---------------------------------------------------------------------------

def llm_context_payload(chart: dict, interpretation: dict) -> dict:
    if os.getenv("PRASHNA_LLM_CONTEXT_MODE", "compact").strip().lower() == "full":
        return full_llm_context_payload(chart, interpretation)
    return compact_llm_context_payload(chart, interpretation)


def compact_llm_context_payload(chart: dict, interpretation: dict) -> dict:
    from app.llm_engine.context_builders import (
        causal_summary, compact_lagna, compact_planet, max_llm_evidence_items,
        precomputed_interpretation_blueprint, probability_estimate,
        ranked_evidence, relevant_planet_names, top_items,
    )
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
        "exchanges": exchanges,
        "combustion": combustion,
        "relationships": relationships,
    }
    verdict = interpretation.get("verdict", {})
    probability = probability_estimate(interpretation, supportive, caution)
    blueprint = precomputed_interpretation_blueprint(chart, interpretation, supportive, caution, archetype, domain)
    limit = max_llm_evidence_items()

    return {
        "reading_mode": "compact_rag",
        "chart_type": chart.get("meta", {}).get("chart_type", "prashna"),
        "question": {
            "text": question,
            "name": first_name(question_meta.get("name", "")),
            "domain": domain,
            "subdomain": subdomain,
            "archetype": archetype,
            "asked_at": readable_datetime(question_meta.get("asked_at_local") or question_meta.get("asked_at_utc")),
            "place": question_meta.get("place_name", ""),
        },
        "lagna": compact_lagna(lagna),
        "rule_engine_verdict": verdict,
        "probability_estimate": probability,
        "supportive_evidence": [plain_item_text(i) for i in supportive[:limit] if plain_item_text(i)],
        "caution_evidence": [plain_item_text(i) for i in caution[:limit] if plain_item_text(i)],
        "neutral_evidence": [plain_item_text(i) for i in neutral[:limit // 2] if plain_item_text(i)],
        "key_planets": {
            name: compact_planet(p) for name, p in planets.items() if name in relevant_names
        },
        "strength_notes": [s for s in strengths if s.get("planet") in relevant_names][:8],
        "aspects": [a for a in aspects if a.get("planet_a") in relevant_names or a.get("planet_b") in relevant_names][:8],
        "yoga_candidates": yoga_candidates,
        "relationship_highlights": scans,
        "causal_summary": causal_summary(chart, interpretation, supportive, caution),
        "precomputed_interpretation_blueprint": blueprint,
        "dashas": chart.get("dashas", {}),
        "timing": interpretation.get("timing"),
        "domain_context": natural_reading_context(chart, interpretation),
    }


def full_llm_context_payload(chart: dict, interpretation: dict) -> dict:
    """Full context mode — passes richer data to the LLM when context window allows."""
    from app.llm_engine.context_builders import (
        causal_summary, compact_lagna, compact_planet, max_llm_evidence_items,
        precomputed_interpretation_blueprint, probability_estimate,
        ranked_evidence, relevant_planet_names, top_items,
    )
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
    yoga_candidates = top_items(yoga_candidate_scan(chart, archetype, domain), 15)
    verdict = interpretation.get("verdict", {})
    probability = probability_estimate(interpretation, supportive, caution)
    blueprint = precomputed_interpretation_blueprint(chart, interpretation, supportive, caution, archetype, domain)

    return {
        "reading_mode": "full_rag",
        "chart_type": chart.get("meta", {}).get("chart_type", "prashna"),
        "question": {
            "text": question,
            "name": first_name(question_meta.get("name", "")),
            "domain": domain,
            "subdomain": subdomain,
            "archetype": archetype,
            "asked_at": readable_datetime(question_meta.get("asked_at_local") or question_meta.get("asked_at_utc")),
            "place": question_meta.get("place_name", ""),
        },
        "lagna": compact_lagna(lagna),
        "planets": {name: compact_planet(p) for name, p in planets.items()},
        "rule_engine_verdict": verdict,
        "probability_estimate": probability,
        "supportive_evidence": [plain_item_text(i) for i in supportive if plain_item_text(i)],
        "caution_evidence": [plain_item_text(i) for i in caution if plain_item_text(i)],
        "neutral_evidence": [plain_item_text(i) for i in neutral if plain_item_text(i)],
        "yoga_candidates": yoga_candidates,
        "relationship_highlights": relationship_scan(chart),
        "aspects": aspect_matrix(chart),
        "exchanges": exchange_scan(chart),
        "combustion": combustion_scan(chart),
        "strength_notes": planet_strength_matrix(chart),
        "causal_summary": causal_summary(chart, interpretation, supportive, caution),
        "precomputed_interpretation_blueprint": blueprint,
        "dashas": chart.get("dashas", {}),
        "timing": interpretation.get("timing"),
        "domain_context": natural_reading_context(chart, interpretation),
    }

# ---------------------------------------------------------------------------
# Map-Reduce Prompts
# ---------------------------------------------------------------------------

def foundation_prompt(chart: dict, interpretation: dict) -> tuple[str, str]:
    sys_prompt = "You are a Vedic Astrologer analyzing the foundation (Lagna and Moon) of a Prashna chart. Be concise, practical, and highly causal."
    ctx = {
        "opening": opening_context(chart, interpretation, {}, "", ""),
        "foundation": foundation_context(chart, interpretation)
    }
    usr_prompt = f"Analyze this foundation. Focus only on the core strength, weakness, and emotional state of the querent.\n\n{json.dumps(ctx, indent=2)}"
    return sys_prompt, usr_prompt


def domain_prompt(chart: dict, interpretation: dict) -> tuple[str, str]:
    sys_prompt = "You are a Vedic Astrologer analyzing the domain outcome and specific rules of a Prashna chart. Focus on success criteria."
    ctx = {
        "karya": karya_context(chart, interpretation),
        "logic": chart_logic_context({}, [], [], []) # Stub for now
    }
    usr_prompt = f"Analyze the domain outcome. Focus on the greatest support and obstacle.\n\n{json.dumps(ctx, indent=2)}"
    return sys_prompt, usr_prompt


def timing_prompt(chart: dict, interpretation: dict) -> tuple[str, str]:
    sys_prompt = "You are a Vedic Astrologer analyzing the timing (Dashas) of a Prashna chart. Identify exactly when the event happens."
    ctx = {
        "timing": timing_context(chart)
    }
    usr_prompt = f"Analyze the timing and dashas.\n\n{json.dumps(ctx, indent=2)}"
    return sys_prompt, usr_prompt


def synthesizer_prompt(chart: dict, interpretation: dict, foundation_text: str, domain_text: str, timing_text: str) -> tuple[str, str]:
    sys_prompt = system_prompt() # Re-use the existing main system prompt for the final synthesis
    usr_prompt = (
        "You are the final synthesizer. We have run parallel analyses on the chart's foundation, domain outcome, and timing. "
        "Weave them into a cohesive 1000-word reading.\n\n"
        "### Foundation Analysis:\n"
        f"{foundation_text}\n\n"
        "### Domain Outcome Analysis:\n"
        f"{domain_text}\n\n"
        "### Timing Analysis:\n"
        f"{timing_text}\n\n"
        "Now, output the final reading using the required markdown headings."
    )
    return sys_prompt, usr_prompt
