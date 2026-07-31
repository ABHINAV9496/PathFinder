from app.core.profile_skills import resolve_skills
from app.core.tailor_engine import extract_keywords


def extract_jd_keywords(jd_text: str, profile: dict = None) -> dict:
    if profile:
        weights, _, categories = resolve_skills(profile)
        return extract_keywords(jd_text, weights, categories)
    return extract_keywords(jd_text)
