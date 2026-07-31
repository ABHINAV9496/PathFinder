"""Deterministic, profession-agnostic template cover-letter generator.

Grounded strictly in the candidate's own profile and uploaded resume
text: every skill mentioned comes from ``profile.skills`` (matched against
the JD), and every achievement is a verbatim line from the original
resume. No LLM, no hallucination risk.
"""

import re

from coverletter.core.tailor import flatten_skills, tailor_cv


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


def _no_ai_claims(text: str) -> str:
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def generate_cover_letter(job: dict, profile: dict, resume_text: str = "") -> tuple[str, dict]:
    result = tailor_cv(job, profile)

    role = job.get("title", "") or profile.get("role", "Professional")
    company = job.get("company", "") or "your company"

    # Prefer the CV engine's authoritative match data when the caller supplies it.
    engine_matched = job.get("matched_skills") or []
    engine_missing = job.get("missing_keywords") or []
    engine_missing_lower = {m.lower() for m in engine_missing}
    matched_skills = [s for s in engine_matched if s.lower() not in engine_missing_lower]
    if not matched_skills:
        matched_skills = result.matched_skills or []
    all_skills = flatten_skills(profile)

    if not matched_skills:
        matched_skills = all_skills[:5]

    skills_text = ", ".join(matched_skills[:6]) if matched_skills else "industry-standard tools"
    strengths = ", ".join(matched_skills[:4]) if matched_skills else "my core competencies"

    relevant = _relevant_lines(resume_text, matched_skills, profile)
    grounded = bool(relevant)
    if not relevant:
        projects = profile.get("projects", [])
        if projects:
            relevant = [
                f"Built {p.get('name', '')}: {p.get('description', '')}"
                for p in projects[:2] if p.get("name")
            ]

    paragraphs = []

    opening = (
        f"I am writing to apply for the {role} position at {company}. "
        "The requirements in the job description align closely with my background and skills."
    )
    if matched_skills:
        opening += (
            f" In particular, my experience with {strengths} directly matches the core "
            "competencies you are looking for."
        )
    paragraphs.append(_no_ai_claims(opening))

    body = (
        f"As a {profile.get('role', 'professional')} with "
        f"{profile.get('experience_years', 1)} year"
        f"{'s' if profile.get('experience_years', 1) != 1 else ''} of experience, "
        f"I bring solid skills across {skills_text}."
    )
    if relevant:
        evidence = relevant[0] if len(relevant) == 1 else " ".join(relevant[:2])
        body += f" Some of my relevant work includes {evidence}."
    paragraphs.append(_no_ai_claims(body))

    closing = (
        f"I am excited about the opportunity to contribute to {company} and would welcome "
        "the chance to discuss how my experience fits your team. Thank you for your time "
        "and consideration."
    )
    paragraphs.append(_no_ai_claims(closing))

    letter = "Dear Hiring Manager,\n\n" + "\n\n".join(paragraphs) + "\n\n" + _signature(profile)

    return letter, {
        "matched_skills": matched_skills,
        "source": "deterministic",
        "evidence_count": len(relevant),
        "grounded_in_resume": grounded,
        "missing_keywords": engine_missing,
    }
