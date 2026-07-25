import logging
import time
import threading

from django.db.models import Exists, OuterRef, Value
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view

from apps.jobs.models import Application, Job, JobEvent, CredStore
from apps.jobs.views.base import BaseAPIView
from apps.jobs.serializers.job import JobSerializer

logger = logging.getLogger(__name__)

_apply_progress = {"running": False, "total": 0, "done": 0, "succeeded": 0, "failed": 0, "current": ""}


class ApplyQueueList(BaseAPIView):
    def get(self, request):
        failed_app = Application.objects.filter(job=OuterRef("pk"), status="failed")
        jobs = (
            Job.objects.exclude(status="ignored")
            .annotate(has_failed_app=Exists(failed_app))
            .exclude(has_failed_app=False, application__isnull=False)
            .filter(apply_email__isnull=False)
            .exclude(apply_email="")
            .order_by("-match_score")
        )

        page, paginator = self.paginate(jobs, request)
        serializer = JobSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ApplyToJob(BaseAPIView):
    def post(self, request, job_id):
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            return self.error("Job not found", status.HTTP_404_NOT_FOUND)

        existing = Application.objects.filter(job=job).first()
        if existing and existing.status != "failed":
            return self.error("Already applied to this job", status.HTTP_409_CONFLICT)

        if not job.apply_email:
            return self.error("No company email found for this job", status.HTTP_400_BAD_REQUEST)

        cred = CredStore.load()
        if not cred.has_credentials:
            return self.error("Configure sender email and password in Profile > Security first", status.HTTP_400_BAD_REQUEST)

        from apps.jobs.applicant import apply_to_job as do_apply

        job_dict = {
            "id": job.id, "uid": job.uid, "title": job.title,
            "company": job.company, "location": job.location,
            "description": job.description, "apply_email": job.apply_email,
            "apply_url": job.apply_url, "matched_skills": job.matched_skills,
            "match_score": job.match_score, "full_text": "",
        }

        email_user = cred.sender_email
        email_pass = cred.get_password()
        resume_path = cred.resume_file.path if cred.resume_file else None

        result = do_apply(job_dict, email_user=email_user, email_pass=email_pass, resume_path=resume_path)

        old_status = job.status
        if result["success"]:
            job.status = "applied"
        else:
            job.status = "failed"
        job.save()

        JobEvent.objects.create(
            job=job, event_type="applied",
            old_status=old_status, new_status=job.status,
            match_score=job.match_score,
        )

        from apps.jobs.services import save_application
        save_application(job, result)

        return self.success({
            "success": result["success"],
            "message": result["message"],
            "job_id": job.id,
            "status": job.status,
        })


def _batch_apply_thread(job_ids: list[int]):
    global _apply_progress
    _apply_progress = {"running": True, "total": len(job_ids), "done": 0, "succeeded": 0, "failed": 0, "current": ""}

    cred = CredStore.load()
    email_user = cred.sender_email
    email_pass = cred.get_password()
    resume_path = cred.resume_file.path if cred.resume_file else None

    from apps.jobs.applicant import apply_to_job as do_apply
    from apps.jobs.services import save_application

    for job_id in job_ids:
        try:
            job = Job.objects.get(pk=job_id)
            _apply_progress["current"] = f"{job.title} at {job.company}"

            existing = Application.objects.filter(job=job).first()
            if existing and existing.status != "failed":
                _apply_progress["done"] += 1
                continue

            if not job.apply_email:
                _apply_progress["done"] += 1
                _apply_progress["failed"] += 1
                continue

            job_dict = {
                "id": job.id, "uid": job.uid, "title": job.title,
                "company": job.company, "location": job.location,
                "description": job.description, "apply_email": job.apply_email,
                "apply_url": job.apply_url, "matched_skills": job.matched_skills,
                "match_score": job.match_score, "full_text": "",
            }

            result = do_apply(job_dict, email_user=email_user, email_pass=email_pass, resume_path=resume_path)

            old_status = job.status
            if result["success"]:
                job.status = "applied"
                _apply_progress["succeeded"] += 1
            else:
                job.status = "failed"
                _apply_progress["failed"] += 1
            job.save()

            JobEvent.objects.create(
                job=job, event_type="applied",
                old_status=old_status, new_status=job.status,
                match_score=job.match_score,
            )
            save_application(job, result)

        except Exception as e:
            logger.exception(f"Failed to apply to job {job_id}")
            _apply_progress["failed"] += 1

        _apply_progress["done"] += 1

        if _apply_progress["done"] < _apply_progress["total"]:
            time.sleep(3)

    _apply_progress["running"] = False
    _apply_progress["current"] = ""


class BatchApply(BaseAPIView):
    def post(self, request):
        if _apply_progress["running"]:
            return self.error("Batch apply is already in progress", status.HTTP_409_CONFLICT)

        job_ids = request.data.get("job_ids", [])
        if not job_ids or not isinstance(job_ids, list):
            return self.error("Provide job_ids as a list of integers", status.HTTP_400_BAD_REQUEST)

        cred = CredStore.load()
        if not cred.has_credentials:
            return self.error("Configure sender email and password in Profile > Security first", status.HTTP_400_BAD_REQUEST)

        valid_ids = list(
            Job.objects.filter(id__in=job_ids, apply_email__isnull=False)
            .exclude(apply_email="")
            .exclude(status="ignored")
            .values_list("id", flat=True)
        )

        already_applied = set(
            Application.objects.filter(job_id__in=job_ids).values_list("job_id", flat=True)
        )
        valid_ids = [jid for jid in valid_ids if jid not in already_applied]

        if not valid_ids:
            return self.error("No eligible jobs to apply to", status.HTTP_400_BAD_REQUEST)

        thread = threading.Thread(target=_batch_apply_thread, args=(valid_ids,), daemon=True)
        thread.start()

        return self.success({
            "message": f"Starting batch apply for {len(valid_ids)} jobs",
            "total": len(valid_ids),
        })


@api_view(["GET"])
def apply_progress(request):
    return JsonResponse(dict(_apply_progress))
