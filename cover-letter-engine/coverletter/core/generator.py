"""Deterministic, profession-agnostic template cover-letter generator.

Selects one of 12 hardcoded ATS-friendly templates based on JD signals
(domain, seniority, tone, JD emphasis) and fills it with the candidate's
own data: matched skills (filtered against missing keywords), best-fit
projects, and grounded resume lines. No LLM, no hallucination risk.
"""

import re
from types import SimpleNamespace

from coverletter.core import classify
from coverletter.core.tailor import flatten_skills, tailor_cv
from coverletter.core.templates import select


def _signature(profile: dict) -> str:
    lines = [profile.get("name", "").strip() or "Sincerely"]
    if profile.get("phone"):
        lines.append(profile["phone"].strip())
    if profile.get("email"):
        lines.append(profile["email"].strip())
    for key in ("portfolio", "github", "linkedin"):
        if profile.get(key):
            lines.append(profile[key].strip())
    return "\n".join(lines)


def _join_and(items) -> str:
    items = list(items)
    if len(items) <= 1:
        return ", ".join(items)
    if len(items) == 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _resume_lines(resume_text: str) -> list[str]:
    if not resume_text:
        return []
    lines = []
    for raw in resume_text.splitlines():
        line = raw.strip().lstrip("\u2022-•").strip()
        if not line or len(line) < 20:
            continue
        if line.lower() in {
            "professional summary", "summary", "technical skills", "skills",
            "projects", "experience", "work experience", "professional experience",
            "education", "header", "profile",
        }:
            continue
        lines.append(line)
    return lines


def _relevant_lines(resume_text: str, matched_skills: list[str], profile: dict) -> list[str]:
    matches = [s.lower() for s in matched_skills]
    project_names = [p.get("name", "").lower() for p in profile.get("projects", [])]
    relevant = []
    for line in _resume_lines(resume_text):
        low = line.lower()
        hits = [m for m in matches if m in low]
        if hits or any(pn and pn in low for pn in project_names):
            relevant.append(line)
        if len(relevant) >= 3:
            break
    return relevant


def _best_project(job: dict, profile: dict) -> tuple[dict, dict | None]:
    desc = (job.get("description") or "").lower()
    matched = [s.lower() for s in (job.get("matched_skills") or [])]
    projects = profile.get("projects", [])

    scored = []
    for p in projects:
        p_tech = {t.lower() for t in p.get("tech", [])}
        overlap = len(set(matched) & p_tech)
        desc_bonus = sum(1 for t in p_tech if t in desc)
        scored.append((overlap + desc_bonus, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    primary = scored[0][1] if scored else {}
    secondary = scored[1][1] if len(scored) > 1 else None
    return primary, secondary


def _company_ref(company: str, style: str = "normal") -> str:
    name = company.strip()
    if not name:
        return "your team"
    if style == "possessive":
        if name.endswith("s"):
            return f"{name}'"
        return f"{name}'s"
    return name


def _need_hook(job: dict, company: str) -> str:
    desc = (job.get("description") or "").lower()
    hooks = []
    if any(w in desc for w in ["scalable", "scale", "high traffic", "millions"]):
        hooks.append(f"scalable systems that handle real traffic at {company}")
    if any(w in desc for w in ["api", "rest", "microservice"]):
        hooks.append(f"clean, well-designed APIs at {company}")
    if any(w in desc for w in ["saas", "platform", "product"]):
        hooks.append(f"production SaaS products at {company}")
    if any(w in desc for w in ["fast-paced", "move fast", "ship"]):
        hooks.append(f"moving fast and shipping at {company}")
    if any(w in desc for w in ["security", "auth", "rbac", "compliance"]):
        hooks.append(f"secure, production-grade systems at {company}")
    if any(w in desc for w in ["ai", "ml", "llm", "machine learning"]):
        hooks.append(f"AI-powered products at {company}")
    if hooks:
        return hooks[0]
    return f"the work your team is doing at {company}"


# Category -> (support keywords to look for in the profile, line builder).
_EMPHASIS_BUILDERS = {
    "ai": (
        ["llm", "rag", "groq", "openai", "langchain", "ai agents", "genai",
         "prompt engineering", "gpt"],
        lambda name: f"On the AI side, I've built production features around {name} -- prompt "
                     f"engineering, structured output parsing, and fallbacks for when the model "
                     f"is unreliable. ",
    ),
    "devops": (
        ["docker", "aws", "gcp", "azure", "kubernetes", "ci/cd", "github actions",
         "ec2", "terraform", "vercel"],
        lambda name: f"I also handle deployment -- {name} plus CI/CD pipelines -- because "
                     f"shipping reliably is part of the job. ",
    ),
    "frontend": (
        ["react", "typescript", "javascript", "vue", "angular"],
        lambda name: f"I build the frontend too ({name}), so I understand the full product "
                     f"loop, not just the API. ",
    ),
    "security": (
        ["jwt", "rbac", "oauth", "encryption", "owasp", "authentication", "auth"],
        lambda name: f"Security is part of my work -- I've implemented {name} access control "
                     f"and hardened APIs against common attack vectors. ",
    ),
    "data": (
        ["postgresql", "sql", "sqlalchemy", "redis", "celery", "mysql", "database"],
        lambda name: f"My data-layer work covers relational modeling and query tuning with "
                     f"{name}. ",
    ),
}


def _emphasis_lines(job: dict, profile: dict, emphases: set[str]) -> dict:
    """Build grounded emphasis lines: only when the JD emphasizes the area
    AND the candidate's profile actually contains a supporting skill."""
    flat = flatten_skills(profile)
    flat_lower = [s.lower() for s in flat]
    result = {f"{k}_line": "" for k in _EMPHASIS_BUILDERS}

    for category in emphases:
        builder = _EMPHASIS_BUILDERS.get(category)
        if not builder:
            continue
        keywords, make_line = builder
        matched = next((flat[i] for i in range(len(flat))
                        if any(kw in flat_lower[i] for kw in keywords)), None)
        if matched:
            result[f"{category}_line"] = make_line(matched)

    return result


def _build_context(job: dict, profile: dict, resume_text: str, matched_skills: list[str]):
    missing_lower = {m.lower() for m in (job.get("missing_keywords") or [])}
    engine_matched = job.get("matched_skills") or []
    matched = [s for s in engine_matched if s.lower() not in missing_lower]
    if not matched:
        matched = list(matched_skills)
    if not matched:
        matched = flatten_skills(profile)[:5]
    seen, cleaned = set(), []
    for s in matched:
        k = s.lower()
        if k and k not in seen:
            seen.add(k)
            cleaned.append(s)
    matched = cleaned

    company = (job.get("company") or "").strip() or "your team"
    primary, secondary = _best_project(job, profile)

    primary_name = primary.get("name", "")
    primary_desc = (primary.get("description") or "").lower()
    primary_tech = ", ".join(primary.get("tech", [])[:6])
    primary_ref = primary_name or "a full-stack application end to end"
    secondary_ref = (
        f"{secondary.get('name', '')} -- {(secondary.get('description') or '').lower()}"
        if secondary else ""
    )

    relevant = _relevant_lines(resume_text, matched, profile)
    grounded = bool(relevant)
    evidence = ""
    if relevant:
        evidence = relevant[0]
    elif primary_name:
        evidence = f"Built {primary_name}: {primary.get('description', '')}"
    evidence_sentence = f" Some of my relevant work includes {evidence}." if evidence else ""

    features = classify.extract(job, profile)
    emphases = features["emphases"]
    lines = _emphasis_lines(job, profile, emphases)

    return SimpleNamespace(
        company=company,
        company_possessive=_company_ref(company, "possessive"),
        title=(job.get("title") or "the open position"),
        role=(profile.get("role") or "professional"),
        experience_years=profile.get("experience_years", 1),
        skills_text=_join_and(matched[:6]) if matched else "industry-standard tools",
        strengths=", ".join(matched[:4]) if matched else "my core competencies",
        primary=primary,
        primary_name=primary_name,
        primary_desc=primary_desc,
        primary_tech=primary_tech,
        primary_ref=primary_ref,
        secondary_ref=secondary_ref,
        evidence_sentence=evidence_sentence,
        need=_need_hook(job, company),
        depth_case=features["seniority"] == "senior" and (profile.get("experience_years") or 0) < 3,
        matched=matched,
        relevant=relevant,
        grounded=grounded,
        features=features,
        **lines,
    )


def generate_cover_letter(job: dict, profile: dict, resume_text: str = "") -> tuple[str, dict]:
    result = tailor_cv(job, profile)
    features = classify.extract(job, profile)
    ctx = _build_context(job, profile, resume_text, result.matched_skills)

    template = select(features)
    body = template["render"](ctx)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    letter = f"Dear Hiring Manager,\n\n{body}\n\n{_signature(profile)}"

    return letter, {
        "matched_skills": ctx.matched,
        "source": "deterministic",
        "template": template["id"],
        "evidence_count": len(ctx.relevant),
        "grounded_in_resume": ctx.grounded,
        "missing_keywords": job.get("missing_keywords") or [],
    }
