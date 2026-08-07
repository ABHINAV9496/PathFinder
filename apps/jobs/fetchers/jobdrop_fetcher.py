import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.utils import make_uid
from apps.jobs.profile_manager import load_profile
from apps.jobs.query_builder import get_jobdrop_queries, get_jobdrop_sources

logger = logging.getLogger(__name__)

JOBDROP_HOURS_OLD = 72
JOBDROP_RESULTS_WANTED = 30


def _map_salary(row) -> tuple[int, str]:
    """Extract salary from Jobdrop's compensation fields."""
    try:
        min_amt = getattr(row, "min_amount", None)
        max_amt = getattr(row, "max_amount", None)
        interval = getattr(row, "interval", None)
        currency = getattr(row, "currency", "USD")

        if not min_amt and not max_amt:
            return 0, ""

        min_val = int(min_amt) if min_amt else 0
        max_val = int(max_amt) if max_amt else 0

        if interval == "yearly":
            annual = max_val or min_val
            if min_val and max_val:
                display = f"{currency} {min_val:,}-{max_val:,}/yr"
            else:
                display = f"{currency} {annual:,}/yr"
        elif interval == "monthly":
            annual = (max_val or min_val) * 12
            if min_val and max_val:
                display = f"{currency} {min_val:,}-{max_val:,}/mo"
            else:
                display = f"{currency} {annual:,}/yr"
        elif interval == "hourly":
            annual = (max_val or min_val) * 2080
            if min_val and max_val:
                display = f"{currency} {min_val:,}-{max_val:,}/hr"
            else:
                display = f"{currency} {annual:,}/yr"
        else:
            annual = max_val or min_val
            display = f"{currency} {annual:,}"

        return annual, display
    except Exception:
        return 0, ""


def _map_location(row) -> str:
    """Build a location string from Jobdrop's location fields."""
    try:
        loc = getattr(row, "location", None)
        if loc and isinstance(loc, dict):
            parts = [
                loc.get("city", ""),
                loc.get("state", ""),
                loc.get("country", ""),
            ]
            return ", ".join(p for p in parts if p) or "Not specified"
        if loc and isinstance(loc, str):
            return loc
    except Exception:
        pass
    return "Not specified"


def _site_name(value) -> str:
    """Return the plain source string from a jobdrop Site enum or str."""
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _fetch_single_jobdrop_query(query: dict) -> list[dict]:
    """Fetch one Jobdrop query. Returns list of job dicts."""
    search_term = query["search_term"]
    location = query["location"]
    is_remote = bool(query.get("is_remote"))
    jobs = []

    try:
        from jobdrop import scrape_jobs
    except ImportError:
        logger.error("jobdrop not installed")
        return []

    country_indeed = (load_profile().get("country") or "").strip().lower() or "india"

    try:
        df = scrape_jobs(
            site_name=get_jobdrop_sources(),
            search_term=search_term,
            location=location,
            results_wanted=JOBDROP_RESULTS_WANTED,
            country_indeed=country_indeed,
            is_remote=is_remote,
            hours_old=JOBDROP_HOURS_OLD,
            verbose=0,
        )

        if df is None or df.empty:
            logger.info(f"Jobdrop: No results for '{search_term}' in '{location}'")
            return []

        per_source = (df.attrs or {}).get("per_source", {})
        contributed = {s: d.get("count", 0) for s, d in per_source.items()}
        if contributed:
            logger.info(f"Jobdrop per_source: {contributed}")
        else:
            logger.warning(f"Jobdrop per_source telemetry missing for '{search_term}'")

        for _, row in df.iterrows():
            title = str(getattr(row, "title", "")).strip()
            company = str(getattr(row, "company", "")).strip()

            if not title or not company:
                continue

            location_str = _map_location(row)
            uid = make_uid(title, company, location_str)

            salary, salary_display = _map_salary(row)
            description = str(getattr(row, "description", "") or "")
            job_url = str(getattr(row, "job_url", "") or "")
            date_posted = str(getattr(row, "date_posted", "") or "")
            site = _site_name(getattr(row, "site", ""))
            full_text = f"{title} {company} {description} {location_str}"

            jobs.append({
                "uid": uid,
                "title": title,
                "company": company,
                "location": location_str,
                "description": description,
                "posted_date": date_posted,
                "source": f"jobdrop:{site}" if site else "jobdrop",
                "apply_email": "",
                "apply_url": job_url,
                "search_query": f"jobdrop: {search_term} in {location}",
                "job_url": job_url,
                "salary": salary,
                "salary_display": salary_display,
                "full_text": full_text,
            })

        logger.info(f"Jobdrop: '{search_term}' in '{location}' → {len(jobs)} jobs")

    except Exception as e:
        logger.error(f"Jobdrop error for '{search_term}': {e}")

    return jobs


def fetch_jobdrop_jobs() -> list[dict]:
    """Fetch jobs from Jobdrop sources in parallel."""
    queries = get_jobdrop_queries()
    if not queries:
        return []

    all_jobs = []
    seen_uids = set()

    with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as pool:
        futures = {pool.submit(_fetch_single_jobdrop_query, q): q for q in queries}
        for future in as_completed(futures):
            try:
                for job in future.result():
                    if job["uid"] not in seen_uids:
                        seen_uids.add(job["uid"])
                        all_jobs.append(job)
            except Exception as e:
                logger.error(f"Jobdrop query failed: {e}")

    logger.info(f"Jobdrop total: {len(all_jobs)} unique jobs")
    return all_jobs
