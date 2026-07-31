"""Minimal profession-agnostic JD matching used by the cover-letter engine.

Kept self-contained so this service has no dependency on the CV engine.
Skills come exclusively from the candidate profile.
"""


def flatten_skills(profile: dict) -> list[str]:
    skills = []
    for cat in (profile.get("skills") or {}).values():
        if not isinstance(cat, list):
            continue
        for s in cat:
            if isinstance(s, str) and s.strip():
                skills.append(s.strip())
    return skills


def map_skills(jd_text: str, profile_skills: dict) -> list[str]:
    jd_lower = jd_text.lower()
    jd_compact = jd_lower.replace(" ", "")
    matched = []
    seen = set()
    for cat in (profile_skills or {}).values():
        if not isinstance(cat, list):
            continue
        for skill in cat:
            if not isinstance(skill, str) or not skill.strip():
                continue
            key = skill.lower()
            if key in seen:
                continue
            seen.add(key)
            if key in jd_lower or key.replace(" ", "") in jd_compact:
                matched.append(skill.strip())
    return matched


class TailorResult:
    def __init__(self, matched_skills: list[str]):
        self.matched_skills = matched_skills


def tailor_cv(job: dict, profile: dict) -> TailorResult:
    jd_text = f"{job.get('title', '')} {job.get('description', '')}"
    matched = map_skills(jd_text, profile.get("skills", {}))
    return TailorResult(matched)
