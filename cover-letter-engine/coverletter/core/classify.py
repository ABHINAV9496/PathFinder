"""JD signal extraction for template selection.

Given a job dict and candidate profile, classify the job across four
dimensions used to score the hardcoded cover-letter templates:

- domain: ai / fintech / startup / enterprise / tech / general
- seniority: fresher / mid / senior
- tone: direct / story / formal (neutral JDs default to ``direct``)
- company_type: startup / corporate / nonprofit / healthcare / education /
  hospitality / government / general
- emphases: subset of {ai, devops, frontend, security, data}
"""


def _text(job: dict) -> str:
    company = (job.get("company") or "").lower()
    desc = (job.get("description") or "").lower()
    title = (job.get("title") or "").lower()
    return f"{company} {desc} {title}"


def classify_domain(job: dict) -> str:
    text = _text(job)

    ai_signals = ["machine learning", "artificial intelligence", " ai ", " ml ",
                  "deep learning", "nlp", "llm", "genai", "generative ai", "rag"]
    if any(s in text for s in ai_signals):
        return "ai"

    fintech_signals = ["fintech", "banking", "finance", "payment", "insurance",
                       "lending", "neobank", "trading"]
    if any(s in text for s in fintech_signals):
        return "fintech"

    startup_signals = ["startup", "series a", "series b", "series c", "seed",
                       "early stage", "fast-paced", "move fast", "bias for action", "scrappy"]
    if any(s in text for s in startup_signals):
        return "startup"

    enterprise_signals = ["enterprise", "fortune", "multinational", "global",
                          "consulting", "services", "fortune 500", "mnc"]
    if any(s in text for s in enterprise_signals):
        return "enterprise"

    tech_signals = ["saas", "platform", "cloud", "api", "microservice",
                    "infrastructure", "devops", "developer tools", "devtools"]
    if any(s in text for s in tech_signals):
        return "tech"

    return "general"


def classify_seniority(job: dict, profile: dict) -> str:
    title = (job.get("title") or "").lower()
    experience = profile.get("experience_years") or 0

    senior_markers = ["senior", "staff", "lead", "principal", "architect",
                      "head", "manager", "director"]
    if any(m in title for m in senior_markers):
        return "senior"

    fresher_markers = ["intern", "trainee", "fresher", "apprentice", "junior", "entry"]
    if any(m in title for m in fresher_markers) or experience < 1.5:
        return "fresher"

    return "mid"


def classify_tone(job: dict) -> str:
    text = _text(job)

    formal_signals = ["enterprise", "fortune", "multinational", "consulting",
                      "mnc", "banking", "regulated", "compliance", "insurance",
                      "governance", "corporate"]
    if any(s in text for s in formal_signals):
        return "formal"

    story_signals = ["mission", "passionate", "journey", "make a difference",
                     "impact", "solving", "curious", "purpose", "change the way"]
    if any(s in text for s in story_signals):
        return "story"

    direct_signals = ["fast-paced", "move fast", "ship", "ownership",
                      "bias for action", "hit the ground", "hands-on"]
    if any(s in text for s in direct_signals):
        return "direct"

    return "direct"


_EMPHASIS_SIGNALS = {
    "ai": ["ai", "ml", "llm", "machine learning", "deep learning", "nlp",
           "genai", "generative", "rag", "prompt", "agent"],
    "devops": ["docker", "aws", "ci/cd", "devops", "kubernetes", "deploy",
               "terraform", "cloud", "ec2", "gcp", "pipeline"],
    "frontend": ["react", "frontend", "front-end", "vue", "angular",
                 "typescript", "javascript", "ui", "ux"],
    "security": ["security", "auth", "authentication", "rbac", "oauth",
                 "compliance", "encryption", "jwt"],
    "data": ["data", "analytics", "etl", "dashboard", "sql", "database",
             "warehouse", "reporting", "excel", "power bi", "tableau"],
}


def classify_company_type(job: dict) -> str:
    """Classify the company a candidate is applying to.

    Combines the company name and JD language. Used by the profession-pack
    composer so the letter matches the organisation (e.g. formal prose for a
    bank, warm prose for a nonprofit, direct prose for a startup).
    """
    text = _text(job)

    nonprofit_signals = ["nonprofit", "ngo", "non-profit", "charity", "foundation",
                         "mission-driven", "social impact", "philanthropy", "society"]
    if any(s in text for s in nonprofit_signals):
        return "nonprofit"

    healthcare_signals = ["hospital", "clinic", "healthcare", "health care", "medical",
                          "health system", "patient", "nhs", "care home", "hospice"]
    if any(s in text for s in healthcare_signals):
        return "healthcare"

    education_signals = ["school", "university", "college", "academy", "institute",
                         "education", "campus", "school district", "teaching hospital"]
    if any(s in text for s in education_signals):
        return "education"

    hospitality_signals = ["hotel", "restaurant", "resort", "hospitality", "cafe",
                           "coffee", "travel", "tourism", "airline", "cruise"]
    if any(s in text for s in hospitality_signals):
        return "hospitality"

    government_signals = ["government", "ministry", "federal", "municipal", "public sector",
                          "state government", "agency", "administration"]
    if any(s in text for s in government_signals):
        return "government"

    startup_signals = ["startup", "series a", "series b", "series c", "seed",
                       "early stage", "fast-paced", "move fast", "bias for action",
                       "scrappy", "scale-up", "venture"]
    if any(s in text for s in startup_signals):
        return "startup"

    corporate_signals = ["enterprise", "fortune", "multinational", "global",
                         "consulting", "mnc", "corporation", "bank", "insurance",
                         "inc.", "ltd", "corp", "corporate"]
    if any(s in text for s in corporate_signals):
        return "corporate"

    return "general"


def classify_emphases(job: dict) -> set[str]:
    text = _text(job)
    emphases = set()
    for category, keywords in _EMPHASIS_SIGNALS.items():
        if any(k in text for k in keywords):
            emphases.add(category)
    return emphases


def extract(job: dict, profile: dict) -> dict:
    """Return the full feature vector used by the template selector."""
    return {
        "domain": classify_domain(job),
        "seniority": classify_seniority(job, profile),
        "tone": classify_tone(job),
        "company_type": classify_company_type(job),
        "emphases": classify_emphases(job),
    }
