import logging
import re

from apps.jobs.profile_manager import build_skill_weights, load_profile
from apps.jobs.services import _extract_salary_from_text
from config.constants import COMMON_JD_SKILLS, NORTH_INDIA_STATES
from config.settings import (
    MATCH_THRESHOLD_APPLY,
    MATCH_THRESHOLD_TRACK,
    MAX_SKILL_GAP_PCT,
    MIN_SALARY,
)

logger = logging.getLogger(__name__)

_profile = load_profile()
SKILL_WEIGHTS = build_skill_weights(_profile)

ALL_MY_SKILLS = []
for _cat in _profile.get("skills", {}).values():
    if isinstance(_cat, list):
        ALL_MY_SKILLS.extend(_cat)
ALL_MY_SKILLS = [s for s in ALL_MY_SKILLS if isinstance(s, str)]
ALL_MY_SKILLS_LOWER = {s.lower(): s for s in ALL_MY_SKILLS}

_TECH_VOCAB = set(ALL_MY_SKILLS_LOWER.keys()) | set(COMMON_JD_SKILLS)


def _reject_job(job: dict, reason: str) -> dict:
    job["match_score"] = 0
    job["matched_skills"] = []
    job["skill_score_breakdown"] = {}
    job["skill_gaps"] = []
    job["status"] = "ignored"
    job["relevant_project"] = None
    job["filter_reason"] = reason
    job["match_explanation"] = ""
    return job


def _is_excluded_location(location: str) -> bool:
    loc = location.lower()
    if "remote" in loc:
        return False
    if _profile.get("avoid_north_india") and any(
        state in loc for state in NORTH_INDIA_STATES
    ):
        return True
    return any(excl.lower() in loc for excl in _profile.get("excluded_locations", []))


def _extract_experience_years(text: str) -> int | None:
    patterns = [
        r"(\d+)\+?\s*-\s*(\d+)\s*years?",
        r"(\d+)\+?\s*years?",
        r"minimum\s*(?:of\s*)?(\d+)\s*years?",
        r"at least\s*(\d+)\s*years?",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return int(groups[1])
            return int(groups[0])
    return None


def _find_matching_skills(text: str) -> tuple[list[str], dict[str, int]]:
    text_lower = text.lower()
    matched = []
    breakdown = {}

    for skill_lower, skill_orig in ALL_MY_SKILLS_LOWER.items():
        if skill_lower in text_lower or skill_lower.replace(" ", "") in text_lower.replace(" ", ""):
            weight = SKILL_WEIGHTS.get(skill_lower, 3)
            matched.append(skill_orig)
            breakdown[skill_orig] = weight

    return matched, breakdown


def _find_skill_gaps(text: str) -> list[str]:
    text_lower = text.lower()
    gaps = []
    for skill in COMMON_JD_SKILLS:
        if skill in text_lower:
            display = skill.replace("_", " ").title()
            gaps.append(display)
    return gaps


def _find_relevant_project(matched_skills: list[str]) -> dict | None:
    best_project = None
    best_overlap = 0

    matched_lower = [s.lower() for s in matched_skills]
    for project in _profile.get("projects", []):
        overlap = sum(1 for t in project["tech"] if t.lower() in matched_lower)
        if overlap > best_overlap:
            best_overlap = overlap
            best_project = project

    return best_project


_MUST_SIGNALS = (
    "required", "must have", "must-have", "must", "mandatory",
    "essential", "minimum", "prerequisite",
)
_NICE_SIGNALS = (
    "nice to have", "nice-to-have", "bonus", "preferred",
    "a plus", "good to have", "beneficial",
)
_SOFT_SKILLS = (
    "communication", "teamwork", "collaboration", "leadership",
    "problem solving", "problem-solving", "analytical", "detail oriented",
    "detail-oriented", "self motivated", "self-motivated", "time management",
    "adaptability", "mentoring", "ownership", "initiative",
)


def _contains_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) is not None


def _in_sentence_with_signal(text: str, term: str, signals: tuple) -> bool:
    """True when ``term`` appears in a JD sentence containing a signal word."""
    text_lower = text.lower()
    term_lower = term.lower()
    for m in re.finditer(rf"(?<!\w){re.escape(term_lower)}(?!\w)", text_lower):
        idx = max(text_lower.rfind(c, 0, m.start()) for c in (".", "\n", "!", "?", ";"))
        ends = [
            i for i in (text_lower.find(c, m.end()) for c in (".", "\n", "!", "?", ";"))
            if i != -1
        ]
        end = min(ends) if ends else len(text_lower)
        sentence = text_lower[idx + 1:end + 1]
        if any(sig in sentence for sig in signals):
            return True
    return False


def classify_jd_keywords(text: str) -> dict:
    """Tier 0-5 keyword classification of a JD (mirrors the ATS rubric).

    tier0 = explicitly required, tier1 = profile skills, tier2 = tools/other,
    tier4 = soft skills, tier5 = nice-to-have.
    """
    text_lower = text.lower()
    tiers = {"tier0": [], "tier1": [], "tier2": [], "tier4": [], "tier5": []}

    candidates = set(ALL_MY_SKILLS_LOWER.keys())
    candidates |= set(COMMON_JD_SKILLS)
    candidates |= set(_SOFT_SKILLS)

    for term in candidates:
        if not _contains_term(text_lower, term):
            continue
        if _in_sentence_with_signal(text_lower, term, _MUST_SIGNALS):
            tiers["tier0"].append(term)
        elif _in_sentence_with_signal(text_lower, term, _NICE_SIGNALS):
            tiers["tier5"].append(term)
        elif term in _SOFT_SKILLS:
            tiers["tier4"].append(term)
        elif term in ALL_MY_SKILLS_LOWER:
            tiers["tier1"].append(term)
        else:
            tiers["tier2"].append(term)
    return tiers


def match_job(job: dict) -> dict:
    full_text = job.get("full_text", "")
    description = job.get("description", "")
    search_text = f"{full_text} {description}"
    location = job.get("location", "")
    job_title_lower = job.get("title", "").lower()

    if _is_excluded_location(location):
        return _reject_job(job, "Excluded location")

    is_target_role = any(
        tl.lower() in job_title_lower or job_title_lower in tl.lower()
        for tl in _profile.get("looking_for", [])
    )
    if not is_target_role:
        has_rejected_keyword = any(
            kw in job_title_lower for kw in _profile.get("excluded_roles", [])
        )
        if has_rejected_keyword:
            return _reject_job(job, f"Not a target role: {job.get('title', '')}")

    salary = job.get("salary", 0)
    salary_display = job.get("salary_display", "")
    if not salary:
        salary, salary_display = _extract_salary_from_text(search_text)
    min_salary = _profile.get("min_salary") or MIN_SALARY
    if salary and min_salary and salary < min_salary:
        return _reject_job(job, f"Salary too low ({_profile.get('currency', 'INR')} {salary:,})")

    required_years = _extract_experience_years(search_text)
    exp_min = _profile.get("experience_min", 0)
    exp_max = _profile.get("experience_max", _profile.get("experience_years", 3))

    if required_years is not None:
        if required_years > exp_max:
            return _reject_job(job, f"Experience too high ({required_years}yr required, max {exp_max})")
        if exp_min > 0 and required_years < exp_min:
            return _reject_job(job, f"Experience too low ({required_years}yr required, min {exp_min})")

    matched_skills, breakdown = _find_matching_skills(search_text)

    tiers = classify_jd_keywords(search_text)

    # Tier-0 gate: if the JD explicitly requires skills and none of the
    # candidate's skills match any of them, reject outright.
    if tiers["tier0"]:
        tier0_hits = [
            t for t in tiers["tier0"]
            if any(s.lower() in t or t in s.lower() for s in matched_skills)
        ]
        if not tier0_hits:
            job["tier_analysis"] = tiers
            return _reject_job(
                job,
                f"Missing required skills: {', '.join(tiers['tier0'][:4])}",
            )

    # Tier-weighted boost: skills the JD explicitly requires count double.
    for t in tiers["tier0"]:
        for s in matched_skills:
            if s.lower() in t or t in s.lower():
                breakdown[s] = breakdown.get(s, 3) * 2

    total_jd_tech = 0
    text_lower = search_text.lower()
    for kw in _TECH_VOCAB:
        if kw in text_lower:
            total_jd_tech += 1

    if total_jd_tech > 0:
        match_pct = len(matched_skills) / total_jd_tech * 100
        if match_pct < (100 - MAX_SKILL_GAP_PCT):
            gaps = _find_skill_gaps(search_text)
            job["matched_skills"] = matched_skills
            job["skill_score_breakdown"] = breakdown
            job["skill_gaps"] = gaps
            return _reject_job(job, f"Too many missing skills ({match_pct:.0f}% match, min 60%)")

    skill_score = sum(breakdown.values())
    max_possible = sum(SKILL_WEIGHTS.values())
    skill_pct = min((skill_score / max_possible) * 100 * 3, 60) if max_possible > 0 else 0

    experience_score = 0
    if required_years is None:
        experience_score = 10
    elif required_years <= 1:
        experience_score = 15
    elif required_years <= 2:
        experience_score = 10
    elif required_years <= 3:
        experience_score = 5
    else:
        experience_score = 0

    title_score = 0
    for title in _profile.get("looking_for", []):
        if title.lower() in job_title_lower or job_title_lower in title.lower():
            title_score = 5
            break

    project = _find_relevant_project(matched_skills)
    project_score = min(len(matched_skills) * 2, 20) if project else 0

    total = skill_pct + experience_score + title_score + project_score
    total = min(total, 100)

    gaps = _find_skill_gaps(search_text)

    explanation_parts = []
    if matched_skills:
        explanation_parts.append(f"Strong match: {', '.join(matched_skills[:5])}")
    if gaps:
        explanation_parts.append(f"Skill gaps: {', '.join(gaps[:3])}")
    if project:
        explanation_parts.append(f"Project {project['name']} directly relevant")
    if required_years:
        explanation_parts.append(f"Requires {required_years}yr experience")
    explanation = ". ".join(explanation_parts)

    if total >= MATCH_THRESHOLD_APPLY:
        status = "matched"
    elif total >= MATCH_THRESHOLD_TRACK:
        status = "matched"
    else:
        status = "ignored"

    job["match_score"] = round(total, 1)
    job["matched_skills"] = matched_skills
    job["skill_score_breakdown"] = breakdown
    job["skill_gaps"] = gaps
    job["tier_analysis"] = tiers
    job["status"] = status
    job["relevant_project"] = project
    job["salary"] = salary
    job["salary_display"] = salary_display
    job["filter_reason"] = ""
    job["match_explanation"] = explanation

    return job


def match_all_jobs(jobs: list[dict]) -> list[dict]:
    all_jobs = []
    ignored_count = 0
    location_blocked = 0
    salary_blocked = 0
    experience_blocked = 0
    skill_gap_blocked = 0

    for job in jobs:
        result = match_job(job)
        reason = result.get("filter_reason", "")

        if reason == "Excluded location":
            location_blocked += 1
        elif reason.startswith("Salary too low"):
            salary_blocked += 1
        elif reason.startswith("Experience too high"):
            experience_blocked += 1
        elif reason.startswith("Too many missing skills"):
            skill_gap_blocked += 1

        all_jobs.append(result)
        if result["status"] == "ignored":
            ignored_count += 1

    all_jobs.sort(key=lambda j: j["match_score"], reverse=True)
    logger.info(
        f"Processed {len(all_jobs)} total: {len(all_jobs) - ignored_count} matched, {ignored_count} ignored "
        f"(Location: {location_blocked}, Salary: {salary_blocked}, "
        f"Experience: {experience_blocked}, Skill gaps: {skill_gap_blocked})"
    )
    return all_jobs
