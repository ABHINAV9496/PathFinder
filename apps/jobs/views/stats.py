from collections import Counter

from django.db.models import Count, Q, Avg
from rest_framework.response import Response

from apps.jobs.models import Job, Application, SkillLog, DailyStats, RawJob
from apps.jobs.views.base import BaseAPIView
from apps.jobs.views.list_filters import apply_job_filters, apply_application_filters
from config.settings import DASHBOARD_STATS_DAYS


class OverviewStats(BaseAPIView):
    def get(self, request):
        params = request.query_params

        total_jobs = apply_job_filters(RawJob.objects.all(), params).count()
        matched_jobs = apply_job_filters(
            Job.objects.exclude(status="ignored"), params
        )
        total_matched = matched_jobs.count()
        total_ignored = apply_job_filters(
            Job.objects.filter(status="ignored"), params
        ).count()

        apps = apply_application_filters(
            Application.objects.select_related("job"), params
        )
        total_applied = apps.filter(status="sent").count()
        total_failed = apps.filter(status="failed").count()
        total_web_apply = apps.filter(status="web_apply").count()

        recent_jobs = list(
            matched_jobs
            .values("id", "title", "company", "location", "match_score", "status", "fetched_date")
            .order_by("-fetched_date")[:10]
        )

        recent_apps = list(
            apps
            .values(
                "id", "job__id", "job__title", "job__company",
                "job__match_score", "status", "sent_at"
            )
            .order_by("-sent_at")[:10]
        )

        stats_history = list(DailyStats.objects.order_by("-date")[:DASHBOARD_STATS_DAYS])
        stats_history.reverse()

        chart_data = {
            "dates": [s.date.strftime("%b %d") for s in stats_history],
            "fetched": [s.total_fetched for s in stats_history],
            "matched": [s.total_matched for s in stats_history],
            "applied": [s.total_applied for s in stats_history],
        }

        skill_counts = list(
            SkillLog.objects
            .values("skill_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        data = {
            "total_jobs": total_jobs,
            "total_matched": total_matched,
            "total_applied": total_applied,
            "total_failed": total_failed,
            "total_ignored": total_ignored,
            "total_web_apply": total_web_apply,
            "recent_jobs": recent_jobs,
            "recent_apps": recent_apps,
            "chart": chart_data,
            "top_skills": list(skill_counts),
        }
        return Response(data)


class SkillStats(BaseAPIView):
    def get(self, request):
        skill_data = list(
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

        apps_with_2plus = (
            SkillLog.objects
            .values("application_id")
            .annotate(skills=Count("skill_name"))
            .filter(skills__gte=2)
            .values_list("application_id", flat=True)
        )

        all_combo = (
            SkillLog.objects
            .filter(application_id__in=apps_with_2plus)
            .order_by("application_id", "skill_name")
            .values_list("application_id", "skill_name")
        )

        skill_pairs = Counter()
        app_skills = {}
        for app_id, skill_name in all_combo:
            app_skills.setdefault(app_id, []).append(skill_name)
        for skills_in_app in app_skills.values():
            for i in range(len(skills_in_app)):
                for j in range(i + 1, len(skills_in_app)):
                    pair = tuple(sorted([skills_in_app[i], skills_in_app[j]]))
                    skill_pairs[pair] += 1

        top_combos = [{"skills": list(k), "count": v} for k, v in skill_pairs.most_common(10)]

        return Response({
            "skills": skill_data,
            "total_apps": total_apps,
            "top_combos": top_combos,
            "chart_labels": [s["skill_name"] for s in skill_data[:12]],
            "chart_values": [s["pct"] for s in skill_data[:12]],
        })


class CompanyStats(BaseAPIView):
    def get(self, request):
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

        return Response({"companies": company_data})


class LocationStats(BaseAPIView):
    def get(self, request):
        location_data = list(
            Job.objects
            .exclude(status="ignored")
            .values("location")
            .annotate(count=Count("id"))
            .order_by("-count")[:15]
        )

        total = sum(loc["count"] for loc in location_data)
        for loc in location_data:
            loc["pct"] = round((loc["count"] / total * 100), 1) if total > 0 else 0

        return Response({"locations": location_data, "total": total})
