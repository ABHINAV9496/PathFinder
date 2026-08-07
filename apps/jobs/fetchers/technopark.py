import html as html_mod
import json as json_mod
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from apps.jobs.query_builder import get_technopark_queries
from apps.jobs.services import _extract_salary_from_text
from common.utils import html_to_markdown, make_uid

logger = logging.getLogger(__name__)

TECHNOPARK_API = "https://technopark.in/api/paginated-jobs"
TECHNOPARK_DETAIL = "https://technopark.in/job-details/{job_id}?job={title}"


def _fetch_job_detail(job_id: int, title: str, client: httpx.Client) -> dict:
    url = TECHNOPARK_DETAIL.format(job_id=job_id, title=title.replace(" ", "+"))
    try:
        resp = client.get(url, follow_redirects=True, timeout=15)
        if resp.status_code != 200:
            return {}

        m = re.search(r'data-page="([^"]+)"', resp.text)
        if not m:
            return {}

        decoded = html_mod.unescape(m.group(1))
        data = json_mod.loads(decoded)
        job_listing = data.get("props", {}).get("jobListing", {})
        return job_listing
    except Exception as e:
        logger.debug(f"  Detail fetch failed for {title}: {e}")
        return {}


def _build_job_dict(item: dict, detail: dict, location_hint: str, keywords: str) -> dict | None:
    title = item.get("job_title", "").strip()
    company_obj = item.get("company", {})
    company = company_obj.get("company", "").strip() if company_obj else ""

    if not title or not company:
        return None

    uid = make_uid(title, company)
    posted = item.get("posted_date", "")
    job_id = item.get("id", 0)

    description = html_to_markdown(detail.get("job_description", ""))
    contact_email = detail.get("contact_email", "")
    location = (
        detail.get("address", "")
        or detail.get("location", "")
        or location_hint
        or "Technopark, Trivandrum"
    )

    if not description:
        description = f"{title} position at {company}. Located at Technopark, Trivandrum."

    apply_url = f"https://technopark.in/job-details/{job_id}?job={title.replace(' ', '+')}"
    full_text = f"{title} {company} {description} {location}"
    salary, salary_display = _extract_salary_from_text(f"{title} {description}")

    return {
        "uid": uid,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posted_date": posted,
        "source": "technopark",
        "apply_email": contact_email,
        "apply_url": apply_url,
        "search_query": f"technopark: {keywords}",
        "job_url": apply_url,
        "salary": salary,
        "salary_display": salary_display,
        "full_text": full_text,
    }


def fetch_technopark_jobs(max_per_query: int = 25) -> list[dict]:
    all_jobs = []
    seen_uids = set()
    detail_items = []

    client = httpx.Client(
        timeout=30,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        },
    )

    for query in get_technopark_queries():
        keywords = query["keywords"]
        location_hint = query.get("location", "")
        logger.info(f"Technopark: Searching '{keywords}'...")

        for page in range(1, 4):
            try:
                resp = client.get(
                    TECHNOPARK_API,
                    params={"page": page, "search": keywords, "type": ""},
                )
                if resp.status_code != 200:
                    logger.warning(f"  API returned {resp.status_code}")
                    break

                data = resp.json()
                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    title = item.get("job_title", "").strip()
                    company_obj = item.get("company", {})
                    company = company_obj.get("company", "").strip() if company_obj else ""

                    if not title or not company:
                        continue

                    uid = make_uid(title, company)
                    if uid in seen_uids:
                        continue
                    seen_uids.add(uid)

                    detail_items.append((item, location_hint, keywords))

                logger.info(f"  Page {page}: {len(items)} jobs")

                if len(items) < 10:
                    break

            except Exception as e:
                logger.error(f"  Technopark error: {e}")
                break

    client.close()

    if detail_items:
        def _fetch_one(args):
            item, loc_hint, kw = args
            jid = item.get("id", 0)
            title = item.get("job_title", "").strip()
            c = httpx.Client(timeout=15, follow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            try:
                detail = _fetch_job_detail(jid, title, c)
                return item, detail, loc_hint, kw
            finally:
                c.close()

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_fetch_one, args): args for args in detail_items}
            for future in as_completed(futures):
                try:
                    item, detail, loc_hint, kw = future.result()
                    job = _build_job_dict(item, detail, loc_hint, kw)
                    if job and job["uid"] not in all_jobs:
                        all_jobs.append(job)
                except Exception as e:
                    logger.error(f"  Detail fetch error: {e}")

    logger.info(f"Technopark total: {len(all_jobs)} unique jobs")
    return all_jobs
