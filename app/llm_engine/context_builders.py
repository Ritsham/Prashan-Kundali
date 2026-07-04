from __future__ import annotations

from app.llm_engine.archetype import question_archetype, archetype_focus
from app.llm_engine.chart_scanners import (
    planet_strength_matrix,
    sign_lord_name,
    exchange_scan,
    planets_by_name,
    angular_gap,
    aspect_synthesis_hint,
    planets_connected,
    add_if_present,
)


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
    import os
    from datetime import datetime
    if not value:
        return "the asked time"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    date = dt.strftime("%B %-d, %Y") if os.name != "nt" else dt.strftime("%B %#d, %Y")
    return f"{dt.strftime('%I:%M %p').lstrip('0')} on {date}"


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
