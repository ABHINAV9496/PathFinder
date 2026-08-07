import re
import unicodedata
from dataclasses import dataclass, field
from app.config import SKILL_WEIGHTS, SKILL_ALIASES, SKILL_CATEGORIES
from app.core.profile_skills import flatten_skills, resolve_skills


@dataclass
class TailorResult:
    matched_skills: list[str] = field(default_factory=list)
    skill_gaps: list[str] = field(default_factory=list)
    ats_score: float = 0.0
    must_have: list[str] = field(default_factory=list)
    nice_to_have: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    experience_order: list[dict] = field(default_factory=list)
    highlights_per_entry: dict = field(default_factory=dict)
    ranked_projects: list[dict] = field(default_factory=list)
    summary_text: str = ""
    company_type: str = "general"
    source: str = "deterministic"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def extract_keywords(jd_text: str, skill_weights: dict = None,
                     skill_categories: dict = None) -> dict:
    jd_lower = jd_text.lower()
    if not skill_weights:
        skill_weights = SKILL_WEIGHTS
    if not skill_categories:
        skill_categories = SKILL_CATEGORIES

    must_have_skills = [s.lower() for s in skill_categories.get("must_have", [])]
    nice_to_have_skills = [s.lower() for s in skill_categories.get("nice_to_have", [])]

    must_have = []
    nice_to_have = []
    tools = []
    concepts = []
    soft_skills = []

    for skill in skill_weights:
        if skill.lower() in jd_lower:
            if skill.lower() in must_have_skills:
                must_have.append(skill)
            elif skill.lower() in nice_to_have_skills:
                nice_to_have.append(skill)
            else:
                tools.append(skill)

    concept_signals = ["api", "microservice", "rest", "authentication", "authorization",
                       "ci/cd", "cicd", "database", "orm", "mvc", "mvt"]
    for c in concept_signals:
        if c in jd_lower:
            concepts.append(c)

    soft_signals = ["communication", "teamwork", "leadership", "problem solving",
                    "analytical", "detail oriented", "self motivated"]
    for s in soft_signals:
        if s in jd_lower:
            soft_skills.append(s)

    return {
        "must_have": list(set(must_have)),
        "nice_to_have": list(set(nice_to_have)),
        "tools": list(set(tools)),
        "concepts": list(set(concepts)),
        "soft_skills": list(set(soft_skills)),
    }


def map_skills(jd_text: str, profile_skills: dict, aliases: dict = None,
               weights: dict = None) -> tuple[list[str], dict[str, int]]:
    jd_lower = jd_text.lower()
    matched = []
    breakdown = {}
    weights = weights or SKILL_WEIGHTS

    all_skills = []
    for cat_skills in profile_skills.values():
        all_skills.extend(cat_skills)

    for skill in all_skills:
        skill_lower = skill.lower()
        skill_aliases = [skill_lower] + [a.lower() for a in (aliases or SKILL_ALIASES).get(skill_lower, [])]
        for alias in skill_aliases:
            if alias in jd_lower or alias.replace(" ", "") in jd_lower.replace(" ", ""):
                weight = weights.get(skill_lower, 3)
                if skill not in matched:
                    matched.append(skill)
                    breakdown[skill] = weight
                break

    return matched, breakdown


def select_projects(profile: dict, matched_skills: list[str], jd_desc: str) -> list[dict]:
    projects = profile.get("projects", [])
    if not projects:
        return []

    jd_lower = jd_desc.lower()
    matched_lower = [s.lower() for s in matched_skills]

    scored = []
    for p in projects:
        p_tech = {t.lower() for t in p.get("tech", [])}
        overlap = len(set(matched_lower) & p_tech)
        desc_bonus = sum(1 for t in p_tech if t in jd_lower)
        scored.append((overlap + desc_bonus, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    return [p for _, p in scored]


def select_experience(profile: dict, matched_skills: list[str], jd_desc: str) -> list[dict]:
    experience = profile.get("experience", [])
    if not experience:
        return []

    jd_lower = jd_desc.lower()
    matched_lower = [s.lower() for s in matched_skills]

    scored = []
    for entry in experience:
        entry_text = f"{entry.get('role', '')} {entry.get('company', '')} {' '.join(entry.get('tech', []))} {' '.join(entry.get('highlights', []))}"
        entry_lower = entry_text.lower()

        skill_overlap = sum(1 for s in matched_lower if s in entry_lower)
        tech_overlap = sum(1 for t in entry.get("tech", []) if t.lower() in jd_lower)
        role_match = 2 if any(w in entry.get("role", "").lower() for w in jd_lower.split()[:20]) else 0

        total = skill_overlap + tech_overlap + role_match
        scored.append((total, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored]


def select_highlights(entry: dict, matched_skills: list[str], total_entries: int = 1) -> list[str]:
    highlights = entry.get("highlights", [])
    if not highlights:
        return []

    if total_entries >= 5:
        max_count = 2
    elif total_entries >= 4:
        max_count = 2
    elif total_entries >= 3:
        max_count = 3
    else:
        max_count = 3

    matched_lower = [s.lower() for s in matched_skills]
    scored = []
    for h in highlights:
        h_lower = h.lower()
        relevance = sum(1 for s in matched_lower if s in h_lower)
        scored.append((relevance, h))
    scored.sort(key=lambda x: x[0], reverse=True)

    return [h for _, h in scored[:max_count]]


def build_summary(profile: dict, job: dict, matched_skills: list[str],
                   company_context: dict = None) -> str:
    role = job.get("title", "") or profile.get("role", "Professional")
    exp_years = profile.get("experience_years", 1)
    if matched_skills:
        strengths = ", ".join(matched_skills[:5])
    else:
        all_skills = flatten_skills(profile)
        strengths = ", ".join(all_skills[:5]) if all_skills else "industry-standard tools"

    summary = (
        f"{role} with {exp_years} year{'s' if exp_years != 1 else ''} of professional "
        f"experience, skilled in {strengths}. "
    )

    focus_areas = []
    if company_context:
        focus_areas = company_context.get("key_focus_areas", [])
    if focus_areas:
        focus_text = ", ".join(focus_areas[:4])
        summary += f"Proven record of delivering results across {focus_text}. "

    summary += "Focused on producing high-quality, measurable outcomes and continuous improvement."

    return summary


def calculate_ats(jd_text: str, cv_text: str, skill_weights: dict = None) -> tuple[float, dict]:
    if not skill_weights:
        skill_weights = SKILL_WEIGHTS

    jd_lower = jd_text.lower()
    cv_lower = cv_text.lower()

    total_keywords = 0
    matched_keywords = 0
    breakdown = {}

    for skill, weight in skill_weights.items():
        aliases = [skill] + SKILL_ALIASES.get(skill, [])
        for alias in aliases:
            if alias in jd_lower:
                total_keywords += weight
                for a in [skill] + aliases:
                    if a in cv_lower:
                        matched_keywords += weight
                        breakdown[skill] = weight
                        break
                break

    score = (matched_keywords / total_keywords * 100) if total_keywords > 0 else 0
    score = min(score, 100)

    return round(score, 1), breakdown


def tailor_cv(job: dict, profile: dict, skill_weights: dict = None,
              aliases: dict = None, categories: dict = None,
              company_context: dict = None) -> TailorResult:
    if not skill_weights or not aliases or not categories:
        resolved_weights, resolved_aliases, resolved_categories = resolve_skills(profile)
        skill_weights = skill_weights or resolved_weights
        aliases = aliases or resolved_aliases
        categories = categories or resolved_categories

    jd_text = f"{job.get('title', '')} {job.get('description', '')}"

    matched_skills, breakdown = map_skills(jd_text, profile.get("skills", {}), aliases, skill_weights)

    if company_context:
        company_tech = company_context.get("tech_stack", [])
        for skill in matched_skills:
            if skill.lower() in [s.lower() for s in company_tech]:
                breakdown[skill] = breakdown.get(skill, 3) * 1.5

    keywords = extract_keywords(jd_text, skill_weights, categories)

    experience_order = select_experience(profile, matched_skills, job.get("description", ""))
    total_entries = len(experience_order)
    highlights_per_entry = {}
    for entry in experience_order:
        entry_id = entry.get("id", "")
        highlights_per_entry[entry_id] = select_highlights(entry, matched_skills, total_entries)

    ranked_projects = select_projects(profile, matched_skills, job.get("description", ""))

    summary = build_summary(profile, job, matched_skills, company_context)

    cv_text = f"{summary} {' '.join(matched_skills)}"
    if company_context:
        must_have = company_context.get("must_have_keywords", [])
        cv_text += " " + " ".join(must_have)
    ats_score, ats_breakdown = calculate_ats(jd_text, cv_text, skill_weights)

    return TailorResult(
        matched_skills=matched_skills,
        skill_gaps=job.get("skill_gaps", []),
        ats_score=ats_score,
        must_have=keywords["must_have"],
        nice_to_have=keywords["nice_to_have"],
        tools=keywords["tools"],
        concepts=keywords["concepts"],
        soft_skills=keywords["soft_skills"],
        experience_order=experience_order,
        highlights_per_entry=highlights_per_entry,
        ranked_projects=ranked_projects,
        summary_text=summary,
        company_type=_classify_company_type(company_context),
        source="deterministic",
    )


def _classify_company_type(company_context: dict = None) -> str:
    if not company_context:
        return "general"
    desc = (company_context.get("description") or "").lower()
    size = (company_context.get("size") or "").lower()

    if "startup" in size or "series" in desc:
        return "startup"
    if "enterprise" in size or "fortune" in desc:
        return "enterprise"
    if "fintech" in desc or "banking" in desc or "finance" in desc:
        return "fintech"
    if "saas" in desc or "platform" in desc or "devtools" in desc:
        return "tech"
    if "ai" in desc or "ml" in desc or "llm" in desc:
        return "ai"
    return "general"
