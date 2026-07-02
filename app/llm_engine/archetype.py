from __future__ import annotations


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
            "Socio-Cultural System Integration: How seamlessly will the user adapt to the host country's economic environment, legal frameworks, language barriers, and social customs?",
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
