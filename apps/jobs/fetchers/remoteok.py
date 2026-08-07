import logging

import httpx

from apps.jobs.fetchers.common import format_annual_range, normalize_remote_location, safe_int
from common.utils import html_to_markdown, make_uid

logger = logging.getLogger(__name__)

REMOTEOK_API_URL = "https://remoteok.com/api"
REMOTEOK_SOURCE = "remoteok"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _parse_remoteok_job(job: dict) -> dict | None:
    title = (job.get("position") or "").strip()
    company = (job.get("company") or "").strip()
    if not title or not company:
        return None

    location = (job.get("location") or "").strip() or "Remote"
    uid = make_uid(title, company, normalize_remote_location(location))

    description = html_to_markdown(job.get("description") or "")

    salary_min = safe_int(job.get("salary_min"))
    salary_max = safe_int(job.get("salary_max"))
    salary, salary_display = format_annual_range(salary_min, salary_max, "USD")

    apply_url = (job.get("apply_url") or "").strip()
    tags = job.get("tags") or []
    full_text = f"{title} {company} {description} {' '.join(tags)}"

    return {
        "uid": uid,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posted_date": (job.get("date") or "").strip(),
        "source": REMOTEOK_SOURCE,
        "apply_email": "",
        "apply_url": apply_url,
        "search_query": REMOTEOK_SOURCE,
        "job_url": apply_url,
        "salary": salary,
        "salary_display": salary_display,
        "full_text": full_text,
    }


def fetch_remoteok_jobs() -> list[dict]:
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
        logger.info(f"Fetching RemoteOK: {REMOTEOK_API_URL}")
        resp = client.get(REMOTEOK_API_URL)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list):
            logger.warning("RemoteOK: unexpected payload shape")
            return jobs
        for item in payload:
            if not isinstance(item, dict):
                continue
            if "legal notice" in (item.get("description") or "").lower():
                continue
            parsed = _parse_remoteok_job(item)
            if parsed:
                jobs.append(parsed)
        logger.info(f"  Got {len(jobs)} jobs from RemoteOK")
    except Exception as e:
        logger.error(f"  RemoteOK failed: {e}")
    finally:
        client.close()
    return jobs
