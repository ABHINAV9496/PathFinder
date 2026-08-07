"""Generate profession packs as modular cover-letter block pools.

Each pack's ``cover_letters`` is keyed by seniority tier and holds three
block pools -- ``openings``, ``bodies``, ``closings``. Every block is a dict
with ``text`` (a ``{placeholder}`` template using the same keys as the
cover-letter generator context) plus selection tags: ``tone``
(direct/story/formal/any), ``company_types`` (startup/corporate/nonprofit/
healthcare/education/hospitality/government/any), ``emphases`` and
``priority`` (tie-breaker, lower wins).

The composer scores blocks against the JD feature vector and assembles a
unique letter. Each profession defines a word bank and a handful of themed
archetypes so the prose stays profession-specific while the selection stays
fully data-driven.

Run:  .venv\\Scripts\\python.exe scripts/generate_profession_packs.py
"""

from __future__ import annotations

import json
from pathlib import Path

PACKS_ROOT = Path(__file__).resolve().parent.parent / "profession_packs"

TAG_ANY = ["any"]
TAG_STARTUP = ["startup", "any"]
TAG_CORPORATE = ["corporate", "any"]
TAG_NONPROFIT = ["nonprofit", "any"]
TAG_HEALTHCARE = ["healthcare", "any"]
TAG_EDUCATION = ["education", "any"]
TAG_HOSPITALITY = ["hospitality", "any"]
TAG_GOVERNMENT = ["government", "any"]

# Placeholders available to block templates (subset of the generator context).
P = {
    "title": "{title}",
    "company": "{company}",
    "possessive": "{company_possessive}",
    "skills": "{skills}",
    "primary": "{primary}",
    "primary_name": "{primary_name}",
    "evidence": "{evidence}",
    "need": "{need}",
    "years": "{experience_years}",
    "role": "{role}",
}


def _block(text: str, tone: str = "any", company_types: list[str] | None = None,
           emphases: list[str] | None = None, priority: int = 99) -> dict:
    return {
        "text": text,
        "tone": tone,
        "company_types": company_types or TAG_ANY,
        "emphases": emphases or [],
        "priority": priority,
    }


# --------------------------------------------------------------------------
# Per-profession word banks
# --------------------------------------------------------------------------

PROFESSIONS = {
    "neutral": {
        "label": "General Professional",
        "keywords": [],
        "vocab": ["leadership", "communication", "teamwork", "problem solving",
                  "time management", "project management", "client management",
                  "presentation", "reporting", "documentation", "collaboration",
                  "quality", "compliance", "safety", "planning", "organization"],
        "words": {
            "craft": "this kind of work",
            "ownership": "owned the work",
            "impact": "results that hold up",
        },
    },
    "it_software": {
        "label": "IT / Software",
        "keywords": ["developer", "software", "engineer", "programmer", "coding",
                     "full stack", "full-stack", "frontend", "backend", "devops",
                     "python", "java", "javascript", "typescript", "react", "django",
                     "sql", "data analyst", "data scientist", "qa", "cloud", "aws"],
        "vocab": ["agile", "scrum", "code review", "git", "testing", "automation",
                  "deployment", "performance", "scalability", "security",
                  "architecture", "requirements", "product", "documentation"],
        "words": {
            "craft": "building software that works",
            "ownership": "owned the code end to end",
            "impact": "systems that hold up in production",

            "field": "software engineering",        },
    },
    "healthcare": {
        "label": "Healthcare",
        "keywords": ["nurse", "nursing", "registered nurse", "rn", "medical",
                     "patient care", "clinical", "healthcare", "hospital", "doctor",
                     "physician", "therapist", "pharmacy", "pharmacist", "caregiver",
                     "care assistant", "dental", "radiology", "paramedic", "midwife"],
        "vocab": ["patient care", "patient safety", "care plan", "clinical documentation",
                  "vitals", "medication", "charting", "compliance", "infection control",
                  "bedside", "assessment", "discharge", "ehr", "critical thinking",
                  "compassion", "team-based care"],
        "words": {
            "craft": "compassionate, clinical care",
            "ownership": "took responsibility for every patient",
            "impact": "safer, calmer care for every patient",

            "field": "healthcare",        },
    },
    "education": {
        "label": "Education",
        "keywords": ["teacher", "teaching", "educator", "education", "tutor",
                     "curriculum", "lecturer", "instructor", "professor", "lesson",
                     "training", "trainer", "school", "classroom", "special education"],
        "vocab": ["lesson planning", "curriculum development", "classroom management",
                  "student assessment", "differentiation", "learning outcomes",
                  "parent communication", "safeguarding", "engagement", "pedagogy",
                  "iep", "teaching assistant"],
        "words": {
            "craft": "helping people learn",
            "ownership": "owned the learning outcomes",
            "impact": "students who understand and grow",

            "field": "teaching and education",        },
    },
    "finance_accounting": {
        "label": "Finance / Accounting",
        "keywords": ["accountant", "accounting", "audit", "auditor", "finance",
                     "financial", "tax", "bookkeeper", "bookkeeping", "payroll",
                     "controller", "cfa", "cpa", "reconciliation", "ledger",
                     "fp&a", "budget", "forecast", "analyst", "investment"],
        "vocab": ["financial statements", "gaap", "ifrs", "reconciliation", "ledger",
                  "month-end close", "budgeting", "forecasting", "audit", "compliance",
                  "payroll", "tax", "internal controls", "reporting", "accuracy"],
        "words": {
            "craft": "accurate, compliant financial work",
            "ownership": "owned the books end to end",
            "impact": "numbers that are right the first time",

            "field": "finance and accounting",        },
    },
    "engineering": {
        "label": "Engineering (Non-Software)",
        "keywords": ["mechanical", "electrical", "civil", "structural", "chemical",
                     "engineer", "engineering", "cad", "manufacturing", "design",
                     "quality control", "maintenance", "autocad", "solidworks",
                     "production", "field engineer", "site engineer"],
        "vocab": ["safety", "quality control", "specifications", "drawings", "cad",
                  "testing", "inspection", "maintenance", "compliance", "process",
                  "efficiency", "documentation", "root cause", "prototype", "fabrication"],
        "words": {
            "craft": "building things that are safe and sound",
            "ownership": "owned the delivery of the work",
            "impact": "reliable, safe outcomes on the ground",

            "field": "engineering",        },
    },
    "marketing_sales": {
        "label": "Marketing / Sales",
        "keywords": ["marketing", "sales", "salesperson", "account manager", "crm",
                     "social media", "content", "seo", "lead generation", "outbound",
                     "business development", "brand", "advertising", "campaign",
                     "copywriting", "growth", "cold calling", "territory"],
        "vocab": ["lead generation", "conversion", "pipeline", "revenue", "crm",
                  "campaigns", "brand awareness", "content strategy", "funnels",
                  "negotiation", "forecasting", "retention", "upselling", "prospecting",
                  "messaging"],
        "words": {
            "craft": "bringing the right message to the right person",
            "ownership": "owned the pipeline from first touch to close",
            "impact": "growth that is measurable",

            "field": "marketing and sales",        },
    },
    "hospitality": {
        "label": "Hospitality / Food Service",
        "keywords": ["hotel", "restaurant", "hospitality", "chef", "waiter", "server",
                     "bartender", "barista", "front desk", "housekeeping", "reservation",
                     "catering", "food service", "reception", "event", "guest"],
        "vocab": ["guest experience", "service standards", "table service", "upselling",
                  "food safety", "hygiene", "reservations", "housekeeping", "inventory",
                  "shifts", "teamwork", "complaints", "welcome", "atmosphere"],
        "words": {
            "craft": "service that feels effortless",
            "ownership": "owned every guest interaction",
            "impact": "guests who come back",

            "field": "hospitality",        },
    },
    "trades_construction": {
        "label": "Trades / Construction",
        "keywords": ["electrician", "electrical", "plumber", "plumbing", "carpenter",
                     "carpentry", "welder", "welding", "hvac", "mechanic", "mechanic",
                     "machinist", "construction", "foreman", "technician", "mason",
                     "painter", "roofer", "site", "tool"],
        "vocab": ["safety", "blueprints", "codes", "inspection", "tools", "measurements",
                  "installations", "repairs", "maintenance", "quality of work", "deadlines",
                  "site safety", "hand tools", "power tools", "materials"],
        "words": {
            "craft": "work that is done right and done safe",
            "ownership": "owned the job from start to finish",
            "impact": "work that stands up to inspection",

            "field": "the trades",        },
    },
    "design_creative": {
        "label": "Design / Creative",
        "keywords": ["designer", "design", "ux", "ui", "graphic", "illustrator",
                     "illustration", "photographer", "photography", "animation",
                     "video", "art", "creative", "portfolio", "branding", "motion",
                     "figma", "photoshop", "typography", "storyboard"],
        "vocab": ["concept", "layout", "typography", "color", "brand identity",
                  "user research", "wireframes", "prototyping", "usability", "storytelling",
                  "feedback", "art direction", "visual hierarchy", "motion", "storyboard"],
        "words": {
            "craft": "work that communicates",
            "ownership": "owned the concept from brief to final",
            "impact": "work that makes people stop and look",

            "field": "design and creative work",        },
    },
    "legal": {
        "label": "Legal",
        "keywords": ["lawyer", "attorney", "paralegal", "legal", "law", "litigation",
                     "contract", "compliance", "counsel", "barrister", "solicitor",
                     "legal assistant", "corporate law", "labor law", "intellectual property",
                     "drafting", "case"],
        "vocab": ["legal research", "contract drafting", "due diligence", "litigation",
                  "compliance", "case management", "statutes", "briefs", "negotiation",
                  "confidentiality", "risk", "counsel", "mediation", "filings", "evidence"],
        "words": {
            "craft": "precise, rigorous legal work",
            "ownership": "owned the case file end to end",
            "impact": "sound decisions that hold up",

            "field": "the law",        },
    },
    "admin_operations": {
        "label": "Administration / Operations",
        "keywords": ["administrative", "administrator", "executive assistant", "office",
                     "operations", "coordinator", "scheduler", "data entry", "receptionist",
                     "clerk", "logistics", "procurement", "scheduling", "inventory",
                     "dispatch", "support"],
        "vocab": ["scheduling", "coordination", "documentation", "inventory", "procurement",
                  "reporting", "databases", "communication", "prioritization", "workflow",
                  "processes", "office management", "records", "correspondence", "deadlines"],
        "words": {
            "craft": "the details that keep things running",
            "ownership": "owned the coordination end to end",
            "impact": "smoother operations for everyone",

            "field": "operations and administration",        },
    },
    "science_research": {
        "label": "Science / Research",
        "keywords": ["scientist", "research", "laboratory", "lab", "data analysis",
                     "experiment", "biotech", "chemistry", "biology", "physics",
                     "genomics", "clinical research", "methodology", "publication",
                     "assay", "research assistant", "researcher"],
        "vocab": ["experimental design", "data analysis", "protocols", "documentation",
                  "reproducibility", "instrumentation", "literature review", "hypothesis",
                  "peer review", "statistics", "safety", "ethics", "publication",
                  "collaboration", "validation"],
        "words": {
            "craft": "rigorous, reproducible science",
            "ownership": "owned the experiment from hypothesis to write-up",
            "impact": "findings you can trust",

            "field": "science and research",        },
    },
    "retail_customer_service": {
        "label": "Retail / Customer Service",
        "keywords": ["retail", "sales associate", "cashier", "customer service",
                     "customer support", "call center", "representative", "stock",
                     "store", "checkout", "merchandising", "client", "complaint",
                     "escalation", "helpdesk", "support"],
        "vocab": ["customer satisfaction", "complaints", "escalation", "product knowledge",
                  "cash handling", "merchandising", "up-selling", "loyalty", "resolution",
                  "first contact", "ticketing", "empathy", "patience", "communication",
                  "speed"],
        "words": {
            "craft": "service that fixes things for people",
            "ownership": "owned the customer's problem to resolution",
            "impact": "customers who feel heard",

            "field": "retail and customer service",        },
    },
    "hr_people": {
        "label": "HR / People",
        "keywords": ["human resources", "hr", "recruiter", "recruitment", "hiring",
                     "talent", "onboarding", "payroll", "employee relations", "benefits",
                     "people operations", "talent acquisition", "hr generalist", "compensation",
                     "performance", "learning and development", "hrbp"],
        "vocab": ["recruitment", "onboarding", "employee relations", "engagement",
                  "compliance", "payroll", "benefits", "performance management", "culture",
                  "retention", "confidentiality", "policies", "training", "diversity",
                  "talent acquisition"],
        "words": {
            "craft": "building workplaces where people do their best work",
            "ownership": "owned the hire from sourcing to offer",
            "impact": "teams that are happier and stay longer",

            "field": "human resources",        },
    },
}


# --------------------------------------------------------------------------
# Shared archetypes parameterized by profession word banks
# --------------------------------------------------------------------------

def _openings(words: dict, field: str) -> list[dict]:
    craft, ownership, impact = words["craft"], words["ownership"], words["impact"]
    field_word = words.get("field") or field.lower()
    return [
        _block(
            f"I am applying for the {{title}} role at {{company}} because it matches "
            f"the work I care about: {craft}. I have spent my recent efforts on "
            f"{{primary}}, where I {ownership}.{{evidence}}",
            tone="direct",
        ),
        _block(
            f"The {{title}} position at {{company}} caught my attention because it asks "
            f"for exactly the strengths I bring: {{skills}}. My most relevant experience "
            f"is {{primary}}, where I {ownership}.{{evidence}}",
            tone="direct",
            company_types=TAG_CORPORATE,
        ),
        _block(
            f"I got into {field_word} because I like taking a task and doing it properly, "
            f"end to end. {{primary}} is that kind of work, and the {{title}} role at "
            f"{{company}} looks like the same kind of work at a bigger scale.{{evidence}}",
            tone="story",
        ),
        _block(
            "What pulls me toward {company} is that the {title} role is about "
            "producing something real, not maintaining something stale. That matches "
            "how I work: I took on {primary} because I wanted to own a problem from "
            "start to finish, using {skills}.{evidence}",
            tone="story",
            company_types=TAG_STARTUP,
        ),
        _block(
            "I am writing to express my interest in the {title} role at {company}. "
            "I have been building toward exactly this kind of work, and the requirements "
            "in the job description align closely with what I have learned and delivered "
            "so far.{evidence}",
            tone="formal",
            company_types=TAG_CORPORATE,
        ),
        _block(
            f"{{company}} has a clear sense of what it stands for, and that matters to me. "
            f"The {{title}} role fits the work I already do -- {craft} -- and I would be "
            f"proud to bring my experience with {{primary}} to {{possessive}} team.{{evidence}}",
            tone="story",
            company_types=TAG_NONPROFIT,
        ),
        _block(
            f"I am excited to apply for the {{title}} opening at {{company}}. My strongest "
            f"areas are {{skills}}, and I have applied them hands-on to {{primary}} with the "
            f"goal of {impact}.{{evidence}}",
            tone="direct",
            company_types=TAG_STARTUP,
        ),
        _block(
            f"{{primary}} taught me what good work looks like: {craft}. The {{title}} role "
            f"at {{company}} describes the same standard, and I would welcome the chance to "
            f"meet it on a larger scale.{{evidence}}",
            tone="story",
            company_types=TAG_HEALTHCARE,
        ),
    ]


def _bodies(words: dict, tier: str) -> list[dict]:
    craft, ownership, impact = words["craft"], words["ownership"], words["impact"]
    if tier == "fresher":
        return [
            _block(
                "My strongest areas are {skills}, and I have used them on {primary}. "
                "That experience taught me to move fast, ask good questions, and take "
                "ownership of what I produce.",
                tone="direct",
            ),
            _block(
                f"I am early in my career, but I know I can be productive from day one. "
                f"I have built {{primary}} using {{skills}}, and I care about {craft} -- "
                f"not just getting the task done, but doing it properly.",
                tone="direct",
            ),
            _block(
                "Across {primary} I have used {skills}, and I have learned to move "
                "fast, ask questions, and own what I deliver. I know I have more to learn, "
                "but I also know I can contribute from the start.",
                tone="story",
            ),
            _block(
                "I treat feedback as part of the work. On {primary} I listened, revised, "
                "and shipped a result I am proud of, using {skills} to make it better "
                "with every round.",
                tone="story",
                company_types=TAG_NONPROFIT,
            ),
            _block(
                f"I am committed to {craft}. My training and my work on {{primary}} have "
                f"given me {{skills}}, and I apply them with care and consistency.",
                tone="formal",
            ),
            _block(
                f"One thing I can promise: I bring {{skills}} and a genuine interest in "
                f"{impact}. {{primary}} shows the standard I hold myself to.",
                tone="direct",
                company_types=TAG_STARTUP,
            ),
        ]
    if tier == "senior":
        return [
            _block(
                "I bring {skills}, and I take responsibility for the full lifecycle: "
                "planning, delivery, quality, and the results that go out. {depth}",
                tone="direct",
            ),
            _block(
                f"My most recent work, {{primary}}, is a good example: I {ownership} and "
                f"stood behind the outcome.{{evidence}}",
                tone="formal",
            ),
            _block(
                f"Beyond the craft, I bring judgement: knowing what to build, how to "
                f"sequence it, and how to keep quality high while moving fast. I have "
                f"delivered {{primary}} with {{skills}}, and I hold myself to {impact}.",
                tone="direct",
                company_types=TAG_CORPORATE,
            ),
            _block(
                f"What I am proudest of is not the titles but the outcomes: {impact}. "
                f"With {{primary}} I {ownership}, and the result has stayed strong "
                f"because the fundamentals were right.",
                tone="story",
                company_types=TAG_NONPROFIT,
            ),
            _block(
                f"I also invest in the people around me -- mentoring, clear expectations, "
                f"and the kind of process that lets a team deliver {impact} without "
                f"burning out.",
                tone="formal",
                company_types=TAG_CORPORATE,
            ),
            _block(
                f"I have delivered {{primary}} using {{skills}}, and I have done it in "
                f"environments where {craft} was the standard, not the exception. I bring "
                f"that standard with me.",
                tone="direct",
                company_types=TAG_STARTUP,
            ),
            _block(
                f"{impact} is the metric I have always aimed at. I have led {{primary}} "
                f"and set the processes that made it reliable, and I would bring the same "
                f"rigour to the {{title}} role.",
                tone="formal",
                company_types=TAG_GOVERNMENT,
            ),
        ]
    return [
        _block(
            "My core strengths are {skills}. I care about doing the job properly, "
            "meeting expectations, and producing work that holds up under review.",
            tone="direct",
        ),
        _block(
            "Most recently I delivered {primary}, where I took responsibility for the "
            "full scope of the work and saw it through from planning to completion. "
            "{evidence}",
            tone="direct",
        ),
        _block(
            "I bring {skills}, and I approach each piece of work the same way -- "
            "understand the goal, plan carefully, deliver something solid, and follow "
            "through until it is finished properly.",
            tone="story",
        ),
        _block(
            f"I work systematically, document thoroughly, and take ownership of quality "
            f"and timelines. On {{primary}} I {ownership}, and it came together because "
            f"the fundamentals were right.",
            tone="formal",
        ),
        _block(
            f"I care about {craft}. With {{primary}} I aimed for {impact}, and the "
            f"result held up because I did not cut corners.",
            tone="story",
            company_types=TAG_NONPROFIT,
        ),
        _block(
            "In {primary} I had to balance speed with quality. I brought {skills} "
            "to that balance, and the outcome was work I could stand behind.",
            tone="direct",
            company_types=TAG_STARTUP,
        ),
        _block(
            f"My experience spans {{primary}} and the steady rhythm of delivering "
            f"{impact} again and again -- exactly what the {{title}} role at {{company}} "
            f"describes.",
            tone="formal",
            company_types=TAG_CORPORATE,
        ),
    ]


def _closings(words: dict) -> list[dict]:
    impact = words["impact"]
    return [
        _block(
            "I am genuinely interested in {need} and would love to discuss how I can "
            "contribute. Thank you for your consideration.",
            tone="direct",
        ),
        _block(
            "I would welcome the chance to contribute to {need} and to grow with your "
            "team. I am happy to provide references or a work sample at any time.",
            tone="direct",
        ),
        _block(
            f"I would love to help deliver {impact} at {{company}}. I am happy to talk "
            f"about how my experience can support {{need}}.",
            tone="story",
        ),
        _block(
            "I am eager to bring my experience to {company} and would welcome a "
            "conversation about how I can contribute to {need}.",
            tone="formal",
        ),
        _block(
            "Thank you for considering my application. I would be delighted to discuss "
            "how my skills align with {need} and with the work your team does.",
            tone="formal",
            company_types=TAG_CORPORATE,
        ),
        _block(
            f"I would be proud to support {{need}} and to help build {impact} at "
            f"{{company}}. I look forward to hearing from you.",
            tone="story",
            company_types=TAG_NONPROFIT,
        ),
        _block(
            "{need} is exactly the kind of challenge I want to take on. I would welcome "
            "the chance to show what I can do at {company}.",
            tone="direct",
            company_types=TAG_STARTUP,
        ),
    ]


# --------------------------------------------------------------------------
# Profession-specific custom blocks (merged into the shared pools)
# --------------------------------------------------------------------------

# Each entry: {tier: {"openings": [...], "bodies": [...], "closings": [...]}}
CUSTOM = {
    "it_software": {
        "mid": {
            "bodies": [
                _block(
                    "I work the whole loop -- design, build, test, deploy -- and I treat "
                    "maintainability as a first-class requirement. With {primary} I "
                    "used {skills}, and it is still shipping because it was built to be "
                    "maintained.",
                    tone="direct",
                    company_types=TAG_STARTUP,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have been the person who owns availability. I have driven "
                    "{primary} through {skills}, and I have learned that the hard part "
                    "of engineering is the discipline around the code -- testing, "
                    "deployment, and owning incidents when they happen. {depth}",
                    tone="direct",
                    company_types=TAG_STARTUP,
                ),
            ],
        },
    },
    "healthcare": {
        "mid": {
            "bodies": [
                _block(
                    "I bring clinical judgement and calm under pressure. On {primary} I "
                    "handled {skills} while keeping the patient at the center -- "
                    "listening first, then acting. That is the standard I hold myself to.",
                    tone="story",
                    company_types=TAG_HEALTHCARE,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have combined bedside skill with team leadership: on {primary} I "
                    "coordinated {skills} across a full care team and upheld the "
                    "standards that keep patients safe. {depth}",
                    tone="formal",
                    company_types=TAG_HEALTHCARE,
                ),
            ],
        },
    },
    "education": {
        "fresher": {
            "bodies": [
                _block(
                    "Teaching is a craft I take seriously. During {primary} I planned "
                    "lessons, adapted to each learner, and used {skills} to make sure "
                    "no one was left behind.",
                    tone="story",
                    company_types=TAG_EDUCATION,
                ),
            ],
        },
        "mid": {
            "bodies": [
                _block(
                    "I plan with clear learning outcomes and adjust in the moment. With "
                    "{primary} I used {skills} to reach different kinds of learners, "
                    "and I kept families and colleagues in the loop the whole way.",
                    tone="story",
                    company_types=TAG_EDUCATION,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have led curriculum and mentored other educators. With {primary} "
                    "I raised the standard of teaching around me using {skills}, and "
                    "the measurable result was better learning outcomes. {depth}",
                    tone="formal",
                    company_types=TAG_EDUCATION,
                ),
            ],
        },
    },
    "finance_accounting": {
        "mid": {
            "bodies": [
                _block(
                    "Accuracy is not a goal, it is the baseline. On {primary} I owned "
                    "the books end to end with {skills}, and the numbers were right "
                    "the first time -- that is what I deliver consistently.",
                    tone="formal",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have owned month-end close, audit readiness, and internal "
                    "controls. With {primary} I used {skills} to keep the books "
                    "clean and the audit clean. {depth}",
                    tone="formal",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
    },
    "engineering": {
        "fresher": {
            "bodies": [
                _block(
                    "I was trained to respect the numbers: measurements, tolerances, and "
                    "safety margins. On {primary} I used {skills} and learned that "
                    "good engineering is mostly discipline.",
                    tone="formal",
                ),
            ],
        },
        "mid": {
            "bodies": [
                _block(
                    "I own my work from drawing to handover. With {primary} I applied "
                    "{skills} on site and in the office, and I made sure the finished "
                    "work matched the specification -- no surprises.",
                    tone="direct",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have run projects end to end and kept people safe doing it. With "
                    "{primary} I drove {skills} to deliver on spec, on schedule, "
                    "and with a safety record I am proud of. {depth}",
                    tone="formal",
                ),
            ],
        },
    },
    "marketing_sales": {
        "mid": {
            "bodies": [
                _block(
                    "I am measured by results: pipeline, conversion, revenue. On "
                    "{primary} I ran {skills} and could show exactly what moved "
                    "the numbers -- and what did not.",
                    tone="direct",
                    company_types=TAG_STARTUP,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have built teams and territories. With {primary} I used "
                    "{skills} to hit the number consistently and to build the systems "
                    "that made the number repeatable. {depth}",
                    tone="direct",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
    },
    "hospitality": {
        "fresher": {
            "bodies": [
                _block(
                    "I bring warmth and attention to detail. During {primary} I used "
                    "{skills} to make every guest feel looked after, and I learned "
                    "that the small things are the big things.",
                    tone="story",
                    company_types=TAG_HOSPITALITY,
                ),
            ],
        },
        "mid": {
            "bodies": [
                _block(
                    "I have run busy shifts and kept service calm through them. With "
                    "{primary} I used {skills} to keep the standard high even when "
                    "the floor was full.",
                    tone="story",
                    company_types=TAG_HOSPITALITY,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have led front-of-house and back-of-house, set the service "
                    "standard, and built teams that deliver it. With {primary} I used "
                    "{skills} and the result was guests who came back. {depth}",
                    tone="story",
                    company_types=TAG_HOSPITALITY,
                ),
            ],
        },
    },
    "trades_construction": {
        "fresher": {
            "bodies": [
                _block(
                    "I was raised on the rule that you do the job right or not at all. "
                    "On {primary} I used {skills} and learned to read the blueprints, "
                    "respect the code, and leave the site cleaner than I found it.",
                    tone="direct",
                ),
            ],
        },
        "mid": {
            "bodies": [
                _block(
                    "I take pride in work that passes inspection the first time. With "
                    "{primary} I applied {skills} on time and on budget, and the "
                    "quality spoke for itself.",
                    tone="direct",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have run crews and kept them safe. With {primary} I managed "
                    "{skills} on site -- quality, schedule, and the safety of every "
                    "person under my supervision. {depth}",
                    tone="formal",
                ),
            ],
        },
    },
    "design_creative": {
        "fresher": {
            "bodies": [
                _block(
                    "I think in terms of what an audience feels, not just what it sees. "
                    "During {primary} I used {skills} and learned to take feedback "
                    "and turn it into better work.",
                    tone="story",
                    company_types=TAG_STARTUP,
                ),
            ],
        },
        "mid": {
            "bodies": [
                _block(
                    "I have shipped work that people remember. With {primary} I used "
                    "{skills} to solve a real problem, and the design held up because "
                    "it was built on a strong concept, not just a strong look.",
                    tone="story",
                    company_types=TAG_STARTUP,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have owned the creative vision and led others to execute it. With "
                    "{primary} I directed {skills} from concept to final, and the "
                    "work won because every detail was intentional. {depth}",
                    tone="direct",
                ),
            ],
        },
    },
    "legal": {
        "mid": {
            "bodies": [
                _block(
                    "I have drafted, negotiated, and reviewed the documents that keep "
                    "companies safe. With {primary} I used {skills} and learned that "
                    "precision is what protects the client.",
                    tone="formal",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have advised on matters where the cost of error was high. With "
                    "{primary} I applied {skills} to get the right outcome and "
                    "manage the risk along the way. {depth}",
                    tone="formal",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
    },
    "admin_operations": {
        "mid": {
            "bodies": [
                _block(
                    "I am the person who makes the calendar, the inventory, and the "
                    "paperwork line up. With {primary} I used {skills} and the team "
                    "around me simply worked better.",
                    tone="story",
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have built the processes that make an office run without drama. "
                    "With {primary} I used {skills} to cut friction, keep records "
                    "clean, and give everyone clarity. {depth}",
                    tone="direct",
                ),
            ],
        },
    },
    "science_research": {
        "fresher": {
            "bodies": [
                _block(
                    "I love the part of research that is not glamorous: the controls, the "
                    "repeats, the careful notes. On {primary} I used {skills} and "
                    "learned that reproducibility is what makes results real.",
                    tone="formal",
                ),
            ],
        },
        "mid": {
            "bodies": [
                _block(
                    "I design experiments so the answer is trustworthy. With {primary} "
                    "I used {skills} to control the variables, document everything, "
                    "and report what the data actually said.",
                    tone="formal",
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have led research from hypothesis to publication. With {primary} "
                    "I directed {skills} across the project and held the work to a "
                    "standard of rigour others could rely on. {depth}",
                    tone="formal",
                ),
            ],
        },
    },
    "retail_customer_service": {
        "fresher": {
            "bodies": [
                _block(
                    "I am patient, quick, and genuinely like helping people. During "
                    "{primary} I used {skills} to turn a problem into a resolved "
                    "customer, and I enjoyed every one of them.",
                    tone="story",
                    company_types=TAG_NONPROFIT,
                ),
            ],
        },
        "mid": {
            "bodies": [
                _block(
                    "I have handled the hard calls and the long queues. With {primary} "
                    "I used {skills} to keep customers satisfied even when the answer "
                    "was no -- that is the skill people remember.",
                    tone="direct",
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have led support teams and set the service bar. With {primary} "
                    "I built {skills} into every agent and measured the result in "
                    "retention and repeat business. {depth}",
                    tone="direct",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
    },
    "hr_people": {
        "mid": {
            "bodies": [
                _block(
                    "I have owned the hire end to end -- sourcing, screening, offer, "
                    "onboarding -- and I have done it with {skills} and discretion. "
                    "People trust me with their careers and their problems.",
                    tone="story",
                ),
            ],
        },
        "senior": {
            "bodies": [
                _block(
                    "I have built people programs that move engagement and retention. "
                    "With {primary} I used {skills} to align hiring, development, "
                    "and culture with what the business actually needed. {depth}",
                    tone="formal",
                    company_types=TAG_CORPORATE,
                ),
            ],
        },
    },
}


# --------------------------------------------------------------------------
# Tiered section assembler
# --------------------------------------------------------------------------

def _tier_sections(words: dict, field: str, tier: str) -> dict:
    return {
        "openings": _openings(words, field),
        "bodies": _bodies(words, tier),
        "closings": _closings(words),
    }


def build_pack(pack_id: str, data: dict) -> dict:
    words = data["words"]
    field = data["label"]
    sections = {
        "fresher": _tier_sections(words, field, "fresher"),
        "mid": _tier_sections(words, field, "mid"),
        "senior": _tier_sections(words, field, "senior"),
    }
    for tier, custom_sections in (CUSTOM.get(pack_id) or {}).items():
        for section, blocks in custom_sections.items():
            sections[tier][section] = list(sections[tier][section]) + list(blocks)
    return {
        "id": pack_id,
        "label": data["label"],
        "detect_keywords": data["keywords"],
        "vocabulary": data["vocab"],
        "cover_letters": sections,
    }


def main() -> None:
    PACKS_ROOT.mkdir(exist_ok=True)
    for pack_id, data in PROFESSIONS.items():
        pack = build_pack(pack_id, data)
        path = PACKS_ROOT / f"{pack_id}.json"
        path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
        counts = {
            tier: {section: len(blocks) for section, blocks in sections.items()}
            for tier, sections in pack["cover_letters"].items()
        }
        print(f"{pack_id}: {counts}")


if __name__ == "__main__":
    main()
