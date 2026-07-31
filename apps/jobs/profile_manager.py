import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROFILE_JSON = Path(__file__).resolve().parent.parent.parent / "profile.json"

DEFAULT_CATEGORY_WEIGHTS = {
    "backend": 20,
    "ai_llm": 14,
    "data": 14,
    "cloud": 10,
    "devops": 8,
    "frontend": 6,
    "mobile": 6,
    "design": 6,
    "marketing": 6,
    "sales": 5,
    "content": 5,
    "finance": 5,
    "tools": 4,
}

DEFAULT_CATEGORY_GROUPS = {
    "must_have": ["backend", "ai_llm", "data", "design", "marketing", "mobile"],
    "nice_to_have": ["cloud", "devops", "frontend", "sales", "content", "finance"],
    "bonus": ["tools"],
}

DEFAULT_PROFILE = {
    "name": "Your Name",
    "email": "you@example.com",
    "phone": "",
    "role": "",
    "experience_years": 0,
    "experience_min": 0,
    "experience_max": 3,
    "location": "",
    "country": "",
    "currency": "INR",
    "min_salary": 0,
    "github": "",
    "linkedin": "",
    "portfolio": "",
    "skills": {},
    "projects": [],
    "experience": [],
    "education": "",
    "languages": ["English"],
    "looking_for": [],
    "excluded_roles": [],
    "excluded_locations": [],
}


def _merge_defaults(data: dict) -> dict:
    merged = dict(DEFAULT_PROFILE)
    if isinstance(data, dict):
        for k, v in data.items():
            merged[k] = v
    return merged


def load_profile() -> dict:
    """Load profile from profile.json (the single source of truth).

    Never imports ``config/profile.py``, so a fresh clone without
    ``config/profile.py`` boots cleanly. Missing keys fall back to
    ``DEFAULT_PROFILE`` so downstream code can assume a full shape.
    """
    if PROFILE_JSON.exists():
        try:
            with open(PROFILE_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "PROFILE" in data:
                data = data["PROFILE"]
            if isinstance(data, dict):
                return _merge_defaults(data)
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning(f"Failed to load profile.json: {e}, using defaults")
    return dict(DEFAULT_PROFILE)


def save_profile(profile: dict) -> bool:
    """Save profile to profile.json."""
    try:
        with open(PROFILE_JSON, "w", encoding="utf-8") as f:
            json.dump({"PROFILE": profile}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save profile.json: {e}")
        return False


def ensure_default_profile() -> bool:
    """Write DEFAULT_PROFILE to profile.json when it does not exist yet.

    Never overwrites an existing profile. Returns True when created.
    """
    if PROFILE_JSON.exists():
        return False
    return save_profile(DEFAULT_PROFILE)


def _flatten_skills(profile: dict) -> list[str]:
    skills = []
    for cat in (profile.get("skills") or {}).values():
        if not isinstance(cat, list):
            continue
        for s in cat:
            if isinstance(s, str) and s.strip():
                skills.append(s.strip())
    return skills


def build_skill_weights(profile: dict | None = None) -> dict:
    """Derive skill weights from the profile's own skills (by category).

    Falls back to the legacy ``config/profile.py`` SKILL_WEIGHTS only when
    the profile carries no skills. Any category not in
    ``DEFAULT_CATEGORY_WEIGHTS`` gets a neutral weight of 5.
    """
    profile = profile or load_profile()
    weights: dict[str, int] = {}
    for cat, cat_skills in (profile.get("skills") or {}).items():
        if not isinstance(cat_skills, list):
            continue
        w = DEFAULT_CATEGORY_WEIGHTS.get(cat.lower(), 5)
        for s in cat_skills:
            if isinstance(s, str) and s.strip():
                weights[s.lower()] = w
    if weights:
        return weights
    try:
        from config.profile import SKILL_WEIGHTS

        if isinstance(SKILL_WEIGHTS, dict):
            return {str(k).lower(): v for k, v in SKILL_WEIGHTS.items()}
    except ImportError:
        pass
    return {}


def build_skill_aliases(profile: dict | None = None) -> dict:
    """Map lowercased skill -> original display form from the profile."""
    profile = profile or load_profile()
    aliases: dict[str, str] = {}
    for cat in (profile.get("skills") or {}).values():
        if not isinstance(cat, list):
            continue
        for s in cat:
            if isinstance(s, str) and s.strip():
                aliases[s.lower()] = s
    return aliases


def build_skill_categories(profile: dict | None = None) -> dict:
    """Group the profile's skills into must_have / nice_to_have / bonus."""
    profile = profile or load_profile()
    groups: dict[str, list[str]] = {"must_have": [], "nice_to_have": [], "bonus": []}
    for cat, cat_skills in (profile.get("skills") or {}).items():
        if not isinstance(cat_skills, list):
            continue
        group = "must_have"
        for g, members in DEFAULT_CATEGORY_GROUPS.items():
            if cat.lower() in members:
                group = g
                break
        for s in cat_skills:
            if isinstance(s, str) and s.strip():
                groups[group].append(s.lower())
    return groups


def load_skill_weights() -> dict:
    """Legacy entry point: legacy config first, derived profile fallback."""
    try:
        from config.profile import SKILL_WEIGHTS

        if isinstance(SKILL_WEIGHTS, dict):
            return {str(k).lower(): v for k, v in SKILL_WEIGHTS.items()}
    except ImportError:
        pass
    return build_skill_weights()


def load_skill_aliases() -> dict:
    """Legacy entry point: legacy config first, derived profile fallback."""
    try:
        from config.profile import SKILL_ALIASES

        if isinstance(SKILL_ALIASES, dict):
            return dict(SKILL_ALIASES)
    except ImportError:
        pass
    return build_skill_aliases()


def load_skill_categories() -> dict:
    """Legacy entry point: legacy config first, derived profile fallback."""
    try:
        from config.profile import SKILL_CATEGORIES

        if isinstance(SKILL_CATEGORIES, dict):
            return dict(SKILL_CATEGORIES)
    except ImportError:
        pass
    return build_skill_categories()
