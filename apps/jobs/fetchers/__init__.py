import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from bs4 import BeautifulSoup

from apps.jobs.fetchers.cutshort import fetch_cutshort_jobs
from apps.jobs.fetchers.jobdrop_fetcher import fetch_jobdrop_jobs
from apps.jobs.fetchers.technopark import fetch_technopark_jobs
from apps.jobs.services import _extract_salary_from_text
from common.utils import make_uid, deduplicate_jobs
from config.queries import SEARCH_QUERIES
from config.settings import FEED_BASE_URL

logger = logging.getLogger(__name__)


def _parse_rss_xml(xml_text: str, query: dict) -> list[dict]:
    soup = BeautifulSoup(xml_text, "xml")
    jobs = []

    for item in soup.find_all("item"):
        title_tag = item.find("title")
        link_tag = item.find("link")
        desc_tag = item.find("description")
        pub_tag = item.find("pubDate")

        if not title_tag:
            continue

        raw_title = title_tag.get_text(strip=True)

        if " at " in raw_title:
            parts = raw_title.rsplit(" at ", 1)
            title = parts[0].strip()
            company = parts[1].strip()
        else:
            title = raw_title
            company = ""

        location = ""
        description = ""
        source = ""
        posted = pub_tag.get_text(strip=True) if pub_tag else ""
        apply_url = link_tag.get_text(strip=True) if link_tag else ""

        if desc_tag:
            desc_html = desc_tag.decode_contents()
            desc_soup = BeautifulSoup(desc_html, "html.parser")
            desc_text = desc_soup.get_text(separator="\n", strip=True)
            description = desc_text

            for line in desc_text.split("\n"):
                line = line.strip()
                low = line.lower()
                if low.startswith("location:") or low.startswith("location :"):
                    location = line.split(":", 1)[1].strip() if ":" in line else ""
                elif low.startswith("source:") or low.startswith("source :"):
                    source = line.split(":", 1)[1].strip() if ":" in line else ""

            src_link = desc_soup.find("a")
            if src_link:
                source = src_link.get_text(strip=True)
                src_href = src_link.get("href", "")
                if src_href and not apply_url:
                    apply_url = src_href

        if not location:
            location = query.get("location", "")

        if not company:
            continue

        uid = make_uid(title, company)
        full_text = f"{title} {company} {description} {location} {source}"

        salary, salary_display = _extract_salary_from_text(f"{title} {description}")

        jobs.append({
            "uid": uid,
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "posted_date": posted,
            "source": source,
            "apply_email": "",
            "apply_url": apply_url,
            "search_query": f"{query['keywords']} in {query['location']}",
            "job_url": apply_url,
            "salary": salary,
            "salary_display": salary_display,
            "full_text": full_text,
        })

    return jobs


def _ensure_feed_exists(client: httpx.Client, query: dict):
    keywords = query["keywords"]
    location = query["location"]

    try:
        client.post(
            FEED_BASE_URL,
            data={"keywords": keywords, "location": location},
            headers={
                "HX-Request": "true",
                "HX-Target": "content",
                "HX-Swap": "innerHTML",
            },
        )
    except Exception as e:
        logger.debug(f"POST feed creation skipped for {keywords} in {location}: {e}")


def _fetch_single_rss_query(query: dict) -> list[dict]:
    """Fetch a single RSS query. Returns list of job dicts."""
    keywords = query["keywords"]
    location = query["location"]
    jobs = []

    client = httpx.Client(
        http2=True,
        timeout=20,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )

    try:
        resp = client.get(
            FEED_BASE_URL,
            params={"keywords": keywords, "location": location},
        )
        if resp.status_code == 404:
            logger.warning(f"RSS: Feed not found (creating): {keywords} in {location}")
            _ensure_feed_exists(client, query)
            resp = client.get(
                FEED_BASE_URL,
                params={"keywords": keywords, "location": location},
            )
        resp.raise_for_status()
        jobs = _parse_rss_xml(resp.text, query)
        logger.info(f"RSS: {keywords} in {location} → {len(jobs)} jobs")
    except httpx.HTTPStatusError as e:
        logger.error(f"RSS: HTTP {e.response.status_code} for {keywords} in {location}")
    except Exception as e:
        logger.error(f"RSS: Failed {keywords} in {location}: {e}")
    finally:
        client.close()

    return jobs


def fetch_rss_jobs() -> list[dict]:
    all_jobs = []
    seen_uids = set()

    with ThreadPoolExecutor(max_workers=len(SEARCH_QUERIES)) as pool:
        futures = {pool.submit(_fetch_single_rss_query, q): q for q in SEARCH_QUERIES}
        for future in as_completed(futures):
            try:
                for job in future.result():
                    if job["uid"] not in seen_uids:
                        seen_uids.add(job["uid"])
                        all_jobs.append(job)
            except Exception as e:
                logger.error(f"RSS query failed: {e}")

    logger.info(f"RSS total: {len(all_jobs)} unique jobs")
    return all_jobs


def _safe_fetch(name: str, func) -> list[dict]:
    """Run a fetcher, return jobs or empty list on error."""
    try:
        return func()
    except Exception as e:
        logger.error(f"{name} scraper failed: {e}")
        return []


def fetch_all_jobs() -> tuple[list[dict], dict]:
    all_jobs = []
    seen_uids = set()
    source_stats = {}
    failed_sources = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_safe_fetch, "RSS", fetch_rss_jobs): "rss",
            pool.submit(_safe_fetch, "Technopark", fetch_technopark_jobs): "technopark",
            pool.submit(_safe_fetch, "Cutshort", fetch_cutshort_jobs): "cutshort",
            pool.submit(_safe_fetch, "Jobdrop", fetch_jobdrop_jobs): "jobdrop",
        }

        for future in as_completed(futures):
            source = futures[future]
            try:
                jobs = future.result()
                source_stats[source] = len(jobs)
                if not jobs:
                    failed_sources.append(source)
                for job in jobs:
                    if job["uid"] not in seen_uids:
                        seen_uids.add(job["uid"])
                        all_jobs.append(job)
                logger.info(f"  {source}: contributed {len(jobs)} jobs")
            except Exception as e:
                source_stats[source] = 0
                failed_sources.append(source)
                logger.error(f"  {source} failed: {e}")

    before_dedup = len(all_jobs)
    all_jobs = deduplicate_jobs(all_jobs)
    dups_removed = before_dedup - len(all_jobs)

    stats = {
        "by_source": source_stats,
        "failed": failed_sources,
        "before_dedup": before_dedup,
        "dups_removed": dups_removed,
        "final": len(all_jobs),
    }

    logger.info(
        f"Total: {before_dedup} exact-unique, "
        f"{dups_removed} fuzzy-duplicates removed, "
        f"{len(all_jobs)} final | by source: {source_stats}"
    )
    return all_jobs, stats
