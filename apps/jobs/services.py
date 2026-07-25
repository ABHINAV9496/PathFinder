import json
import re
import logging
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from django.db.models import Count

from apps.jobs.models import Job, Application, SkillLog, DailyStats, RawJob, JobEvent
from config.constants import RECRUITER_KEYWORDS
from config.settings import MIN_SALARY
from common.utils import is_company_email as _validate_company_email, EMAIL_REGEX, JUNK_DOMAINS, html_to_markdown

logger = logging.getLogger(__name__)

SALARY_PATTERNS = [
    r"(?:upto|up\s*to|max|maximum|capped?\s*at)\s*[\u20b9\uffe0Rs\.]*\s*(\d[\d,]*)\s*(?:[-\u2013to]+\s*[\u20b9\uffe0Rs\.]*\s*(\d[\d,]*))?\s*(?:lpa|lakhs?|per\s*annum|p\.?a\.?)",
    r"[\u20b9\uffe0Rs\.]+\s*(\d[\d,]*)\s*[-\u2013to]+\s*[\u20b9\uffe0Rs\.]*\s*(\d[\d,]*)\s*(?:lpa|lakhs?|per\s*annum|p\.?a\.?|per\s*month|pm|monthly)?",
    r"[\u20b9\uffe0Rs\.]+\s*(\d[\d,]*)\s*/?-?\s*(?:lpa|lakhs?|per\s*annum|p\.?a\.?|per\s*month|pm|monthly|k\b)",
    r"(?:ctc|stipend|salary|package|compensation|pay)\s*[:\s]*[\u20b9\uffe0Rs\.INR]*\s*(\d[\d,]*)\s*[-\u2013to]+\s*(\d[\d,]*)\s*(?:lpa|lakhs?|k|per\s*month|pm|monthly)?",
    r"(?:ctc|stipend|salary|package|compensation|pay)\s*[:\s]*[\u20b9\uffe0Rs\.INR]*\s*(\d[\d,]*)\s*(?:lpa|lakhs?|k|per\s*month|pm|monthly|per\s*annum|p\.?a\.?|/month)",
    r"(\d[\d,]*)\s*[-\u2013to]+\s*(\d[\d,]*)\s*(?:lpa|lakhs?|per\s*annum|p\.?a\.?)",
    r"(\d[\d,]*)\s*[-\u2013to]+\s*(\d[\d,]*)\s*(?:k|,?000)\s*(?:per\s*month|pm|monthly|/month)?",
    r"(\d[\d,]*)\s*(?:lpa|lakhs?|per\s*annum|p\.?a\.?)",
    r"(\d[\d,]*)\s*(?:k|,?000)\s*(?:per\s*month|pm|monthly|/month)",
]

_SALARY_NEGATIVE = [
    "program fee", "training fee", "course fee", "certification fee",
    "internship fee", "enrollment fee", "registration fee",
    "tuition", "cost of", "price of", "investment of",
    "you pay", "candidate pays", "participant pays",
]


def _format_salary(amount: int) -> str:
    if amount >= 100000:
        return f"\u20b9{amount // 100000}L PA"
    elif amount >= 1000:
        return f"\u20b9{amount // 1000}K"
    return f"\u20b9{amount:,}"


def _extract_salary_from_text(text: str) -> tuple[int, str]:
    text_lower = text.lower()

    if any(w in text_lower for w in [
        "competitive salary", "negotiable", "market rate", "based on experience"
    ]):
        return 0, ""

    for pat in SALARY_PATTERNS:
        matches = re.finditer(pat, text, re.IGNORECASE)
        for m in matches:
            groups = m.groups()
            numbers = []
            for g in groups:
                if g:
                    clean = g.replace(",", "").replace(" ", "")
                    try:
                        numbers.append(int(clean))
                    except ValueError:
                        pass

            if not numbers:
                continue

            salary = max(numbers)
            window_start = max(0, m.start() - 60)
            window_end = min(len(text_lower), m.end() + 60)
            context = text_lower[window_start:window_end]

            if any(neg in context for neg in _SALARY_NEGATIVE):
                continue

            has_annual_ctx = "lpa" in context or "lakhs" in context or "lakh" in context or "per annum" in context or "p.a." in context
            has_monthly_ctx = "per month" in context or "pm" in context or "monthly" in context or "/month" in context
            has_k_ctx = "k" in context and not has_annual_ctx

            if has_annual_ctx:
                if salary < 100000:
                    salary = salary * 100000
            elif has_monthly_ctx:
                if has_k_ctx:
                    salary = salary * 1000
                salary = salary * 12
            elif has_k_ctx:
                salary = salary * 1000
            elif salary < 1000:
                salary = salary * 1000
            elif salary >= 1000 and salary < 100000:
                salary = salary * 100000

            if salary > 50000000:
                continue

            if salary >= MIN_SALARY:
                return salary, _format_salary(salary)

    return 0, ""


def job_exists(uid: str) -> bool:
    return Job.objects.filter(uid=uid).exists()


def save_job(job_data: dict) -> Job:
    salary = job_data.get("salary", 0)
    salary_display = job_data.get("salary_display", "")

    if not salary:
        search_text = f"{job_data.get('full_text', '')} {job_data.get('description', '')}"
        salary, salary_display = _extract_salary_from_text(search_text)

    if salary and not salary_display:
        salary_display = _format_salary(salary)

    description = job_data.get("description", "")
    if description and "<" in description:
        description = html_to_markdown(description)

    existing = Job.objects.filter(uid=job_data["uid"]).first()

    defaults = {
        "title": job_data.get("title", ""),
        "company": job_data.get("company", ""),
        "location": job_data.get("location", ""),
        "description": description,
        "source": job_data.get("source", ""),
        "posted_date": job_data.get("posted_date", ""),
        "match_score": job_data.get("match_score", 0),
        "status": job_data.get("status", "new"),
        "apply_email": job_data.get("apply_email", ""),
        "apply_url": job_data.get("apply_url", ""),
        "search_query": job_data.get("search_query", ""),
        "matched_skills": job_data.get("matched_skills", []),
        "skill_score_breakdown": job_data.get("skill_score_breakdown", {}),
        "skill_gaps": job_data.get("skill_gaps", []),
        "filter_reason": job_data.get("filter_reason", ""),
        "match_explanation": job_data.get("match_explanation", ""),
        "job_url": job_data.get("job_url", ""),
    }

    if existing:
        if salary:
            defaults["salary"] = salary
            defaults["salary_display"] = salary_display
        elif not existing.salary:
            defaults["salary"] = 0
            defaults["salary_display"] = ""
        else:
            pass
        job = existing
        for k, v in defaults.items():
            setattr(job, k, v)
        job.save()
        created = False
    else:
        defaults["salary"] = salary
        defaults["salary_display"] = salary_display
        job, created = Job.objects.update_or_create(
            uid=job_data["uid"],
            defaults=defaults,
        )

    if not created:
        new_status = job_data.get("status", "")
        if new_status and new_status != job.status:
            old_status = job.status
            job.status = new_status
            job.save()
            JobEvent.objects.create(
                job=job, event_type="status_changed",
                old_status=old_status, new_status=new_status,
                match_score=job_data.get("match_score", 0),
            )

    return job


def bulk_save_jobs(jobs_list: list[dict]) -> None:
    """Batch-save jobs with fewer DB round-trips."""
    if not jobs_list:
        return

    uids = [j["uid"] for j in jobs_list]
    existing_map = {
        j.uid: j for j in Job.objects.filter(uid__in=uids)
    }

    to_create = []
    to_update = []

    for job_data in jobs_list:
        salary = job_data.get("salary", 0)
        salary_display = job_data.get("salary_display", "")

        if not salary:
            search_text = f"{job_data.get('full_text', '')} {job_data.get('description', '')}"
            salary, salary_display = _extract_salary_from_text(search_text)

        if salary and not salary_display:
            salary_display = _format_salary(salary)

        description = job_data.get("description", "")
        if description and "<" in description:
            description = html_to_markdown(description)

        defaults = {
            "title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "location": job_data.get("location", ""),
            "description": description,
            "source": job_data.get("source", ""),
            "posted_date": job_data.get("posted_date", ""),
            "match_score": job_data.get("match_score", 0),
            "status": job_data.get("status", "new"),
            "apply_email": job_data.get("apply_email", ""),
            "apply_url": job_data.get("apply_url", ""),
            "search_query": job_data.get("search_query", ""),
            "matched_skills": job_data.get("matched_skills", []),
            "skill_score_breakdown": job_data.get("skill_score_breakdown", {}),
            "skill_gaps": job_data.get("skill_gaps", []),
            "filter_reason": job_data.get("filter_reason", ""),
            "match_explanation": job_data.get("match_explanation", ""),
            "job_url": job_data.get("job_url", ""),
            "salary": salary,
            "salary_display": salary_display,
        }

        existing = existing_map.get(job_data["uid"])
        if existing:
            for k, v in defaults.items():
                setattr(existing, k, v)
            to_update.append(existing)
        else:
            to_create.append(Job(uid=job_data["uid"], **defaults))

    if to_create:
        Job.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=200)

    if to_update:
        Job.objects.bulk_update(to_update, [
            "title", "company", "location", "description", "source",
            "posted_date", "match_score", "status", "apply_email", "apply_url",
            "search_query", "matched_skills", "skill_score_breakdown", "skill_gaps",
            "filter_reason", "match_explanation", "job_url", "salary", "salary_display",
        ], batch_size=200)


def save_application(job: Job, result: dict) -> Application:
    criteria = {
        "skills_in_jd": result.get("skills_in_jd", []),
        "skills_highlighted": result.get("skills_highlighted", []),
        "sections_included": result.get("sections_included", []),
        "project_mentioned": result.get("project_mentioned", ""),
        "role_level": result.get("role_level", ""),
        "min_years_required": result.get("min_years_required"),
        "email_used": job.apply_email,
        "email_domain_valid": bool(job.apply_email),
        "resume_attached": True,
        "match_score": job.match_score,
    }

    existing = Application.objects.filter(job=job).first()

    app, created = Application.objects.update_or_create(
        job=job,
        defaults={
            "email_subject": result.get("email_subject", ""),
            "cover_letter_text": result.get("cover_letter", "") or (existing.cover_letter_text if existing else ""),
            "status": "sent" if result.get("success") else "failed",
            "error_message": "" if result.get("success") else result.get("message", ""),
            "skills_highlighted": result.get("skills_highlighted", []),
            "skills_in_job_desc": result.get("skills_in_jd", []),
            "skill_match_pct": job.match_score,
            "criteria_data": criteria,
            "skill_gaps": job.skill_gaps,
            "match_explanation": job.match_explanation,
        },
    )

    if created:
        for skill in result.get("skills_highlighted", job.matched_skills):
            SkillLog.objects.create(
                application=app,
                job=job,
                skill_name=skill,
                found_in_job_desc=True,
                highlighted_in_cover_letter=True,
            )

    return app


def save_web_apply(job: Job, result: dict) -> Application:
    criteria = {
        "skills_in_jd": result.get("skills_in_jd", []),
        "skills_highlighted": result.get("skills_highlighted", []),
        "sections_included": result.get("sections_included", []),
        "project_mentioned": result.get("project_mentioned", ""),
        "role_level": result.get("role_level", ""),
        "min_years_required": result.get("min_years_required"),
        "email_used": "",
        "email_domain_valid": False,
        "resume_attached": False,
        "match_score": job.match_score,
        "apply_url": job.apply_url,
    }

    app, created = Application.objects.update_or_create(
        job=job,
        defaults={
            "email_subject": result.get("email_subject", ""),
            "cover_letter_text": result.get("cover_letter", ""),
            "status": "web_apply",
            "error_message": "No company email \u2014 manual apply via: " + (job.apply_url or ""),
            "skills_highlighted": result.get("skills_highlighted", []),
            "skills_in_job_desc": result.get("skills_in_jd", []),
            "skill_match_pct": job.match_score,
            "criteria_data": criteria,
            "skill_gaps": job.skill_gaps,
            "match_explanation": job.match_explanation,
        },
    )
    return app


def update_daily_stats():
    today = date.today()
    stats, _ = DailyStats.objects.get_or_create(date=today)
    stats.total_fetched = RawJob.objects.filter(fetched_at__date=today).count()
    stats.total_matched = JobEvent.objects.filter(event_type="matched", created_at__date=today).count()
    stats.total_applied = Application.objects.filter(sent_at__date=today, status="sent").count()
    stats.total_ignored = JobEvent.objects.filter(event_type="ignored", created_at__date=today).count()
    stats.total_failed = Application.objects.filter(sent_at__date=today, status="failed").count()

    top_skills = (
        SkillLog.objects
        .filter(created_at__date=today)
        .values("skill_name")
        .annotate(count=Count("skill_name"))
        .order_by("-count")[:20]
    )
    stats.top_keywords = [s["skill_name"] for s in top_skills]

    top_companies = (
        Application.objects
        .filter(sent_at__date=today)
        .values("job__company")
        .annotate(count=Count("job__company"))
        .order_by("-count")[:20]
    )
    stats.top_companies = [c["job__company"] for c in top_companies]
    stats.save()


def get_recent_jobs(limit=50):
    return Job.objects.all()[:limit]


def get_matched_jobs():
    return Job.objects.filter(status__in=["matched", "applied"]).order_by("-match_score")


def get_all_applications():
    return Application.objects.select_related("job").order_by("-sent_at")


def get_job_stats():
    return {
        "total_jobs": Job.objects.count(),
        "total_matched": Job.objects.filter(status="matched").count(),
        "total_applied": Application.objects.filter(status="sent").count(),
        "total_failed": Application.objects.filter(status="failed").count(),
        "total_ignored": Job.objects.filter(status="ignored").count(),
    }


def is_company_email(email: str, company: str = "") -> bool:
    is_valid, reason = _validate_company_email(email)
    if not is_valid:
        return False

    email = email.lower().strip()
    domain = email.split("@")[1]

    if company:
        company_slug = re.sub(r"[^a-z0-9]", "", company.lower())
        if company_slug and len(company_slug) >= 3:
            if company_slug in domain:
                return True

    if any(kw in domain for kw in RECRUITER_KEYWORDS):
        return False

    if email.startswith("noreply@") or email.startswith("no-reply@"):
        return False

    if len(email) > 60:
        return False

    return True


def _extract_emails_from_text(text: str) -> list[str]:
    raw = EMAIL_REGEX.findall(text)
    return [e.lower() for e in raw if is_company_email(e)]


def _get_http_client() -> httpx.Client:
    return httpx.Client(
        http2=True, timeout=15, follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def find_job_salary(job: dict, client: httpx.Client | None = None) -> tuple[int, str]:
    close_client = False
    if client is None:
        client = _get_http_client()
        close_client = True

    try:
        url = job.get("apply_url", "")
        if not url:
            return 0, ""

        try:
            resp = client.get(url, follow_redirects=True, timeout=15)
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                page_text = soup.get_text(separator="\n", strip=True)
                salary, salary_display = _extract_salary_from_text(page_text)
                if salary:
                    logger.info(f"  Found salary from page: {salary_display}")
                    return salary, salary_display
        except Exception as e:
            logger.debug(f"  Page fetch failed for salary: {e}")

        description = f"{job.get('title', '')} {job.get('description', '')} {job.get('full_text', '')}"
        return _extract_salary_from_text(description)

    finally:
        if close_client:
            client.close()

    return 0, ""


def _fetch_salary_for_job(job: dict) -> tuple[int, str]:
    client = _get_http_client()
    try:
        return find_job_salary(job, client)
    finally:
        client.close()


def enrich_jobs_with_salaries(jobs: list[dict], batch_size: int = 5) -> list[dict]:
    candidates = [
        (i, job) for i, job in enumerate(jobs)
        if not job.get("salary", 0) and job.get("apply_url")
    ]

    if not candidates:
        return jobs

    enriched = 0
    with ThreadPoolExecutor(max_workers=min(len(candidates), 8)) as pool:
        future_to_idx = {
            pool.submit(_fetch_salary_for_job, job): i
            for i, job in candidates
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                salary, salary_display = future.result()
                if salary:
                    jobs[idx]["salary"] = salary
                    jobs[idx]["salary_display"] = salary_display
                    enriched += 1
            except Exception as e:
                logger.debug(f"  Salary enrichment failed: {e}")

    logger.info(f"Enriched {enriched}/{len(jobs)} jobs with salary from detail pages")
    return jobs


def find_job_email(job: dict, client: httpx.Client | None = None) -> str:
    if job.get("apply_email"):
        if is_company_email(job["apply_email"], job.get("company", "")):
            return job["apply_email"]
        else:
            logger.info(f"  Rejected email {job['apply_email']} (not company domain)")
            job["apply_email"] = ""

    close_client = False
    if client is None:
        client = httpx.Client(
            http2=True, timeout=15, follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        close_client = True

    try:
        url = job.get("apply_url", "")
        if not url:
            return ""

        try:
            resp = client.get(url, follow_redirects=True, timeout=15)
            if resp.status_code == 200:
                all_emails = _extract_emails_from_text(resp.text)
                company = job.get("company", "")
                emails = [e for e in all_emails if is_company_email(e, company)]
            else:
                emails = []
        except Exception:
            emails = []

        if emails:
            email = emails[0]
            logger.info(f"  Found company email: {email}")
            return email

        description = job.get("description", "") + " " + job.get("full_text", "")
        desc_emails = _extract_emails_from_text(description)
        company = job.get("company", "")
        desc_emails_valid = [e for e in desc_emails if is_company_email(e, company)]
        if desc_emails_valid:
            return desc_emails_valid[0]

    except Exception as e:
        logger.debug(f"Email extraction failed: {e}")

    finally:
        if close_client:
            client.close()

    return ""


def _fetch_email_for_job(job: dict) -> str:
    client = httpx.Client(
        http2=True, timeout=15, follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        return find_job_email(job, client)
    finally:
        client.close()


def enrich_jobs_with_emails(jobs: list[dict], batch_size: int = 5) -> list[dict]:
    candidates = []
    for i, job in enumerate(jobs):
        if job.get("apply_email"):
            if not is_company_email(job["apply_email"], job.get("company", "")):
                logger.info(f"  Rejected {job['apply_email']} for {job['company']}")
                job["apply_email"] = ""
            else:
                continue
        elif job.get("apply_url"):
            candidates.append((i, job))

    if not candidates:
        return jobs

    enriched = 0
    with ThreadPoolExecutor(max_workers=min(len(candidates), 8)) as pool:
        future_to_idx = {
            pool.submit(_fetch_email_for_job, job): i
            for i, job in candidates
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                email = future.result()
                if email:
                    jobs[idx]["apply_email"] = email
                    enriched += 1
            except Exception as e:
                logger.debug(f"  Email enrichment failed: {e}")

    logger.info(f"Enriched {enriched}/{len(jobs)} jobs with valid company emails")
    return jobs
