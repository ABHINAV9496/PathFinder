"""ATS Analyst engine — deterministic mock-ATS scorer with an optional LLM
upgrade, implemented from the user's v3 rubric.

The deterministic path always works with zero configuration. When ``ai_config``
is provided, ``analyze_with_llm`` runs the same rubric through an LLM (the v3
prompt is the canonical system prompt) and gracefully falls back to the
deterministic report on any failure.
"""

import json
import logging
import re
from dataclasses import dataclass, field

from app.core.ats_prompts import DEFAULT_PROMPT_VERSION, SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

MUST_SIGNALS = (
    "required", "must have", "must-have", "must", "mandatory", "essential",
    "minimum", "prerequisite", "core requirement",
)

NICE_SIGNALS = (
    "nice to have", "nice-to-have", "bonus", "preferred", "a plus", "good to have",
    "beneficial", "ideal but not", "not required but",
)

SOFT_SKILLS = (
    "communication", "teamwork", "collaboration", "leadership", "problem solving",
    "problem-solving", "analytical", "detail oriented", "detail-oriented",
    "self motivated", "self-motivated", "time management", "adaptability",
    "mentoring", "ownership", "initiative", "stakeholder", "cross-functional",
    "attention to detail",
)

CERT_SIGNALS = (
    "certification", "certified", "certificate", "aws certified", "bachelor",
    "bachelor's", "master", "master's", "mba", "degree", "phd", "btech",
    "b.tech", "graduation", "diploma", "scrum master", "pmp", "cpa", "cfa",
    "google cloud certified",
)

TOOLS_VOCAB = (
    "docker", "kubernetes", "k8s", "terraform", "aws", "azure", "gcp",
    "google cloud", "git", "github", "gitlab", "jenkins", "ci/cd", "cicd",
    "sql", "postgres", "postgresql", "mysql", "sqlite", "mongodb", "redis",
    "kafka", "rabbitmq", "graphql", "elasticsearch", "snowflake", "databricks",
    "airflow", "spark", "tableau", "power bi", "excel", "notion", "jira",
    "figma", "photoshop", "wordpress", "shopify", "salesforce", "hubspot",
    "semrush", "google analytics", "ga4", "adobe", "after effects", "blender",
    "django", "flask", "fastapi", "react", "react.js", "reactjs", "next.js",
    "vue", "typescript", "javascript", "tailwind", "node.js", "nodejs",
    "graphql", "rest api", "restful", "microservices", "microservices architecture",
)

ACTION_VERBS = (
    "built", "designed", "developed", "implemented", "led", "shipped", "launched",
    "optimized", "created", "automated", "improved", "delivered", "scaled",
    "architected", "deployed", "streamlined", "engineered", "mentored",
    "managed", "reduced", "increased", "accelerated", "migrated", "integrated",
    "introduced", "refactored", "revamped", "spearheaded", "owned", "analyzed",
    "boosted", "cut", "saved", "drove", "established", "executed",
)

QUANT_PATTERNS = (
    r"\d+\s*%",
    r"\$\s?\d",
    r"\d+\s*(?:ms|sec|s|min|hours?|days?|weeks?|months?|years?)",
    r"\d+\s*x\b",
    r"\d+\s*(?:K|k|M|m|B|b)(?:\+)?\b",
    r"(?:reduced|increased|cut|grew|boosted|saved)\s+(?:by\s+)?\d",
    r"sub-\d+",
)

RESUME_SECTION_NAMES = (
    "summary", "skills", "experience", "projects", "education",
    "professional summary", "technical skills", "work experience",
    "professional experience", "employment history", "academic qualifications",
)

_TIER_WEIGHTS = {
    "tier0_required": 5,
    "tier1_core": 3,
    "tier2_tools": 2,
    "tier3_certs": 1,
    "tier4_soft": 1,
    "tier5_nice": 1,
}

_TIER_LABELS = {
    "tier0_required": "Tier 0 - required",
    "tier1_core": "Tier 1 - core skills",
    "tier2_tools": "Tier 2 - tools & platforms",
    "tier3_certs": "Tier 3 - certifications",
    "tier4_soft": "Tier 4 - soft skills",
    "tier5_nice": "Tier 5 - nice to have",
}


@dataclass
class ATSReport:
    score: float
    breakdown: dict
    tiers: dict
    parseability: dict
    resume_quality: dict
    frequency_recency: dict
    missing_keywords: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    summary: str = ""
    source: str = "deterministic"


def _in(text: str, term: str) -> bool:
    """Word-ish presence check that tolerates terms like ``c++`` / ``ci/cd``."""
    if not text or not term:
        return False
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE) is not None


def _within_signal(text: str, term: str, signals: tuple, window: int = 14) -> bool:
    text_lower = text.lower()
    term_lower = term.lower()
    for m in re.finditer(rf"(?<!\w){re.escape(term_lower)}(?!\w)", text_lower):
        start = max(0, m.start() - window)
        end = min(len(text_lower), m.end() + window)
        ctx = text_lower[start:end]
        if any(sig in ctx for sig in signals):
            return True
    return False


def _in_sentence_with_signal(text: str, term: str, signals: tuple) -> bool:
    """True when ``term`` appears in a JD sentence that contains a signal word.

    Sentence-scope beats a fixed char window: "Must have strong SQL and Power
    BI." correctly flags both SQL and Power BI as hard requirements.
    """
    text_lower = text.lower()
    term_lower = term.lower()
    for m in re.finditer(rf"(?<!\w){re.escape(term_lower)}(?!\w)", text_lower):
        idx = max(
            text_lower.rfind(c, 0, m.start())
            for c in (".", "\n", "!", "?", ";")
        )
        ends = [
            i for i in (text_lower.find(c, m.end()) for c in (".", "\n", "!", "?", ";"))
            if i != -1
        ]
        end = min(ends) if ends else len(text_lower)
        sentence = text_lower[idx + 1:end + 1]
        if any(sig in sentence for sig in signals):
            return True
    return False


def _classify_tiers(jd_text: str, skill_weights: dict, skill_categories: dict) -> dict:
    """Deterministic tier 0-5 keyword classification of the JD."""
    jd_lower = jd_text.lower()
    tiers: dict = {key: {"matched": [], "missing": []} for key in _TIER_WEIGHTS}

    must_have_skills = [s.lower() for s in (skill_categories or {}).get("must_have", [])]

    candidates = {}
    for skill in skill_weights:
        if _in(jd_lower, skill):
            candidates.setdefault(skill, {"type": "skill", "weight": _TIER_WEIGHTS["tier1_core"]})
    for tool in TOOLS_VOCAB:
        if _in(jd_lower, tool):
            candidates.setdefault(tool, {"type": "tool", "weight": _TIER_WEIGHTS["tier2_tools"]})
    for soft in SOFT_SKILLS:
        if _in(jd_lower, soft):
            candidates.setdefault(soft, {"type": "soft", "weight": _TIER_WEIGHTS["tier4_soft"]})

        for term, info in candidates.items():
            if _in_sentence_with_signal(jd_lower, term, MUST_SIGNALS):
                tier = "tier0_required"
            elif _in_sentence_with_signal(jd_lower, term, NICE_SIGNALS):
                tier = "tier5_nice"
            elif term.lower() in must_have_skills:
                tier = "tier0_required"
            else:
                type_to_tier = {"skill": "tier1_core", "tool": "tier2_tools", "soft": "tier4_soft"}
                tier = type_to_tier[info["type"]]
            tiers[tier]["missing"].append(term)

    if _in(jd_lower, "cert") or any(_in(jd_lower, c) for c in CERT_SIGNALS):
        if any(_in_sentence_with_signal(jd_lower, c, MUST_SIGNALS) for c in CERT_SIGNALS):
            tiers["tier0_required"]["missing"].append("certification/degree requirement")
        else:
            tiers["tier3_certs"]["missing"].append("certification/degree")

    return tiers


def _check_parseability(resume_text: str) -> dict:
    issues = []
    sections_detected = []
    text = (resume_text or "").strip()
    if not text:
        return {
            "score": 0,
            "issues": ["Resume text is empty — nothing to parse"],
            "sections_detected": [],
        }

    for name in RESUME_SECTION_NAMES:
        if re.search(rf"^\s*{re.escape(name)}\s*$", text, re.IGNORECASE | re.MULTILINE):
            sections_detected.append(name)

    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        issues.append("No email address found in the header")
    if not re.search(r"\+?\d[\d\s().-]{7,}\d", text):
        issues.append("No phone number found in the header")
    if "skills" not in sections_detected:
        issues.append("No 'Skills' section header detected")

    expected = {"summary", "skills", "experience"}
    missing_sections = expected - {s for s in sections_detected}
    if missing_sections:
        issues.append(f"Missing standard sections: {', '.join(sorted(missing_sections))}")

    score = 100
    score -= len(issues) * 20
    score = max(0, min(100, score))
    return {"score": score, "issues": issues, "sections_detected": sections_detected}


def _check_resume_quality(resume_text: str, tiers: dict) -> dict:
    issues = []
    text = (resume_text or "").lower()

    action_verbs = sum(1 for v in ACTION_VERBS if _in(text, v))
    quantified = sum(1 for p in QUANT_PATTERNS if re.search(p, text, re.IGNORECASE))

    if action_verbs < 3:
        issues.append(f"Few action verbs found ({action_verbs}); start bullets with strong verbs")
    if quantified < 2:
        issues.append("Few quantified outcomes; add %, $, or time-scale metrics")

    base = 100
    base += min(action_verbs, 10) * 2
    base += min(quantified, 8) * 2
    score = min(base, 100)
    return {
        "score": score,
        "action_verbs": action_verbs,
        "quantified_outcomes": quantified,
        "issues": issues,
    }


def _check_frequency_recency(resume_text: str, tiers: dict) -> dict:
    issues = []
    text = (resume_text or "").lower()
    score = 100

    core = tiers.get("tier1_core", {}).get("missing", [])[:5]
    repeated = 0
    for skill in core:
        if text.count(skill) >= 2:
            repeated += 1
    if repeated < len(core) // 2:
        issues.append("Core skills should be repeated in the skills section AND experience bullets")

    if not re.search(r"\b(20[12][0-9]|20[0-9]{2})\b", text):
        issues.append("No dates found — recency cannot be confirmed")
        score -= 20
    elif re.search(r"\b(2023|2024|2025|2026)\b", text):
        score += 10

    score -= len(issues) * 15
    return {"score": max(0, min(100, score)), "issues": issues}


def _tier_coverage(tiers: dict) -> float:
    total = 0
    matched = 0
    for tier, weight in _TIER_WEIGHTS.items():
        for kw in tiers[tier]["matched"]:
            total += weight
            matched += weight
        for kw in tiers[tier]["missing"]:
            total += weight
    return (matched / total * 100) if total else 100.0


def _jd_tailoring(tiers: dict) -> float:
    critical = {**tiers["tier0_required"], **tiers["tier1_core"]}
    total = len(critical["matched"]) + len(critical["missing"])
    return (len(critical["matched"]) / total * 100) if total else 100.0


def _missing_keywords(tiers: dict) -> list[str]:
    missing = []
    tiers_to_scan = (
        "tier0_required", "tier1_core", "tier2_tools",
        "tier3_certs", "tier4_soft", "tier5_nice",
    )
    for tier in tiers_to_scan:
        missing.extend(tiers[tier]["missing"])
    return missing


def _build_fixes(tiers: dict, parseability: dict, quality: dict, resume_text: str) -> list[str]:
    fixes = []
    for tier, label in _TIER_LABELS.items():
        for kw in tiers[tier]["missing"]:
            fixes.append(f"Add '{kw}' to your resume ({label})")
    for issue in parseability["issues"]:
        fixes.append(f"Parseability: {issue}")
    for issue in quality["issues"]:
        fixes.append(f"Resume quality: {issue}")
    if not (resume_text or "").strip():
        fixes.append("Upload your resume PDF so it can be scored against this job")
    return fixes


def _build_summary(jd_text: str, resume_text: str, score: float, tiers: dict) -> str:
    t0 = tiers["tier0_required"]
    parts = []
    if t0["missing"]:
        parts.append(f"missing required keywords: {', '.join(t0['missing'][:4])}")
    if t0["matched"]:
        parts.append(f"matched required keywords: {', '.join(t0['matched'][:4])}")
    if not (resume_text or "").strip():
        parts.append("no resume text provided")
    tail = f" ({', '.join(parts)})" if parts else ""
    return f"ATS score {score:.0f}/100 using the tier 0-5 rubric{tail}."


def analyze(jd_text: str, resume_text: str, profile: dict = None,
            skill_weights: dict = None, skill_categories: dict = None) -> ATSReport:
    """Deterministic ATS analysis following the v3 rubric."""
    from app.core.profile_skills import resolve_skills

    profile = profile or {}
    if not skill_weights or not skill_categories:
        resolved_weights, _resolved_aliases, resolved_categories = resolve_skills(profile)
        skill_weights = skill_weights or resolved_weights
        skill_categories = skill_categories or resolved_categories

    jd_text = jd_text or ""
    resume_text = resume_text or ""
    caveats = []

    tiers = _classify_tiers(jd_text, skill_weights, skill_categories)
    parseability = _check_parseability(resume_text)
    quality = _check_resume_quality(resume_text, tiers)
    freq_recency = _check_frequency_recency(resume_text, tiers)

    for tier in tiers.values():
        tier["matched"] = [kw for kw in tier["missing"] if _in(resume_text, kw)]
        tier["missing"] = [kw for kw in tier["missing"] if kw not in tier["matched"]]

    keyword_coverage = _tier_coverage(tiers)
    tailoring = _jd_tailoring(tiers)
    freq_score = freq_recency["score"]

    score = (
        0.40 * keyword_coverage
        + 0.20 * quality["score"]
        + 0.15 * parseability["score"]
        + 0.15 * tailoring
        + 0.10 * freq_score
    )
    score = round(max(0, min(100, score)), 1)

    if not jd_text.strip():
        caveats.append("No job description provided; score reflects the resume alone")
    if not resume_text.strip():
        caveats.append(
            "Resume text is empty — keyword and parseability results reflect the JD only"
        )
    if not tiers["tier0_required"]["missing"] and not tiers["tier0_required"]["matched"]:
        caveats.append("No Tier 0 (required) keywords detected in this JD")

    missing = _missing_keywords(tiers)
    fixes = _build_fixes(tiers, parseability, quality, resume_text)

    breakdown = {
        "keyword_coverage": round(keyword_coverage, 1),
        "resume_quality": quality["score"],
        "parseability": parseability["score"],
        "jd_tailoring": round(tailoring, 1),
        "frequency_recency": freq_score,
    }

    return ATSReport(
        score=score,
        breakdown=breakdown,
        tiers=tiers,
        parseability=parseability,
        resume_quality=quality,
        frequency_recency=freq_recency,
        missing_keywords=missing,
        fixes=fixes,
        caveats=caveats,
        summary=_build_summary(jd_text, resume_text, score, tiers),
        source="deterministic",
    )


def _to_report_dict(report: ATSReport) -> dict:
    return {
        "score": report.score,
        "breakdown": report.breakdown,
        "tiers": report.tiers,
        "parseability": report.parseability,
        "resume_quality": report.resume_quality,
        "frequency_recency": report.frequency_recency,
        "missing_keywords": report.missing_keywords,
        "fixes": report.fixes,
        "caveats": report.caveats,
        "summary": report.summary,
        "source": report.source,
    }


def analyze_with_llm(jd_text: str, resume_text: str, profile: dict,
                     ai_config: dict, prompt_version: str = DEFAULT_PROMPT_VERSION) -> dict:
    """Run the v3 ATS rubric through an LLM; fall back to the deterministic
    report on any error, non-JSON response, or missing config."""
    deterministic = _to_report_dict(analyze(jd_text, resume_text, profile))
    api_key = (ai_config or {}).get("api_key")
    api_base_url = (ai_config or {}).get("api_base_url")
    model = (ai_config or {}).get("model")
    if not api_key or not api_base_url or not model:
        return deterministic

    system_prompt = SYSTEM_PROMPTS.get(prompt_version) or SYSTEM_PROMPTS[DEFAULT_PROMPT_VERSION]
    user_prompt = (
        "JOB DESCRIPTION:\n"
        f"{jd_text[:6000]}\n\n"
        "CANDIDATE RESUME:\n"
        f"{resume_text[:6000]}"
    )

    try:
        import httpx
        url = f"{api_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1200,
            "temperature": 0.2,
        }
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if not choices:
            raise ValueError("no choices in LLM response")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise ValueError("empty LLM content")

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", content)
            if not m:
                raise ValueError("non-JSON LLM output")
            data = json.loads(m.group())

        if not isinstance(data, dict):
            raise ValueError("LLM output not an object")

        merged = {
            "score": float(data.get("final_score", {}).get("score", deterministic["score"])),
            "breakdown": data.get("final_score", {}).get("breakdown", deterministic["breakdown"]),
            "tiers": data.get("tiers", deterministic["tiers"]),
            "parseability": data.get("parseability", deterministic["parseability"]),
            "resume_quality": data.get("resume_quality", deterministic["resume_quality"]),
            "frequency_recency": data.get("frequency_recency", deterministic["frequency_recency"]),
            "missing_keywords": data.get("missing_keywords", deterministic["missing_keywords"]),
            "fixes": data.get("fixes", deterministic["fixes"]),
            "caveats": data.get("caveats", deterministic["caveats"]),
            "summary": "",
            "source": "llm",
        }
        return merged
    except Exception as e:
        logger.warning("LLM ATS analysis failed, falling back to deterministic: %s", e)
        return deterministic


def build_gap_report(report: ATSReport) -> dict:
    """Django-compatible gap report from an ATS report."""
    confirmed = []
    for kw in report.tiers.get("tier0_required", {}).get("missing", []):
        confirmed.append({
            "item": kw,
            "severity": "high",
            "detail": "Required in JD (Tier 0), absent from resume",
        })
    for kw in report.tiers.get("tier1_core", {}).get("missing", []):
        confirmed.append({
            "item": kw,
            "severity": "medium",
            "detail": "Explicitly listed in JD (Tier 1), absent from resume",
        })
    return {"confirmed_gaps": confirmed, "research_flagged_gaps": []}


def build_source_trace(report: ATSReport) -> list:
    """Django-compatible source trace from an ATS report."""
    trace = []
    seen = set()
    for tier in ("tier0_required", "tier1_core"):
        for kw in report.tiers.get(tier, {}).get("matched", []):
            if kw.lower() in seen:
                continue
            seen.add(kw.lower())
            trace.append({
                "claim": f"Proficient in {kw}",
                "source": "original_resume",
                "confirmed": True,
                "tier": tier,
            })
    return trace
