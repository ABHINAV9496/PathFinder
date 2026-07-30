import base64
import logging
import tempfile
from rest_framework import status
from apps.jobs.models import Job, Application, CredStore, JobEvent
from apps.jobs.profile_manager import load_profile
from apps.jobs.views.base import BaseAPIView

logger = logging.getLogger(__name__)


class TailoredApply(BaseAPIView):
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

        resume_pdf_b64 = request.data.get("resume_pdf_base64", "")
        if not resume_pdf_b64:
            return self.error("No tailored resume provided", status.HTTP_400_BAD_REQUEST)

        try:
            tailored_resume_bytes = base64.b64decode(resume_pdf_b64)
        except Exception:
            return self.error("Invalid resume PDF data", status.HTTP_400_BAD_REQUEST)

        profile = load_profile()
        job_dict = {
            "id": job.id, "uid": job.uid, "title": job.title,
            "company": job.company, "location": job.location,
            "description": job.description, "apply_email": job.apply_email,
            "apply_url": job.apply_url, "matched_skills": job.matched_skills,
            "match_score": job.match_score, "full_text": "",
        }

        cover_letter = request.data.get("cover_letter_text")
        if not cover_letter:
            from apps.jobs.cv_engine.cover_templates import generate_cover_letter_template
            cover_letter, template_used = generate_cover_letter_template(job_dict, profile)

        from apps.jobs.applicant import send_application
        email_user = cred.sender_email
        email_pass = cred.get_password()
        name = profile.get("name", "Resume").split()[0]
        tailored_filename = f"{name}.pdf"

        success, message = send_application(
            job_dict, cover_letter,
            email_user=email_user, email_pass=email_pass,
            resume_path=None,
            tailored_resume_bytes=tailored_resume_bytes,
            tailored_filename=tailored_filename,
        )

        old_status = job.status
        if success:
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
        save_application(job, {
            "success": success,
            "message": message,
            "cover_letter": cover_letter,
            "email_subject": f"Application for {job.title} - {profile.get('name', '')}",
        })

        return self.success({
            "success": success,
            "message": message,
            "job_id": job.id,
            "status": job.status,
        })
