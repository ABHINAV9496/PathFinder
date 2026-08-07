"""Neutral, pack-based cover-letter fallback (Django side).

Used when the Cover Letter Engine service is unreachable. Mirrors the
engine's deterministic generator: pick the best-matching profession pack for
the job + profile, score that pack's block pools against the JD feature
vector (seniority, tone, company type), and compose a unique letter from one
opening, two to three bodies, and one closing.

No tech-specific prose. Every claim comes from the candidate's own data:
matched skills (from ``job.matched_skills``), the best-fit project, and
grounded project lines.
"""

import re

from common.profession_packs import compose_cover_letter, features_for, pack_for_job


def _get_profile(profile=None):
    if profile:
        return profile
    from apps.jobs.profile_manager import load_profile
    return load_profile()


def _company_ref(company: str, style: str = "normal") -> str:
    name = company.strip()
    if not name:
        return "your team"
    if style == "possessive":
        if name.endswith("s"):
            return f"{name}'"
        return f"{name}'s"
    return name


def _join_and(items) -> str:
    items = list(items)
    if len(items) <= 1:
        return ", ".join(items)
    if len(items) == 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _best_project(job: dict, profile: dict) -> tuple[dict, dict]:
    desc = (job.get("description") or "").lower()
    matched = {s.lower() for s in (job.get("matched_skills") or [])}
    projects = profile.get("projects", []) or []

    scored = []
    for p in projects:
        p_tech = {t.lower() for t in p.get("tech", [])}
        overlap = len(matched & p_tech)
        desc_bonus = sum(1 for t in p_tech if t in desc)
        scored.append((overlap + desc_bonus, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    if scored:
        primary = scored[0][1]
        secondary = scored[1][1] if len(scored) > 1 else None
    else:
        primary, secondary = {}, None
    return primary, secondary


def _need_hook(job: dict, company: str) -> str:
    desc = (job.get("description") or "").lower()
    hooks = []
    if any(w in desc for w in ["scalable", "scale", "high traffic", "millions"]):
        hooks.append(f"work that has to perform at real scale, like what {company} does")
    if any(w in desc for w in ["api", "rest", "microservice"]):
        hooks.append(f"building dependable systems and integrations at {company}")
    if any(w in desc for w in ["saas", "platform", "product"]):
        hooks.append(f"building a product people rely on at {company}")
    if any(w in desc for w in ["fast-paced", "move fast", "ship"]):
        hooks.append(f"moving fast and shipping real results at {company}")
    if any(w in desc for w in ["security", "auth", "rbac", "compliance"]):
        hooks.append(f"keeping the work secure and dependable at {company}")
    if any(w in desc for w in ["ai", "ml", "llm", "machine learning"]):
        hooks.append(f"building modern products powered by AI and data at {company}")
    if any(w in desc for w in ["patient", "care", "health"]):
        hooks.append(f"the standard of care and service {company} is known for")
    if any(w in desc for w in ["customer", "client", "service"]):
        hooks.append(f"serving the customers and clients {company} works with")
    if hooks:
        return hooks[0]
    return f"the work your team is doing at {company}"


def _depth_sentence(job: dict, profile: dict) -> str:
    title = (job.get("title") or "").lower()
    is_senior = any(m in title for m in (
        "senior", "staff", "lead", "principal", "architect", "head", "manager", "director"
    ))
    if is_senior and (profile.get("experience_years") or 0) < 3:
        return (
            "My years on paper don't tell the whole story: I have owned meaningful "
            "work from start to finish -- the decisions, the trade-offs, and the "
            "quality of what goes out. That is what this role actually needs."
        )
    return (
        "Over time I have moved from doing tasks well to owning outcomes: the "
        "planning, the execution, the quality, and the results that go out."
    )


def _context(job: dict, profile: dict) -> dict:
    """Build the canonical pack placeholder values (neutral mirror of the
    engine's context builder)."""
    company = (job.get("company") or "").strip() or "your team"
    matched = job.get("matched_skills") or []
    skills_text = _join_and(matched[:6]) if matched else "my core competencies"

    primary, _ = _best_project(job, profile)
    primary_ref = primary.get("name") if primary else "work I have delivered end to end"
    evidence = ""
    if primary and primary.get("description"):
        evidence = (
            f" Some of my relevant work includes {primary.get('name')}: "
            f"{primary.get('description')}."
        )

    return {
        "company": company,
        "possessive": _company_ref(company, "possessive"),
        "title": job.get("title") or "the open position",
        "skills": skills_text,
        "primary": primary_ref,
        "evidence": evidence,
        "need": _need_hook(job, company),
        "depth": _depth_sentence(job, profile),
    }


def _compose(job: dict, profile: dict) -> tuple[str | None, str]:
    pack = pack_for_job(job, profile)
    pack_id = pack.get("id", "neutral")
    features = features_for(job, profile)
    ctx = _context(job, profile)

    body = compose_cover_letter(pack, features)
    if not body:
        return None, pack_id
    try:
        return body.format_map(ctx), pack_id
    except (KeyError, ValueError, IndexError):
        return None, pack_id


def _manual_neutral_letter(job: dict, profile: dict) -> str:
    """Last-resort neutral letter when pack composition fails entirely."""
    ctx = _context(job, profile)
    return (
        f"I am applying for the {ctx['title']} role at {ctx['company']} because it "
        f"matches the work I care about. My strongest areas are {ctx['skills']}, and "
        f"I have applied them to {ctx['primary']}.{ctx['evidence']}\n\n"
        f"I approach each piece of work the same way -- understand the goal, plan "
        f"carefully, deliver something solid, and follow through until it is finished "
        f"properly. {ctx['depth']}\n\n"
        f"I am genuinely interested in {ctx['need']} and would welcome the chance to "
        f"contribute to your team."
    )


def _signature(profile: dict) -> str:
    name = profile.get("name", "")
    phone = profile.get("phone", "")
    portfolio = profile.get("portfolio", "")
    github = profile.get("github", "")
    linkedin = profile.get("linkedin", "")

    lines = [f"Regards,\n{name}"]
    if phone:
        lines.append(phone)
    links = []
    if portfolio:
        links.append(f"Portfolio: {portfolio}")
    if github:
        links.append(f"GitHub: {github}")
    if linkedin:
        links.append(f"LinkedIn: {linkedin}")
    if links:
        lines.append(" | ".join(links))
    return "\n".join(lines)


def generate_cover_letter_template(job: dict, profile: dict = None) -> tuple[str, str]:
    """Generate a profession-neutral cover letter from the pack block pools.

    Returns ``(letter, template)`` where ``template`` is the pack id (e.g.
    ``"healthcare"``) or ``"neutral"`` for the last-resort manual letter.
    """
    profile = _get_profile(profile)
    body, template = _compose(job, profile)
    if not body:
        body = _manual_neutral_letter(job, profile)
        template = "neutral"

    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    letter = f"{body}\n\n{_signature(profile)}"
    return letter.strip(), template
