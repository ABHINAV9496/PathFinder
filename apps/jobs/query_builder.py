"""Build job-search queries from the user's profile (any profession).

Every fetcher asks this module for its queries instead of importing the
hardcoded lists in ``config/queries.py``. When the profile carries no
``looking_for`` roles the legacy config defaults are used, so the app
always works with zero configuration.
"""

import logging

from apps.jobs.profile_manager import load_profile
from config.queries import (
    SEARCH_QUERIES as _DEFAULT_SEARCH_QUERIES,
    TECHNOPARK_QUERIES as _DEFAULT_TECHNOPARK_QUERIES,
    CUTSHORT_SEARCH_URLS as _DEFAULT_CUTSHORT_URLS,
    JOBDROP_QUERIES as _DEFAULT_JOBDROP_QUERIES,
    JOBDROP_SOURCES as _DEFAULT_JOBDROP_SOURCES,
)

logger = logging.getLogger(__name__)

MAX_KEYWORDS = 5
MAX_RSS_QUERIES = 12
MAX_JOBDROP_QUERIES = 6
MAX_CUTSHORT_URLS = 8

BROWSER_FREE_JOBDROP_SOURCES = [
    "adzuna",
    "jooble",
    "findwork",
    "the_muse",
    "remoteok",
    "weworkremotely",
]


def _roles(profile: dict) -> list[str]:
    roles = []
    for r in profile.get("looking_for") or []:
        if isinstance(r, str) and r.strip():
            roles.append(r.strip())
    if not roles and profile.get("role"):
        roles.append(str(profile["role"]).strip())
    return roles[:MAX_KEYWORDS]


def _locations(profile: dict) -> list[str]:
    locs: list[str] = []
    country = (profile.get("country") or "").strip().lower()
    location = (profile.get("location") or "").strip()

    if country:
        locs.append(country)

    tokens = [t.strip().lower() for t in location.split(",") if t.strip()]
    for token in tokens[:2]:
        if token and token not in locs:
            locs.append(token)

    if "remote" not in locs:
        locs.append("remote")
    if not country and "india" not in locs:
        locs.append("india")
    return locs


def get_search_queries() -> list[dict]:
    """RSS feed queries: role keywords x profile locations."""
    profile = load_profile()
    roles = _roles(profile)
    if not roles:
        return list(_DEFAULT_SEARCH_QUERIES)

    locations = _locations(profile)
    if len(locations) * len(roles) > MAX_RSS_QUERIES:
        roles = roles[: max(1, MAX_RSS_QUERIES // len(locations))]

    queries = []
    seen = set()
    for role in roles:
        for loc in locations:
            key = (role.lower(), loc)
            if key in seen:
                continue
            seen.add(key)
            queries.append({"keywords": role, "location": loc})
    return queries


def get_technopark_queries() -> list[dict]:
    """Technopark is Kerala-specific; only used when the profile is Kerala-based."""
    profile = load_profile()
    haystack = (
        f"{profile.get('country') or ''} {profile.get('location') or ''}".lower()
    )
    if not any(kw in haystack for kw in ("kerala", "kozhikode", "technopark", "infopark", "trivandrum", "kochi", "campus")):
        return []
    return list(_DEFAULT_TECHNOPARK_QUERIES)


def get_cutshort_urls() -> list[str]:
    """Cutshort search URLs built from the profile's target roles."""
    profile = load_profile()
    roles = _roles(profile)
    if not roles:
        return list(_DEFAULT_CUTSHORT_URLS)

    urls = []
    for role in roles:
        slug = "-".join(role.lower().split())
        urls.append(f"https://cutshort.io/jobs/{slug}-jobs")
        urls.append(f"https://cutshort.io/jobs/remote-{slug}-jobs")
    return urls[:MAX_CUTSHORT_URLS]


def get_jobdrop_queries() -> list[dict]:
    """Jobdrop queries: role x (remote + primary country/region)."""
    profile = load_profile()
    roles = _roles(profile)
    if not roles:
        return list(_DEFAULT_JOBDROP_QUERIES)

    country = (profile.get("country") or "").strip().lower() or "india"
    locations = _locations(profile)
    remote = "Remote" if "remote" in locations else country.capitalize()

    queries = []
    for role in roles[:MAX_JOBDROP_QUERIES]:
        queries.append({"search_term": role, "location": remote, "is_remote": "remote" in remote.lower()})
        queries.append({"search_term": role, "location": country.capitalize(), "is_remote": False})
    return queries


def get_jobdrop_sources() -> list[str]:
    """Only browser-free, HTTP-based Jobdrop sources.

    Browser/CAPTCHA-based sources (google, zip_recruiter, greenhouse,
    lever, workday, ashby, wellfound, naukri) either crash on Windows
    background threads or trip Google's CAPTCHA, so they are pruned.
    """
    return list(BROWSER_FREE_JOBDROP_SOURCES)
