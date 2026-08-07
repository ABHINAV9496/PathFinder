import logging

from django.shortcuts import get_object_or_404
from rest_framework import status

from apps.jobs.models import Application, Job
from apps.jobs.profile_manager import load_profile
from apps.jobs.services.cover_letter_client import (
    CoverLetterEngineUnavailableError,
    generate_cover_letter,
)
from apps.jobs.views.base import BaseAPIView

logger = logging.getLogger(__name__)


class GenerateTemplateCoverLetter(BaseAPIView):
    def post(self, request, job_id):
        job_obj = get_object_or_404(Job.objects.select_related(), id=job_id)

        job_dict = {
            "id": job_obj.id,
            "company": job_obj.company,
            "title": job_obj.title,
            "location": job_obj.location or "",
            "description": job_obj.description or "",
            "matched_skills": job_obj.matched_skills or [],
            "skill_gaps": job_obj.skill_gaps or [],
        }

        profile = load_profile()

        try:
            result = generate_cover_letter(job_dict, profile, mode="template")
            cover_letter = result.get("cover_letter", "")
            template_used = result.get("template_used", "deterministic")
        except CoverLetterEngineUnavailableError:
            from apps.jobs.cv_engine.cover_templates import generate_cover_letter_template
            cover_letter, template_used = generate_cover_letter_template(job_dict)
            logger.warning(
                "Cover letter engine down for job %d; used legacy template fallback",
                job_obj.id,
            )

        if not cover_letter:
            return self.error(
                "Could not generate a cover letter. The cover letter service is unavailable.",
                status.HTTP_502_BAD_GATEWAY,
            )

        existing_app = Application.objects.filter(job=job_obj).first()
        if existing_app:
            existing_app.cover_letter_text = cover_letter
            existing_app.save(update_fields=["cover_letter_text"])

        return self.success({
            "cover_letter": cover_letter,
            "template": template_used,
        })
