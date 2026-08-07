import logging

import httpx

from apps.jobs.fetchers.common import (
    annualize_salary,
    format_annual_range,
    normalize_remote_location,
    safe_int,
)
from common.utils import html_to_markdown, make_uid

logger = logging.getLogger(__name__)

JOBICY_API_URL = "https://jobicy.com/api/v2/remote-jobs"
JOBICY_SOURCE = "jobicy"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _to_text(value: object) -> str:
    """Coerce a Jobicy field to text (industry/jobType come back as lists)."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return (value or "").strip()


def _parse_jobicy_job(job: dict) -> dict | None:
    title = _to_text(job.get("jobTitle"))
    company = _to_text(job.get("companyName"))
    if not title or not company:
        return None

    location = _to_text(job.get("jobGeo")) or "Remote"
    uid = make_uid(title, company, normalize_remote_location(location))

    description = html_to_markdown(job.get("jobDescription") or job.get("jobExcerpt") or "")

    salary_min = annualize_salary(safe_int(job.get("salaryMin")), job.get("salaryPeriod"))
    salary_max = annualize_salary(safe_int(job.get("salaryMax")), job.get("salaryPeriod"))
    salary, salary_display = format_annual_range(
        salary_min, salary_max, _to_text(job.get("salaryCurrency"))
    )

    industry = _to_text(job.get("jobIndustry"))
    level = _to_text(job.get("jobLevel"))
    job_type = _to_text(job.get("jobType"))
    full_text = f"{title} {company} {description} {industry} {job_type} {level}"

    return {
        "uid": uid,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posted_date": job.get("pubDate") or "",
        "source": JOBICY_SOURCE,
        "apply_email": "",
        "apply_url": job.get("url") or "",
        "search_query": f"jobicy:{industry}",
        "job_url": job.get("url") or "",
        "salary": salary,
        "salary_display": salary_display,
        "full_text": full_text,
    }


def fetch_jobicy_jobs() -> list[dict]:
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
        logger.info(f"Fetching Jobicy: {JOBICY_API_URL}")
        resp = client.get(JOBICY_API_URL, params={"count": 100})
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("jobs") if isinstance(payload, dict) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                parsed = _parse_jobicy_job(item)
            except Exception:
                logger.exception("  Jobicy: skipping malformed job")
                continue
            if parsed:
                jobs.append(parsed)
        logger.info(f"  Got {len(jobs)} jobs from Jobicy")
    except Exception as e:
        logger.error(f"  Jobicy failed: {e}")
    finally:
        client.close()
    return jobs
