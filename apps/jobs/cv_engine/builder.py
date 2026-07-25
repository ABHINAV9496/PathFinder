import re
import logging

from config.profile import PROFILE, SKILL_WEIGHTS

logger = logging.getLogger(__name__)

TECH_COMPANY_KEYWORDS = {
    "software", "tech", "ai", "ml", "data", "cloud", "saas", "platform",
    "engineering", "digital", "cyber", "automation", "robotics", "iot",
    "fintech", "edtech", "healthtech", "devops", "infrastructure",
}

CREATIVE_COMPANY_KEYWORDS = {
    "design", "creative", "media", "advertising", "marketing", "brand",
    "studio", "agency", "arts", "entertainment", "fashion", "lifestyle",
}

CORPORATE_KEYWORDS = {
    "consulting", "services", "solutions", "group", "holdings", "corp",
    "inc", "ltd", "llc", "bank", "financial", "insurance", "audit",
    "accounting", "legal", "management",
}


def _classify_company(job: dict) -> str:
    company = job.get("company", "").lower()
    title = job.get("title", "").lower()
    desc = job.get("description", "").lower()
    combined = f"{company} {title} {desc}"

    tech_score = sum(1 for kw in TECH_COMPANY_KEYWORDS if kw in combined)
    creative_score = sum(1 for kw in CREATIVE_COMPANY_KEYWORDS if kw in combined)
    corporate_score = sum(1 for kw in CORPORATE_KEYWORDS if kw in combined)

    scores = {
        "technical": tech_score,
        "creative": creative_score,
        "professional": corporate_score,
    }

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "modern"
    return best


def _rank_skills(job: dict) -> list[str]:
    desc = f"{job.get('title', '')} {job.get('description', '')} {job.get('full_text', '')}".lower()
    all_skills = []
    for cat_skills in PROFILE["skills"].values():
        all_skills.extend(cat_skills)
    seen = set()
    unique = []
    for s in all_skills:
        sl = s.lower()
        if sl not in seen:
            seen.add(sl)
            unique.append(s)

    matched = []
    not_matched = []
    for skill in unique:
        if skill.lower() in desc or skill.lower().replace(" ", "") in desc.replace(" ", ""):
            weight = SKILL_WEIGHTS.get(skill.lower(), 3)
            matched.append((skill, weight))
        else:
            not_matched.append(skill)

    matched.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in matched] + not_matched


def _pick_projects(job: dict, max_count: int = 2) -> list[dict]:
    desc = f"{job.get('title', '')} {job.get('description', '')}".lower()
    scored = []
    for proj in PROFILE.get("projects", []):
        tech_set = {t.lower() for t in proj.get("tech", [])}
        overlap = sum(1 for t in tech_set if t in desc)
        scored.append((overlap, proj))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_count]]


def _build_summary(job: dict) -> str:
    title = job.get("title", "developer")
    company = job.get("company", "your team")
    matched = _rank_skills(job)[:5]
    top_skills = ", ".join(matched[:3]) if matched else "Python and Django"

    exp = PROFILE.get("experience_years", 1)
    return (
        f"{PROFILE['role']} with {exp}+ years of hands-on experience in "
        f"{top_skills}. Proven ability to build and ship production-grade "
        f"applications. Eager to contribute to {company}'s engineering "
        f"team as a {title}."
    )


def build_cv_data(job: dict) -> dict:
    template_type = _classify_company(job)
    ranked_skills = _rank_skills(job)
    projects = _pick_projects(job)
    summary = _build_summary(job)

    skill_groups = {}
    for cat, cat_skills in PROFILE["skills"].items():
        cat_display = cat.replace("_", " ").title()
        ordered = sorted(cat_skills, key=lambda s: (s not in ranked_skills))
        skill_groups[cat_display] = ordered

    ordered_groups = {}
    if "Backend" in skill_groups:
        ordered_groups["Backend"] = skill_groups["Backend"]
    if "Frontend" in skill_groups:
        ordered_groups["Frontend"] = skill_groups["Frontend"]
    if "Devops" in skill_groups:
        ordered_groups["DevOps"] = skill_groups["Devops"]
    if "Cloud" in skill_groups:
        ordered_groups["Cloud & Infrastructure"] = skill_groups["Cloud"]
    if "Ai Llm" in skill_groups:
        ordered_groups["AI & LLM"] = skill_groups["Ai Llm"]
    if "Tools" in skill_groups:
        ordered_groups["Tools & Platforms"] = skill_groups["Tools"]

    return {
        "name": PROFILE["name"],
        "email": PROFILE["email"],
        "phone": PROFILE["phone"],
        "location": PROFILE["location"],
        "role": PROFILE["role"],
        "github": PROFILE.get("github", ""),
        "linkedin": PROFILE.get("linkedin", ""),
        "portfolio": PROFILE.get("portfolio", ""),
        "education": PROFILE.get("education", ""),
        "languages": PROFILE.get("languages", []),
        "summary": summary,
        "skills": ranked_skills,
        "skill_groups": ordered_groups,
        "projects": projects,
        "template_type": template_type,
        "target_company": job.get("company", ""),
        "target_role": job.get("title", ""),
    }
