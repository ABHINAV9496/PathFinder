import time

from django.core.management.base import BaseCommand

from apps.jobs.fetchers import fetch_all_jobs
from apps.jobs.matcher import match_all_jobs
from apps.jobs.models import Application, Job
from apps.jobs.services import (
    bulk_save_jobs,
    enrich_jobs_with_emails,
    is_company_email,
    job_exists,
    save_web_apply,
    update_daily_stats,
)
from apps.jobs.warehouse import build_warehouse
from common.utils import safe_console
from config.settings import DASHBOARD_MIN_SCORE_TRACK, MATCH_THRESHOLD_APPLY


class Command(BaseCommand):
    help = "Run one fetch-match-apply cycle (skip already applied)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting fetch cycle..."))
        start = time.time()

        raw_jobs, fetch_stats = fetch_all_jobs()
        self.stdout.write(self.style.SUCCESS(f"Fetched {len(raw_jobs)} raw jobs from all sources"))

        # Report per-source breakdown
        for src, count in fetch_stats.get("by_source", {}).items():
            status_icon = "x" if count == 0 and src in fetch_stats.get("failed", []) else "+"
            self.stdout.write(f"  [{status_icon}] {src}: {count} jobs")

        if fetch_stats.get("failed"):
            self.stdout.write(self.style.WARNING(
                f"  Warning: {', '.join(fetch_stats['failed'])} returned no jobs (may be down)"
            ))

        if fetch_stats.get("dups_removed"):
            self.stdout.write(f"  {fetch_stats['dups_removed']} cross-source duplicates merged")

        new_count = sum(1 for j in raw_jobs if not job_exists(j["uid"]))
        self.stdout.write(f"  {new_count} new jobs (not seen before)")

        matched_jobs = match_all_jobs(raw_jobs)
        self.stdout.write(self.style.SUCCESS(f"Matched {len(matched_jobs)} jobs"))

        filter_stats = {}
        for j in raw_jobs:
            reason = j.get("filter_reason", "")
            if reason:
                key = reason.split("(")[0].strip()
                filter_stats[key] = filter_stats.get(key, 0) + 1
        if filter_stats:
            for reason, count in filter_stats.items():
                safe_reason = safe_console(reason)
                self.stdout.write(f"  Filtered: {safe_reason} ({count})")

        already_applied_uids = set(
            Application.objects.select_related("job")
            .values_list("job__uid", flat=True)
        )

        apply_candidates = [
            j for j in matched_jobs
            if j["match_score"] >= MATCH_THRESHOLD_APPLY and j["uid"] not in already_applied_uids
        ]
        self.stdout.write(self.style.NOTICE(
            f"  {len(apply_candidates)} NEW jobs above {MATCH_THRESHOLD_APPLY}% "
            f"(skipping {len(matched_jobs) - len(apply_candidates)} already matched/applied)"
        ))

        if apply_candidates:
            apply_candidates = enrich_jobs_with_emails(apply_candidates)

            valid_emails = sum(
                1 for j in apply_candidates
                if j.get("apply_email") and is_company_email(j["apply_email"], j.get("company", ""))
            )
            self.stdout.write(self.style.SUCCESS(f"  Found {valid_emails} valid company emails"))

        jobs_to_save = [
            j for j in matched_jobs if j["uid"] not in already_applied_uids
        ]
        bulk_save_jobs(jobs_to_save)

        matched = 0
        skipped = 0
        has_email = 0
        no_email = 0
        for job_data in matched_jobs:
            if job_data["uid"] in already_applied_uids:
                skipped += 1
                continue

            email = job_data.get("apply_email", "")
            if email and not is_company_email(email, job_data.get("company", "")):
                job_data["apply_email"] = ""
                email = ""

            if email and job_data["match_score"] >= MATCH_THRESHOLD_APPLY:
                has_email += 1
            elif job_data["match_score"] >= DASHBOARD_MIN_SCORE_TRACK:
                no_email += 1
                job_obj = Job.objects.filter(uid=job_data["uid"]).first()
                if job_obj:
                    save_web_apply(job_obj, job_data)

            matched += 1

        ignored_count = len(raw_jobs) - len(matched_jobs)
        update_daily_stats(
            fetched=len(raw_jobs),
            matched=len(matched_jobs),
            applied=0,
            ignored=ignored_count,
            failed=0,
        )

        try:
            warehouse = build_warehouse()
            if "error" in warehouse:
                message = f"  Warehouse build skipped: {warehouse['error']}"
                self.stdout.write(self.style.WARNING(message))
            else:
                rows = sum(warehouse["counts"].values())
                self.stdout.write(self.style.SUCCESS(
                    f"  Warehouse updated: {rows} rows across 6 tables"
                ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Warehouse build skipped: {e}"))

        elapsed = round(time.time() - start, 1)
        sources_count = len(fetch_stats.get("by_source", {}))
        self.stdout.write(self.style.SUCCESS(
            f"\nCycle complete in {elapsed}s\n"
            f"  Fetched:     {len(raw_jobs)} (from {sources_count} sources)\n"
            f"  Matched:     {len(matched_jobs)}\n"
            f"  Has email:   {has_email} (visible in Apply Queue)\n"
            f"  No email:    {no_email}\n"
            f"  Skipped:     {skipped} (already applied)\n"
            f"  Ignored:     {ignored_count}"
        ))
