import json
import logging
import threading
from collections import Counter

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q, Avg
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from apps.jobs.models import Job, Application, SkillLog, DailyStats
from config.settings import DASHBOARD_PAGE_SIZE, DASHBOARD_STATS_DAYS, DEBUG

logger = logging.getLogger(__name__)

_fetcher_running = False


def overview(request):
    total_jobs = Job.objects.count()
    total_matched = Job.objects.filter(status="matched").count()
    total_applied = Application.objects.filter(status="sent").count()
    total_failed = Application.objects.filter(status="failed").count()
    total_ignored = Job.objects.filter(status="ignored").count()
    total_web_apply = Job.objects.filter(status="web_apply").count()

    recent_jobs = (
        Job.objects
        .exclude(status="ignored")
        .select_related()
        .order_by("-fetched_date")[:10]
    )
    recent_apps = (
        Application.objects
        .select_related("job")
        .order_by("-sent_at")[:10]
    )

    stats_history = list(DailyStats.objects.order_by("-date")[:DASHBOARD_STATS_DAYS])
    stats_history.reverse()

    chart_dates = [s.date.strftime("%b %d") for s in stats_history]
    chart_fetched = [s.total_fetched for s in stats_history]
    chart_matched = [s.total_matched for s in stats_history]
    chart_applied = [s.total_applied for s in stats_history]

    skill_counts = (
        SkillLog.objects
        .values("skill_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    chart_skill_labels = [s["skill_name"] for s in skill_counts]
    chart_skill_values = [s["count"] for s in skill_counts]

    return render(request, "overview.html", {
        "total_jobs": total_jobs,
        "total_matched": total_matched,
        "total_applied": total_applied,
        "total_failed": total_failed,
        "total_ignored": total_ignored,
        "total_web_apply": total_web_apply,
        "recent_jobs": recent_jobs,
        "recent_apps": recent_apps,
        "chart_dates": json.dumps(chart_dates),
        "chart_fetched": json.dumps(chart_fetched),
        "chart_matched": json.dumps(chart_matched),
        "chart_applied": json.dumps(chart_applied),
        "chart_skill_labels": json.dumps(chart_skill_labels),
        "chart_skill_values": json.dumps(chart_skill_values),
        "show_fetcher_button": DEBUG,
    })


def job_list(request):
    status_filter = request.GET.get("status", "all")
    location_filter = request.GET.get("location", "all")
    salary_filter = request.GET.get("salary", "all")
    sort = request.GET.get("sort", "-match_score")

    jobs = Job.objects.all()

    if status_filter != "all":
        jobs = jobs.filter(status=status_filter)

    if location_filter == "kerala":
        jobs = jobs.filter(location__icontains="kerala")
    elif location_filter == "india":
        jobs = jobs.filter(
            Q(location__icontains="india") | Q(location__icontains="kerala") |
            Q(location__icontains="bangalore") | Q(location__icontains="mumbai") |
            Q(location__icontains="chennai") | Q(location__icontains="hyderabad") |
            Q(location__icontains="pune") | Q(location__icontains="delhi")
        )
    elif location_filter == "remote":
        jobs = jobs.filter(location__icontains="remote")

    if salary_filter == "has":
        jobs = jobs.filter(salary__gt=0)
    elif salary_filter == "3l":
        jobs = jobs.filter(salary__gte=300000)
    elif salary_filter == "6l":
        jobs = jobs.filter(salary__gte=600000)
    elif salary_filter == "10l":
        jobs = jobs.filter(salary__gte=1000000)

    valid_sorts = ["-match_score", "match_score", "-fetched_date", "company", "title", "-salary", "salary"]
    if sort in valid_sorts:
        jobs = jobs.order_by(sort)

    paginator = Paginator(jobs, DASHBOARD_PAGE_SIZE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    sort_labels = {
        "-match_score": "Score (High to Low)",
        "match_score": "Score (Low to High)",
        "-fetched_date": "Date (Newest First)",
        "company": "Company (A \u2192 Z)",
        "title": "Title (A \u2192 Z)",
        "-salary": "Salary (High to Low)",
        "salary": "Salary (Low to High)",
    }

    active_chips = []
    if status_filter != "all":
        active_chips.append({"label": f"Status: {status_filter.title()}", "param": "status", "value": status_filter})
    if location_filter != "all":
        active_chips.append({"label": f"Location: {location_filter.title()}", "param": "location", "value": location_filter})
    if salary_filter != "all":
        salary_labels = {"has": "Has Salary", "3l": "\u20b93L+ PA", "6l": "\u20b96L+ PA", "10l": "\u20b910L+ PA"}
        active_chips.append({"label": f"Salary: {salary_labels.get(salary_filter, salary_filter)}", "param": "salary", "value": salary_filter})

    context = {
        "jobs": page_obj,
        "page_obj": page_obj,
        "status_filter": status_filter,
        "location_filter": location_filter,
        "salary_filter": salary_filter,
        "current_sort": sort,
        "sort_label": sort_labels.get(sort, "Score (High to Low)"),
        "total_count": paginator.count,
        "active_chips": active_chips,
    }
    return render(request, "jobs.html", context)


def job_detail(request, job_id):
    job = get_object_or_404(
        Job.objects.select_related(),
        id=job_id,
    )
    application = (
        Application.objects
        .filter(job=job)
        .select_related("job")
        .first()
    )
    skill_logs = (
        SkillLog.objects
        .filter(job=job)
        .select_related("application")
    )

    return render(request, "job_detail.html", {
        "job": job,
        "application": application,
        "skill_logs": skill_logs,
    })


def application_list(request):
    apps = Application.objects.select_related("job").order_by("-sent_at")

    status_filter = request.GET.get("status", "all")
    if status_filter != "all":
        apps = apps.filter(status=status_filter)

    paginator = Paginator(apps, DASHBOARD_PAGE_SIZE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    active_chips = []
    if status_filter != "all":
        active_chips.append({"label": f"Status: {status_filter.title()}", "param": "status", "value": status_filter})

    return render(request, "applications.html", {
        "applications": page_obj,
        "page_obj": page_obj,
        "status_filter": status_filter,
        "total_count": paginator.count,
        "active_chips": active_chips,
    })


def skill_stats(request):
    skill_data = (
        SkillLog.objects
        .values("skill_name")
        .annotate(
            total=Count("id"),
            found_count=Count("id", filter=Q(found_in_job_desc=True)),
            highlighted_count=Count("id", filter=Q(highlighted_in_cover_letter=True)),
        )
        .order_by("-total")
    )

    total_apps = Application.objects.count()

    for s in skill_data:
        s["pct"] = round((s["total"] / total_apps * 100), 1) if total_apps > 0 else 0

    apps_with_2plus_skills = (
        SkillLog.objects
        .values("application_id")
        .annotate(skills=Count("skill_name"))
        .filter(skills__gte=2)
        .values_list("application_id", flat=True)
    )

    all_combo_skills = (
        SkillLog.objects
        .filter(application_id__in=apps_with_2plus_skills)
        .order_by("application_id", "skill_name")
        .values_list("application_id", "skill_name")
    )

    skill_pairs = Counter()
    app_skills = {}
    for app_id, skill_name in all_combo_skills:
        app_skills.setdefault(app_id, []).append(skill_name)
    for skills_in_app in app_skills.values():
        for i in range(len(skills_in_app)):
            for j in range(i + 1, len(skills_in_app)):
                pair = tuple(sorted([skills_in_app[i], skills_in_app[j]]))
                skill_pairs[pair] += 1

    top_combos = skill_pairs.most_common(10)

    return render(request, "skill_stats.html", {
        "skill_data": skill_data,
        "total_apps": total_apps,
        "top_combos": top_combos,
        "chart_labels": json.dumps([s["skill_name"] for s in skill_data[:12]]),
        "chart_values": json.dumps([s["pct"] for s in skill_data[:12]]),
    })


def company_stats(request):
    company_data = list(
        Job.objects
        .exclude(status="ignored")
        .values("company")
        .annotate(
            job_count=Count("id"),
            avg_score=Avg("match_score"),
            applied_count=Count("id", filter=Q(status="applied")),
        )
        .order_by("-job_count")[:20]
    )

    companies = [c["company"] for c in company_data]
    company_skills = (
        SkillLog.objects
        .filter(job__company__in=companies)
        .values("job__company", "skill_name")
        .distinct()
    )

    skills_map = {}
    for entry in company_skills:
        comp = entry["job__company"]
        skills_map.setdefault(comp, []).append(entry["skill_name"])

    for c in company_data:
        c["skills"] = skills_map.get(c["company"], [])[:6]
        c["avg_score"] = round(c["avg_score"], 1) if c["avg_score"] else 0

    return render(request, "company_stats.html", {
        "company_data": company_data,
    })


def location_stats(request):
    location_data = (
        Job.objects
        .exclude(status="ignored")
        .values("location")
        .annotate(count=Count("id"))
        .order_by("-count")[:15]
    )

    total = sum(loc["count"] for loc in location_data)
    for loc in location_data:
        loc["pct"] = round((loc["count"] / total * 100), 1) if total > 0 else 0

    return render(request, "location_stats.html", {
        "location_data": location_data,
        "total": total,
    })


def missing_emails(request):
    jobs = (
        Job.objects
        .filter(status="matched")
        .filter(apply_email="")
        .order_by("-match_score")
    )

    return render(request, "missing_emails.html", {
        "jobs": jobs,
        "total_count": jobs.count(),
    })


def web_apply_list(request):
    apps = (
        Application.objects
        .select_related("job")
        .filter(status="web_apply")
        .order_by("-sent_at")
    )
    return render(request, "web_apply.html", {
        "applications": apps,
        "total_count": apps.count(),
    })


def profile_view(request):
    from apps.jobs.profile_manager import load_profile, save_profile

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            profile = data.get("profile", {})
            required = ["name", "email", "role", "experience_years", "location"]
            for field in required:
                if not profile.get(field):
                    return JsonResponse({"error": f"Missing required field: {field}"}, status=400)

            for cat in profile.get("skills", {}):
                raw = profile["skills"][cat]
                if isinstance(raw, str):
                    profile["skills"][cat] = [s.strip() for s in raw.split(",") if s.strip()]

            projects_raw = profile.get("projects", "[]")
            if isinstance(projects_raw, str):
                try:
                    profile["projects"] = json.loads(projects_raw)
                except json.JSONDecodeError:
                    profile["projects"] = []

            looking_raw = profile.get("looking_for", "")
            if isinstance(looking_raw, str):
                profile["looking_for"] = [s.strip() for s in looking_raw.split(",") if s.strip()]

            lang_raw = profile.get("languages", "")
            if isinstance(lang_raw, str):
                profile["languages"] = [s.strip() for s in lang_raw.split(",") if s.strip()]

            for field, default in [("experience_years", 1), ("experience_min", 0), ("experience_max", 3)]:
                try:
                    profile[field] = int(profile.get(field, default))
                except (ValueError, TypeError):
                    profile[field] = default

            if save_profile(profile):
                return JsonResponse({"success": True, "message": "Profile saved successfully"})
            else:
                return JsonResponse({"error": "Failed to save profile"}, status=500)
        except Exception:
            return JsonResponse({"error": "Invalid request"}, status=400)

    profile = load_profile()
    return render(request, "profile.html", {"profile": profile})


def _run_fetcher_background():
    global _fetcher_running
    try:
        from apps.jobs.fetchers import fetch_all_jobs
        from apps.jobs.matcher import match_all_jobs
        from apps.jobs.services import (
            enrich_jobs_with_emails, is_company_email,
            save_job,
            update_daily_stats, job_exists,
        )
        from config.settings import DASHBOARD_MIN_SCORE_TRACK

        _fetcher_running = True

        raw_jobs, fetch_stats = fetch_all_jobs()
        matched_jobs = match_all_jobs(raw_jobs)

        already_applied_uids = set(
            Application.objects.select_related("job")
            .values_list("job__uid", flat=True)
        )

        email_candidates = [
            j for j in matched_jobs
            if j["uid"] not in already_applied_uids and j.get("apply_url")
        ]

        if email_candidates:
            enrich_jobs_with_emails(email_candidates)

        matched = 0
        has_email = 0
        no_email = 0

        for job_data in matched_jobs:
            if job_data["uid"] in already_applied_uids:
                continue

            save_job(job_data)

            email = job_data.get("apply_email", "")
            if email and not is_company_email(email, job_data.get("company", "")):
                job_data["apply_email"] = ""
                email = ""

            if email:
                has_email += 1
            elif job_data["match_score"] >= DASHBOARD_MIN_SCORE_TRACK:
                no_email += 1

            matched += 1

        ignored_count = len(raw_jobs) - len(matched_jobs)
        update_daily_stats(
            fetched=len(raw_jobs),
            matched=len(matched_jobs),
            applied=0,
            ignored=ignored_count,
            failed=0,
        )

        logger.info(
            "Fetcher complete: fetched=%d matched=%d has_email=%d no_email=%d",
            len(raw_jobs), len(matched_jobs), has_email, no_email,
        )
    except Exception:
        logger.exception("Fetcher failed")
    finally:
        _fetcher_running = False


@require_POST
def run_fetcher_view(request):
    if not DEBUG:
        return JsonResponse({"error": "Only available in debug mode"}, status=403)

    global _fetcher_running
    if _fetcher_running:
        return JsonResponse({"error": "Fetcher is already running"}, status=409)

    thread = threading.Thread(target=_run_fetcher_background, daemon=True)
    thread.start()

    return JsonResponse({"success": True, "message": "Fetcher started"})
