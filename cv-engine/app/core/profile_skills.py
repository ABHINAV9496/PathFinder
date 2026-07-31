"""Derive skill weights / aliases / categories from the candidate profile.

The CV Engine is profession-agnostic: for a Python developer OR a data
analyst OR a graphic designer, the tailoring vocabulary comes from the
candidate's own ``profile.skills`` categories. The static vocab in
``app.config`` is only a fallback when the profile carries no skills.
"""

from typing import Any

DEFAULT_CATEGORY_WEIGHTS = {
    "backend": 20,
    "ai_llm": 14,
    "data": 14,
    "analytics": 12,
    "languages": 12,
    "cloud": 10,
    "design": 10,
    "devops": 8,
    "frontend": 6,
    "mobile": 6,
    "marketing": 6,
    "content": 6,
    "sales": 5,
    "finance": 5,
    "techniques": 6,
    "tools": 6,
}

FALLBACK_CATEGORY_WEIGHT = 6

MUST_HAVE_WEIGHT = 10
NICE_TO_HAVE_WEIGHT = 6


def flatten_skills(profile: dict) -> list[str]:
    skills = []
    for cat in (profile.get("skills") or {}).values():
        if not isinstance(cat, list):
            continue
        for s in cat:
            if isinstance(s, str) and s.strip():
                skills.append(s.strip())
    return skills


def derive_skill_weights(profile: dict) -> dict[str, int]:
    weights: dict[str, int] = {}
    for cat, cat_skills in (profile.get("skills") or {}).items():
        if not isinstance(cat_skills, list):
            continue
        w = DEFAULT_CATEGORY_WEIGHTS.get(cat.lower(), FALLBACK_CATEGORY_WEIGHT)
        for s in cat_skills:
            if isinstance(s, str) and s.strip():
                weights[s.strip().lower()] = w
    return weights


def derive_skill_aliases(profile: dict) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for skill in flatten_skills(profile):
        key = skill.lower()
        aliases.setdefault(key, [])
        no_space = skill.replace(" ", "").lower()
        if no_space != key and no_space not in aliases[key]:
            aliases[key].append(no_space)
    return aliases


def derive_skill_categories(profile: dict) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"must_have": [], "nice_to_have": [], "bonus": []}
    for cat, cat_skills in (profile.get("skills") or {}).items():
        w = DEFAULT_CATEGORY_WEIGHTS.get(cat.lower(), FALLBACK_CATEGORY_WEIGHT)
        group = "bonus"
        if w >= MUST_HAVE_WEIGHT:
            group = "must_have"
        elif w >= NICE_TO_HAVE_WEIGHT:
            group = "nice_to_have"
        if not isinstance(cat_skills, list):
            continue
        for s in cat_skills:
            if isinstance(s, str) and s.strip():
                groups[group].append(s.strip().lower())
    return groups


def resolve_skills(profile: dict) -> tuple[dict, dict, dict]:
    """Return (weights, aliases, categories) for a profile.

    Falls back to the static ``app.config`` vocab only when the profile
    has no skills at all, so the engine never crashes on an empty profile.
    """
    weights = derive_skill_weights(profile)
    if weights:
        aliases = derive_skill_aliases(profile)
        categories = derive_skill_categories(profile)
        return weights, aliases, categories

    from app.config import SKILL_WEIGHTS, SKILL_ALIASES, SKILL_CATEGORIES

    return dict(SKILL_WEIGHTS), dict(SKILL_ALIASES), dict(SKILL_CATEGORIES)
