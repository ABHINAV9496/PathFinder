import logging

import httpx

from apps.jobs.fetchers.common import normalize_remote_location
from apps.jobs.services import _extract_salary_from_text
from common.utils import html_to_markdown, make_uid

logger = logging.getLogger(__name__)

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_SOURCE = "remotive"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _display_location(location: str) -> str:
    if normalize_remote_location(location) == "remote":
        return "Remote"
    return (location or "").strip() or "Remote"


def _parse_remotive_job(job: dict) -> dict | None:
    title = (job.get("title") or "").strip()
    company = (job.get("company_name") or "").strip()
    if not title or not company:
        return None

    raw_location = (job.get("candidate_required_location") or "").strip()
    location = _display_location(raw_location)
    uid = make_uid(title, company, normalize_remote_location(raw_location))

    description = html_to_markdown(job.get("description") or "")
    salary, salary_display = _extract_salary_from_text(f"{title} {description}")

    category = (job.get("category") or "").strip()
    tags = job.get("tags") or []
    full_text = f"{title} {company} {description} {' '.join(tags)} {category}"

    return {
        "uid": uid,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posted_date": job.get("publication_date") or "",
        "source": REMOTIVE_SOURCE,
        "apply_email": "",
        "apply_url": job.get("url") or "",
        "search_query": f"remotive:{category}",
        "job_url": job.get("url") or "",
        "salary": salary,
        "salary_display": salary_display,
        "full_text": full_text,
    }


def fetch_remotive_jobs() -> list[dict]:
    jobs = []
    client = httpx.Client(
        http2=True,
        timeout=20,
        follow_redirects=True,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )
    try:
        logger.info(f"Fetching Remotive: {REMOTIVE_API_URL}")
        resp = client.get(REMOTIVE_API_URL)
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("jobs") if isinstance(payload, dict) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            parsed = _parse_remotive_job(item)
            if parsed:
                jobs.append(parsed)
        logger.info(f"  Got {len(jobs)} jobs from Remotive")
    except Exception as e:
        logger.error(f"  Remotive failed: {e}")
    finally:
        client.close()
    return jobs
