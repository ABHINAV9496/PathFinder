"""Shared profession pack loading, detection, and cover-letter composition.

Pure stdlib module used by BOTH the Django app (``apps/jobs/profession_packs``
re-exports it) and the standalone cover-letter engine (via a small shim), so
there is a single source of truth for the block-pool composer.

Profession packs live in ``profession_packs/*.json`` at the project root and
are pure data files -- no code changes are needed to support a new
profession. Each pack declares:

- ``id`` / ``label``: stable identifier and display name.
- ``detect_keywords``: role / looking_for / skill phrases that identify the
  profession.
- ``vocabulary``: generic JD vocabulary used by the matcher's skill-gap
  detection and the cover-letter engine.
- ``cover_letters``: ``{fresher, mid, senior}`` sections, each holding three
  *block pools* -- ``openings``, ``bodies``, ``closings``. Every block is a
  dict with ``text`` (a ``{placeholder}`` template using the same keys as the
  cover-letter generator context), plus selection tags:

  - ``tone``: ``direct`` / ``story`` / ``formal`` / ``any``
  - ``company_types``: ``startup`` / ``corporate`` / ``nonprofit`` /
    ``healthcare`` / ``education`` / ``hospitality`` / ``government`` / ``any``
  - ``emphases``: optional list of JD emphasis categories the block speaks to
  - ``priority``: tie-breaker (lower wins)

``compose_cover_letter(pack, features)`` scores every block in the pack
against the JD feature vector -- seniority, tone, company type and emphases --
and assembles a unique letter from one opening, two to three bodies, and one
closing. Different JDs for the same person produce different letters: the
combination space is the product of the three pools.

Block placeholders (canonical contract, same as the cover-letter generator
context):

- ``{company}``, ``{possessive}`` (``"Company's"``), ``{title}``, ``{role}``
- ``{skills}`` (comma/and-joined matched skills), ``{primary}`` (best-fit
  project), ``{evidence}`` (grounded resume/project line)
- ``{need}`` (JD-derived hook), ``{depth}`` (seniority-depth sentence),
  ``{experience_years}``

``detect_profession(profile)`` scores every pack against the profile and
returns the best match, defaulting to ``"neutral"`` so every profession gets
the same output richness with zero configuration.
"""

from __future__ import annotations

import json
from pathlib import Path

PACKS_ROOT = Path(__file__).resolve().parent.parent / "profession_packs"

# Extra professions users can request in the onboarding wizard even before the
# packs ship; unknown ones fall back to the neutral pack.
KNOWN_PROFESSIONS = {
    "healthcare": "Healthcare",
    "education": "Education",
    "finance": "Finance / Accounting",
    "it": "IT / Software",
    "engineering": "Engineering (Non-Software)",
    "marketing": "Marketing / Sales",
    "sales": "Marketing / Sales",
    "hospitality": "Hospitality / Food Service",
    "trades": "Trades / Construction",
    "design": "Design / Creative",
    "legal": "Legal",
    "admin": "Administration / Operations",
    "science": "Science / Research",
    "retail": "Retail / Customer Service",
    "hr": "HR / People",
    "customer_service": "Retail / Customer Service",
}

_pack_cache: dict[str, dict] | None = None


def _load_all() -> dict[str, dict]:
    global _pack_cache
    if _pack_cache is not None:
        return _pack_cache
    packs: dict[str, dict] = {}
    if PACKS_ROOT.is_dir():
        for path in sorted(PACKS_ROOT.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    pack = json.load(f)
                if isinstance(pack, dict) and pack.get("id"):
                    packs[pack["id"]] = pack
            except (json.JSONDecodeError, OSError, ValueError):
                continue
    _pack_cache = packs
    return packs


def list_packs() -> list[dict]:
    """Return all packs (id/label), sorted, neutral first."""
    packs = _load_all()
    ordered = sorted(packs.values(), key=lambda p: p.get("label", ""))
    neutral = [p for p in ordered if p.get("id") == "neutral"]
    rest = [p for p in ordered if p.get("id") != "neutral"]
    return neutral + rest


def get_pack(pack_id: str) -> dict:
    """Return a pack by id, or the neutral pack when unknown/missing."""
    packs = _load_all()
    pack = packs.get(pack_id)
    if pack:
        return pack
    return packs.get("neutral", {"id": "neutral", "label": "General Professional",
                                 "detect_keywords": [], "vocabulary": [],
                                 "cover_letters": {}})


def _flatten_skills(profile: dict) -> list[str]:
    skills = []
    for cat in (profile.get("skills") or {}).values():
        if isinstance(cat, list):
            for s in cat:
                if isinstance(s, str) and s.strip():
                    skills.append(s.strip())
    return skills


def _profile_text(profile: dict) -> str:
    parts = []
    for key in ("profession", "role"):
        val = profile.get(key)
        if isinstance(val, str):
            parts.append(val)
    for val in profile.get("looking_for", []) or []:
        if isinstance(val, str):
            parts.append(val)
    parts.extend(_flatten_skills(profile))
    return " ".join(parts).lower()


def detect_profession(profile: dict) -> dict:
    """Return the pack best matching the profile (defaults to neutral)."""
    text = _profile_text(profile)
    if not text:
        return get_pack("neutral")

    best: dict = get_pack("neutral")
    best_score = 0
    for pack in _load_all().values():
        if pack.get("id") == "neutral":
            continue
        keywords = pack.get("detect_keywords") or []
        score = sum(1 for kw in keywords if kw and kw.lower() in text)
        if score > best_score:
            best_score = score
            best = pack
    return best


def pack_vocabulary(profile: dict) -> set[str]:
    """Skill-gap vocabulary for a profile: its pack's keywords, lowercased."""
    pack = detect_profession(profile)
    return {kw.lower() for kw in pack.get("vocabulary") or []}


def pack_for_job(job: dict, profile: dict) -> dict:
    """Detect a pack from a JD, preferring the profile pack on ties.

    Used by the cover-letter engine: the JD's own language may reveal a
    profession (e.g. a nurse job) even when the profile is sparse. The
    profile's own pack always participates in scoring and keeps any tie,
    so a Python developer never gets design-pack wording just because
    another pack matched the JD equally well.
    """
    jd_text = " ".join([
        str(job.get("title") or ""),
        str(job.get("description") or ""),
        str(job.get("company") or ""),
    ]).lower()
    if not jd_text:
        return detect_profession(profile)

    best = detect_profession(profile)
    best_id = best.get("id")
    best_score = sum(1 for kw in best.get("detect_keywords") or []
                     if kw and kw.lower() in jd_text)
    for pack in _load_all().values():
        pack_id = pack.get("id")
        if pack_id == "neutral" or pack_id == best_id:
            continue
        score = sum(1 for kw in pack.get("detect_keywords") or []
                    if kw and kw.lower() in jd_text)
        if score > best_score:
            best_score = score
            best = pack
    return best


# --- Minimal neutral JD feature vector for pack block selection --------------
#
# The engine's own classifier is richer (tech domains/emphases); this smaller
# extractor keeps the Django fallback self-contained while producing the same
# seniority/tone/company_type vocabulary the pack composer scores on.

_SENIOR_MARKERS = ("senior", "staff", "lead", "principal", "architect",
                   "head", "manager", "director")
_FRESHER_MARKERS = ("intern", "trainee", "fresher", "apprentice", "junior", "entry")

_FORMAL_SIGNALS = ("enterprise", "fortune", "multinational", "consulting", "mnc",
                   "banking", "regulated", "compliance", "insurance",
                   "governance", "corporate")
_STORY_SIGNALS = ("mission", "passionate", "journey", "make a difference",
                  "impact", "solving", "curious", "purpose", "change the way")
_DIRECT_SIGNALS = ("fast-paced", "move fast", "ship", "ownership",
                   "bias for action", "hit the ground", "hands-on")

_COMPANY_TYPE_SIGNALS = {
    "nonprofit": ["nonprofit", "ngo", "non-profit", "charity", "foundation",
                  "mission-driven", "social impact", "philanthropy", "society"],
    "healthcare": ["hospital", "clinic", "healthcare", "health care", "medical",
                   "health system", "patient", "nhs", "care home", "hospice"],
    "education": ["school", "university", "college", "academy", "institute",
                  "education", "campus", "school district", "teaching hospital"],
    "hospitality": ["hotel", "restaurant", "resort", "hospitality", "cafe",
                    "coffee", "travel", "tourism", "airline", "cruise"],
    "government": ["government", "ministry", "federal", "municipal",
                   "public sector", "state government", "agency", "administration"],
    "startup": ["startup", "series a", "series b", "series c", "seed",
                "early stage", "fast-paced", "move fast", "bias for action",
                "scrappy", "scale-up", "venture"],
    "corporate": ["enterprise", "fortune", "multinational", "global",
                  "consulting", "mnc", "corporation", "bank", "insurance",
                  "inc.", "ltd", "corp", "corporate"],
}


def features_for(job: dict, profile: dict) -> dict:
    """Minimal neutral feature vector: seniority / tone / company_type.

    ``emphases`` is empty here (the engine's classifier derives tech
    emphases); blocks tagged with emphases still score correctly because a
    missing tag matches anything.
    """
    title = (job.get("title") or "").lower()
    experience = profile.get("experience_years") or 0

    if any(m in title for m in _SENIOR_MARKERS):
        seniority = "senior"
    elif any(m in title for m in _FRESHER_MARKERS) or experience < 1.5:
        seniority = "fresher"
    else:
        seniority = "mid"

    text = " ".join([
        str(job.get("company") or ""),
        str(job.get("description") or ""),
        str(job.get("title") or ""),
    ]).lower()

    if any(s in text for s in _FORMAL_SIGNALS):
        tone = "formal"
    elif any(s in text for s in _STORY_SIGNALS):
        tone = "story"
    else:
        tone = "direct"

    company_type = "general"
    for ctype, signals in _COMPANY_TYPE_SIGNALS.items():
        if any(s in text for s in signals):
            company_type = ctype
            break

    return {
        "seniority": seniority,
        "tone": tone,
        "company_type": company_type,
        "emphases": set(),
    }


def _score_block(block: dict, features: dict) -> tuple[float, int]:
    """Score one block against the JD feature vector.

    Returns ``(score, priority)``; higher score wins, ties break on lower
    priority. Missing tags match anything (``"any"`` behaviour).
    """
    score = 0.0
    tone = features.get("tone")
    block_tone = block.get("tone") or "any"
    if block_tone == "any" or block_tone == tone:
        score += 3

    company_type = features.get("company_type")
    block_types = block.get("company_types") or ["any"]
    if "any" in block_types or company_type in block_types:
        score += 2

    emphases = set(features.get("emphases") or [])
    block_emphases = set(block.get("emphases") or [])
    score += min(2, len(emphases & block_emphases))

    priority = block.get("priority") if isinstance(block.get("priority"), int) else 99
    return score, -priority


def _pick(pool: list[dict], features: dict, exclude: set[int] | None = None) -> dict:
    """Pick the best block from a pool, optionally excluding indexes."""
    exclude = exclude or set()
    candidates = [(i, b) for i, b in enumerate(pool) if i not in exclude]
    if not candidates:
        return {}
    best = max(candidates, key=lambda ib: _score_block(ib[1], features))
    return best[1]


def compose_cover_letter(pack: dict, features: dict) -> str:
    """Assemble a unique letter body from the pack's block pools.

    Picks one opening, two to three bodies (senior gets three), and one
    closing -- each scored against the JD feature vector so the letter is
    tailored to the role, the candidate's seniority, the company type, and
    the JD's emphasis areas.
    """
    sections = (pack.get("cover_letters") or {}).get(features.get("seniority") or "mid") or {}
    openings = sections.get("openings") or []
    bodies = sections.get("bodies") or []
    closings = sections.get("closings") or []

    opening = _pick(openings, features)
    closing = _pick(closings, features)

    body_count = 3 if features.get("seniority") == "senior" else 2
    chosen: list[dict] = []
    used: set[int] = set()
    for _ in range(min(body_count, len(bodies))):
        pool = [(i, b) for i, b in enumerate(bodies) if i not in used]
        if not pool:
            break
        idx, block = max(pool, key=lambda ib: _score_block(ib[1], features))
        chosen.append(block)
        used.add(idx)

    parts = []
    if opening:
        parts.append(opening.get("text", ""))
    for block in chosen:
        if block.get("text"):
            parts.append(block["text"])
    if closing:
        parts.append(closing.get("text", ""))

    return "\n\n".join(p for p in parts if p and p.strip())
