import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROFILE_JSON = Path(__file__).resolve().parent.parent.parent / "profile.json"


def load_profile() -> dict:
    """Load profile from profile.json if exists, else from config/profile.py."""
    if PROFILE_JSON.exists():
        try:
            with open(PROFILE_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "PROFILE" in data:
                return data["PROFILE"]
            return data
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load profile.json: {e}, falling back to config")

    from config.profile import SKILL_WEIGHTS
    return {"skills": {}, "projects": [], "experience": [], "looking_for": []}


def save_profile(profile: dict) -> bool:
    """Save profile to profile.json."""
    try:
        with open(PROFILE_JSON, "w", encoding="utf-8") as f:
            json.dump({"PROFILE": profile}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save profile.json: {e}")
        return False


def load_skill_weights() -> dict:
    """Load SKILL_WEIGHTS from config/profile.py."""
    from config.profile import SKILL_WEIGHTS
    return SKILL_WEIGHTS


def load_skill_aliases() -> dict:
    """Load SKILL_ALIASES from config/profile.py."""
    from config.profile import SKILL_ALIASES
    return SKILL_ALIASES


def load_skill_categories() -> dict:
    """Load SKILL_CATEGORIES from config/profile.py."""
    from config.profile import SKILL_CATEGORIES
    return SKILL_CATEGORIES
